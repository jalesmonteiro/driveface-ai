"""
Módulo de detecção facial e extração de landmarks anatômicos (RetinaFace / SCRFD).
Garante limiar mínimo de confiança >= 0.80 (Regra R_5).
"""
import logging
from typing import List, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class FaceDetector:
    def __init__(self, confidence_threshold: float = None):
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(settings, "FACE_DETECTION_CONFIDENCE_THRESHOLD", 0.80)
        )

    def detect_faces(self, image_bytes) -> List[Dict[str, Any]]:
        """
        Recebe buffer de imagem e retorna bounding boxes e landmarks.
        Rejeita predições com confiança < confidence_threshold.
        """
        # Implementação detalhada na Task 3.1
        return []
