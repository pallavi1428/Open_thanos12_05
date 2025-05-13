import os
import base64
from typing import List, Dict
from openai.agents import tool
from openthanos.automation.core02 import BrowserAutomator
from automation.screenshot import ScreenshotManager

class AutomationToolkit:
    def __init__(self):
        self.automator = BrowserAutomator(os.getenv("OPENAI_API_KEY"))
        self.screenshot_mgr = ScreenshotManager()

    @tool
    def browse_web(self, instruction: str) -> Dict:
        """Perform web automation tasks with screenshot support.
        
        Args:
            instruction: Natural language description of the task
            
        Returns:
            {
                "log": List[str],
                "screenshots": List[dict],
                "summary": str
            }
        """
        actions = self.automator.get_ai_response(instruction)
        result = self.automator.execute_actions(actions)
        
        # Store screenshots for later retrieval
        for i, img_bytes in enumerate(self.automator.screenshot_history):
            self.screenshot_mgr.store_screenshot(f"step_{i}.png", img_bytes)
        
        return {
            "log": result["log"],
            "screenshots": [
                {"step": s["step"], "action": s["action"]} 
                for s in result["screenshots"]
            ],
            "summary": f"Completed {len(result['screenshots'])} steps"
        }

    @tool
    def get_screenshot(self, step: int) -> str:
        """Retrieve a specific screenshot by step number."""
        img_bytes = self.screenshot_mgr.get_screenshot(step)
        return base64.b64encode(img_bytes).decode('utf-8')