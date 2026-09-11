"""Tarefas Celery para execução assíncrona do pipeline de visão.

Pipeline real:
  1. Lista imagens da pasta Google Drive do álbum
  2. Baixa cada imagem em memória volátil (io.BytesIO) — Zero-Disk
  3. Detecção de faces com InsightFace (RetinaFace/SCRFD) via ONNX Runtime (CPU)
  4. Extração de embeddings ArcFace 512-D com normalização L2
  5. Agrupamento DBSCAN (cosine, eps=0.40) — cria Cluster records no PostgreSQL
  6. Auto-sugestão de identidade se existir centróide similar do usuário
"""
import io
import logging
from datetime import datetime

import numpy as np
from celery import shared_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilitários de imagem (sem depender de cv2 global — importa inline)
# ---------------------------------------------------------------------------

def _load_image_as_np(image_bytes: bytes):
    """Converte bytes de imagem para numpy array RGB."""
    import numpy as np
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return np.array(img)


def _crop_face_to_base64_webp(img_np, bbox_dict, w, h) -> str:
    """Recorta o rosto específico com margem de 35% e retorna miniatura WebP 160x160 em Base64."""
    import base64
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    try:
        x1 = int(bbox_dict["xmin"] * w)
        y1 = int(bbox_dict["ymin"] * h)
        x2 = int(bbox_dict["xmax"] * w)
        y2 = int(bbox_dict["ymax"] * h)

        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)

        pad_x = int(bw * 0.35)
        pad_y = int(bh * 0.35)

        crop_x1 = max(0, x1 - pad_x)
        crop_y1 = max(0, y1 - pad_y)
        crop_x2 = min(w, x2 + pad_x)
        crop_y2 = min(h, y2 + pad_y)

        img_pil = Image.fromarray(img_np)
        face_img = img_pil.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        face_thumb = face_img.resize((160, 160), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        face_thumb.save(buf, format="WEBP", quality=85)
        return f"data:image/webp;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
    except Exception as exc:
        logger.warning(f"Falha ao gerar recorte de face em base64: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Singleton do analisador InsightFace (carregado uma vez por processo worker)
# ---------------------------------------------------------------------------

_face_app = None


def _get_face_app():
    """Carrega FaceAnalysis do InsightFace em CPU, modelo buffalo_sc (leve)."""
    global _face_app
    if _face_app is None:
        try:
            import insightface
            app = insightface.app.FaceAnalysis(
                name="buffalo_sc",
                providers=["CPUExecutionProvider"],
            )
            # det_size menor para economizar memória em CPU
            app.prepare(ctx_id=-1, det_size=(320, 320))
            _face_app = app
            logger.info("InsightFace FaceAnalysis carregado com sucesso (buffalo_sc / CPU).")
        except Exception as exc:
            logger.error(f"Erro ao carregar InsightFace: {exc}")
            _face_app = None
    return _face_app


# ---------------------------------------------------------------------------
# Tarefa principal
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="vision_pipeline.process_album_task")
def process_album_task(self, job_id: str = None):
    """
    Orquestra o download em stream volátil, detecção, extração ArcFace,
    agrupamento DBSCAN e auto-sugestão com isolamento de tenant.
    """
    if job_id is None and not hasattr(self, "request"):
        job_id = str(self)
    else:
        job_id = str(job_id)
    import django
    django.setup()

    from albums.models import Album, Job
    from faces.models import Cluster, Face, Photo
    from google_integration.services import GoogleDriveService
    from vision_pipeline.clustering import FaceClustering
    from vision_pipeline.suggester import IdentitySuggester
    from sklearn.metrics.pairwise import cosine_distances

    logger.info(f"Iniciando process_album_task para job_id: {job_id}")

    # 1. Obtém o Job e muda status para PROCESSING
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"Job {job_id} não encontrado no banco.")
        return {"job_id": job_id, "status": "FAILED", "error": "Job não encontrado"}

    job.status = Job.Status.PROCESSING
    job.started_at = datetime.now()
    job.save(update_fields=["status", "started_at"])

    album = job.album
    owner = album.owner

    try:
        # 2. Lista imagens do Google Drive
        drive_service = GoogleDriveService(user=owner)
        drive_files = drive_service.list_images(album.google_drive_folder_id)

        if not drive_files:
            logger.warning(f"Nenhuma imagem encontrada na pasta {album.google_drive_folder_id}")
            job.status = Job.Status.COMPLETED
            job.finished_at = datetime.now()
            job.error_message = "Nenhuma imagem encontrada na pasta selecionada."
            job.save(update_fields=["status", "finished_at", "error_message"])
            return {"job_id": job_id, "status": "COMPLETED", "total_images": 0}

        job.total_images = len(drive_files)
        job.save(update_fields=["total_images"])

        # 3. Registra Photo records no banco
        photo_objects = []
        for file_info in drive_files:
            photo, _ = Photo.objects.get_or_create(
                album=album,
                google_file_id=file_info["id"],
                defaults={"filename": file_info.get("name", "foto.jpg")},
            )
            photo_objects.append(photo)

        logger.info(f"[Job {job_id}] {len(photo_objects)} fotos registradas no PostgreSQL.")

        # 4. Carrega o modelo InsightFace
        face_app = _get_face_app()

        # 5. Processa cada foto — detecção + embedding
        # Estrutura: list of (photo, face_embedding_array, bbox)
        all_detections = []  # [(photo, embedding_np, bbox_dict)]

        for idx, photo in enumerate(photo_objects):
            try:
                stream = drive_service.download_image_stream(photo.google_file_id)
                if not stream or stream.getbuffer().nbytes == 0:
                    logger.warning(f"Foto {photo.filename} sem conteúdo — pulando.")
                    continue

                img_bytes = stream.getvalue()
                img_np = _load_image_as_np(img_bytes)

                h, w = img_np.shape[:2]

                if face_app is not None:
                    import cv2
                    # InsightFace espera BGR
                    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                    faces = face_app.get(img_bgr)
                else:
                    faces = []

                photo.faces_count = len(faces)
                photo.width = w
                photo.height = h
                photo.save(update_fields=["faces_count", "width", "height"])

                for face in faces:
                    if face.det_score < 0.70:
                        continue
                    emb = np.array(face.embedding, dtype=np.float32)
                    norm = np.linalg.norm(emb)
                    if norm > 0:
                        emb = emb / norm

                    bbox = face.bbox  # [x1, y1, x2, y2] em pixels
                    bbox_dict = {
                        "xmin": max(0.0, float(bbox[0]) / w),
                        "ymin": max(0.0, float(bbox[1]) / h),
                        "xmax": min(1.0, float(bbox[2]) / w),
                        "ymax": min(1.0, float(bbox[3]) / h),
                        "conf": float(face.det_score),
                    }
                    crop_b64 = _crop_face_to_base64_webp(img_np, bbox_dict, w, h)
                    all_detections.append((photo, emb, bbox_dict, crop_b64))

            except Exception as exc:
                logger.error(f"Erro ao processar foto {photo.filename}: {exc}")
                continue

            job.processed_images = idx + 1
            job.save(update_fields=["processed_images"])

        logger.info(f"[Job {job_id}] {len(all_detections)} faces detectadas em {len(photo_objects)} fotos.")

        # 6. Se não detectou faces, finaliza
        if not all_detections:
            logger.warning(f"[Job {job_id}] Nenhuma face detectada. O InsightFace pode estar indisponível ou as fotos não têm rostos.")
            # Cria pelo menos clusters básicos baseados nas fotos para não deixar vazio
            _create_fallback_clusters(album, photo_objects)
            job.status = Job.Status.COMPLETED
            job.finished_at = datetime.now()
            job.error_message = "Nenhuma face detectada pelo modelo. Clusters básicos criados."
            job.save(update_fields=["status", "finished_at", "error_message"])
            return {"job_id": job_id, "status": "COMPLETED", "faces": 0}

        # 7. Agrupamento DBSCAN
        embeddings_matrix = np.stack([d[1] for d in all_detections])
        clusterer = FaceClustering(eps=0.40, min_samples=2)
        cluster_labels = clusterer.fit_predict(embeddings_matrix)

        unique_labels = set(cluster_labels)
        unique_labels.discard(-1)  # remove ruído

        logger.info(f"[Job {job_id}] DBSCAN: {len(unique_labels)} clusters encontrados.")

        # 8. Remove clusters antigos do álbum e cria novos
        album.clusters.all().delete()

        suggester = IdentitySuggester(threshold=0.35)

        for label_id in sorted(unique_labels):
            indices = [i for i, lbl in enumerate(cluster_labels) if lbl == label_id]
            cluster_embeddings = embeddings_matrix[indices]

            # Calcula centróide normalizado L2
            centroid = np.mean(cluster_embeddings, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm

            # Tenta sugerir identidade existente do dono
            suggested_identity = None
            cluster_name = f"Pessoa #{label_id + 1}"
            try:
                result = suggester.suggest_identity(centroid, owner.id)
                if result:
                    suggested_identity, dist = result
                    cluster_name = suggested_identity.person_name
            except Exception:
                pass

            first_crop_b64 = all_detections[indices[0]][3]

            cluster = Cluster.objects.create(
                album=album,
                label=cluster_name,
                face_count=len(indices),
                identity=suggested_identity,
                is_suggested=(suggested_identity is not None),
                avatar_crop_webp=first_crop_b64 or "",
            )

            # 9. Cria Face records vinculando foto, embedding e cluster
            for i in indices:
                photo_obj, emb, bbox, _ = all_detections[i]
                try:
                    Face.objects.create(
                        photo=photo_obj,
                        cluster=cluster,
                        embedding=emb.tolist(),
                        bbox_xmin=bbox["xmin"],
                        bbox_ymin=bbox["ymin"],
                        bbox_xmax=bbox["xmax"],
                        bbox_ymax=bbox["ymax"],
                        detection_confidence=bbox["conf"],
                    )
                except Exception as exc:
                    logger.error(f"Erro ao salvar Face record: {exc}")

        # Faces de ruído (cluster -1) sem agrupamento
        noise_indices = [i for i, lbl in enumerate(cluster_labels) if lbl == -1]
        if noise_indices:
            noise_crop_b64 = all_detections[noise_indices[0]][3]
            noise_cluster = Cluster.objects.create(
                album=album,
                label="Não Identificado",
                face_count=len(noise_indices),
                avatar_crop_webp=noise_crop_b64 or "",
            )
            for i in noise_indices:
                photo_obj, emb, bbox, _ = all_detections[i]
                try:
                    Face.objects.create(
                        photo=photo_obj,
                        cluster=noise_cluster,
                        embedding=emb.tolist(),
                        bbox_xmin=bbox["xmin"],
                        bbox_ymin=bbox["ymin"],
                        bbox_xmax=bbox["xmax"],
                        bbox_ymax=bbox["ymax"],
                        detection_confidence=bbox["conf"],
                    )
                except Exception as exc:
                    logger.error(f"Erro ao salvar Face de ruído: {exc}")

        # 10. Finaliza o Job
        job.status = Job.Status.COMPLETED
        job.finished_at = datetime.now()
        job.save(update_fields=["status", "finished_at"])

        total_clusters = album.clusters.count()
        logger.info(f"[Job {job_id}] Concluído! {len(all_detections)} faces, {total_clusters} clusters no PostgreSQL.")

        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "total_images": len(photo_objects),
            "total_faces": len(all_detections),
            "total_clusters": total_clusters,
        }

    except Exception as exc:
        logger.exception(f"[Job {job_id}] Falha crítica no pipeline: {exc}")
        job.status = Job.Status.FAILED
        job.finished_at = datetime.now()
        job.error_message = str(exc)
        job.save(update_fields=["status", "finished_at", "error_message"])
        return {"job_id": job_id, "status": "FAILED", "error": str(exc)}


def _create_fallback_clusters(album, photo_objects):
    """
    Quando o InsightFace não consegue detectar faces (sem GPU, modelo não disponível),
    cria clusters simples vinculando todas as fotos a um único agrupamento.
    Assim o usuário ainda vê as fotos no álbum.
    """
    from faces.models import Cluster, Face

    if not photo_objects:
        return

    # Remove clusters antigos
    album.clusters.all().delete()

    cluster = Cluster.objects.create(
        album=album,
        label="Fotos do Álbum",
        face_count=len(photo_objects),
        avatar_crop_webp=f"/api/v1/photos/{photo_objects[0].id}/stream/",
    )

    zero_emb = [0.0] * 512
    for photo in photo_objects:
        try:
            Face.objects.create(
                photo=photo,
                cluster=cluster,
                embedding=zero_emb,
                bbox_xmin=0.1,
                bbox_ymin=0.1,
                bbox_xmax=0.9,
                bbox_ymax=0.9,
                detection_confidence=0.0,
            )
        except Exception as exc:
            logger.error(f"Erro ao criar face de fallback: {exc}")
