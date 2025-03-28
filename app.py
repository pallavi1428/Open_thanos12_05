import os
import time
from dotenv import load_dotenv
import gradio as gr
from automation.core import BrowserAutomator
from automation.screenshot import ScreenshotManager

# Load environment
load_dotenv()

# Initialize components
automator = BrowserAutomator(os.getenv("OPENAI_API_KEY"))
screenshot_manager = ScreenshotManager()

def process_prompt(prompt: str) -> tuple:
    """Handle the workflow from prompt to execution."""
    screenshot_manager.reset()
    
    try:
        # Get AI response
        start_time = time.time()
        actions = automator.get_ai_response(prompt)
        ai_time = time.time() - start_time
        
        # Execute actions
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
        
        # Get the final screenshot to display
        current_img = screenshot_manager.get_current()
        status = (
            f"Screenshot {screenshot_manager.current_index + 1} of {len(screenshot_manager.history)}" 
            if screenshot_manager.history else "No screenshots"
        )
        
        return log_output, current_img, status
    
    except Exception as e:
        return f"Error occurred: {str(e)}", None, "Error"

# Define Examples
examples = [
    ["Search cricket on Google"],
    ["Go to example.com and click on the first link"],
    ["Open Wikipedia and search for artificial intelligence"],
    ["Search for latest iPhone models on Amazon"],
    ["Check trending repositories on GitHub"]
]

# Create Gradio interface
with gr.Blocks(css="""
#screenshot-nav { display: flex; justify-content: center; gap: 10px; margin-top: 10px; }
#screenshot-container { border: 1px solid #ccc; padding: 10px; border-radius: 5px; margin-top: 10px; }
#screenshot-status { text-align: center; margin-top: 5px; font-style: italic; }
""") as demo:
    gr.Markdown("# 🤖 Advanced Browser Automation with Screenshots")
    gr.Markdown("Enter natural language instructions for browser automation. Examples: 'Search cricket on Google', 'Book a table for 2 at OpenTable'")
    
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

if __name__ == "__main__":
    demo.launch()