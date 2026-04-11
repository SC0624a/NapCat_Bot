# plugin_manager.py 完整修正版（无循环导入）
import os
import sys
import importlib
import asyncio
from loguru import logger
from typing import Dict, List, Optional, Tuple, Set

# 获取项目根目录（core的上级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 插件根目录（项目根目录下的plugins）
PLUGIN_DIR = os.path.join(PROJECT_ROOT, "plugins")

# 已加载插件缓存 {插件包名: (模块对象, 插件目录路径, 子文件列表)}
LOADED_PLUGINS: Dict[str, Tuple[importlib.ModuleType, str, Set[str]]] = {}
# 插件模块黑名单
BLACKLIST = {"__pycache__", ".DS_Store", "README.md"}


class PluginManager:
    """插件管理器：兼容多文件插件包的加载/重载"""

    @staticmethod
    def _get_plugin_packages() -> List[Tuple[str, str]]:
        """获取所有合法插件包（每个子目录为一个插件）
        返回：[(插件包名, 插件目录路径)]
        """
        plugin_packages = []
        if not os.path.exists(PLUGIN_DIR):
            os.makedirs(PLUGIN_DIR)
            logger.info(f"插件管理器：创建插件目录 -> {PLUGIN_DIR}")
            return plugin_packages

        # 遍历一级子目录作为插件包
        for item in os.listdir(PLUGIN_DIR):
            item_path = os.path.join(PLUGIN_DIR, item)
            if os.path.isdir(item_path) and item not in BLACKLIST:
                plugin_packages.append((item, item_path))

        logger.debug(f"插件管理器：扫描到 {len(plugin_packages)} 个插件包 -> {[p[0] for p in plugin_packages]}")
        return plugin_packages

    @staticmethod
    def _get_plugin_name_by_file(file_path: str) -> Optional[str]:
        """从文件路径提取插件包名（如 dic/a.py → dic）"""
        try:
            abs_path = os.path.abspath(file_path)
            if not abs_path.startswith(PLUGIN_DIR):
                return None

            rel_path = os.path.relpath(abs_path, PLUGIN_DIR)
            parts = rel_path.split(os.sep)
            plugin_name = parts[0]

            plugin_path = os.path.join(PLUGIN_DIR, plugin_name)
            if os.path.isdir(plugin_path):
                return plugin_name
            return None
        except Exception as e:
            logger.error(f"插件管理器：解析插件名失败 {file_path} -> {str(e)}")
            return None

    @staticmethod
    def _validate_plugin_package(plugin_path: str) -> bool:
        """验证插件包是否合法（至少包含 __init__.py）"""
        init_file = os.path.join(plugin_path, "__init__.py")
        if not os.path.exists(init_file):
            logger.warning(f"插件管理器：插件包无 __init__.py -> {plugin_path}")
            return False
        return True

    @staticmethod
    def _get_plugin_all_files(plugin_path: str) -> Set[str]:
        """获取插件包内所有 .py 文件路径"""
        py_files = set()
        for root, _, files in os.walk(plugin_path):
            for file in files:
                if file.endswith(".py") and file not in BLACKLIST:
                    py_files.add(os.path.abspath(os.path.join(root, file)))
        return py_files

    @classmethod
    async def load_all_plugins(cls) -> Dict[str, importlib.ModuleType]:
        plugin_packages = cls._get_plugin_packages()
        if not plugin_packages:
            logger.info("插件管理器：无可用插件包")
            return {}

        loaded_modules = {}
        for plugin_name, plugin_path in plugin_packages:
            if not cls._validate_plugin_package(plugin_path):
                continue
            module = await cls.load_plugin(plugin_name)
            if module:
                loaded_modules[plugin_name] = module

        logger.info(
            f"插件管理器：插件加载完成 | 总数：{len(plugin_packages)} | "
            f"成功：{len(loaded_modules)} | 失败：{len(plugin_packages) - len(loaded_modules)}"
        )
        return loaded_modules

    @classmethod
    async def load_plugin(cls, plugin_name: str) -> Optional[importlib.ModuleType]:
        try:
            plugin_path = os.path.join(PLUGIN_DIR, plugin_name)
            if not os.path.isdir(plugin_path):
                logger.error(f"插件管理器：加载失败 -> 插件目录不存在 {plugin_path}")
                return None

            if not cls._validate_plugin_package(plugin_path):
                return None

            if plugin_name in LOADED_PLUGINS:
                await cls.unload_plugin(plugin_name)

            if PROJECT_ROOT not in sys.path:
                sys.path.insert(0, PROJECT_ROOT)

            module = importlib.import_module(f"plugins.{plugin_name}")
            plugin_files = cls._get_plugin_all_files(plugin_path)
            LOADED_PLUGINS[plugin_name] = (module, plugin_path, plugin_files)

            logger.success(f"插件管理器：加载插件成功 | 插件名：{plugin_name}")
            return module
        except Exception as e:
            logger.error(f"插件管理器：加载插件失败 {plugin_name} -> {e}", exc_info=True)
            return None

    @classmethod
    async def unload_plugin(cls, plugin_name: str) -> bool:
        try:
            if plugin_name not in LOADED_PLUGINS:
                return False

            module, plugin_path, _ = LOADED_PLUGINS.pop(plugin_name)

            # 清理模块
            modules_to_delete = []
            plugin_module_prefix = f"plugins.{plugin_name}"
            for mod_name in sys.modules:
                if mod_name == plugin_module_prefix or mod_name.startswith(f"{plugin_module_prefix}."):
                    modules_to_delete.append(mod_name)

            for mod_name in modules_to_delete:
                try:
                    del sys.modules[mod_name]
                except:
                    pass

            # ✅ 关键：卸载插件时清空该插件的所有命令
            from core.handle import clear_plugin_handlers
            clear_plugin_handlers(plugin_name)

            logger.info(f"插件管理器：卸载插件成功 | 插件名：{plugin_name}")
            return True
        except Exception as e:
            logger.error(f"插件管理器：卸载失败 {plugin_name} -> {e}", exc_info=True)
            return False

    @classmethod
    async def reload_plugin(cls, plugin_name: str) -> Optional[importlib.ModuleType]:
        try:
            plugin_path = os.path.join(PLUGIN_DIR, plugin_name)
            if not os.path.isdir(plugin_path):
                return None

            logger.info(f"插件管理器：开始重载插件 -> {plugin_name}")
            await cls.unload_plugin(plugin_name)
            module = await cls.load_plugin(plugin_name)

            if module:
                logger.success(f"插件管理器：重载插件成功 -> {plugin_name}")
            return module
        except Exception as e:
            logger.error(f"插件管理器：重载失败 {plugin_name} -> {e}", exc_info=True)
            return None

    @classmethod
    async def reload_all_plugins(cls) -> Dict[str, importlib.ModuleType]:
        logger.info("插件管理器：开始重载所有插件")
        loaded_plugins = list(LOADED_PLUGINS.keys())
        reloaded_modules = {}

        for plugin_name in loaded_plugins:
            module = await cls.reload_plugin(plugin_name)
            if module:
                reloaded_modules[plugin_name] = module

        return reloaded_modules


plugin_manager = PluginManager()