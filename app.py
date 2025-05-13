import os
import uuid
import asyncio
import threading
import gradio as gr
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from automation.core import BrowserAutomator
from automation.virtual_browser import VirtualBrowserManager
from automation.screenshot import ScreenshotManager
from dotenv import load_dotenv

load_dotenv()

# Initialize components
automator = BrowserAutomator(os.getenv("OPENAI_API_KEY"))
screenshot_manager = ScreenshotManager()
vb_manager = VirtualBrowserManager()

# Create Gradio app
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 OpenThanos Browser Automation")
    
    with gr.Tab("🔧 Manual Mode"):
        with gr.Row():
            with gr.Column():
                prompt_input = gr.Textbox(lines=2, placeholder="Enter automation command...")
                use_virtual = gr.Checkbox(label="Virtual Mode")
                run_btn = gr.Button("Run")
                output_log = gr.Textbox(label="Execution Log")
            
            with gr.Column():
                if use_virtual.value:
                    gr.HTML("<div id='virtual-browser'></div>")
                else:
                    screenshot = gr.Image(label="Screenshot")

    def execute_command(prompt, use_virtual):
        session_id = str(uuid.uuid4())
        try:
            actions = automator.get_ai_response(prompt)
            if use_virtual:
                automator.set_virtual_mode(True, vb_manager.update_frame)
                threading.Thread(
                    target=lambda: asyncio.run(
                        automator.execute_actions(session_id, actions)
                    )
                ).start()
                return "Running in virtual mode...", None
            else:
                log = automator.execute_actions(
                    session_id, 
                    actions,
                    screenshot_callback=screenshot_manager.capture
                )
                return log, screenshot_manager.get_current()
        except Exception as e:
            return f"Error: {str(e)}", None

    run_btn.click(
        execute_command,
        inputs=[prompt_input, use_virtual],
        outputs=[output_log, screenshot]
    )

# Create and configure FastAPI app
app = FastAPI()
app = gr.mount_gradio_app(app, demo, path="/")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        # Handle messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)  # Changed to 127.0.0.1