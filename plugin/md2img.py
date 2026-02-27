import markdown
import os
import re
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from loguru import logger
from typing import Optional

async def md_to_image_async(md_text: str, output_path: str = None) -> Optional[str]:
    """
    异步版 Markdown文本转图片（适配asyncio异步框架）
    :param md_text: 要转换的Markdown文本
    :param output_path: 图片保存路径（默认：当前目录/md_output.png）
    :return: 图片路径（失败返回None）
    """
    if not md_text:
        logger.error("MD文本为空，无法转换")
        return None

    # 1. 生成默认输出路径
    if not output_path:
        output_path = os.path.join(os.getcwd(), "md_output.png")

    try:
        # 2. MD转HTML + 修复删除线
        html_content = markdown.markdown(
            md_text,
            extensions=[
                'markdown.extensions.extra',
                'markdown.extensions.fenced_code'
            ]
        )
        # 手动替换~~文本~~为<del>文本</del>
        html_content = re.sub(r'~~(.*?)~~', r'<del>\1</del>', html_content)

        # 3. 构造完整HTML模板
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
        <meta charset="UTF-8">
        <link href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
        <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            width: 850px;
            margin: 20px auto;
            padding: 30px;
            font-family: "微软雅黑", "Microsoft YaHei", sans-serif;
            line-height: 1.8;
            background: #ffffff;
            font-size: 16px;
            color: #333;
        }}
        h1 {{ 
            color: #24292e; 
            border-bottom: 2px solid #eaecef; 
            padding-bottom: 10px; 
            margin-bottom: 25px;
        }}
        h2 {{ color: #24292e; margin: 30px 0 15px 0; }}
        h3 {{ color: #24292e; margin: 20px 0 15px 0; }}
        pre {{
            background: #f6f8fa !important;
            padding: 20px !important;
            border-radius: 8px !important;
            overflow-x: auto;
            font-size: 14px !important;
            margin: 15px 0 !important;
            font-family: "Consolas", "Monaco", monospace !important;
        }}
        code {{
            background: #f6f8fa !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
        }}
        ul, ol {{ padding-left: 30px; margin: 10px 0; }}
        li {{ margin: 8px 0; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            border: 1px solid #d0d7de;
        }}
        th, td {{
            border: 1px solid #d0d7de;
            padding: 12px 15px;
            text-align: left;
            font-size: 15px;
        }}
        th {{ 
            background: #f6f8fa; 
            font-weight: bold; 
            color: #24292e;
        }}
        tr:nth-child(even) {{
            background: #f9fafb;
        }}
        del {{ 
            color: #d73a4a !important;
            text-decoration: line-through !important;
            text-decoration-thickness: 2px !important;
            text-decoration-color: #d73a4a !important;
        }}
        strong {{ color: #24292e; font-weight: bold; }}
        em {{ color: #24292e; font-style: italic; }}
        </style>
        </head>
        <body>
        {html_content}
        </body>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            if (window.Prism) {{
                Prism.highlightAll();
            }}
        }});
        </script>
        </html>
        """

        # 4. Playwright异步API渲染截图（核心修改）
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"]
            )
            page = await browser.new_page(
                viewport={"width": 900, "height": 1300},
                extra_http_headers={"Accept-Language": "zh-CN"}
            )
            page.set_default_timeout(10000)

            await page.set_content(html, wait_until="load")
            await asyncio.sleep(2)  # 异步等待CDN加载（替换time.sleep）
            await page.wait_for_load_state("networkidle")

            # 异步截图保存
            await page.screenshot(
                path=output_path,
                full_page=True,
                type="png"
            )

            await page.close()
            await browser.close()

        logger.info(f"MD转图片成功，保存路径：{output_path}")
        return output_path

    except PlaywrightTimeoutError:
        logger.error("CDN加载超时，建议使用离线版Prism.js")
        return None
    except Exception as e:
        logger.error(f"MD转图片失败：{str(e)}")
        return None

# 同步兼容接口（保留，供非异步场景测试）
def md_to_image(md_text: str, output_path: str = None) -> Optional[str]:
    """
    同步版接口（内部调用异步函数）
    """
    return asyncio.run(md_to_image_async(md_text, output_path))
