import os
import json
import random
import asyncio
from typing import Dict, Any, List, Optional, Callable
from openai import OpenAI
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

class BrowserAutomator:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.system_prompt = """You are an expert browser automation assistant that translates natural language into precise Playwright actions. Follow these rules:

1. Output STRICTLY in JSON format matching OpenAI's Computer Use API schema
2. Always provide multiple CSS selectors for each element (2-3 alternatives)
3. Include automatic waits between actions (200-1000ms)
4. Add networkidle waits after page loads
5. Include fallback strategies for critical actions

Action types available:
- navigate: {url: string, wait_until?: "load"|"domcontentloaded"|"networkidle"}
- click: {selector: string, timeout?: number, click_count?: number}
- type: {selector: string, text: string, delay?: number, clear?: boolean}
- keypress: {keys: string|List[string]}
- scroll: {x?: number, y?: number, selector?: string}
- wait: {timeout: number (ms), state?: "visible"|"hidden"|"attached"|"detached"}
- screenshot: {path?: string, full_page?: boolean}

For Google searches specifically:
1. Always use google.com (not country-specific domains)
2. For search box, use: "textarea[name='q'], textarea[title='Search'], input[name='q']"
3. After typing, press Enter rather than clicking search button
4. Wait for networkidle after search results load

Response format:
```json
{
  "output": [
    {
      "type": "reasoning",
      "summary": [{"text": "<action explanation>"}]
    },
    {
      "type": "computer_call",
      "action": {
        "type": "<action_type>",
        // action-specific parameters
      },
      "pending_safety_checks": []
    }
  ]
}
"""
        self.active_page = None
        self.virtual_mode = False
        self.stream_callback = None
        self.active_sessions = {}

    async def get_actions(self, prompt: str) -> Dict[str, Any]:
        """Convert natural language to Playwright actions"""
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    async def execute_stream(self, prompt: str, callback: Callable[[dict], None]):
        """Main entry point for virtual browser execution"""
        actions = await self.get_actions(prompt)
        self.stream_callback = callback
        
        async with async_playwright() as p:
            browser = await self._get_authenticated_browser(p, headless=True)
            context = await self._get_authenticated_context(browser)
            self.active_page = await context.new_page()
            
            try:
                # Initial state
                await self._send_update("init")
                
                for action_item in actions.get("output", []):
                    if action_item["type"] != "computer_call":
                        continue
                        
                    action = action_item["action"]
                    try:
                        # Pre-action highlight
                        if action["type"] in ["click", "type"]:
                            await self._highlight_element(action["selector"])
                            await self._send_update("highlight", action=action)
                            await asyncio.sleep(0.3)  # Visual delay
                            
                        # Execute action
                        result = await self._perform_action(action)
                        
                        # Post-action update
                        await self._send_update("action", 
                                             action=action,
                                             result=result)
                                             
                    except Exception as e:
                        await self._send_update("error", error=str(e))
                        
            finally:
                await context.close()
                await browser.close()
                self.active_page = None

    async def _send_update(self, update_type: str, **kwargs):
        """Helper to send standardized updates"""
        if not self.stream_callback:
            return
            
        data = {
            "type": update_type,
            "data": await self._get_page_state()
        }
        data.update(kwargs)
        
        await self.stream_callback(data)

    async def _get_page_state(self) -> Dict[str, Any]:
        """Capture current DOM state for virtual browser"""
        if not self.active_page:
            return {}
            
        return {
            "url": await self.active_page.url(),
            "html": await self.active_page.content(),
            "interactive_elements": await self._get_interactive_elements(),
            "focused_element": await self._get_focused_element()
        }

    async def _get_interactive_elements(self) -> List[Dict[str, Any]]:
        """Identify all clickable/typeable elements with their selectors"""
        return await self.active_page.evaluate("""() => {
            const elements = [];
            const selectors = [
                'a', 'button', 'input', 'textarea', 'select',
                '[role=button]', '[onclick]', '[contenteditable]'
            ];
            
            document.querySelectorAll(selectors.join(',')).forEach(el => {
                if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                    elements.push({
                        selector: cssPath(el),
                        bounds: el.getBoundingClientRect().toJSON(),
                        tag: el.tagName.toLowerCase(),
                        type: el.type || '',
                        value: el.value || ''
                    });
                }
            });
            return elements;
            
            function cssPath(el) {
                const path = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let selector = el.nodeName.toLowerCase();
                    if (el.id) {
                        selector += `#${el.id}`;
                        path.unshift(selector);
                        break;
                    } else {
                        let sib = el, nth = 1;
                        while (sib = sib.previousElementSibling) {
                            if (sib.nodeName.toLowerCase() === selector) nth++;
                        }
                        if (nth !== 1) selector += `:nth-of-type(${nth})`;
                    }
                    path.unshift(selector);
                    el = el.parentNode;
                }
                return path.join(' > ');
            }
        }""")

    async def _get_focused_element(self) -> Optional[str]:
        """Get CSS path of currently focused element"""
        return await self.active_page.evaluate("""() => {
            const el = document.activeElement;
            if (!el || el === document.body) return null;
            
            const path = [];
            let current = el;
            while (current && current.nodeType === Node.ELEMENT_NODE) {
                let selector = current.nodeName.toLowerCase();
                if (current.id) {
                    selector += `#${current.id}`;
                    path.unshift(selector);
                    break;
                } else {
                    let sib = current, nth = 1;
                    while (sib = sib.previousElementSibling) {
                        if (sib.nodeName.toLowerCase() === selector) nth++;
                    }
                    if (nth !== 1) selector += `:nth-of-type(${nth})`;
                }
                path.unshift(selector);
                current = current.parentNode;
            }
            return path.join(' > ');
        }""")

    async def _highlight_element(self, selector: str):
        """Visually highlight an element (no screenshots)"""
        await self.active_page.evaluate("""(selector) => {
            document.querySelectorAll('.automation-highlight').forEach(el => {
                el.classList.remove('automation-highlight');
            });
            const el = document.querySelector(selector);
            if (el) {
                el.classList.add('automation-highlight');
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }""", selector)

    async def _perform_action(self, action: Dict[str, Any]) -> str:
        """Execute a single Playwright action with enhanced feedback"""
        action_type = action.get("type")
        try:
            if action_type == "navigate":
                await self.active_page.goto(
                    action["url"],
                    wait_until=action.get("wait_until", "load")
                )
                return f"Navigated to {action['url']}"
                
            elif action_type == "click":
                await self._highlight_element(action["selector"])
                await self.active_page.click(action["selector"])
                return f"Clicked {action['selector']}"
                
            elif action_type == "type":
                await self._highlight_element(action["selector"])
                await self.active_page.fill(action["selector"], action["text"])
                return f"Typed into {action['selector']}"
                
            elif action_type == "keypress":
                keys = action["keys"]
                if isinstance(keys, str):
                    await self.active_page.keyboard.press(keys)
                else:
                    for key in keys:
                        await self.active_page.keyboard.press(key)
                return f"Pressed keys: {keys}"
                
            elif action_type == "wait":
                if action.get("state") == "networkidle":
                    await self.active_page.wait_for_load_state("networkidle")
                else:
                    await self.active_page.wait_for_timeout(action["timeout"])
                return f"Waited {action.get('timeout', 0)}ms"
                
            elif action_type == "scroll":
                if "selector" in action:
                    await self.active_page.locator(action["selector"]).scroll_into_view_if_needed()
                else:
                    await self.active_page.mouse.wheel(
                        action.get("x", 0),
                        action.get("y", 100)
                    )
                return "Scrolled page"
                
            return f"Executed {action_type}"
            
        except PlaywrightTimeoutError:
            return f"Timeout during {action_type}"
        except Exception as e:
            return f"Error during {action_type}: {str(e)}"

    async def _get_authenticated_browser(self, playwright, headless: bool = False):
        """Browser launch with human-like settings"""
        return await playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ],
            slow_mo=random.randint(100, 300),
            channel="chrome",
            ignore_default_args=["--enable-automation"]
        )

    async def _get_authenticated_context(self, browser):
        """Create stealthy browsing context"""
        context = await browser.new_context(
            viewport={'width': random.randint(1200, 1400), 'height': random.randint(700, 800)},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{}.0.{}.{} Safari/537.36'.format(
                random.randint(90, 120),
                random.randint(1000, 5000),
                random.randint(100, 999)
            ),
            locale='en-US',
            permissions=['geolocation'],
            color_scheme='light',
            timezone_id='America/New_York'
        )
        
        await context.add_init_script("""
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        navigator.webdriver = false;
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        return context

    async def execute_actions(self, prompt: str, screenshot_callback: Optional[Callable] = None):
        """Legacy method that can delegate to execute_stream"""
        def adapter(data):
            if data["type"] == "action" and screenshot_callback:
                asyncio.create_task(self._capture_screenshot(screenshot_callback))
        await self.execute_stream(prompt, adapter)

    async def _capture_screenshot(self, callback: Callable):
        """Optional screenshot fallback"""
        if self.active_page:
            await callback(await self.active_page.screenshot())