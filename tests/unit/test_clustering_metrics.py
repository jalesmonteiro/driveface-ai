import pytest
import numpy as np
from apps.vision_pipeline.clustering import FaceClustering
from albums.models import Album, Job
from albums.serializers import JobStatusSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="academic_researcher@ufrn.edu.br",
        password="ValidPassword123!",
        full_name="Pesquisador PPgTI",
    )


@pytest.fixture
def test_album(db, test_user):
    return Album.objects.create(
        owner=test_user,
        google_drive_folder_id="drive_folder_academic_123",
        folder_name="Evento Acadêmico UFRN",
    )


class TestClusteringMetrics:
    def test_compute_intrinsic_metrics_normal(self):
        """Valida o cálculo de Silhouette e DB Index com múltiplos clusters coesos."""
        clusterer = FaceClustering(eps=0.40, min_samples=2)

        # 3 clusters bem definidos com 10 vetores cada + 2 ruídos
        rng = np.random.RandomState(42)
        c1 = rng.randn(512)
        c1 /= np.linalg.norm(c1)
        c2 = rng.randn(512)
        c2 /= np.linalg.norm(c2)
        c3 = rng.randn(512)
        c3 /= np.linalg.norm(c3)

        vectors = []
        labels = []
        for _ in range(10):
            v1 = c1 + rng.randn(512) * 0.015
            vectors.append(v1 / np.linalg.norm(v1))
            labels.append(0)

        for _ in range(10):
            v2 = c2 + rng.randn(512) * 0.015
            vectors.append(v2 / np.linalg.norm(v2))
            labels.append(1)

        for _ in range(10):
            v3 = c3 + rng.randn(512) * 0.015
            vectors.append(v3 / np.linalg.norm(v3))
            labels.append(2)

        # 2 ruídos
        for _ in range(2):
            vr = rng.randn(512)
            vectors.append(vr / np.linalg.norm(vr))
            labels.append(-1)

        embs = np.array(vectors, dtype=np.float32)
        lbls = np.array(labels, dtype=int)

        metrics = clusterer.compute_intrinsic_metrics(embs, lbls)

        assert metrics["total_faces"] == 32
        assert metrics["clustered_faces"] == 30
        assert metrics["noise_faces"] == 2
        assert metrics["clusters_count"] == 3
        assert metrics["silhouette_score"] is not None
        assert metrics["silhouette_score"] > 0.60
        assert metrics["davies_bouldin_score"] is not None
        assert metrics["davies_bouldin_score"] < 1.0

    def test_compute_intrinsic_metrics_edge_cases(self):
        """Valida que edge cases (vazio, cluster único, só ruído) não levantam exceções."""
        clusterer = FaceClustering()

        # Vazio
        empty_res = clusterer.compute_intrinsic_metrics(np.array([]), np.array([]))
        assert empty_res["total_faces"] == 0
        assert empty_res["silhouette_score"] is None
        assert empty_res["davies_bouldin_score"] is None

        # Cluster único (Silhouette requer >= 2 clusters)
        single_cluster_embs = np.random.randn(5, 512)
        single_cluster_labels = np.array([0, 0, 0, 0, 0])
        single_res = clusterer.compute_intrinsic_metrics(single_cluster_embs, single_cluster_labels)
        assert single_res["clusters_count"] == 1
        assert single_res["silhouette_score"] is None
        assert single_res["davies_bouldin_score"] is None

        # Apenas ruído (-1)
        noise_embs = np.random.randn(4, 512)
        noise_labels = np.array([-1, -1, -1, -1])
        noise_res = clusterer.compute_intrinsic_metrics(noise_embs, noise_labels)
        assert noise_res["clusters_count"] == 0
        assert noise_res["noise_faces"] == 4
        assert noise_res["silhouette_score"] is None

    def test_job_model_and_serializer_clustering_metrics(self, db, test_album):
        """Garante que Job armazena e o serializer expõe clustering_metrics."""
        job = Job.objects.create(
            album=test_album,
            status=Job.Status.COMPLETED,
            total_images=20,
            processed_images=20,
            clustering_metrics={
                "silhouette_score": 0.68,
                "davies_bouldin_score": 0.52,
                "clusters_count": 5,
                "total_faces": 28,
            },
        )

        # Leitura do banco
        job.refresh_from_db()
        assert job.clustering_metrics["silhouette_score"] == 0.68
        assert job.clustering_metrics["davies_bouldin_score"] == 0.52

        # Serializer DRF
        serializer = JobStatusSerializer(job)
        data = serializer.data
        assert "clustering_metrics" in data
        assert data["clustering_metrics"]["silhouette_score"] == 0.68
        assert data["clustering_metrics"]["davies_bouldin_score"] == 0.52
