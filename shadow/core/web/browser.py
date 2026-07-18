import os
import asyncio
from typing import Dict, Any, List, Optional
from shadow.core.browser import HeadlessBrowser, PLAYWRIGHT_SUPPORTED

class BrowserAutomation:
    def __init__(self):
        self.browser = HeadlessBrowser()

    async def run_actions(self, url: str, actions: List[Dict[str, Any]], screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Loads URL, runs clicks/form-fills/waits, returns logs, network request details and screenshot.
        """
        try:
            open_res = await self.browser.open_url(url)
            if not open_res.get("success"):
                return {"success": False, "error": "Could not load URL"}

            # Process interactive actions
            for action in actions:
                atype = action.get("type")
                selector = action.get("selector")
                value = action.get("value")

                if atype == "click":
                    await self.browser.click_element(selector)
                elif atype == "fill":
                    await self.browser.fill_form(selector, value)
                elif atype == "wait":
                    await asyncio.sleep(float(value or 1))

            # Optional screenshot
            captured_screenshot = None
            if screenshot_path:
                captured_screenshot = await self.browser.take_screenshot(screenshot_path)

            return {
                "success": True,
                "url": url,
                "content": self.browser.dom_content,
                "screenshot": captured_screenshot,
                "console_logs": self.browser.capture_console_logs(),
                "network_requests": self.browser.capture_network_requests()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            await self.browser.close()
