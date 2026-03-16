/**
 * SRT2Web — WebSocket client
 * Handles real-time log streaming and status updates with automatic reconnection.
 */

class WSClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 50;
        this.baseReconnectDelay = 1000;  // Start with 1 second
        this.maxReconnectDelay = 30000;  // Max 30 seconds
        this.reconnectDelay = this.baseReconnectDelay;
        this.onLog = null;
        this.onStatus = null;
        this.onConnectionChange = null;
        this.connected = false;
        this.connecting = false;
        this.heartbeatInterval = null;
        this.lastPingTime = 0;
    }

    connect() {
        if (this.connecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return;
        }

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws/logs`;

        this.connecting = true;

        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                this.connected = true;
                this.connecting = false;
                this.reconnectAttempts = 0;
                this.reconnectDelay = this.baseReconnectDelay;
                console.log('[WS] Connected');
                this._startHeartbeat();
                if (this.onConnectionChange) {
                    this.onConnectionChange(true);
                }
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'log' && this.onLog) {
                        this.onLog(data);
                    } else if (data.type === 'status' && this.onStatus) {
                        this.onStatus(data);
                    } else if (data.type === 'pong') {
                        this.lastPingTime = Date.now();
                    }
                } catch (e) {
                    console.warn('[WS] Parse error:', e);
                }
            };

            this.ws.onclose = (event) => {
                this.connected = false;
                this.connecting = false;
                this._stopHeartbeat();
                console.log('[WS] Disconnected (code: ' + event.code + ')');
                if (this.onConnectionChange) {
                    this.onConnectionChange(false);
                }
                this._scheduleReconnect();
            };

            this.ws.onerror = (err) => {
                console.warn('[WS] Error:', err);
                // onerror is usually followed by onclose
            };

        } catch (e) {
            console.error('[WS] Connection failed:', e);
            this.connecting = false;
            this._scheduleReconnect();
        }
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WS] Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        // Exponential backoff with jitter
        const jitter = Math.random() * 0.3 * this.reconnectDelay;
        const delay = Math.min(this.reconnectDelay + jitter, this.maxReconnectDelay);
        
        console.log(`[WS] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts})`);
        
        // Double the delay for next attempt (exponential backoff)
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        
        setTimeout(() => this.connect(), delay);
    }

    _startHeartbeat() {
        this._stopHeartbeat();
        this.lastPingTime = Date.now();
        
        // Send ping every 30 seconds
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
                
                // If no pong received in 10 seconds, assume connection is dead
                if (Date.now() - this.lastPingTime > 10000) {
                    console.warn('[WS] Heartbeat timeout, reconnecting...');
                    this.ws.close();
                }
            }
        }, 30000);
    }

    _stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    disconnect() {
        this._stopHeartbeat();
        this.maxReconnectAttempts = 0;  // Prevent reconnection
        if (this.ws) {
            this.ws.close();
        }
    }

    requestStatus() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'get_status' }));
        }
    }

    ping() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
        }
    }
}

// Global instance
const wsClient = new WSClient();
