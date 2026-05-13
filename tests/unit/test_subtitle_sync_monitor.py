import pytest

from core.subtitle_sync_monitor import SubtitleSyncMonitor


class TestSubtitleSyncMonitor:
    def test_drift_detection_gradual(self):
        """Drift gradual debe detectarse"""
        monitor = SubtitleSyncMonitor(threshold_ms=500)

        # Simular drift gradual: +10ms por iteración
        for i in range(10):
            audio_ts = 1000 + i * 10
            subtitle_ts = 1000
            correction = monitor.check_sync(audio_ts, subtitle_ts)

        # Después de 10 iteraciones, drift suavizado debe estar cerca de 77ms
        assert abs(monitor.get_drift_ms() - 77) < 10

    def test_drift_detection_abrupt(self):
        """Salto abrupto de drift debe detectarse rápido"""
        monitor = SubtitleSyncMonitor(threshold_ms=500)

        # Salto de 200ms
        correction = monitor.check_sync(1200, 1000)

        # Drift suavizado debe ser ~60ms después del smoothing
        assert abs(monitor.get_drift_ms() - 60) < 30

    def test_correction_active_when_threshold_exceeded(self):
        """Corrección debe activarse si drift > threshold"""
        monitor = SubtitleSyncMonitor(threshold_ms=500)

        # Simular drift grande: audio adelantado 800ms
        for _ in range(20):
            monitor.check_sync(1800, 1000)

        assert monitor.correction_active is True
        assert monitor.get_state() == "correcting"

    def test_state_transitions(self):
        """Estados deben cambiar correctamente"""
        monitor = SubtitleSyncMonitor(threshold_ms=500)

        # Inicialmente: in_sync
        assert monitor.get_state() == "in_sync"

        # Pequeño drift: drifting
        for _ in range(10):
            monitor.check_sync(1150, 1000)
        assert monitor.get_state() == "drifting"

        # Gran drift: correcting
        for _ in range(20):
            monitor.check_sync(1800, 1000)
        assert monitor.get_state() == "correcting"

        # Volver a normal: in_sync
        for _ in range(30):
            monitor.check_sync(1005, 1000)  # Casi sin drift
        assert monitor.get_state() == "in_sync"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
