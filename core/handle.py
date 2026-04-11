import re
import inspect
from loguru import logger
from core.api import Api
from core.message import Message

COMMANDS = []
REGEX_COMMANDS = []
GLOBAL_HANDLER = None

PLUGIN_HANDLERS = {}


def clear_plugin_handlers(plugin_name):
    if plugin_name not in PLUGIN_HANDLERS:
        return
    for handler in PLUGIN_HANDLERS[plugin_name]:
        if handler in COMMANDS:
            COMMANDS.remove(handler)
        if handler in REGEX_COMMANDS:
            REGEX_COMMANDS.remove(handler)
    del PLUGIN_HANDLERS[plugin_name]
    logger.info(f"已清理插件 {plugin_name} 的所有命令")


class CommandArg:
    def __init__(self):
        self.message = None
        self.handler = None

    def _bind(self, message: Message, handler):
        self.message = message
        self.handler = handler

    def group(self, index=0):
        return self.handler.group(index) if self.handler._match else None

    def extract_plain_text(self):
        return self.message.extract_plain_text()

    def __getattr__(self, name):
        return getattr(self.message, name)


class CommandHandler(Api):
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.func = None
        self.args = CommandArg()
        self._match = None
        self.plugin_name = None

    def handle(self):
        def decorator(func):
            self.func = func
            # 关键修复：列表命令必须在这里同步绑定函数
            for cmd_handler in COMMANDS:
                if hasattr(cmd_handler, "_parent") and cmd_handler._parent == self:
                    cmd_handler.func = func
            return func
        return decorator

    async def invoke(self, message: Message):
        if not self.func:
            return
        try:
            self.args._bind(message, self)
            sig = inspect.signature(self.func)
            if sig.parameters:
                await self.func(self.args)
            else:
                await self.func()
        except Exception as e:
            logger.error(f"命令执行错误: {e}")


def on_command(command=None):
    handler = CommandHandler(command)

    try:
        for frame_info in inspect.stack():
            file_path = frame_info.filename
            from core.plugin_manager import plugin_manager
            plugin_name = plugin_manager._get_plugin_name_by_file(file_path)
            if plugin_name:
                handler.plugin_name = plugin_name
                break
    except:
        pass

    if command is None:
        global GLOBAL_HANDLER
        GLOBAL_HANDLER = handler
        return handler

    # ===================== 列表多命令核心修复 =====================
    if isinstance(command, list):
        for cmd in command:
            h = CommandHandler(cmd)
            h._parent = handler  # 标记父命令
            h.plugin_name = handler.plugin_name
            COMMANDS.append(h)
            if h.plugin_name:
                PLUGIN_HANDLERS.setdefault(h.plugin_name, []).append(h)
        return handler

    # 普通命令
    if isinstance(command, str):
        if any(c in command for c in r'()[]|+*$.^?\''):
            REGEX_COMMANDS.append(handler)
        else:
            COMMANDS.append(handler)

    elif isinstance(command, re.Pattern):
        REGEX_COMMANDS.append(handler)
    else:
        COMMANDS.append(handler)

    if handler.plugin_name:
        PLUGIN_HANDLERS.setdefault(handler.plugin_name, []).append(handler)

    return handler


async def dispatch_command(message: Message):
    try:
        if GLOBAL_HANDLER:
            await GLOBAL_HANDLER.invoke(message)

        text = message.extract_plain_text().strip()
        if not text:
            return
        match_text = text.lstrip('/').strip()

        for h in COMMANDS:
            if str(h.command).strip() == match_text:
                await h.invoke(message)
                return

        for h in REGEX_COMMANDS:
            try:
                pattern = re.compile(h.command)
                match = pattern.match(text)
                if match:
                    h._match = match
                    await h.invoke(message)
                    return
            except:
                continue

    except Exception as e:
        logger.error(f"分发错误: {e}")
