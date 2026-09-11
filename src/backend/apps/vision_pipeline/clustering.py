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

    def compute_intrinsic_metrics(self, embeddings: np.ndarray, labels: np.ndarray) -> dict:
        """
        Calcula métricas intrínsecas de qualidade do agrupamento não-supervisionado:
        - Silhouette Score (métrica de cosseno)
        - Davies-Bouldin Index
        - Contagens de ruído, total de clusters e proporção de ruído.
        """
        from sklearn.metrics import davies_bouldin_score, silhouette_score

        total_faces = len(embeddings)
        if total_faces == 0:
            return {
                "silhouette_score": None,
                "davies_bouldin_score": None,
                "total_faces": 0,
                "clustered_faces": 0,
                "noise_faces": 0,
                "noise_ratio": 0.0,
                "clusters_count": 0,
            }

        valid_mask = labels != -1
        valid_embeddings = embeddings[valid_mask]
        valid_labels = labels[valid_mask]
        unique_clusters = np.unique(valid_labels) if len(valid_labels) > 0 else np.array([])
        noise_count = int(np.sum(~valid_mask))
        clusters_count = int(len(unique_clusters))

        sil_score = None
        db_score = None

        # Silhouette e Davies-Bouldin exigem pelo menos 2 clusters e amostras suficientes
        if clusters_count >= 2 and len(valid_embeddings) > clusters_count:
            try:
                sil_score = float(silhouette_score(valid_embeddings, valid_labels, metric="cosine"))
            except Exception as e:
                logger.warning(f"Erro ao calcular silhouette_score: {e}")
                sil_score = None

            try:
                db_score = float(davies_bouldin_score(valid_embeddings, valid_labels))
            except Exception as e:
                logger.warning(f"Erro ao calcular davies_bouldin_score: {e}")
                db_score = None

        return {
            "silhouette_score": round(sil_score, 4) if sil_score is not None else None,
            "davies_bouldin_score": round(db_score, 4) if db_score is not None else None,
            "total_faces": total_faces,
            "clustered_faces": int(len(valid_embeddings)),
            "noise_faces": noise_count,
            "noise_ratio": round(noise_count / total_faces, 4) if total_faces > 0 else 0.0,
            "clusters_count": clusters_count,
        }
