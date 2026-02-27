from command import on_command
from message import message
import sys,asyncio,requests as fw,json,os
from plugin import md2img
from io import StringIO
from plugin.chat import chat_manager
from plugin.ks_video import extract_ks_video

a = on_command("测试")
b = on_command(["帮助", "help", "菜单"])
c = on_command("你好")
d = on_command(["结束",'退出'])
send = on_command(r'发送 ([\s\S]+)')
op = on_command(r'/?执行[\n\r]([\s\S]+)')
chat = on_command(r'/?豆包 ?([\s\S]+)')
card = on_command()

@a.box()
async def _(ctx):
    await a.send_msg(group_id=message.group_id, text='成功')

@b.box()
async def _(ctx):
    """处理「帮助/help/菜单」命令"""
    help_text = """
    指令列表：
    📝 测试 - 测试指令
    ❓ 帮助/help/菜单 - 查看帮助
    """
    await b.send_msg(group_id=message.group_id, text=help_text.strip())

@c.box()
async def _(ctx):
    await c.send_msg(group_id=message.group_id, text='成功')

@d.box()
async def _(ctx):
    await c.send_msg(group_id=message.group_id, text='已退出')
    sys.exit(0)

@send.box()
async def _(ctx):
    await send.send_msg(group_id=message.group_id, text=ctx['match'].group(1))

@chat.box()
async def _(ctx):
    try:
        user_input = ctx["match"].group(1)
        session_id = message.group_id
        reply = await chat_manager.get_chat_reply(session_id, user_input)
        msg = []
        path = False
        if len(reply) > 150:
            img_path = os.path.join(os.getcwd(), f"md_img_{message.user_id}.png")
            path = await md2img.md_to_image_async(f'{reply}',img_path)
        if path:
            await chat._add_image(f'file://{path}')
        else:
            await chat._add_text(f'{reply}')
        if reply:
            await chat.send_msg(group_id=message.group_id)
        else:
            await chat.send_msg(group_id=message.group_id, text="抱歉，我暂时无法回答，请稍后再试！")
    except Exception as e:
        await chat.send_msg(group_id=message.group_id, text=f"聊天指令出错啦：{str(e)}")

@op.box()
async def _(ctx):
    if message.user_id != 2163712324:
        await op.send_msg(group_id=message.group_id,text='禁止使用！')
    else:
        code = ctx['match'].group(1)
        old = sys.stdout
        new = StringIO()
        sys.stdout = new
        try:
            exec(code)
        finally:
            sys.stdout = old
        op_1 = new.getvalue()
        await op.send_msg(group_id=message.group_id, text=f'执行结果：\n{op_1}')


@card.box()
async def _(ctx):
    try:
        if not ctx['ark_data']:
            pass
        else:
            # 1. 核心修复：将字典转为JSON字符串（避免[object Object]）
            ark_data_str = json.dumps(ctx['ark_data'], ensure_ascii=False, indent=2)

            # 2. 安全处理：限制消息长度（避免超长消息发送失败）
            if len(ark_data_str) > 2000:
                ark_data_str = ark_data_str[:2000] + "\n\n（内容过长，已截断）"

            # 3. 发送格式化后的字符串（而非原始字典）
            await card.send_msg(
                group_id=message.group_id,
                text=f"检测到卡片消息：\n{ark_data_str}"
            )

            # ========== 可选：解析快手视频链接（恢复你注释的逻辑） ==========
            data_1 = ctx['ark_data']
            # 防KeyError：逐层判断字段是否存在
            if 'meta' in data_1 and 'news' in data_1['meta'] and 'jumpUrl' in data_1['meta']['news']:
                url = data_1['meta']['news']['jumpUrl']
                video_url = await extract_ks_video(url)
                if video_url:
                    # 发送视频（确保msg格式正确）
                    await card._add_video(video_url)
                    await card.send_msg(group_id=message.group_id)
                    await card.send_msg(group_id=message.group_id, text='解析成功')
            # ==============================================================
    except Exception as e:
        # 异常捕获：避免单次卡片解析失败导致循环触发
        await card.send_msg(
            group_id=message.group_id,
            text=f"卡片消息处理出错：{str(e)}"
        )