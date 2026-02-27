from message import message
from api import Api
import re
import uuid
import json
from typing import List, Union, Optional, Callable
from loguru import logger

# ========== 全局变量 ==========
PROCESSED_MSG_IDS = set()  # 全局去重，避免重复触发
MAX_PROCESSED_CACHE = 1000  # 缓存上限，防止内存溢出

# 处理器注册表：按类型分类
HANDLERS = {
    "global": [],  # 全局监听（on_command() 不传参）
    "command": {},  # 普通文本命令（如 on_command("你好")）
    "regex": []  # 正则匹配（如 on_command(r"^测.*试$")）
}

# 卡片消息专属标识（用于生成唯一ID）
ARK_MSG_PREFIX = "ark_"


# ========== 工具函数：判断是否为正则表达式 ==========
def is_regex_pattern(pattern: str) -> bool:
    """简单判断字符串是否为正则表达式（通过正则元字符+编译验证）"""
    if not pattern:
        return False
    # 正则元字符列表：包含这些字符则判定为正则
    regex_meta_chars = r'^$.*+?[](){}|\\'
    if not any(char in pattern for char in regex_meta_chars):
        return False
    # 尝试编译，排除无效正则
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


# ========== 核心处理器类（整合所有类型） ==========
class CommandHandler(Api):
    def __init__(self, pattern: Optional[Union[str, List[str]]] = None):
        """
        统一处理器：
        - 不传参 (pattern=None) → 全局监听（所有消息：文本/卡片/图片等）
        - 传普通字符串 → 普通命令
        - 传正则字符串 → 正则匹配
        """
        super().__init__()
        self.pattern = pattern
        self.handler_type = "global"  # 默认全局监听
        self.compiled_regex = None
        self.commands = []

        # 传参时，判断是普通命令还是正则
        if pattern is not None:
            # 统一转为列表处理
            if isinstance(pattern, str):
                self.commands = [pattern.strip()]
            elif isinstance(pattern, list):
                self.commands = [c.strip() for c in pattern if c.strip()]

            # 判断是否为正则
            if self.commands and is_regex_pattern(self.commands[0]):
                self.handler_type = "regex"
                self.compiled_regex = re.compile(self.commands[0])
            else:
                self.handler_type = "command"

        self.func = None

    def box(self):
        def decorator(func):
            self.func = func
            wrapped_func = self._wrap_handler(func)

            # 注册到对应处理器类型
            if self.handler_type == "global":
                HANDLERS["global"].append(wrapped_func)
            elif self.handler_type == "command":
                for cmd in self.commands:
                    HANDLERS["command"][cmd] = wrapped_func
                    HANDLERS["command"][f"/{cmd}"] = wrapped_func  # 兼容 /命令 格式
            elif self.handler_type == "regex":
                HANDLERS["regex"].append((self.compiled_regex, wrapped_func))

            return func

        return decorator

    def _wrap_handler(self, func):
        async def wrapper(text="", match=None, ark_data=None):
            try:
                # 构造上下文：包含所有消息类型的关键信息
                ctx = {
                    "group_id": message.group_id,  # 群ID
                    "message_id": getattr(message, "message_id", str(uuid.uuid4())),  # 消息ID
                    "raw_message": message.message,  # 原始消息数据
                    "text": text,  # 文本内容（文本消息）
                    "match": match,  # 正则匹配结果（正则消息）
                    "ark_data": ark_data,  # 卡片数据（卡片消息）
                    "msg_type": self._get_msg_type(text, ark_data)  # 消息类型标识
                }
                await func(ctx)
            except Exception as e:
                logger.error(f"处理器执行出错: {e}")
                # 异常回复（保证机器人不崩溃）
                await self.send_msg(
                    group_id=message.group_id,
                    text=f"处理消息时出错啦 😥\n错误详情: {str(e)[:200]}"
                )

        return wrapper

    def _get_msg_type(self, text: str, ark_data: dict) -> str:
        """判断消息类型：text/ark/other"""
        if ark_data:
            return "ark"
        elif text:
            return "text"
        else:
            return "other"  # 图片、语音、表情等


