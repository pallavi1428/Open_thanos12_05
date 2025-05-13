class VirtualBrowserUI {
    constructor() {
        this.ws = new WebSocket(`ws://${window.location.host}/ws`);
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.getElementById('execute-btn').addEventListener('click', () => {
            const command = document.getElementById('command-input').value;
            this.ws.send(`EXECUTE:${command}`);
        });

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.renderUpdate(data);
        };
    }

    renderUpdate(data) {
        // Update URL bar
        document.getElementById('url-display').textContent = data.data?.url || '';

        // Update DOM
        if (data.data?.html) {
            const domContainer = document.getElementById('dom-container');
            domContainer.innerHTML = data.data.html;
            
            // Highlight interactive elements
            data.data?.interactive_elements?.forEach(el => {
                const element = document.querySelector(el.selector);
                if (element) {
                    element.style.boxShadow = '0 0 0 2px rgba(0, 100, 255, 0.3)';
                }
            });
        }

        // Update action log
        const log = document.getElementById('action-log');
        if (data.type === 'action') {
            log.innerHTML += `<div class="log-entry">
                <span class="action-type">${data.action.type}</span>
                <span class="action-details">${JSON.stringify(data.action)}</span>
            </div>`;
        }
    }
}

new VirtualBrowserUI();