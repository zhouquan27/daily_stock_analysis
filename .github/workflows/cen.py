import asyncio
import logging
import os
from datetime import datetime

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def run_cen_with_handler(query: str | None = None) -> list[str]:
    headless_env = os.getenv("HEADLESS", "true").lower() not in ("0", "true", "no")
    search_term = query or os.getenv("CEN_QUERY", "ISO 9001")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_path = os.getenv("TRACE_PATH", f"./app/log/cen_handler_trace_{timestamp}.zip")
    trace_dir = os.path.dirname(trace_path)
    if trace_dir:
        os.makedirs(trace_dir, exist_ok=True)

    logger.info(
        "cen run start headless=%s query=%s trace=%s",
        headless_env,
        search_term,
        trace_path,
    )
    logger.info("开始搜索关键词: %s", search_term)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless_env)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        await context.tracing.start(screenshots=True, snapshots=True)
        page = await context.new_page()

        url = "https://standards.cencenelec.eu/ords/f?p=CEN:105"
 
        await page.goto(url, wait_until="networkidle", timeout=100000) #networkidle
        logger.info("正在访问页面... %s", url)
        await page.goto(url, wait_until="domcontentloaded")
        results: list[str] = []
        try:
            search_input_selector = "input#KEYWORDS_AND"
            logger.info("定位搜索框...")
            # await page.wait_for_selector(search_input_selector)
            await page.locator(search_input_selector).wait_for(state="visible", timeout=60000)
            logger.info("输入关键词: %s", search_term)
            await page.fill(search_input_selector, search_term)

            logger.info("提交搜索请求...")
            await page.keyboard.press("Enter")

            logger.info("等待结果返回...")
            await page.wait_for_load_state("domcontentloaded")

            logger.info("提取搜索结果..., 当前页面: %s", page.url)
            clean_text = await page.locator("table.dashlist").all_inner_texts()
            results.append(clean_text)

            if results:
                logger.info("获取到数据 %d 条", len(results))
                for row in results:
                    logger.info(row)
            else:
                logger.warning("未找到相关结果或页面结构已变化。")

            await page.screenshot(path="search_result.png")
        except Exception:
            logger.exception("操作失败")
        finally:
            try:
                await context.tracing.stop(path=trace_path)
            except Exception:
                logger.debug("Tracing stop failed or was not started.")
            await browser.close()
            logger.info("浏览器已关闭")

# 运行异步函数
if __name__ == "__main__":
    asyncio.run(run_cen_with_handler())
