/**
 * DeVitalik Thought Stream
 * A real-time stream of DeVitalik's thought process and actions
 */

class DeVitalikStream {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container with ID "${containerId}" not found`);
        }

        // Default options
        this.options = {
            maxEntries: options.maxEntries || 100,
            autoScroll: options.autoScroll !== undefined ? options.autoScroll : true,
            showTimestamp: options.showTimestamp !== undefined ? options.showTimestamp : true,
            theme: options.theme || 'light',
            reconnectAttempts: options.reconnectAttempts || 5,
            reconnectDelay: options.reconnectDelay || 3000
        };

        // Set theme
        if (this.options.theme === 'dark') {
            this.container.classList.add('dark-theme');
        }

        this.connectionAttempts = 0;
        this.connect();
    }

    connect() {
        try {
            this.ws = new WebSocket(DEVITALIK_STREAM.websocket);
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onerror = (error) => this.handleError(error);
            this.ws.onclose = () => this.handleClose();
            this.ws.onopen = () => {
                console.log('Connected to DeVitalik stream');
                this.connectionAttempts = 0;
            };
        } catch (error) {
            console.error('Failed to connect to DeVitalik stream:', error);
            this.handleError(error);
        }
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.addEntry(data);
            
            // Dispatch custom event for external listeners
            const customEvent = new CustomEvent('devitalik-thought', { 
                detail: data 
            });
            this.container.dispatchEvent(customEvent);
        } catch (error) {
            console.error('Error processing message:', error);
        }
    }

    addEntry(data) {
        const entry = document.createElement('div');
        entry.className = `thought-entry ${data.type}`;
        
        // Format timestamp if needed
        const timestamp = this.options.showTimestamp ? 
            new Date(data.timestamp).toLocaleTimeString() : '';
        
        entry.innerHTML = `
            ${this.options.showTimestamp ? 
                `<span class="timestamp">${timestamp}</span>` : ''}
            <span class="emoji">${data.emoji}</span>
            <span class="content">${this.escapeHtml(data.content)}</span>
        `;
        
        // Add data attributes for potential interactions
        if (data.data) {
            Object.entries(data.data).forEach(([key, value]) => {
                if (typeof value !== 'object') {
                    entry.dataset[key] = value;
                }
            });
        }
        
        this.container.appendChild(entry);
        
        // Auto-scroll if enabled
        if (this.options.autoScroll) {
            entry.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Maintain max entries limit
        while (this.container.children.length > this.options.maxEntries) {
            this.container.removeChild(this.container.firstChild);
        }
    }

    handleError(error) {
        console.error('DeVitalik Stream Error:', error);
        this.addEntry({
            timestamp: new Date().toISOString(),
            type: 'error',
            emoji: '❌',
            content: 'Connection error. Attempting to reconnect...'
        });
    }

    handleClose() {
        if (this.connectionAttempts < this.options.reconnectAttempts) {
            this.connectionAttempts++;
            console.log(`Reconnecting... Attempt ${this.connectionAttempts}`);
            setTimeout(() => this.connect(), this.options.reconnectDelay);
        } else {
            this.addEntry({
                timestamp: new Date().toISOString(),
                type: 'error',
                emoji: '⚠️',
                content: 'Connection lost. Please refresh the page.'
            });
        }
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Public methods
    setTheme(theme) {
        this.container.classList.remove('dark-theme');
        if (theme === 'dark') {
            this.container.classList.add('dark-theme');
        }
        this.options.theme = theme;
    }

    clear() {
        while (this.container.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
} 