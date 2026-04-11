import websockets, json, asyncio
from loguru import logger
from core.message import Message
from config import config
from websockets.asyncio.client import connect as ws_connect
from core.plugin_manager import plugin_manager
from core.file_watcher import file_watcher
from core.handle import dispatch_command
from datetime import datetime

ws_url = config.ws_url

async def ws_client():
    while True:
        try:
            async with ws_connect(uri=ws_url, additional_headers={"Authorization": f"Bearer {config.ws_token}"}) as ws:
                logger.info('ws连接成功！')
                Message.start_time = datetime.now()
                while True:
                    try:
                        data = await ws.recv()
                        logger.info(f'{data}')
                        if 'message_type' in data:
                            data_1 = json.loads(data)
                            self_id = data_1.get('self_id')
                            user_id = data_1.get('user_id')
                            if self_id == user_id:
                                continue
                            await Message._set_message_data(data_1)
                            await dispatch_command(Message)
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning('连接断开！尝试重连...')
                        break
        except Exception as e:
            logger.error(f'连接失败：{e}，5秒后重试')
            await asyncio.sleep(5)


async def main():
    # 1. 加载所有插件
    aabb = await plugin_manager.load_all_plugins()
    # 2. 启动文件监视器
    await file_watcher.start()
    logger.debug(f'{aabb}')
    # 3. 启动WS客户端
    await ws_client()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序：用户中断，开始清理资源")
        asyncio.run(file_watcher.stop())
        logger.info("程序：已退出")
