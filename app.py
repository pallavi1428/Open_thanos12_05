import os
import time
from dotenv import load_dotenv
import gradio as gr
from automation.core import BrowserAutomator
from automation.screenshot import ScreenshotManager
from automation.agent_tools import AutomationToolkit

# Load environment
load_dotenv()

# Initialize components
automator = BrowserAutomator(os.getenv("OPENAI_API_KEY"))
screenshot_manager = ScreenshotManager()
toolkit = AutomationToolkit()

def process_prompt(prompt: str) -> tuple:
    """Original workflow handler"""
    screenshot_manager.reset()
    try:
        start_time = time.time()
        actions = automator.get_ai_response(prompt)
        ai_time = time.time() - start_time
        
        start_time = time.time()
        execution_log = automator.execute_actions(
            actions,
            screenshot_callback=screenshot_manager.capture
        )
        exec_time = time.time() - start_time
        
        log_output = (
            f"AI Processing Time: {ai_time:.2f}s\n"
            f"Execution Time: {exec_time:.2f}s\n\n"
            f"Execution Log:\n{execution_log}"
        )
        
        current_img = screenshot_manager.get_current()
        status = (
            f"Screenshot {screenshot_manager.current_index + 1} of {len(screenshot_manager.history)}" 
            if screenshot_manager.history else "No screenshots"
        )
        return log_output, current_img, status
    except Exception as e:
        return f"Error occurred: {str(e)}", None, "Error"

def run_agent(prompt: str) -> str:
    """New agent handler"""
    try:
        return toolkit.browse_web(prompt)
    except Exception as e:
        return f"Agent error: {str(e)}"

# Define examples
examples = [
    ["Search cricket on Google"],
    ["Go to example.com and click on the first link"],
    ["Open Wikipedia and search for artificial intelligence"],
    ["Search for latest iPhone models on Amazon"],
    ["Check trending repositories on GitHub"]
]

# Build interface
with gr.Blocks(css="""
#screenshot-nav { display: flex; justify-content: center; gap: 10px; margin-top: 10px; }
#screenshot-container { border: 1px solid #ccc; padding: 10px; border-radius: 5px; margin-top: 10px; }
#screenshot-status { text-align: center; margin-top: 5px; font-style: italic; }
""") as demo:
    gr.Markdown("# 🤖 Advanced Browser Automation with Screenshots")
    
    with gr.Tab("🔧 Manual Mode"):
        with gr.Row():
            with gr.Column():
                prompt_input = gr.Textbox(lines=2, placeholder="Enter what you want to automate...", label="Instruction")
                submit_btn = gr.Button("Execute", variant="primary")
                log_output = gr.Textbox(label="Execution Log", interactive=False)
                
                with gr.Accordion("Examples", open=False):
                    gr.Examples(examples=examples, inputs=prompt_input, label="Click any example to load it")
            
            with gr.Column():
                with gr.Group(elem_id="screenshot-container"):
                    screenshot_output = gr.Image(label="Browser Screenshot", interactive=False)
                    screenshot_status = gr.Textbox(elem_id="screenshot-status", interactive=False, show_label=False)
                    with gr.Row(elem_id="screenshot-nav"):
                        prev_btn = gr.Button("Previous", variant="secondary")
                        next_btn = gr.Button("Next", variant="secondary")
    
    with gr.Tab("🤖 Agent Mode"):
        gr.Markdown("## Describe your task in natural language")
        agent_input = gr.Textbox(label="Task description", lines=3)
        agent_output = gr.Textbox(label="Agent Execution Log", interactive=False)
        agent_button = gr.Button("Run Agent", variant="primary")
    
    # Event handlers
    submit_btn.click(
        fn=process_prompt,
        inputs=prompt_input,
        outputs=[log_output, screenshot_output, screenshot_status]
    )
    prev_btn.click(
        fn=lambda: screenshot_manager.navigate("prev"),
        outputs=[screenshot_output, screenshot_status]
    )
    next_btn.click(
        fn=lambda: screenshot_manager.navigate("next"),
        outputs=[screenshot_output, screenshot_status]
    )
    agent_button.click(
        fn=run_agent,
        inputs=agent_input,
        outputs=agent_output
    )

if __name__ == "__main__":
    demo.launch()