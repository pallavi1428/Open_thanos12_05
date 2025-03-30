import os
import logging
from typing import Optional
from automation.core import BrowserAutomator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tool decorator with fallback
try:
    from openai.agents import tool
    logger.info("Using official OpenAI Agents SDK")
except ImportError:
    logger.info("Using local tool implementation - install openai-agents for full functionality")
    
    def tool(func):
        """Local @tool decorator fallback"""
        func.is_tool = True  # Mark as tool
        func.tool_name = func.__name__  # Add tool name attribute
        func.tool_description = func.__doc__ or ""  # Store description
        return func

class AutomationToolkit:
    def __init__(self):
        """Initialize with your existing BrowserAutomator"""
        self.automator = BrowserAutomator(os.getenv("OPENAI_API_KEY"))
        self._setup_tools()

    def _setup_tools(self):
        """Register all available tools"""
        self.tools = {
            "browse_web": self.browse_web,
            "get_screenshot": self.get_screenshot
        }

    @tool
    def browse_web(self, instruction: str) -> str:
        """
        Perform web automation tasks. 
        
        Args:
            instruction: Natural language description of the task
                Example: "Search for AI news on TechCrunch"
                
        Returns:
            Execution log with results
        """
        try:
            actions = self.automator.get_ai_response(instruction)
            return self.automator.execute_actions(
                actions, 
                headless=False  # Keep visible for Gradio
            )
        except Exception as e:
            logger.error(f"Browser automation failed: {str(e)}")
            return f"Error: {str(e)}"

    @tool
    def get_screenshot(self, step: int) -> Optional[bytes]:
        """
        Retrieve screenshot from automation history.
        
        Args:
            step: Index of the screenshot to retrieve (0-based)
            
        Returns:
            Screenshot image bytes or None if not found
        """
        if hasattr(self.automator, 'screenshot_history'):
            try:
                return self.automator.screenshot_history[step]
            except IndexError:
                logger.warning(f"Screenshot step {step} not found")
        return None

    def as_tool_list(self) -> list:
        """Get tools in OpenAI-compatible format"""
        return [
            {
                "name": tool.tool_name,
                "description": tool.tool_description,
                "function": tool
            }
            for tool in self.tools.values()
        ]