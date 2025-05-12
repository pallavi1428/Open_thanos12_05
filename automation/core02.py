import os
import json
import random
import time
import base64
from typing import Dict, Any, List, Optional, Callable
from openai import OpenAI
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

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
        self.screenshot_history = []
        self.current_screenshot_index = -1
    

    def get_authenticated_browser(self, playwright):
        """Launch browser with human-like settings"""
        return playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ],
            slow_mo=random.randint(100, 300),  # Random delays
            channel="chrome",
            ignore_default_args=["--enable-automation"]
        )

    def get_authenticated_context(self, browser):
        """Create stealthy browsing context"""
        context = browser.new_context(
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
        
        # Remove automation痕迹
        context.add_init_script("""
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        navigator.webdriver = false;
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        return context

    def human_type(self, page, selector: str, text: str):
        """Type like a human with random delays"""
        for char in text:
            page.type(selector, char, delay=random.randint(50, 250))
            if random.random() > 0.9:  # 10% chance to "mistake"
                page.keyboard.press('Backspace')
                page.wait_for_timeout(random.randint(50, 200))
                page.type(selector, char)

    def get_ai_response(self, prompt: str) -> Dict[str, Any]:
        """Get structured actions from OpenAI (unchanged)"""
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)

    def try_selectors(self, page, selectors: str, action: str, **kwargs) -> bool:
        """Enhanced with human-like interactions"""
        selector_list = [s.strip() for s in selectors.split(",")]
        
        for selector in selector_list:
            try:
                if action == "click":
                    # Human-like mouse movement
                    box = page.locator(selector).bounding_box()
                    if box:
                        x = box['x'] + random.randint(5, 15)
                        y = box['y'] + random.randint(5, 15)
                        page.mouse.move(x, y)
                        page.wait_for_timeout(random.randint(100, 500))
                    page.click(selector, **kwargs)
                    
                elif action == "type":
                    if kwargs.get("clear", False):
                        page.fill(selector, "")
                    self.human_type(page, selector, kwargs["text"])
                    
                elif action == "fill":
                    page.fill(selector, kwargs["text"])
                    
                elif action == "wait_for":
                    page.wait_for_selector(selector, state=kwargs.get("state", "visible"), 
                                         timeout=kwargs.get("timeout", 5000))
                return True
            except Exception:
                continue
        return False

    def execute_actions(self, actions_json: Dict[str, Any], 
                       screenshot_callback: Optional[Callable] = None,
                       headless: bool = False) -> str:
        """Execute actions with anti-bot measures"""
        results = []
        with sync_playwright() as p:
            browser = self.get_authenticated_browser(p)
            context = self.get_authenticated_context(browser)
            page = context.new_page()
            
            try:
                # Initial human-like activity
                page.mouse.move(100, 100)
                page.wait_for_timeout(500)
                
                for action_item in actions_json.get("output", []):
                    if action_item["type"] != "computer_call":
                        continue
                        
                    action = action_item["action"]
                    action_type = action.get("type")
                    results.append(f"Executing: {action_type}")
                    
                    try:
                        if action_type == "navigate":
                            page.goto(
                                action["url"],
                                wait_until=action.get("wait_until", "load"),
                                timeout=action.get("timeout", 30000),
                                referer="https://www.google.com/"
                            )
                            results.append(f"✓ Navigated to {action['url']}")
                            page.wait_for_timeout(random.randint(1000, 3000))  # Human delay
                            
                        elif action_type == "click":
                            if not self.try_selectors(
                                page,
                                action["selector"],
                                "click",
                                timeout=action.get("timeout", 5000),
                                click_count=action.get("click_count", 1),
                                delay=random.randint(50, 150)
                            ):
                                raise Exception(f"Failed to click on any selector: {action['selector']}")
                            results.append(f"✓ Clicked: {action['selector'].split(',')[0].strip()}")
                            
                        elif action_type == "type":
                            if not self.try_selectors(
                                page,
                                action["selector"],
                                "type",
                                text=action["text"],
                                clear=action.get("clear", False)
                            ):
                                raise Exception(f"Failed to type in any selector: {action['selector']}")
                            results.append(f"✓ Typed '{action['text']}' into {action['selector'].split(',')[0].strip()}")
                            
                        elif action_type == "keypress":
                            keys = action["keys"]
                            if isinstance(keys, str):
                                page.wait_for_timeout(random.randint(50, 200))
                                page.keyboard.press(keys)
                            else:
                                for key in keys:
                                    page.wait_for_timeout(random.randint(50, 200))
                                    page.keyboard.press(key)
                            results.append(f"✓ Pressed keys: {keys}")
                            
                        elif action_type == "wait":
                            if action.get("state") == "networkidle":
                                page.wait_for_load_state("networkidle", timeout=action.get("timeout", 10000))
                            else:
                                page.wait_for_timeout(action["timeout"])
                            results.append(f"✓ Waited for {action.get('timeout', 0)}ms")
                            
                        elif action_type == "scroll":
                            if "selector" in action:
                                page.locator(action["selector"]).scroll_into_view_if_needed()
                            else:
                                page.mouse.wheel(
                                    action.get("x", random.randint(0, 100)), 
                                    action.get("y", random.randint(100, 300))
                                )
                            results.append("✓ Scrolled page")
                            
                        # Screenshot handling
                        if screenshot_callback:
                            screenshot_callback(page)
                            
                    except PlaywrightTimeoutError:
                        results.append(f"⌛ Timeout during {action_type} (selector: {action.get('selector', 'N/A')})")
                    except Exception as e:
                        results.append(f"❌ Error during {action_type}: {str(e)}")
                        
                    # Randomized delay between actions
                    if action_type not in ["wait", "navigate"]:
                        page.wait_for_timeout(random.randint(200, 800))
                        
            except Exception as e:
                results.append(f"⚠ Critical error: {str(e)}")
            finally:
                context.close()
                browser.close()
        
        return "\n".join(results)

    def execute_for_agent(self, prompt: str) -> Dict[str, Any]:
        """Agent-compatible execution with stealth"""
        actions = self.get_ai_response(prompt)
        return {
            "success": True,
            "log": self.execute_actions(actions, headless=False),  # Visible for debugging
            "actions": actions["output"]
        }