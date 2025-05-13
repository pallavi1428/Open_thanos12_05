import base64
import time
from typing import Dict, List, Optional, Callable
from PIL import Image
import io

class VirtualBrowserManager:
    def __init__(self):
        self.active_sessions = {}
        self.frame_callbacks = []
        
    def register_callback(self, callback: Callable):
        """Register frame update callback"""
        self.frame_callbacks.append(callback)
        
    def update_frame(self, data: Dict):
        """Handle new frame data from automation"""
        session_id = data["session_id"]
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "frames": [],
                "actions": [],
                "last_update": time.time()
            }
            
        frame_data = {
            "timestamp": time.time(),
            "image": base64.b64decode(data["frame"]),
            "action": data["action"]
        }
        
        self.active_sessions[session_id]["frames"].append(frame_data)
        self.active_sessions[session_id]["actions"].append(data["action"])
        self.active_sessions[session_id]["last_update"] = time.time()
        
        for callback in self.frame_callbacks:
            callback(frame_data)
            
    def get_latest_frame(self, session_id: str) -> Optional[Dict]:
        """Get most recent frame for a session"""
        if session_id in self.active_sessions and self.active_sessions[session_id]["frames"]:
            return self.active_sessions[session_id]["frames"][-1]
        return None
        
    def get_session_frames(self, session_id: str) -> List[Dict]:
        """Get all frames for a session"""
        return self.active_sessions.get(session_id, {}).get("frames", [])

    def cleanup_session(self, session_id: str):
        """Remove session data"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]