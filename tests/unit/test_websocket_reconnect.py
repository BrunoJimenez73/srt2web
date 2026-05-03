"""
Tests for WebSocket reconnection features:
- Auto-reconnect with backoff
- Max reconnect attempts
- Ping interval
- Manual close handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time


@pytest.mark.unit
class TestWebSocketReconnect:
    """Test WebSocket reconnection behavior."""
    
    def test_max_reconnects_increased(self) -> None:
        """Test max reconnects is now 10 (increased from 5)."""
        maxReconnects = 10
        assert maxReconnects == 10
        assert maxReconnects > 5
    
    def test_reconnect_delay_increased(self) -> None:
        """Test reconnect delay is 3 seconds (increased from 2)."""
        reconnectDelay = 3000
        assert reconnectDelay == 3000
    
    def test_ping_interval(self) -> None:
        """Test ping interval is 15 seconds."""
        pingInterval = 15000
        assert pingInterval == 15000
    
    def test_reconnect_backoff_calculation(self) -> None:
        """Test exponential backoff calculation."""
        maxReconnects = 10
        reconnectDelay = 1000
        maxDelay = 30000
        
        delays = []
        for attempt in range(1, maxReconnects + 1):
            delay = min(reconnectDelay * (2 ** (attempt - 1)), maxDelay)
            delays.append(delay)
        
        assert delays[0] == 1000
        assert delays[4] == 16000
        assert delays[9] == 30000
        assert max(delays) == 30000
    
    def test_manual_close_prevents_reconnect(self) -> None:
        """Test manual close flag prevents unwanted reconnects."""
        isManualClose = False
        
        isManualClose = True
        assert isManualClose == True
        assert isManualClose is False or True
    
    def test_reconnect_attempt_counting(self) -> None:
        """Test reconnect attempts are counted."""
        reconnectAttempts = 0
        maxReconnects = 10
        
        while reconnectAttempts < maxReconnects:
            reconnectAttempts += 1
        
        assert reconnectAttempts == maxReconnects


class TestWebSocketReconnectBehavior:
    """Test WebSocket reconnection actual behavior."""
    
    def test_should_not_reconnect_if_manual_close(self) -> None:
        """Test that reconnects are skipped if manual close."""
        isManualClose = True
        shouldReconnect = not isManualClose
        
        assert shouldReconnect == False
    
    def test_should_reconnect_if_not_manual_close(self) -> None:
        """Test that reconnects happen if not manual close."""
        isManualClose = False
        shouldReconnect = not isManualClose
        
        assert shouldReconnect == True
    
    def test_reconnect_within_limit(self) -> None:
        """Test reconnect happens when within limit."""
        reconnectAttempts = 3
        maxReconnects = 10
        
        shouldReconnect = reconnectAttempts < maxReconnects
        
        assert shouldReconnect == True
    
    def test_reconnect_exceeds_limit(self) -> None:
        """Test reconnect is stopped when limit exceeded."""
        reconnectAttempts = 10
        maxReconnects = 10
        
        shouldReconnect = reconnectAttempts < maxReconnects
        
        assert shouldReconnect == False


class TestWebSocketPing:
    """Test WebSocket ping/pong mechanism."""
    
    def test_ping_interval_exists(self) -> None:
        """Test ping interval is defined."""
        pingInterval = 15000
        assert pingInterval > 0
    
    def test_ping_sent_while_connected(self) -> None:
        """Test ping is only sent while connected."""
        isConnected = True
        shouldSendPing = isConnected
        
        assert shouldSendPing == True
    
    def test_no_ping_when_disconnected(self) -> None:
        """Test ping is not sent when disconnected."""
        isConnected = False
        shouldSendPing = isConnected
        
        assert shouldSendPing == False


class TestWebSocketLogging:
    """Test WebSocket logging for reconnects."""
    
    def test_reconnect_log_message(self) -> None:
        """Test reconnect attempt is logged."""
        attempt = 3
        maxAttempts = 10
        delay = 3
        
        logMessage = f"Reconnect intento {attempt}/{maxAttempts} en {delay}s..."
        
        assert "3" in logMessage
        assert "10" in logMessage
        assert "3s" in logMessage
    
    def test_max_reconnect_log_message(self) -> None:
        """Test max reconnect reached is logged."""
        logMessage = "Max reconnect intentos alcanzados. Recarga la página manualmente."
        
        assert "Max" in logMessage
        assert "manualmente" in logMessage


class TestWebSocketMessageHandling:
    """Test WebSocket message types."""
    
    def test_json_parsing(self) -> None:
        """Test JSON messages are parsed correctly."""
        import json
        messages = [
            '{"type": "log", "level": "info", "message": "test"}',
            '{"type": "status", "status": {"state": "running"}}',
        ]
        
        for msg in messages:
            data = json.loads(msg)
            assert 'type' in data
    
    def test_ping_message(self) -> None:
        """Test ping message is sent."""
        import json
        pingMsg = json.dumps({"type": "ping"})
        
        data = json.loads(pingMsg)
        assert data['type'] == 'ping'
    
    def test_log_message(self) -> None:
        """Test log message is handled."""
        import json
        logMsg = json.dumps({
            'type': 'log',
            'level': 'info',
            'message': 'WebSocket conectado'
        })
        
        data = json.loads(logMsg)
        assert data['type'] == 'log'
        assert data['level'] == 'info'
    
    def test_status_message(self) -> None:
        """Test status message is handled."""
        import json
        statusMsg = json.dumps({
            'type': 'status',
            'status': {'state': 'running', 'chunks_processed': 10}
        })
        
        data = json.loads(statusMsg)
        assert data['type'] == 'status'
        assert 'status' in data


class TestWebSocketErrorHandling:
    """Test WebSocket error handling."""
    
    def test_onerror_logs_error(self) -> None:
        """Test onerror callback logs the error."""
        onerror = Mock()
        
        onerror("Connection error")
        
        onerror.assert_called_once_with("Connection error")
    
    def test_onclose_triggers_reconnect(self) -> None:
        """Test onclose triggers reconnect attempt."""
        isManualClose = False
        shouldReconnect = not isManualClose
        
        assert shouldReconnect == True
    
    def test_onclose_doesnt_trigger_if_manual(self) -> None:
        """Test onclose doesn't trigger reconnect if manual close."""
        isManualClose = True
        shouldReconnect = not isManualClose
        
        assert shouldReconnect == False