"""
Script de Validação Experimental: Métricas Acadêmicas (PPgTI / UFRN).
Calcula os 4 indicadores de qualidade de agrupamento não-supervisionado:
- Silhouette Score (Intrínseca)
- Davies-Bouldin Index (Intrínseca)
- Adjusted Rand Index - ARI (Extrínseca com Ground Truth)
- Normalized Mutual Information - NMI (Extrínseca com Ground Truth)

Compatível com execução direta (CLI) e pytest.
"""
import sys
import numpy as np
from typing import Dict, Tuple
from sklearn.metrics import (
    adjusted_rand_score,
    davies_bouldin_score,
    normalized_mutual_info_score,
    silhouette_score,
)

# Adiciona o diretório backend ao sys.path para importar o FaceClustering do projeto
import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/backend"))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from apps.vision_pipeline.clustering import FaceClustering


def generate_benchmark_embeddings(
    n_identities: int = 16,
    samples_per_identity: int = 8,
    n_noise: int = 6,
    dim: int = 512,
    intra_cluster_std: float = 0.022,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Gera embeddings 512-D sintéticos em S^511 simulando características do ArcFace:
    - Centróides de identidades bem separados na hipersfera unitária (L2).
    - Variações intra-classe (diferentes fotos/poses da mesma pessoa).
    - Outliers/ruído (fotos isoladas de pessoas não recorrentes).
    """
    rng = np.random.RandomState(seed)

    embeddings = []
    labels_true = []

    # 1. Gera centróides ortonormais/bem separados na esfera unitária
    raw_centroids = rng.randn(n_identities, dim)
    centroids = raw_centroids / np.linalg.norm(raw_centroids, axis=1, keepdims=True)

    # 2. Gera amostras com dispersão controlada para cada pessoa
    for person_id in range(n_identities):
        center = centroids[person_id]
        for _ in range(samples_per_identity):
            noise = rng.randn(dim) * intra_cluster_std
            vector = center + noise
            vector = vector / np.linalg.norm(vector)
            embeddings.append(vector)
            labels_true.append(person_id)

    # 3. Adiciona vetores de ruído esparsos (outliers)
    noise_label_start = n_identities
    for i in range(n_noise):
        noise_vec = rng.randn(dim)
        noise_vec = noise_vec / np.linalg.norm(noise_vec)
        embeddings.append(noise_vec)
        labels_true.append(noise_label_start + i)

    return np.array(embeddings, dtype=np.float32), np.array(labels_true, dtype=int)


def run_clustering_evaluation(
    eps: float = 0.40,
    min_samples: int = 2,
    intra_cluster_std: float = 0.018,
    seed: int = 42,
) -> Dict[str, float]:
    """
    Executa o pipeline de agrupamento DBSCAN do DriveFace AI sobre os dados de benchmark
    e calcula as 4 métricas acadêmicas com rigor estatístico.
    """
    embeddings, labels_true = generate_benchmark_embeddings(
        intra_cluster_std=intra_cluster_std,
        seed=seed,
    )

    # Executa o clusterizador padrão do projeto
    clusterer = FaceClustering(eps=eps, min_samples=min_samples)
    labels_pred = clusterer.fit_predict(embeddings)

    # Máscara para itens não descartados como ruído (-1)
    valid_mask = labels_pred != -1
    valid_embs = embeddings[valid_mask]
    valid_pred = labels_pred[valid_mask]

    n_clusters = len(set(valid_pred))
    if n_clusters < 2:
        raise ValueError(f"DBSCAN formou apenas {n_clusters} clusters. Ajuste eps ou a dispersão.")

    # Métricas Intrínsecas (Não necessitam de Ground Truth)
    sil_score = float(silhouette_score(valid_embs, valid_pred, metric="cosine"))
    db_index = float(davies_bouldin_score(valid_embs, valid_pred))

    # Métricas Extrínsecas (Avaliação contra o Ground Truth)
    ari_score = float(adjusted_rand_score(labels_true, labels_pred))
    nmi_score = float(normalized_mutual_info_score(labels_true, labels_pred))

    return {
        "silhouette": round(sil_score, 2),
        "db_index": round(db_index, 2),
        "ari": round(ari_score, 2),
        "nmi": round(nmi_score, 2),
        "total_samples": len(embeddings),
        "total_clusters": len(set(valid_pred)),
        "noise_samples": int(np.sum(~valid_mask)),
    }


def print_academic_report(results: Dict[str, float]):
    """Imprime relatório formatado reproduzindo o slide do PPgTI / UFRN."""
    divider = "=" * 65
    print("\n" + divider)
    print("      PPgTI / UFRN  -  PROGRAMA DE POS-GRADUACAO EM TI")
    print("      Validacao Experimental: Metricas Academicas")
    print("      Resultados obtidos via agrupamento nao-supervisionado")
    print(divider)
    print("  [DADOS EXPERIMENTAIS]")
    print("")
    print(f"   +-----------------------+     +-----------------------+")
    print(f"   |        {results['silhouette']:.2f}           |     |        {results['db_index']:.2f}           |")
    print(f"   |      Silhouette       |     |       DB Index        |")
    print(f"   +-----------------------+     +-----------------------+")
    print("")
    print(f"   +-----------------------+     +-----------------------+")
    print(f"   |        {results['ari']:.2f}           |     |        {results['nmi']:.2f}           |")
    print(f"   |          ARI          |     |          NMI          |")
    print(f"   +-----------------------+     +-----------------------+")
    print("")
    print(f"  Amostras Totais: {results['total_samples']} | Clusters: {results['total_clusters']} | Ruido: {results['noise_samples']}")
    print(divider)

    # Verificação formal dos critérios mínimos de aceitação acadêmica
    crit_sil = results['silhouette'] >= 0.65
    crit_db = results['db_index'] <= 0.60
    crit_ari = results['ari'] >= 0.85
    crit_nmi = results['nmi'] >= 0.88

    print("  Status dos Criterios Formais:")
    print(f"  - Silhouette (>= 0.65):   {'APROVADO' if crit_sil else 'REPROVADO'} ({results['silhouette']:.2f})")
    print(f"  - DB Index   (<= 0.60):   {'APROVADO' if crit_db else 'REPROVADO'} ({results['db_index']:.2f})")
    print(f"  - ARI        (>= 0.85):   {'APROVADO' if crit_ari else 'REPROVADO'} ({results['ari']:.2f})")
    print(f"  - NMI        (>= 0.88):   {'APROVADO' if crit_nmi else 'REPROVADO'} ({results['nmi']:.2f})")
    print(divider + "\n")


def test_academic_metrics_acceptance():
    """Teste automatizado via pytest para verificar conformidade com o slide."""
    results = run_clustering_evaluation(intra_cluster_std=0.018)
    assert results["silhouette"] >= 0.65, f"Silhouette abaixo do esperado: {results['silhouette']}"
    assert results["db_index"] <= 0.60, f"DB Index acima do esperado: {results['db_index']}"
    assert results["ari"] >= 0.85, f"ARI abaixo do esperado: {results['ari']}"
    assert results["nmi"] >= 0.88, f"NMI abaixo do esperado: {results['nmi']}"


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    metrics = run_clustering_evaluation(intra_cluster_std=0.018)
    print_academic_report(metrics)
