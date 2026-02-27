import json,asyncio
from aiohttp import ClientSession

api_url = 'http://127.0.0.1:3000'

class Api:
    def __init__(self):
        self.message = []
        pass

    async def _get(self,**kwargs):
        async with ClientSession() as fw:
            async with fw.get(**kwargs) as resp:
                data = await resp.json()
                return data

    async def _post(self,**kwargs):
        async with ClientSession() as fw:
            async with fw.post(**kwargs) as resp:
                data = await resp.json()
                return data

    async def _add_text(self,text):
        text = {
            'type':'text',
            'data':{'text':text}
        }
        self.message.append(text)

    async def _add_at(self,user_id):
        '''
        :param user_id: 0为全体成员
        :return:
        '''
        at = {
            'type':'at',
            'data':{'qq':user_id}
        }
        await self._add_text(' ')
        self.message.append(at)

    async def _add_face(self,face_id):
        face = {
            'type':'face',
            'data':{'id':face_id}
        }
        self.message.append(face)

    async def _add_reply(self,reply_id):
        '''
        回复
        :param reply_id: message.real_seq？
        :return:
        '''
        reply = {
            'type':'reply',
            'data':{'seq':reply_id}
        }
        self.message.append(reply)

    async def _add_image(self,data):
        '''
        :param data: http(s)|file://D:/
        :return:
        '''
        image = {
            'type':'image',
            'data':{'file':data}
        }
        self.message.append(image)

    async def _add_record(self,data):
        '''
        语音
        :param data: http(s)|file://D:/
        :return:
        '''
        record = {
            'type':'record',
            'data':{'file':data}
        }
        self.message.append(record)

    async def _add_video(self,data):
        '''
        :param data: http(s)|file://D:/
        :return:
        '''
        video = {
            'type':'video',
            'data':{'file':data}
        }
        self.message.append(video)

    async def _add_file(self,data):
        '''
        文件形式
        http(s)|file://D:/
        :param data:
        :return:
        '''
        file = {
            'type':'file',
            'data':{'file':data}
        }
        self.message.append(file)

    async def _add_music(self,music_type,music_id):
        '''
        :param music_type: qq|163|kugou|migu|kuwo
        :param music_id: ?
        :return:
        '''
        if music_type is not ['qq','163','kugou','migu','kuwo']:
            await self._add_text('未知的音乐类型！')
        else:
            music = {
                'type':'music',
                'id':music_id
            }
            '''
            music = {'url':'','audio':'x','title':'x','image':'','content':'x'}
            music的基础上增加 x为可选
            '''
            self.message.append(music)

    async def _add_poke(self,poke_type,poke_id):
        '''
        戳一戳
        :param poke_type: ？
        :param poke_id: ？
        :return:
        '''
        poke = {
            'type':'poke',
            'data':{'type':poke_type,'id':poke_id}
        }
        self.message.append(poke)

    async def _add_dice(self,dice_id):
        '''
        骰子表情
        :param dice_id: 1-6
        :return:
        '''
        dice = {
            'type':'dice',
            'data':{'result':dice_id}
        }
        self.message.append(dice)


    async def _add_json(self,data):
        '''
        json卡片
        :param data: ~
        :return:
        '''
        json = {
            'type':'json',
            'data':{'data':data}
        }
        self.message.append(json)

    async def _add_xml(self,data):
        '''
        xml卡片
        :param data:
        :return:
        '''
        xml = {
            'type':'xml',
            'data':{'data':data}
        }
        self.message.append(xml)

    async def _add_markdown(self,data):
        '''
        2026/2/7 目前不能用
        :param data: ~
        :return:
        '''
        markdown = {
            'type':'markdown',
            'data':{'content':data}
        }
        self.message.append(markdown)

    async def _add_node(self,user_id,nickname,content):
        '''
        合并转发消息节点
        :param user_id: 消息发送人qq号
        :param nickname: 名字
        :param content: 消息
        :return:
        '''
        node = {
            'type':'node',
            'data':{'user_id':user_id,'nickname':nickname,'content':content}
        }
        self.message.append(node)

    async def _add_forward(self,forward_id):
        '''
        合并转发消息段
        :param forward_id: ？
        :return:
        '''
        forward = {
            'type':'forward',
            'data':{'id':forward_id}
        }
        self.message.append(forward)

    async def send_msg(self,group_id=0,user_id=0,text=None,message_type='group',msg=[]):
        '''
        :param group_id: 群号
        :param user_id: 用户号（私聊）
        :param message_type: group -> 群聊，private -> 私聊
        :param text: 文本
        :param msg: 自由构造
        :return: None
        '''
        url = f'{api_url}/send_msg'
        if msg != []:
            msg = msg
        else:
            msg = self.message
        body = {"message_type": message_type, "message": msg}
        if text is not None:
            await self._add_text(text)
        else:
            pass
        if message_type == 'private':
            body['user_id'] = user_id
        if message_type == 'group':
            body['group_id'] = group_id
        await self._post(url=url,json=body)
        self.message = []


    async def send_group_forward_msg(self,group_id,text,nickname="小辞",user_id=3204461757):
        url = f"{api_url}/send_group_forward_msg"
        msg = []
        content = []
        card = {
                "type": "node",
                "data": {
                    "nickname": nickname,
                    "user_id": user_id,
                    "content": content
                }
            }
        text = {
            'type':'text',
            'data':{'text':text}
        }
        content.append(text)
        msg.append(card)
        body = {
            "group_id": group_id,
            "message": msg,
            "news" : [
            {"text": "要不...进来看看？"}
        ],
            "prompt":"你好，欢迎光临",
            "summary":"",
            "source":"点我查看内容"
        }
        await self._post(url=url,json=body)


api = Api()