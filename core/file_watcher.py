# core/file_watcher.py
import os
import time
import asyncio
from loguru import logger
from .plugin_manager import plugin_manager, PLUGIN_DIR
from typing import Dict, List, Optional, Tuple, Set

# 监听的文件后缀
WATCH_EXTENSIONS = {".py"}
# 文件修改时间缓存 {文件路径: 最后修改时间}
FILE_MTIME_CACHE = {}
# 异步锁（防止同一插件多次触发重载）
RELOAD_LOCK = asyncio.Lock()
# 防抖延迟（秒）
DEBOUNCE_DELAY = 0.5
# 已加载插件标记（避免启动时重复触发）
PLUGIN_LOADED_FLAG = False


class PluginFileWatcher:
    """插件文件监视器：兼容多文件插件包的修改检测"""

    def __init__(self, watch_dir: str = PLUGIN_DIR, interval: float = 1.0):
        self.watch_dir = watch_dir
        self.interval = interval  # 检查文件变化的间隔（秒）
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.debounce_timers = {}  # {插件名: 定时器}

    def _get_watched_files(self):
        """获取所有需要监听的插件文件路径（包含所有子文件）"""
        watched_files = []
        if not os.path.exists(self.watch_dir):
            return watched_files

        for root, _, files in os.walk(self.watch_dir):
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in WATCH_EXTENSIONS and file not in {"__pycache__"}:
                    file_path = os.path.join(root, file)
                    watched_files.append(file_path)
                    # 初始化缓存
                    if file_path not in FILE_MTIME_CACHE:
                        try:
                            FILE_MTIME_CACHE[file_path] = os.path.getmtime(file_path)
                        except Exception as e:
                            logger.warning(f"文件监视器：初始化缓存失败 {file_path} -> {str(e)}")
        return watched_files

    async def _check_file_changes(self):
        """检查文件变化并处理（兼容子文件修改）"""
        global PLUGIN_LOADED_FLAG
        # 等待插件加载完成后再检测
        if not PLUGIN_LOADED_FLAG:
            return

        watched_files = self._get_watched_files()

        # 检查文件变化
        for file_path in watched_files:
            try:
                # 跳过不存在的文件
                if not os.path.exists(file_path):
                    if file_path in FILE_MTIME_CACHE:
                        del FILE_MTIME_CACHE[file_path]
                    continue

                # 获取当前修改时间
                current_mtime = os.path.getmtime(file_path)
                # 对比缓存（仅当文件真的修改时触发）
                if FILE_MTIME_CACHE.get(file_path) != current_mtime:
                    FILE_MTIME_CACHE[file_path] = current_mtime
                    # 提取插件名（如 dic/a.py → dic）
                    plugin_name = plugin_manager._get_plugin_name_by_file(file_path)
                    if plugin_name:
                        logger.debug(f"文件监视器：检测到插件文件修改 -> {file_path} (所属插件：{plugin_name})")
                        await self._debounce_reload(plugin_name)
            except Exception as e:
                logger.error(f"文件监视器：检查文件失败 {file_path} -> {str(e)}")

        # 清理已删除文件的缓存
        for file_path in list(FILE_MTIME_CACHE.keys()):
            if not os.path.exists(file_path):
                del FILE_MTIME_CACHE[file_path]

    async def _debounce_reload(self, plugin_name):
        """防抖处理：延迟重载插件（避免重复触发）"""
        # 取消之前的定时器
        if plugin_name in self.debounce_timers:
            self.debounce_timers[plugin_name].cancel()

        # 创建新定时器
        async def reload_task():
            async with RELOAD_LOCK:
                logger.info(f"文件监视器：开始重载插件 -> {plugin_name}（因子文件修改触发）")
                await plugin_manager.reload_plugin(plugin_name)
                logger.info(f"文件监视器：插件重载完成 -> {plugin_name}")

        timer = asyncio.get_event_loop().call_later(
            DEBOUNCE_DELAY,
            lambda: asyncio.create_task(reload_task())
        )
        self.debounce_timers[plugin_name] = timer

    async def _watch_loop(self):
        """监控主循环"""
        while self.is_running:
            await self._check_file_changes()
            await asyncio.sleep(self.interval)

    async def start(self):
        """启动文件监视器"""
        if self.is_running:
            logger.warning("文件监视器：已处于运行状态")
            return

        # 初始化文件缓存
        self._get_watched_files()

        self.is_running = True
        self.task = asyncio.create_task(self._watch_loop())
        logger.info(f"文件监视器：启动（监听目录：{self.watch_dir}，检查间隔：{self.interval}秒）")

        # 标记插件加载完成（延迟1秒避免启动时触发）
        await asyncio.sleep(1)
        global PLUGIN_LOADED_FLAG
        PLUGIN_LOADED_FLAG = True

    async def stop(self):
        """停止文件监视器"""
        if not self.is_running:
            return

        self.is_running = False
        # 取消所有定时器
        for timer in self.debounce_timers.values():
            timer.cancel()
        # 取消监控任务
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("文件监视器：已停止")


# 全局文件监视器实例
file_watcher = PluginFileWatcher(interval=1.0)