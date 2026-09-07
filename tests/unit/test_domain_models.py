import pytest
import uuid
from django.contrib.auth import get_user_model
from albums.models import Album, AlbumShare, Job
from faces.models import Photo, Cluster, Face, Identity

User = get_user_model()


@pytest.mark.django_db
class TestDomainModels:
    def test_album_and_job_creation(self):
        """Valida criação de Album e Job vinculado com valores padrão."""
        owner = User.objects.create_user(email="owner@driveface.ai", password="Password123!")
        album = Album.objects.create(
            owner=owner,
            google_drive_folder_id="12345_folder",
            folder_name="Evento 2026",
        )

        assert album.id is not None
        assert album.owner == owner
        assert album.share_token.startswith("sh_")
        assert not album.is_share_active

        job = Job.objects.create(album=album, status=Job.Status.PENDING)
        assert job.album == album
        assert job.status == Job.Status.PENDING
        assert job.total_images == 0
        assert job.processed_images == 0

    def test_album_share_whitelist(self):
        """Valida whitelist de compartilhamento do álbum."""
        owner = User.objects.create_user(email="owner2@driveface.ai", password="Password123!")
        album = Album.objects.create(
            owner=owner,
            google_drive_folder_id="drive_xyz",
            folder_name="Turma A",
        )
        share = AlbumShare.objects.create(
            album=album,
            invited_email="participante@driveface.ai",
            role=AlbumShare.Role.VIEWER,
        )

        assert share.album == album
        assert share.invited_email == "participante@driveface.ai"
        assert share.role == AlbumShare.Role.VIEWER
        assert album.shares.count() == 1

    def test_faces_and_identities_relationship(self):
        """Valida a cadeia Photo -> Face -> Cluster -> Identity."""
        owner = User.objects.create_user(email="user_ai@driveface.ai", password="Password123!")
        album = Album.objects.create(
            owner=owner,
            google_drive_folder_id="drive_ai_folder",
            folder_name="Pastas IA",
        )
        photo = Photo.objects.create(
            album=album,
            google_file_id="img_001",
            filename="foto1.jpg",
            width=1920,
            height=1080,
            faces_count=1,
        )
        identity = Identity.objects.create(
            user=owner,
            person_name="Jales Monteiro",
            centroid_embedding=[0.0] * 512,
            total_samples=1,
        )
        cluster = Cluster.objects.create(
            album=album,
            identity=identity,
            label="Jales Monteiro",
            face_count=1,
        )
        face = Face.objects.create(
            photo=photo,
            cluster=cluster,
            embedding=[0.1] * 512,
            bbox_xmin=0.1,
            bbox_ymin=0.1,
            bbox_xmax=0.5,
            bbox_ymax=0.5,
            detection_confidence=0.98,
        )

        assert face.photo == photo
        assert face.cluster == cluster
        assert face.cluster.identity == identity
        assert face.cluster.identity.user == owner
        assert len(face.embedding) == 512
