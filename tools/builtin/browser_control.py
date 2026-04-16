# -*- coding: utf-8 -*-
"""
浏览器自动化工具
基于 Playwright 的浏览器操作工具集

支持操作:
- navigate: 导航到指定URL
- click: 点击元素
- type: 输入文本
- screenshot: 截图
- get_content: 获取页面内容
- scroll: 滚动页面
- go_back/go_forward: 前进后退
"""
from __future__ import annotations
import asyncio
import base64
import logging
from typing import Optional, Literal, Any
from urllib.parse import urljoin, urlparse

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # 定义占位类型以避免类型错误
    Page = Any
    Browser = Any
    BrowserContext = Any

from agentscope.message import TextBlock, ImageBlock
from agentscope.tool import ToolResponse

logger = logging.getLogger(__name__)

# 全局浏览器实例缓存
_browser_instance = None
_browser_context = None
_current_page = None


async def _get_browser() -> Optional[Browser]:
    """获取或创建浏览器实例"""
    global _browser_instance

    if _browser_instance is None:
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright 未安装，请运行: pip install playwright && playwright install chromium")
            return None

        try:
            playwright = await async_playwright().start()
            _browser_instance = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            logger.info("✅ 浏览器实例已启动")
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return None

    return _browser_instance


async def _get_page() -> Optional[Page]:
    """获取当前页面实例"""
    global _current_page, _browser_context

    if _current_page is None:
        browser = await _get_browser()
        if browser is None:
            return None

        if _browser_context is None:
            _browser_context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

        _current_page = await _browser_context.new_page()
        logger.info("✅ 新页面已创建")

    return _current_page


async def _close_browser():
    """关闭浏览器实例"""
    global _browser_instance, _browser_context, _current_page

    if _current_page:
        await _current_page.close()
        _current_page = None

    if _browser_context:
        await _browser_context.close()
        _browser_context = None

    if _browser_instance:
        await _browser_instance.close()
        _browser_instance = None

    logger.info("✅ 浏览器已关闭")


