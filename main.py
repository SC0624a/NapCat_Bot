import websockets,json,asyncio,importlib,command
from loguru import logger
from message import message
import command,dic

# dic.py 只需在命令处理时 reload，避免启动时多余 reload
ws_url = 'ws://127.0.0.1:3001'

async def ws_client():
    while True:
        try:
            async with websockets.connect(uri=ws_url) as ws:
                logger.info('ws连接成功！')
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
                            # 只在收到消息时 reload dic，减少循环依赖
                            importlib.reload(dic)
                            await message._set_message_data(data_1)
                            await command.process_message()
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning('连接断开！尝试重连...')
                        break
        except Exception as e:
            logger.error(f'连接失败：{e}，5秒后重试')
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(ws_client())