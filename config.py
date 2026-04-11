

class Config:
    def __init__(self):
        self.ws_url = 'ws://127.0.0.1:3001'  # websocket地址
        self.api_url = 'http://127.0.0.1:3000'  # API地址
        self.admin_id = 2163712324  # 管理员ID
        self.max_processed_cache = 1000  # 最大消息缓存数
        self.doubao_api_key = '8c09bbf4-311a-4ca8-9678-6656774b1247'
        self.doubao_model_id = 'doubao-seed-1-8-251228'
        self.ws_token = 'sc20060624aaa'
        self.api_token = 'sc20060624aaa'

config = Config()