async def browser_use(
    action: str,
    url: str = None,
    selector: str = None,
    text: str = None,
    scroll_amount: int = None,
    wait_for: str = None,
    js_code: str = None,
) -> ToolResponse:
    """
    浏览器自动化工具

    通过 Playwright 控制浏览器执行各种操作。

    Args:
        action: 操作类型
            - navigate: 导航到指定URL
            - click: 点击页面元素
            - type: 在输入框中输入文本
            - screenshot: 截取页面截图
            - get_content: 获取页面文本内容
            - scroll: 滚动页面（正数向下，负数向上）
            - go_back: 后退到上一页
            - go_forward: 前进到下一页
            - refresh: 刷新页面
            - close: 关闭浏览器
            - get_url: 获取当前页面URL
            - evaluate: 执行JavaScript代码

        url: 用于navigate操作的URL
        selector: 用于click/type操作的CSS选择器
        text: 用于type操作的输入文本
        scroll_amount: 用于scroll操作的滚动像素数
        wait_for: 操作后等待的选择器（等待元素出现）
        js_code: 用于evaluate操作的JS代码

    Returns:
        ToolResponse: 操作结果

    Examples:
        # 导航到网页
        browser_use(action="navigate", url="https://www.example.com")

        # 点击按钮
        browser_use(action="click", selector="#submit-button")

        # 输入文本
        browser_use(action="type", selector="#search-box", text="搜索关键词")

        # 截图
        browser_use(action="screenshot")

        # 获取页面内容
        browser_use(action="get_content")

        # 滚动页面
        browser_use(action="scroll", scroll_amount=500)

        # 执行JS
        browser_use(action="evaluate", js_code="document.title")
    """
    if not PLAYWRIGHT_AVAILABLE:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text="错误: Playwright 未安装。请运行:\npip install playwright\nplaywright install chromium"
            )]
        )

    try:
        page = await _get_page()
        if page is None:
            return ToolResponse(
                content=[TextBlock(type="text", text="错误: 无法初始化浏览器")]
            )

        # 执行各种操作
        if action == "navigate":
            if not url:
                return ToolResponse(
                    content=[TextBlock(type="text", text="错误: navigate操作需要提供url参数")]
                )

            await page.goto(url, wait_until="networkidle", timeout=30000)
            title = await page.title()

            # 等待指定元素
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=10000)
                except Exception:
                    pass

            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text=f"✅ 已导航到: {url}\n页面标题: {title}"
                )]
            )

        elif action == "click":
            if not selector:
                return ToolResponse(
                    content=[TextBlock(type="text", text="错误: click操作需要提供selector参数")]
                )

            await page.click(selector, timeout=10000)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)

            return ToolResponse(
                content=[TextBlock(type="text", text=f"✅ 已点击元素: {selector}")]
            )

        elif action == "type":
            if not selector or text is None:
                return ToolResponse(
                    content=[TextBlock(type="text", text="错误: type操作需要提供selector和text参数")]
                )

            await page.fill(selector, text, timeout=10000)

            return ToolResponse(
                content=[TextBlock(type="text", text=f"✅ 已在 {selector} 输入文本")]
            )

        elif action == "screenshot":
            screenshot_bytes = await page.screenshot(full_page=True)
            base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')

            return ToolResponse(
                content=[
                    TextBlock(type="text", text="✅ 截图完成:"),
                    ImageBlock(
                        type="image",
                        source={"type": "base64", "media_type": "image/png", "data": base64_image}
                    )
                ]
            )

        elif action == "get_content":
            # 获取页面可见文本
            content = await page.evaluate("""() => {
                return document.body.innerText;
            }""")

            # 截断过长内容
            max_length = 8000
            if len(content) > max_length:
                content = content[:max_length] + f"\n\n... (内容已截断，共 {len(content)} 字符)"

            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text=f"页面内容:\n```\n{content}\n```"
                )]
            )

        elif action == "scroll":
            amount = scroll_amount or 500
            await page.evaluate(f"window.scrollBy(0, {amount})")

            direction = "向下" if amount > 0 else "向上"
            return ToolResponse(
                content=[TextBlock(type="text", text=f"✅ {direction}滚动 {abs(amount)} 像素")]
            )

        elif action == "go_back":
            await page.go_back(wait_until="networkidle")
            url = page.url
            return ToolResponse(
                content=[TextBlock(type="text", text=f"✅ 已后退到: {url}")]
            )

        elif action == "go_forward":
            await page.go_forward(wait_until="networkidle")
            url = page.url
            return ToolResponse(
                content=[TextBlock(type="text", text=f"✅ 已前进到: {url}")]
            )

        elif action == "refresh":
            await page.reload(wait_until="networkidle")
            return ToolResponse(
                content=[TextBlock(type="text", text="✅ 页面已刷新")]
            )

        elif action == "get_url":
            url = page.url
            title = await page.title()
            return ToolResponse(
                content=[TextBlock(type="text", text=f"当前URL: {url}\n页面标题: {title}")]
            )

        elif action == "evaluate":
            if not js_code:
                return ToolResponse(
                    content=[TextBlock(type="text", text="错误: evaluate操作需要提供js_code参数")]
                )

            result = await page.evaluate(js_code)

            # 格式化结果
            if isinstance(result, (dict, list)):
                import json
                result_str = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result_str = str(result)

            # 截断过长结果
            max_length = 4000
            if len(result_str) > max_length:
                result_str = result_str[:max_length] + f"\n\n... (结果已截断)"

            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text=f"JavaScript执行结果:\n```\n{result_str}\n```"
                )]
            )

        elif action == "close":
            await _close_browser()
            return ToolResponse(
                content=[TextBlock(type="text", text="✅ 浏览器已关闭")]
            )

        else:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"错误: 未知操作类型: {action}")]
            )

    except Exception as e:
        logger.error(f"浏览器操作失败: {e}")
        return ToolResponse(
            content=[TextBlock(type="text", text=f"错误: 浏览器操作失败 - {str(e)}")]
        )
