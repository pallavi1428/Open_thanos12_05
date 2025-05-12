import os
import json
import random
import time
import base64
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
        self.screenshot_history = []
        self.current_screenshot_index = -1
        self.virtual_mode = False
        self.frame_callback = None
        self.active_sessions = {}

    async def get_ai_response(self, prompt: str) -> Dict[str, Any]:
        """Your existing AI response generation"""
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)

    async def execute_actions(self, session_id: str, actions_json: Dict[str, Any], 
                           screenshot_callback: Optional[Callable] = None,
                           headless: bool = False) -> str:
        """Main execution entry point"""
        if self.virtual_mode:
            return await self._execute_virtual(session_id, actions_json)
        return await self._execute_real(session_id, actions_json, screenshot_callback, headless)

    async def _execute_virtual(self, session_id: str, actions_json: Dict[str, Any]) -> str:
        """Surf-like virtual browser execution"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await self._get_authenticated_context(browser)
            page = await context.new_page()
            self.active_sessions[session_id] = {"browser": browser, "page": page}
            
            log = []
            try:
                # Initial human-like activity
                await page.mouse.move(100, 100)
                await page.wait_for_timeout(500)
                
                for action_item in actions_json.get("output", []):
                    if action_item["type"] != "computer_call":
                        continue
                        
                    action = action_item["action"]
                    result = await self._perform_action(page, action)
                    log.append(result)
                    
                    if self.frame_callback:
                        screenshot = await page.screenshot()
                        self.frame_callback({
                            "session_id": session_id,
                            "frame": base64.b64encode(screenshot).decode('utf-8'),
                            "action": action
                        })
                        
            except Exception as e:
                log.append(f"⚠ Critical error: {str(e)}")
            finally:
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                await context.close()
                await browser.close()
        
            return "\n".join(log)

    async def _execute_real(self, session_id: str, actions_json: Dict[str, Any],
                          screenshot_callback: Optional[Callable],
                          headless: bool) -> str:
        """Original browser execution with screenshots"""
        async with async_playwright() as p:
            browser = await self._get_authenticated_browser(p, headless)
            context = await self._get_authenticated_context(browser)
            page = await context.new_page()
            self.active_sessions[session_id] = {"browser": browser, "page": page}
            
            log = []
            try:
                # Initial human-like activity
                await page.mouse.move(100, 100)
                await page.wait_for_timeout(500)
                
                for action_item in actions_json.get("output", []):
                    if action_item["type"] != "computer_call":
                        continue
                        
                    action = action_item["action"]
                    result = await self._perform_action(page, action)
                    log.append(result)
                    
                    if screenshot_callback:
                        screenshot = await page.screenshot()
                        screenshot_callback(screenshot)
                        self.screenshot_history.append(screenshot)
                        
            except Exception as e:
                log.append(f"⚠ Critical error: {str(e)}")
            finally:
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                await context.close()
                await browser.close()
        
            return "\n".join(log)

    async def _perform_action(self, page, action: Dict[str, Any]) -> str:
        """Execute single action with error handling"""
        action_type = action.get("type")
        try:
            if action_type == "navigate":
                await page.goto(
                    action["url"],
                    wait_until=action.get("wait_until", "load"),
                    timeout=action.get("timeout", 30000)
                )
                return f"✓ Navigated to {action['url']}"
                
            elif action_type == "click":
                if not await self._try_selectors(
                    page,
                    action["selector"],
                    "click",
                    timeout=action.get("timeout", 5000),
                    click_count=action.get("click_count", 1)
                ):
                    raise Exception(f"Failed to click: {action['selector']}")
                return f"✓ Clicked: {action['selector'].split(',')[0].strip()}"
                
            elif action_type == "type":
                if not await self._try_selectors(
                    page,
                    action["selector"],
                    "type",
                    text=action["text"],
                    clear=action.get("clear", False)
                ):
                    raise Exception(f"Failed to type in: {action['selector']}")
                return f"✓ Typed '{action['text']}' into {action['selector'].split(',')[0].strip()}"
                
            # Add other action types as needed...
            
            await page.wait_for_timeout(random.randint(200, 800))
            return f"✓ Executed {action_type}"
            
        except PlaywrightTimeoutError:
            return f"⌛ Timeout during {action_type}"
        except Exception as e:
            return f"❌ Error during {action_type}: {str(e)}"

    # [Keep all your existing helper methods (_try_selectors, _human_type, etc.)]
    
    def set_virtual_mode(self, enabled: bool, callback: Optional[Callable] = None):
        """Toggle virtual browser mode"""
        self.virtual_mode = enabled
        self.frame_callback = callback

    async def close_session(self, session_id: str):
        """Cleanup specific session"""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            await session["page"].close()
            await session["browser"].close()