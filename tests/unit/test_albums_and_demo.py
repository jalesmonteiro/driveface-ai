import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from albums.models import Album
from faces.models import Cluster, Face, Identity, Photo

User = get_user_model()


@pytest.mark.django_db
class TestDemoLoginAndAlbums:
    demo_login_url = "/api/v1/auth/demo-login/"
    albums_url = "/api/v1/albums/"

    def test_demo_login_issues_valid_jwt_and_accesses_albums(self, api_client):
        """Valida que o demo login emite tokens válidos e permite acessar a API de álbuns."""
        # 1. Requisição para o login demo
        response = api_client.post(self.demo_login_url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "alexandre.google@driveface.ai"

        # 2. Acesso à API de álbuns com o token retornado
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        albums_res = api_client.get(self.albums_url)
        assert albums_res.status_code == status.HTTP_200_OK
        assert isinstance(albums_res.json(), list)

    def test_album_list_includes_cover_url(self, api_client):
        """Valida que a listagem de álbuns inclui campo cover_url."""
        user = User.objects.create_user(
            email="owner@driveface.ai",
            password="StrongPassword123!",
            full_name="Album Owner",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_f1",
            folder_name="Viagem Praia 2026",
        )
        Photo.objects.create(
            album=album,
            google_file_id="photo_1",
            filename="foto1.jpg",
        )

        api_client.force_authenticate(user=user)
        res = api_client.get(self.albums_url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data) == 1
        assert data[0]["folder_name"] == "Viagem Praia 2026"
        assert "cover_url" in data[0]
        assert "api/v1/photos/" in data[0]["cover_url"]

    def test_delete_album_without_deleting_faceids(self, api_client):
        """Valida exclusão do álbum mantendo as FaceIDs cadastradas intactas."""
        user = User.objects.create_user(
            email="owner_del1@driveface.ai",
            password="StrongPassword123!",
            full_name="Owner Del",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_del_1",
            folder_name="Evento Corporativo",
        )
        identity = Identity.objects.create(
            user=user,
            person_name="Carlos Executivo",
            centroid_embedding=[0.1] * 512,
            total_samples=1,
        )
        Cluster.objects.create(
            album=album,
            identity=identity,
            label="Carlos Executivo",
            face_count=5,
        )

        api_client.force_authenticate(user=user)
        del_res = api_client.delete(f"/api/v1/albums/{album.id}/?delete_faceids=false")
        assert del_res.status_code == status.HTTP_200_OK
        assert not Album.objects.filter(id=album.id).exists()
        # Identity DEVE continuar existindo no banco
        assert Identity.objects.filter(id=identity.id).exists()

    def test_delete_album_with_deleting_faceids(self, api_client):
        """Valida exclusão do álbum removendo também as FaceIDs vinculadas se solicitado."""
        user = User.objects.create_user(
            email="owner_del2@driveface.ai",
            password="StrongPassword123!",
            full_name="Owner Del 2",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_del_2",
            folder_name="Festa de Fim de Ano",
        )
        identity = Identity.objects.create(
            user=user,
            person_name="Mariana Convidada",
            centroid_embedding=[0.2] * 512,
            total_samples=1,
        )
        Cluster.objects.create(
            album=album,
            identity=identity,
            label="Mariana Convidada",
            face_count=3,
        )

        api_client.force_authenticate(user=user)
        del_res = api_client.delete(f"/api/v1/albums/{album.id}/?delete_faceids=true")
        assert del_res.status_code == status.HTTP_200_OK
        assert not Album.objects.filter(id=album.id).exists()
        # Identity DEVE ter sido removida conforme solicitado pelo usuário
        assert not Identity.objects.filter(id=identity.id).exists()

    def test_cluster_avatar_endpoint_cached(self, api_client):
        """Valida que o endpoint de avatar retorna imagem em bytes a partir de base64 em cache."""
        import base64
        import io
        from PIL import Image

        user = User.objects.create_user(
            email="avatar_user@driveface.ai",
            password="StrongPassword123!",
            full_name="Avatar User",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_av_1",
            folder_name="Álbum Avatar",
        )

        # Gera uma imagem 160x160 válida em memória
        img = Image.new("RGB", (160, 160), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        b64_str = f"data:image/webp;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        cluster = Cluster.objects.create(
            album=album,
            label="Pessoa Teste",
            face_count=1,
            avatar_crop_webp=b64_str,
        )

        res = api_client.get(f"/api/v1/faces/clusters/{cluster.id}/avatar/")
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "image/webp"
        assert len(res.content) > 0

    def test_cluster_avatar_endpoint_dynamic_crop(self, api_client, monkeypatch):
        """Valida que o endpoint recorta dinamicamente o rosto específico a partir da foto."""
        import io
        from PIL import Image

        user = User.objects.create_user(
            email="dynamic_crop@driveface.ai",
            password="StrongPassword123!",
            full_name="Crop User",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_crop_1",
            folder_name="Álbum Crop",
        )
        photo = Photo.objects.create(
            album=album,
            google_file_id="photo_group_1",
            filename="foto_grupo.jpg",
            width=1000,
            height=1000,
        )
        cluster = Cluster.objects.create(
            album=album,
            label="Rosto Recortado",
            face_count=1,
            avatar_crop_webp="",
        )
        # Face em um canto específico da foto (ex: centro 40% a 60%)
        Face.objects.create(
            photo=photo,
            cluster=cluster,
            embedding=[0.0] * 512,
            bbox_xmin=0.4,
            bbox_ymin=0.4,
            bbox_xmax=0.6,
            bbox_ymax=0.6,
            detection_confidence=0.95,
        )

        # Mock do download da imagem do Google Drive
        def mock_download_stream(self, file_id):
            img = Image.new("RGB", (1000, 1000), color="red")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            buf.seek(0)
            return buf

        from google_integration.services import GoogleDriveService
        monkeypatch.setattr(GoogleDriveService, "download_image_stream", mock_download_stream)

        res = api_client.get(f"/api/v1/faces/clusters/{cluster.id}/avatar/")
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "image/webp"

        # Verifica que o avatar recortado foi salvo em cache no banco
        cluster.refresh_from_db()
        assert cluster.avatar_crop_webp.startswith("data:image/webp;base64,")

    def test_album_clusters_returns_job_progress(self, api_client):
        """Valida que a rota /api/v1/albums/<id>/clusters/ retorna o objeto de job com métricas de progresso."""
        from albums.models import Job

        user = User.objects.create_user(
            email="progress_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="Progress Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_prog_1",
            folder_name="Álbum com Progresso",
        )
        job = Job.objects.create(
            album=album,
            status=Job.Status.PROCESSING,
            total_images=50,
            processed_images=25,
        )

        api_client.force_authenticate(user=user)
        res = api_client.get(f"/api/v1/albums/{album.id}/clusters/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "job" in data
        assert data["job"]["status"] == "PROCESSING"
        assert data["job"]["total_images"] == 50
        assert data["job"]["processed_images"] == 25
        assert data["job"]["progress_percentage"] == 50.0

    def test_album_reprocess_endpoint(self, api_client, monkeypatch):
        """Valida que o endpoint /api/v1/albums/<id>/reprocess/ dispara o job na fila."""
        user = User.objects.create_user(
            email="reprocess_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="Reprocess Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_reproc_1",
            folder_name="Álbum Reprocess",
        )

        # Mock Celery delay
        mock_called = []
        from vision_pipeline.tasks import process_album_task
        monkeypatch.setattr(process_album_task, "delay", lambda job_id: mock_called.append(job_id))

        api_client.force_authenticate(user=user)
        res = api_client.post(f"/api/v1/albums/{album.id}/reprocess/")
        assert res.status_code == status.HTTP_202_ACCEPTED
        data = res.json()
        assert data["status"] == "PENDING"
        assert len(mock_called) == 1

    def test_cluster_name_creates_and_updates_persistent_faceid_identity(self, api_client):
        """Valida que nomear um cluster persiste a identidade biométrica (FaceID) com centróide 512-D."""
        user = User.objects.create_user(
            email="faceid_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="FaceID Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_fid_1",
            folder_name="Álbum FaceID",
        )
        photo = Photo.objects.create(
            album=album,
            google_file_id="photo_fid_1",
            filename="foto1.jpg",
        )
        cluster = Cluster.objects.create(
            album=album,
            label="Pessoa Desconhecida",
            face_count=2,
        )

        # Vetor 512-D com valor 1.0 na primeira dimensão (L2-normalizado)
        emb1 = [0.0] * 512
        emb1[0] = 1.0
        emb2 = [0.0] * 512
        emb2[0] = 1.0

        Face.objects.create(
            photo=photo,
            cluster=cluster,
            embedding=emb1,
            bbox_xmin=0.1,
            bbox_ymin=0.1,
            bbox_xmax=0.3,
            bbox_ymax=0.3,
            detection_confidence=0.99,
        )
        Face.objects.create(
            photo=photo,
            cluster=cluster,
            embedding=emb2,
            bbox_xmin=0.4,
            bbox_ymin=0.4,
            bbox_xmax=0.6,
            bbox_ymax=0.6,
            detection_confidence=0.98,
        )

        api_client.force_authenticate(user=user)
        res = api_client.post(f"/api/v1/faces/clusters/{cluster.id}/name/", {"person_name": "Maria Silva"})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["person_name"] == "Maria Silva"
        assert data["centroid_updated"] is True
        assert data["total_samples"] == 2

        # Valida que a Identity foi persistida no PostgreSQL
        from faces.models import Identity
        identity = Identity.objects.filter(user=user, person_name="Maria Silva").first()
        assert identity is not None
        assert identity.total_samples == 2
        assert len(identity.centroid_embedding) == 512
        assert identity.centroid_embedding[0] == 1.0

        # Cluster vinculado à Identity
        cluster.refresh_from_db()
        assert cluster.identity == identity
        assert cluster.label == "Maria Silva"

    def test_album_clusters_list_orders_outras_at_the_very_end(self, api_client):
        """Valida que o cluster 'Outras' é posicionado no final da grade, mesmo com a maior contagem de faces."""
        user = User.objects.create_user(
            email="order_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="Order Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_order_1",
            folder_name="Álbum Ordem",
        )
        # Cluster Outras com 80 faces (maior contagem)
        c_outras = Cluster.objects.create(
            album=album,
            label="Outras",
            face_count=80,
        )
        # Clusters identificados com menos faces
        c_ana = Cluster.objects.create(
            album=album,
            label="Ana",
            face_count=30,
        )
        c_carlos = Cluster.objects.create(
            album=album,
            label="Carlos",
            face_count=10,
        )

        api_client.force_authenticate(user=user)
        res = api_client.get(f"/api/v1/albums/{album.id}/clusters/")
        assert res.status_code == status.HTTP_200_OK
        clusters_resp = res.json()["clusters"]
        assert len(clusters_resp) == 3

        # A ordem deve ser: Ana (30), Carlos (10), e por último Outras (80)
        assert clusters_resp[0]["label"] == "Ana"
        assert clusters_resp[1]["label"] == "Carlos"
        assert clusters_resp[2]["label"] == "Outras"

    def test_identity_preserved_on_album_delete_and_recognized_by_suggester(self, api_client):
        """Valida que ao excluir um álbum sem remover FaceIDs, a identidade biométrica permanece no PostgreSQL."""
        user = User.objects.create_user(
            email="preserve_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="Preserve Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_pres_1",
            folder_name="Álbum Para Excluir",
        )
        from faces.models import Identity
        emb = [0.0] * 512
        emb[0] = 1.0
        identity = Identity.objects.create(
            user=user,
            person_name="Pessoa Cadastrada",
            centroid_embedding=emb,
            total_samples=5,
        )
        Cluster.objects.create(
            album=album,
            label="Pessoa Cadastrada",
            face_count=5,
            identity=identity,
        )

        api_client.force_authenticate(user=user)
        # Exclui o álbum SEM marcar delete_faceids
        res = api_client.delete(f"/api/v1/albums/{album.id}/", {"delete_faceids": "false"})
        assert res.status_code == status.HTTP_200_OK

        # O álbum foi excluído do banco
        assert not Album.objects.filter(id=album.id).exists()

        # A identidade FaceID PERMANECE intocada
        assert Identity.objects.filter(id=identity.id).exists()

        # Testa o IdentitySuggester com o vetor da face para confirmar que a pessoa é reconhecida
        from vision_pipeline.suggester import IdentitySuggester
        import numpy as np
        suggester = IdentitySuggester(threshold=0.40)
        face_vector = np.array(emb, dtype=np.float32)
        match = suggester.suggest_identity(face_vector, user.id)
        assert match is not None
        matched_id, dist = match
        assert matched_id.id == identity.id
        assert matched_id.person_name == "Pessoa Cadastrada"

    def test_cluster_rename_merges_duplicate_clusters_in_same_album(self, api_client):
        """Valida que ao renomear um cluster para o mesmo nome de outro existente no álbum, ocorre o merge automático."""
        user = User.objects.create_user(
            email="merge_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="Merge Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_merge_1",
            folder_name="Álbum Merge",
        )
        photo1 = Photo.objects.create(
            album=album,
            google_file_id="photo_m1",
            filename="foto_m1.jpg",
        )
        photo2 = Photo.objects.create(
            album=album,
            google_file_id="photo_m2",
            filename="foto_m2.jpg",
        )

        # Cluster A já identificado como "Carlos Silva" com 2 fotos
        cluster_a = Cluster.objects.create(
            album=album,
            label="Carlos Silva",
            face_count=2,
            avatar_crop_webp="data:image/webp;base64,existing_avatar",
        )
        Face.objects.create(
            photo=photo1,
            cluster=cluster_a,
            embedding=[0.1] * 512,
            bbox_xmin=0.1,
            bbox_ymin=0.1,
            bbox_xmax=0.3,
            bbox_ymax=0.3,
            detection_confidence=0.95,
        )
        Face.objects.create(
            photo=photo1,
            cluster=cluster_a,
            embedding=[0.1] * 512,
            bbox_xmin=0.4,
            bbox_ymin=0.4,
            bbox_xmax=0.6,
            bbox_ymax=0.6,
            detection_confidence=0.96,
        )

        # Cluster B ("Pessoa #2") com 1 foto que é a mesma pessoa
        cluster_b = Cluster.objects.create(
            album=album,
            label="Pessoa #2",
            face_count=1,
        )
        Face.objects.create(
            photo=photo2,
            cluster=cluster_b,
            embedding=[0.1] * 512,
            bbox_xmin=0.2,
            bbox_ymin=0.2,
            bbox_xmax=0.4,
            bbox_ymax=0.4,
            detection_confidence=0.97,
        )

        api_client.force_authenticate(user=user)
        # Renomeia o Cluster B para "Carlos Silva"
        res = api_client.post(f"/api/v1/faces/clusters/{cluster_b.id}/name/", {"person_name": "Carlos Silva"})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        # Valida flag de mesclagem no retorno
        assert data["merged"] is True
        assert data["target_cluster_id"] == str(cluster_a.id)
        assert data["source_cluster_id"] == str(cluster_b.id)
        assert data["face_count"] == 3

        # O Cluster B foi removido do banco
        assert not Cluster.objects.filter(id=cluster_b.id).exists()

        # O Cluster A agora possui as 3 faces unificadas
        cluster_a.refresh_from_db()
        assert cluster_a.face_count == 3
        assert cluster_a.faces.count() == 3
        assert cluster_a.label == "Carlos Silva"

        # A identidade FaceID foi criada/atualizada com as 3 amostras acumuladas
        from faces.models import Identity
        identity = Identity.objects.filter(user=user, person_name="Carlos Silva").first()
        assert identity is not None
        assert identity.total_samples == 3

    def test_multi_template_matching_for_same_identity(self):
        """Valida que o IdentitySuggester reconhece a pessoa através de múltiplos templates faciais (Multi-Template FaceID)."""
        user = User.objects.create_user(
            email="multitemplate@driveface.ai",
            password="StrongPassword123!",
            full_name="Multi Template User",
        )
        from faces.models import Identity, FaceTemplate
        from vision_pipeline.suggester import IdentitySuggester
        import numpy as np

        # Template 1: Face frontal (vetor apontando para dimensão 0)
        t1_vec = [0.0] * 512
        t1_vec[0] = 1.0

        identity = Identity.objects.create(
            user=user,
            person_name="Mariana Souza",
            centroid_embedding=t1_vec,
            total_samples=5,
        )

        # Template 2: Face de perfil (vetor apontando para dimensão 1)
        t2_vec = [0.0] * 512
        t2_vec[1] = 1.0
        FaceTemplate.objects.create(
            identity=identity,
            centroid_embedding=t2_vec,
            total_samples=3,
            notes="Perfil lateral",
        )

        suggester = IdentitySuggester(threshold=0.40)

        # Foto A: Nova foto frontal (próxima a t1, distante de t2)
        test_frontal = np.array(t1_vec, dtype=np.float32)
        match_a = suggester.suggest_identity(test_frontal, user.id)
        assert match_a is not None
        assert match_a[0].id == identity.id
        assert match_a[0].person_name == "Mariana Souza"

        # Foto B: Nova foto de perfil (próxima a t2, ortogonal a t1)
        # Se fosse média única entre t1 e t2, foto B poderia não atingir o threshold. Com multi-template, o match é exato!
        test_perfil = np.array(t2_vec, dtype=np.float32)
        match_b = suggester.suggest_identity(test_perfil, user.id)
        assert match_b is not None
        assert match_b[0].id == identity.id
        assert match_b[0].person_name == "Mariana Souza"
        assert match_b[1] < 0.05  # distância quase nula ao template 2