# ========== 统一注册接口（极简版） ==========
def on_command(pattern: Optional[Union[str, List[str]]] = None):
    """
    极简监听接口：
    ✅ on_command() → 监听所有消息（文本/卡片/图片/语音等）
    ✅ on_command("你好") → 监听普通文本命令
    ✅ on_command(r"^测.*试$") → 监听正则匹配的文本消息
    """
    return CommandHandler(pattern=pattern)


# ========== 消息处理入口（核心逻辑） ==========
async def process_message():
    global PROCESSED_MSG_IDS

    # 1. 解析消息内容（提取文本/卡片/其他类型）
    msg_text = ""  # 文本内容
    ark_data = None  # 卡片数据（只取第一个卡片，避免多卡片重复）
    raw_segs = message.message  # 原始消息段

    for seg in raw_segs:
        # 解析文本消息
        if seg["type"] == "text" and seg["data"].get("text", "").strip():
            msg_text = seg["data"]["text"].strip()
        # 解析卡片消息（JSON类型）
        elif seg["type"] == "json" and seg["data"].get("data") and not ark_data:
            try:
                ark_data = json.loads(seg["data"]["data"])
            except json.JSONDecodeError as e:
                logger.warning(f"卡片消息JSON解析失败: {e}")
                ark_data = None

    # 2. 生成唯一消息ID（核心去重逻辑）
    final_msg_id = None
    # 优先用原生message_id
    if hasattr(message, "message_id") and message.message_id:
        final_msg_id = message.message_id
    # 卡片消息：用appid+msg_seq+uin生成唯一ID
    elif ark_data:
        extra = ark_data.get("extra", {})
        final_msg_id = f"{ARK_MSG_PREFIX}_{extra.get('appid', '')}_{extra.get('msg_seq', '')}_{extra.get('uin', '')}"
    # 文本消息：用群ID+文本+随机串生成
    elif msg_text:
        final_msg_id = f"text_{message.group_id}_{msg_text[:50]}_{str(uuid.uuid4())[:8]}"
    # 其他消息（图片/语音）：纯随机ID
    else:
        final_msg_id = f"other_{message.group_id}_{str(uuid.uuid4())}"

    # 3. 去重判断：已处理过则直接返回
    if final_msg_id in PROCESSED_MSG_IDS:
        logger.debug(f"消息已处理，跳过：{final_msg_id}")
        return
    PROCESSED_MSG_IDS.add(final_msg_id)

    # 4. 清理缓存（防止内存溢出）
    if len(PROCESSED_MSG_IDS) > MAX_PROCESSED_CACHE:
        # 保留后50%的缓存，避免频繁清理
        PROCESSED_MSG_IDS = set(list(PROCESSED_MSG_IDS)[-MAX_PROCESSED_CACHE // 2:])
        logger.debug(f"清理消息缓存，当前缓存量：{len(PROCESSED_MSG_IDS)}")

    # 5. 消息匹配逻辑（优先级：精准匹配 > 全局监听）
    # 5.1 优先匹配普通命令（文本消息）
    if msg_text and msg_text in HANDLERS["command"]:
        await HANDLERS["command"][msg_text](text=msg_text)
        return

    # 5.2 匹配正则命令（文本消息）
    if msg_text:
        for compiled_pattern, handler in HANDLERS["regex"]:
            match = compiled_pattern.fullmatch(msg_text)
            if match:
                await handler(text=msg_text, match=match)
                return

    # 5.3 全局监听（所有类型：卡片/文本/其他）
    if HANDLERS["global"]:
        for global_handler in HANDLERS["global"]:
            await global_handler(text=msg_text, ark_data=ark_data)
            # 全局监听默认只执行第一个处理器（避免多处理器重复回复）
            # 如需执行所有全局处理器，注释下面的return
            return


# ========== 辅助函数：清理缓存 ==========
def clear_processed_cache():
    """清空已处理消息缓存（手动调用）"""
    global PROCESSED_MSG_IDS
    PROCESSED_MSG_IDS.clear()
    logger.info("已清空消息去重缓存")