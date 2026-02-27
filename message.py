class Message:
    """
    QQ消息对象，封装所有消息字段，支持异步数据填充。
    """
    def __init__(self):
        self.raw_data : dict|list
        self.self_id :int #机器人QQ
        self.user_id :int #用户QQ
        self.time :int #时间戳
        self.message_id :int #消息id
        self.message_seq :int #被回复的消息id（没有默认为消息本身id）
        self.real_id :int #？（消息本身？）
        self.real_seq :int #？
        self.message_type :str #消息类型 group 群
        self.sender :dict #发送人信息
        self.sender_user_id :int #发送人QQ
        self.sender_nickname :str #发送昵称
        self.sender_card :dict|list|str|None #？
        self.sender_role :str #发送人的权限 owner 群主
        self.raw_message :str #原始信息
        self.font :int #字体
        self.sub_type :str #？
        self.message :dict|list #信息拆分
        self.message_format :str #array数组
        self.group_id :int #群号
        self.group_name :str #群昵称

    async def _set_message_data(self, data: dict|list) -> None:
        """
        填充消息对象数据
        :param data: 消息字典或列表
        """
        self.raw_data = data
        self.self_id = data.get('self_id', 0)
        self.user_id = data.get('user_id', 0)
        self.time = data.get('time', 0)
        self.message_id = data.get('message_id', 0)
        self.message_seq = data.get('message_seq', 0)
        self.real_id = data.get('real_id', 0)
        self.real_seq = data.get('real_seq', 0)
        self.message_type = data.get('message_type', '')
        self.sender = data.get('sender', {})
        self.sender_user_id = self.sender.get('user_id', 0) if isinstance(self.sender, dict) else 0
        self.sender_nickname = self.sender.get('nickname', '') if isinstance(self.sender, dict) else ''
        self.sender_card = self.sender.get('card', None) if isinstance(self.sender, dict) else None
        self.sender_role = self.sender.get('role', '') if isinstance(self.sender, dict) else ''
        self.raw_message = data.get('raw_message', '')
        self.font = data.get('font', 0)
        self.sub_type = data.get('sub_type', '')
        self.message = data.get('message', {})
        self.message_format = data.get('message_format', '')
        self.group_id = data.get('group_id', 0)
        self.group_name = data.get('group_name', '')


message = Message()