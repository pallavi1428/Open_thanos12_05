import json
import time
from typing import Dict, Any
from openai import OpenAI
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

    def get_ai_response(self, prompt: str) -> Dict[str, Any]:
        """Get structured actions from OpenAI based on user prompt."""
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
        """Try multiple selectors for an action with fallback handling."""
        selector_list = [s.strip() for s in selectors.split(",")]
        
        for selector in selector_list:
            try:
                if action == "click":
                    page.click(selector, **kwargs)
                elif action == "type":
                    if kwargs.get("clear", False):
                        page.fill(selector, "")
                    page.type(selector, kwargs["text"], delay=kwargs.get("delay", 100))
                elif action == "fill":
                    page.fill(selector, kwargs["text"])
                elif action == "wait_for":
                    page.wait_for_selector(selector, state=kwargs.get("state", "visible"), 
                                         timeout=kwargs.get("timeout", 5000))
                return True
            except Exception:
                continue
        return False

    def execute_actions(self, actions_json: Dict[str, Any], screenshot_callback=None) -> str:
        """Execute the generated actions using Playwright with robust error handling."""
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=100)
            context = browser.new_context(viewport={'width': 1280, 'height': 720})
            page = context.new_page()
            
            try:
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
                                timeout=action.get("timeout", 30000)
                            )
                            results.append(f"✓ Navigated to {action['url']}")
                            
                        elif action_type == "click":
                            if not self.try_selectors(
                                page,
                                action["selector"],
                                "click",
                                timeout=action.get("timeout", 5000),
                                click_count=action.get("click_count", 1)
                            ):
                                raise Exception(f"Failed to click on any selector: {action['selector']}")
                            results.append(f"✓ Clicked: {action['selector'].split(',')[0].strip()}")
                            
                        elif action_type == "type":
                            if not self.try_selectors(
                                page,
                                action["selector"],
                                "type",
                                text=action["text"],
                                clear=action.get("clear", False),
                                delay=action.get("delay", 100)
                            ):
                                raise Exception(f"Failed to type in any selector: {action['selector']}")
                            results.append(f"✓ Typed '{action['text']}' into {action['selector'].split(',')[0].strip()}")
                            
                        elif action_type == "keypress":
                            keys = action["keys"]
                            if isinstance(keys, str):
                                page.keyboard.press(keys)
                            else:
                                for key in keys:
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
                                page.mouse.wheel(action.get("x", 0), action.get("y", 100))
                            results.append("✓ Scrolled page")
                            
                        # Call screenshot callback if provided
                        if screenshot_callback:
                            screenshot_callback(page)
                            
                    except PlaywrightTimeoutError:
                        results.append(f"⌛ Timeout during {action_type} (selector: {action.get('selector', 'N/A')})")
                    except Exception as e:
                        results.append(f"❌ Error during {action_type}: {str(e)}")
                        
                        # Capture screenshot on error if callback provided
                        if screenshot_callback:
                            try:
                                screenshot_callback(page)
                            except:
                                pass
                        
                    # Small delay between actions unless waiting is explicitly handled
                    if action_type not in ["wait", "navigate"]:
                        page.wait_for_timeout(300)
                        
            except Exception as e:
                results.append(f"⚠ Critical error: {str(e)}")
            finally:
                context.close()
                browser.close()
        
        return "\n".join(results)