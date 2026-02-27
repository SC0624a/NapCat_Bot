import json
import requests
from typing import List, Dict, Optional
from loguru import logger
import asyncio  # 用于异步框架中调用同步代码
import os

class VolcArkMultiChat:
    """
    火山方舟豆包API多轮对话封装类（requests同步版）
    """

    def __init__(
            self,
            api_key: str,
            model_id: str = "doubao-1-5-pro-32k-250115",
            api_url: str = "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            max_history_rounds: int = 10,
            temperature: float = 0.7,
            max_tokens: int = 2000
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.api_url = api_url
        self.max_history_rounds = max_history_rounds
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 初始化对话上下文（包含system指令）
        self.context_messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": "你是一个专业的AI助手，回答简洁、准确，保持对话的连贯性。"
            }
        ]

    def _trim_context(self) -> None:
        """
        修剪上下文，只保留最近max_history_rounds轮对话（原逻辑不变）
        """
        if len(self.context_messages) <= 1:
            return
        history = self.context_messages[1:]
        start_idx = max(0, len(history) - 2 * self.max_history_rounds)
        self.context_messages = [self.context_messages[0]] + history[start_idx:]

    def chat_sync(self, user_input: str) -> Optional[str]:
        """
        同步版对话调用（核心：用requests，和你最初能运行的代码一致）
        :param user_input: 用户本轮输入
        :return: 模型回复内容（失败返回None）
        """
        # 1. 添加用户输入到上下文
        self.context_messages.append({
            "role": "user",
            "content": user_input
        })

        # 2. 修剪上下文
        self._trim_context()

        # 3. 构造请求参数（原requests逻辑）
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        request_data = {
            "model": self.model_id,
            "messages": self.context_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }

        # 4. 同步调用requests（核心修改：替换aiohttp为requests）
        try:
            response = requests.post(
                url=self.api_url,
                headers=headers,
                json=request_data,  # requests直接支持json参数，无需dumps
                timeout=30,
                #verify=False  # 禁用SSL验证，和你最初的配置一致
            )
            response.raise_for_status()
            result = response.json()

            # 5. 解析回复（原逻辑不变）
            if "choices" in result and len(result["choices"]) > 0:
                assistant_reply = result["choices"][0]["message"]["content"]
                self.context_messages.append({
                    "role": "assistant",
                    "content": assistant_reply
                })
                # 打印token用量
                usage = result.get("usage", {})
                logger.info(
                    f"豆包：Token用量：输入{usage.get('prompt_tokens', 0)} | 输出{usage.get('completion_tokens', 0)} | 总计{usage.get('total_tokens', 0)}")
                return assistant_reply
            else:
                logger.error(f"API返回无有效结果：{result}")
                self.context_messages.pop()
                return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP错误：{e.response.status_code} - {e.response.text}")
            self.context_messages.pop()
            return None
        except requests.exceptions.Timeout:
            logger.error("请求超时，请检查网络或API服务状态")
            self.context_messages.pop()
            return None
        except Exception as e:
            logger.error(f"调用异常：{str(e)}")
            self.context_messages.pop()
            return None

    async def chat(self, user_input: str) -> Optional[str]:
        """
        异步封装版：在异步框架中调用同步的chat_sync方法（关键适配机器人）
        """
        # 用asyncio执行同步函数，避免阻塞异步事件循环
        loop = asyncio.get_running_loop()
        # 把同步的chat_sync放到线程池中执行
        reply = await loop.run_in_executor(
            None,  # 使用默认线程池
            lambda: self.chat_sync(user_input)  # 调用同步方法
        )
        return reply

    def clear_context(self) -> None:
        """
        清空对话上下文（原逻辑不变）
        """
        self.context_messages = [self.context_messages[0]]

    def get_context(self) -> List[Dict[str, str]]:
        """
        获取当前对话上下文（原逻辑不变）
        """
        return self.context_messages.copy()

# ====================== 多群隔离的对话管理器（适配同步版） ======================
class ChatManager:
    """
    对话管理器：按群号/QQ号隔离不同的对话上下文
    """
    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id
        self.chat_instances: Dict[str, VolcArkMultiChat] = {}

    async def get_chat_reply(self, session_id: str, user_input: str) -> Optional[str]:
        """
        异步获取回复（适配机器人框架）
        """
        if session_id not in self.chat_instances:
            self.chat_instances[session_id] = VolcArkMultiChat(
                api_key=self.api_key,
                model_id=self.model_id
            )
        # 调用异步封装的chat方法
        return await self.chat_instances[session_id].chat(user_input)

    def clear_session_context(self, session_id: str) -> bool:
        """
        清空指定会话的上下文
        """
        if session_id in self.chat_instances:
            self.chat_instances[session_id].clear_context()
            return True
        return False

# ====================== 全局实例（支持环境变量配置） ======================
YOUR_ARK_API_KEY = os.getenv("ARK_API_KEY", "自行获取")
YOUR_MODEL_ID = os.getenv("ARK_MODEL_ID", "doubao-seed-1-8-251228")

chat_manager = ChatManager(
    api_key=YOUR_ARK_API_KEY,
    model_id=YOUR_MODEL_ID
)

