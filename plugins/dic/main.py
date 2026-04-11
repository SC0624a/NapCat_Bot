from core.handle import on_command
from core.message import Message

import sys,asyncio,requests as fw,json,os,psutil
from datetime import datetime
from io import StringIO

from plugins.set import md2img
from plugins.set.chat import chat_manager
from plugins.set.ks_video import extract_ks_video


a = on_command("测试")
b = on_command(["帮助", "help", "菜单"])
c = on_command("你好")
d = on_command(["结束",'退出'])
send = on_command(r'发送 ([\s\S]+)')
op = on_command(r'/?执行[\n\r]([\s\S]+)')
chat = on_command(r'/?豆包 ?([\s\S]+)')
run = on_command("运行")


@a.handle()
async def _(args = Message):
    await a.send_msg(group_id=args.group_id, text='成功')

@b.handle()
async def _(args = Message):
    """处理「帮助/help/菜单」命令"""
    help_text = """
    指令列表：
    📝 测试 - 测试指令
    ❓ 帮助/help/菜单 - 查看帮助
    """
    await b.send_msg(group_id=args.group_id, text=help_text.strip())

@c.handle()
async def _(args = Message):
    await c.send_msg(group_id=args.group_id, text='成功')

@d.handle()
async def _(args = Message):
    await c.send_msg(group_id=args.group_id, text='已退出')
    sys.exit(0)

@send.handle()
async def _(args = Message):
    await send.send_msg(group_id=args.group_id, text=args.group(1))

@chat.handle()
async def _(args = Message):
    try:
        user_input = args.group(1)
        session_id = args.group_id
        reply = await chat_manager.get_chat_reply(session_id, user_input)
        msg = []
        path = False
        if len(reply) > 150:
            img_path = os.path.join(os.getcwd(), f"md_img_{args.user_id}.png")
            path = await md2img.md_to_image_async(f'{reply}',img_path)
        if path:
            await chat._add_image(f'file://{path}')
        else:
            await chat._add_text(f'{reply}')
        if reply:
            await chat.send_msg(group_id=args.group_id)
        else:
            await chat.send_msg(group_id=args.group_id, text="抱歉，我暂时无法回答，请稍后再试！")
    except Exception as e:
        await chat.send_msg(group_id=args.group_id, text=f"聊天指令出错啦：{str(e)}")

@op.handle()
async def _(args = Message):
    if args.user_id != 2163712324:
        await op.send_msg(group_id=args.group_id,text='禁止使用！')
    else:
        code = args = Message['match'].group(1)
        old = sys.stdout
        new = StringIO()
        sys.stdout = new
        try:
            exec(code,globals())
        finally:
            sys.stdout = old
        op_1 = new.getvalue()
        await op.send_msg(group_id=args.group_id, text=f'执行结果：\n{op_1}')

@run.handle()
async def _(args = Message):
    cpu_percent = psutil.cpu_percent(interval=1)
    mem_info = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')
    pids = psutil.pids()
    text = f"CPU使用率: {cpu_percent}%\n内存: {mem_info.total / (1024 ** 3):.2f}/{mem_info.used / (1024 ** 3):.2f} GB\n内存使用率: {mem_info.percent}%\n磁盘总空间: {disk_usage.total / (1024 ** 3):.2f}/{disk_usage.used / (1024 ** 3):.2f} GB\n磁盘使用率: {disk_usage.percent}%\n总进程数: {len(pids)}"
    end_time = datetime.now()
    run_seconds = (end_time - args.start_time).total_seconds()
    days = int(run_seconds // (24 * 3600))
    hours = int((run_seconds % (24 * 3600)) // 3600)
    minutes = int((run_seconds % 3600) // 60)
    seconds = round(run_seconds % 60, 2)
    text = f'{text}\n运行时间：{days}天 {hours}小时 {minutes}分钟 {seconds}秒'
    await run.send_msg(group_id=args.group_id,text=text)
