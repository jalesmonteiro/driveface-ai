import logging
import numpy as np
from .models import FaceTemplate, Identity

logger = logging.getLogger(__name__)


def register_face_template(identity: Identity, centroid_vec, samples_count: int = 1, notes: str = "") -> FaceTemplate:
    """
    Registra ou atualiza um template biométrico facial sob a Identity.
    Preserva múltiplos centróides característicos para a mesma pessoa (Multi-Template FaceID):
    - Se já existir um template com distância cosseno <= 0.15, refina-o com média ponderada.
    - Se a distância for > 0.15, cria um novo FaceTemplate independente (novo ângulo, óculos, etc.).
    """
    if centroid_vec is None:
        return None

    vec = np.array(centroid_vec, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    templates = list(identity.templates.all())
    best_tmpl = None
    min_dist = float("inf")

    for tmpl in templates:
        if not tmpl.centroid_embedding:
            continue
        t_vec = np.array(tmpl.centroid_embedding, dtype=np.float32)
        dist = 1.0 - float(np.dot(vec, t_vec))
        if dist < min_dist:
            min_dist = dist
            best_tmpl = tmpl

    if best_tmpl and min_dist <= 0.15:
        # Centróide muito próximo: refina o template existente
        old_t = np.array(best_tmpl.centroid_embedding, dtype=np.float32)
        combined = (old_t * best_tmpl.total_samples + vec * samples_count) / (best_tmpl.total_samples + samples_count)
        norm_c = np.linalg.norm(combined)
        if norm_c > 0:
            combined = combined / norm_c
        best_tmpl.centroid_embedding = combined.tolist()
        best_tmpl.total_samples += samples_count
        best_tmpl.save(update_fields=["centroid_embedding", "total_samples"])
        return best_tmpl
    else:
        # Ângulo ou variação facial distinta: cria novo template biométrico
        new_tmpl = FaceTemplate.objects.create(
            identity=identity,
            centroid_embedding=vec.tolist(),
            total_samples=samples_count,
            notes=notes,
        )
        return new_tmpl
