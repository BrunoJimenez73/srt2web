# File: core/subtitle_sync_monitor.py
import logging
from typing import Optional

class SubtitleSyncMonitor:
    """Detecta y monitorea desfase (drift) entre audio y subtítulos"""
    
    def __init__(self, threshold_ms: int = 500, smoothing_factor: float = 0.7):
        self.threshold_ms: int = threshold_ms
        self.smoothing_factor: float = smoothing_factor
        self.drift_history: list[float] = []
        self.smoothed_drift: float = 0.0
        self.correction_active: bool = False
        self.logger = logging.getLogger(__name__)
    
    def check_sync(self, audio_timestamp_ms: float, subtitle_timestamp_ms: float) -> float:
        """
        Verifica sincronización y retorna factor de corrección.
        
        Args:
            audio_timestamp_ms: Timestamp actual del audio
            subtitle_timestamp_ms: Timestamp actual del subtítulo
        
        Returns:
            Correction factor (1.0 = sin corrección, 1.02 = corregir +2%)
        """
        # Calcular drift actual
        drift = audio_timestamp_ms - subtitle_timestamp_ms
        self.drift_history.append(drift)
        
        # Mantener historial acotado
        if len(self.drift_history) > 100:
            self.drift_history.pop(0)
        
        # Exponential smoothing
        if self.drift_history:
            self.smoothed_drift = (
                self.smoothing_factor * self.smoothed_drift +
                (1 - self.smoothing_factor) * drift
            )
        
        # Decidir si activar corrección
        if abs(self.smoothed_drift) > self.threshold_ms:
            self.correction_active = True
            # Retornar factor de corrección (ajuste pequeño)
            correction = 1.0 + (self.smoothed_drift / (audio_timestamp_ms + 1))
            self.logger.warning(
                f"Drift detected: {self.smoothed_drift:.1f}ms, "
                f"applying correction: {correction:.3f}"
            )
            return correction
        else:
            if self.correction_active:
                self.logger.info("Drift corrected, back to normal sync")
            self.correction_active = False
            return 1.0
    
    def get_drift_ms(self) -> float:
        """Retorna drift actual suavizado"""
        return self.smoothed_drift
    
    def get_state(self) -> str:
        """Retorna estado: 'in_sync', 'drifting', 'correcting'"""
        drift = abs(self.smoothed_drift)
        if drift < 100:
            return "in_sync"
        elif drift < 500:
            return "drifting"
        else:
            return "correcting"