import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from loguru import logger
from typing import Optional

async def extract_ks_video(url: str) -> Optional[str]:
    """
    异步提取快手视频链接
    :param url: 快手分享链接（如 https://v.kuaishou.com/nrfif6A1）
    :return: 视频源地址（失败返回None）
    """
    if not url or not url.startswith("https://v.kuaishou.com/"):
        logger.error("无效的快手链接，格式应为：https://v.kuaishou.com/xxx")
        return None

    browser = None
    try:
        async with async_playwright() as p:
            # 1. 启动浏览器（适配低版本无头模式）
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", "--disable-gpu",
                    "--window-size=1920,1080",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            # 2. 创建上下文（模拟真实浏览器）
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = await context.new_page()
            pages = [page]
            context.on("page", lambda new_page: pages.append(new_page))

            # 3. 访问目标页面并等待跳转完成
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)
            current_page = pages[-1]
            await current_page.bring_to_front()

            # 4. 点击重试按钮（多层兜底）
            retry_btn = current_page.get_by_text("点击重试", exact=True)
            try:
                await retry_btn.wait_for(state="visible", timeout=30000)
                # 优先普通点击，失败则强制点击
                try:
                    await retry_btn.click(timeout=10000)
                except:
                    await retry_btn.click(force=True)
                await asyncio.sleep(2)  # 点击后等待页面刷新
            except PlaywrightTimeoutError:
                logger.warning("未找到「点击重试」按钮，跳过点击")

            # 5. 等待video元素加载
            logger.info("等待视频元素加载...")
            video_element = current_page.locator("video.player-video")
            await video_element.wait_for(state="visible", timeout=20000)

            # 6. 提取video的src链接（多种方式兜底）
            # 方式1：Playwright内置方法
            video_src = await video_element.get_attribute("src")

            # 方式2：原生JS提取（兜底）
            if not video_src:
                video_src = await current_page.evaluate("""() => {
                    const video = document.querySelector('video.player-video');
                    return video ? video.src : null;
                }""")

            # 7. 验证链接有效性
            if video_src and video_src.startswith("http"):
                logger.info(f"成功提取快手视频链接：{video_src}")
                return video_src
            else:
                # 打印页面中所有video元素，排查问题
                all_videos = await current_page.query_selector_all("video")
                logger.warning(f"未提取到有效视频链接，页面中找到 {len(all_videos)} 个video元素")
                for idx, vid in enumerate(all_videos):
                    vid_class = await vid.get_attribute("class")
                    vid_src = await vid.get_attribute("src")
                    logger.warning(f"  视频{idx + 1}：class='{vid_class}'，src='{vid_src}'")
                return None

    except PlaywrightTimeoutError:
        logger.error(f"提取超时：访问 {url} 超时或视频元素加载失败")
        # 保存错误截图（可选）
        if browser and current_page:
            await current_page.screenshot(path="ks_video_timeout.png")
        return None
    except Exception as e:
        logger.error(f"提取快手视频链接失败：{str(e)}")
        # 保存错误截图（可选）
        if browser and current_page:
            await current_page.screenshot(path="ks_video_error.png")
        return None
    finally:
        if browser:
            await browser.close()
