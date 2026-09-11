"""
Módulo de auto-sugestão de identidade baseado em centróides normalizados.
Aplica obrigatoriamente o isolamento multi-tenant: WHERE user_id = owner_id (Regras R_1 e R_4).
"""
import logging
import numpy as np
from typing import Optional, Tuple
from faces.models import Identity

logger = logging.getLogger(__name__)


class IdentitySuggester:
    def __init__(self, threshold: float = 0.35):
        self.threshold = threshold

    @staticmethod
    def compute_centroid(embeddings: np.ndarray) -> np.ndarray:
        """Calcula centróide médio com normalização L2."""
        centroid = np.sum(embeddings, axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        return centroid

    def suggest_identity(self, centroid: np.ndarray, user_id) -> Optional[Tuple[Identity, float]]:
        """
        Consulta centróides com isolamento estrito WHERE user_id = owner_id.
        Retorna (Identity, distance) se menor distância <= threshold, senão None.
        """
        # Consulta isolada por tenant com prefetch dos templates biométricos (Regra R_1)
        identities = Identity.objects.filter(user_id=user_id).prefetch_related("templates")
        if not identities.exists():
            return None

        best_identity = None
        min_distance = float("inf")

        for identity in identities:
            # Avalia todos os templates biométricos associados à pessoa (Multi-Template FaceID)
            candidate_vectors = []
            if identity.centroid_embedding:
                candidate_vectors.append(identity.centroid_embedding)
            for tmpl in identity.templates.all():
                if tmpl.centroid_embedding:
                    candidate_vectors.append(tmpl.centroid_embedding)

            for cand in candidate_vectors:
                id_vec = np.array(cand, dtype=np.float32)
                # cosine distance = 1 - (u . v) para vetores normalizados L2
                dist = 1.0 - float(np.dot(centroid, id_vec))
                if dist < min_distance:
                    min_distance = dist
                    best_identity = identity

        if best_identity is not None and min_distance <= self.threshold:
            return best_identity, min_distance

        return None
