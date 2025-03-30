# **OpenThanos: AI-Powered Browser Automation**  

## **1. Introduction**  
OpenThanos is an AI-powered browser automation tool that converts plain English instructions into Playwright commands using OpenAI. It automates web tasks while simulating human-like behavior—including natural typing delays and occasional "mistakes"—to make interactions appear more organic and bypass bot detection. The tool provides step-by-step visual feedback through screenshots and works seamlessly in Docker for easy deployment.  

## **2. Features**  
- **Natural Language Automation**: Execute browser tasks by providing simple text instructions.  
- **Step-by-Step Visual Feedback**: Automatically captures screenshots for better understanding.  
- **Cross-Platform Compatibility**: Works on Windows, macOS, and Linux.  
- **Docker Support**: Runs in a containerized environment for easy deployment.  
- **AI Agent Integration**: Compatible with OpenAI Agents SDK for advanced automation.  

---

## **3. Setup Instructions**  

### **3.1 Prerequisites**  
To use OpenThanos, ensure you have the following:  
- **[Docker Desktop](https://www.docker.com/products/docker-desktop)** – Required for running OpenThanos in a containerized environment.  
- **Python 3.12+** – Required for local development (not needed if using Docker).  

---

### **3.2 Quick Installation and Usage**  

To install and run OpenThanos using Docker, follow these steps:  
```bash
# Clone the repository
git clone <repo url>
cd openthanos

# Build and run using Docker
docker build -t thanos-automator .
docker run -p 7860:7860 -it thanos-automator

# Access the interface at:
http://localhost:7860 

---

## **4. Running OpenThanos Locally (Without Docker)**  

If you prefer running OpenThanos without Docker, follow these steps:  
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
playwright install

# Run the application
python app.py
```  

---

## **5. API Integration**  

OpenThanos can be integrated into other applications using Python:  
```python
from automation.agent_tools import AutomationToolkit

toolkit = AutomationToolkit()
result = toolkit.browse_web("Search for AI news on TechCrunch")
```  

---

## **6. Example Commands**  

You can test the following commands in the OpenThanos interface:  
- **"Search for cricket on Google"**  
- **"Open Wikipedia and find information about artificial intelligence"**  
- **"Check trending repositories on GitHub"**  

---

## **7. License**  

OpenThanos is available under the **MIT License**. See [LICENSE](LICENSE) for more details.  

---

## **8. Important Notes**  

If you plan to use OpenAI’s API with OpenThanos, create a `.env` file in the project folder and add your API key:  
```ini
OPENAI_API_KEY=your_api_key_here
```  
