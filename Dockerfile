# 1. Start with Playwright's ready-to-use image
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# 2. Copy your files (no changes needed)
WORKDIR /app
COPY . .

# 3. Install Python dependencies
RUN pip install -r requirements.txt

# 4. Set up the browser (automatically handled by Playwright image)
RUN playwright install chromium

# 5. Make Gradio accessible
ENV GRADIO_SERVER_NAME=0.0.0.0

# 6. Launch command (same as running locally)
CMD ["python", "app.py"]