import gradio as gr
import time
import threading

class VirtualBrowser:
    def __init__(self):
        self.current_frame = None
        self.running = False
        
    def update_frame(self, b64_image: str):
        """Callback for frame updates"""
        self.current_frame = b64_image
        
    def start_stream(self, automator, actions_json):
        """Start execution in virtual mode"""
        self.running = True
        automator.set_virtual_mode(True, self.update_frame)
        automator.execute_actions(actions_json)
        self.running = False
        
    def get_current_frame(self):
        """Get latest frame for Gradio"""
        if self.current_frame:
            return f"data:image/png;base64,{self.current_frame}"
        return None