from typing import List, Optional
from PIL import Image
import io

class ScreenshotManager:
    def __init__(self):
        self.history: List[bytes] = []
        self.current_index: int = -1

    def capture(self, page) -> None:
        """Capture a screenshot from the page."""
        screenshot_bytes = page.screenshot(full_page=True)
        self.history.append(screenshot_bytes)
        self.current_index = len(self.history) - 1

    def get_current(self) -> Optional[Image.Image]:
        """Get the current screenshot as PIL Image."""
        if not self.history or self.current_index < 0:
            return None
        
        img_bytes = self.history[self.current_index]
        return Image.open(io.BytesIO(img_bytes))

    def navigate(self, direction: str) -> tuple:
        """Navigate through screenshot history."""
        if direction == "prev" and self.current_index > 0:
            self.current_index -= 1
        elif direction == "next" and self.current_index < len(self.history) - 1:
            self.current_index += 1
        
        current_img = self.get_current()
        status = (
            f"Screenshot {self.current_index + 1} of {len(self.history)}" 
            if self.history else "No screenshots available"
        )
        return current_img, status

    def reset(self) -> None:
        """Reset the screenshot history."""
        self.history = []
        self.current_index = -1