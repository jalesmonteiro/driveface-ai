"""
Módulo de agrupamento não-supervisionado DBSCAN com distância de cosseno (Regra R_3).
eps = 0.40, min_samples = 2.
"""
import logging
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances

logger = logging.getLogger(__name__)


class FaceClustering:
    def __init__(self, eps: float = 0.40, min_samples: int = 2):
        self.eps = eps
        self.min_samples = min_samples

    def fit_predict(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Executa DBSCAN sobre matriz de distância de cosseno pré-computada.
        Retorna labels dos clusters (-1 para ruído / não agrupados).
        """
        if len(embeddings) == 0:
            return np.array([], dtype=int)

        dist_matrix = cosine_distances(embeddings)
        dbscan = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="precomputed")
        return dbscan.fit_predict(dist_matrix)
