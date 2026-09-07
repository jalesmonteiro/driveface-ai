"""
Módulo extrator de características profundas ArcFace (D = 512) com normalização L2.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


class FeatureExtractor:
    def __init__(self, model_name: str = "buffalo_l", device: str = "cpu"):
        self.model_name = model_name
        self.device = device

    def extract_embedding(self, aligned_face_image) -> np.ndarray:
        """
        Extrai vetor denso de 512 dimensões com ||v||_2 = 1.0.
        """
        # Implementação detalhada na Task 3.2
        vec = np.zeros(512, dtype=np.float32)
        vec[0] = 1.0
        return vec
