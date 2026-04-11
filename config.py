

class Config:
    def __init__(self):
        self.ws_url = 'ws://127.0.0.1:3001'  # websocket地址
        self.api_url = 'http://127.0.0.1:3000'  # API地址
        self.admin_id = 2163712324  # 管理员ID
        self.max_processed_cache = 1000  # 最大消息缓存数
        self.doubao_api_key = '自行获取'
        self.doubao_model_id = 'doubao-seed-1-8-251228'
        self.ws_token = '你的wstoken'
        self.api_token = '你的api token'

config = Config()
