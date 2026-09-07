# DriveFace AI

Sistema inteligente multi-usuário para agrupamento facial e indexação automática em fotos do Google Drive.

## Arquitetura
- **Backend:** Django 5.x, Django REST Framework, Celery
- **Banco de Dados & Vetores:** PostgreSQL 16 com extensão `pgvector` (vetores de 512 dimensões)
- **Broker / Cache:** Redis 7
- **Pipeline de Visão:** RetinaFace (Detecção & Landmarks), ArcFace (Deep Embeddings 512-d), DBSCAN (Clustering por Distância de Cosseno)
- **Integração:** Google Drive API v3 (streaming volátil em RAM via `io.BytesIO`)

Consulte a pasta `docs/` para especificações completas (`const.md`, `spec.md`, `plan.md`, `tasks.md`).
