*Formato: Markdown*

# **PLAN: DRIVEFACE AI**

## **Versão:** 1.0  |  **Data:** 28/08/2026  |  **Status:** Aguardando Aprovação (Fase 3\)

**Autor:** SDD Architect  
**Público-Alvo:** Agentes Autônomos de Codificação (Antigravity) e Pesquisadores

---

# **1\. Arquitetura e Stack Tecnológica**

## **1.1. Visão Geral da Arquitetura**

O sistema adota uma arquitetura desacoplada e orientada a eventos assíncronos, separando as requisições web síncronas do pipeline de visão computacional executado em GPU.

\`\`\`mermaid  
flowchart TD  
    Client\["CLIENT: React / Next.js SPA (Tailwind CSS \+ Lucide)"\]  
    API\["BACKEND API: Django 5.x \+ DRF / Gunicorn (Auth JWT, ACL Engine, Drive Proxy)"\]  
    Broker\["MESSAGE BROKER: Redis 7 (Celery Broker)"\]  
    DB\[("RELATIONAL & VECTOR DB: PostgreSQL 16 \+ pgvector (Multi-tenant)")\]  
    Worker\["AI WORKER PIPELINE: Celery Worker (InsightFace RetinaFace \+ ArcFace \+ DBSCAN)"\]  
    GDrive\["EXTERNAL: Google Drive API v3"\]

    Client \--\>|HTTPS / REST / JSON| API  
    API \--\>|Enfileira Task ID| Broker  
    API \--\>|Leitura / Escrita Metadados| DB  
    Broker \--\>|Consome Job em Lote| Worker  
    Worker \--\>|Embeddings 512-d & Clusters| DB  
    Worker \<--\>|Stream de Imagens em RAM BytesIO| GDrive

## **1.2. Matriz de Componentes e Tecnologias**

| Camada | Tecnologia Escolhida | Justificativa Arquitetural |
| :---- | :---- | :---- |
| **Linguagem Principal** | Python 3.11+ | Suporte nativo para PyTorch, bibliotecas de visão computacional e manipulação matricial. |
| **Web Framework & API** | Django 5.x \+ DRF | Framework maduro com sistema robusto de permissões orientadas a objeto (BasePermission para ACL), autenticação e ORM extensível. |
| **Fila de Tarefas Assíncronas** | Celery 5.x \+ Redis 7 | Orquestração distribuída de jobs de inferência em segundo plano, desacoplando requisições web do processamento em GPU. |
| **Banco Relacional & Vetorial** | PostgreSQL 16 \+ pgvector | Suporte unificado a dados relacionais (usuários, permissões, álbuns) e vetores de $512$ dimensões com indexação HNSW/IVFFlat. |
| **Pipeline de Visão Computacional** | InsightFace (PyTorch / ONNX Runtime com CUDA) | Estado da arte em detecção/alinhamento com RetinaFace e extração de características profundas com ArcFace ($D \= 512$). |
| **Agrupamento Não-Supervisionado** | Scikit-Learn (DBSCAN) | Algoritmo determinístico baseado em densidade sobre matriz de distância de cosseno, isolando automaticamente ruídos/outliers. |
| **Autenticação & Segurança** | djangorestframework-simplejwt \+ Argon2id | Autenticação stateless via JWT e hashing criptográfico de alta resistência. |
| **Integração Cloud Storage** | Google Drive API v3 (google-api-python-client) | Download de arquivos em lote via *streams* em memória (io.BytesIO) e criação de pastas/cópias diretas no Drive. |

# **2\. Estratégia de Testes**

## **2.1. Pirâmide e Cobertura de Testes**

A suíte de testes deve atingir cobertura mínima de **$85\\%$**, com tolerância zero para falhas nos módulos de isolamento multi-tenant (ACL) e cálculo de similaridade vetorial.

* **Testes Unitários (\~60%):** Lógica matemática de distância de cosseno, isolamento multi-tenant de centróides, regras de permissão ACL ($R\_6$), serializadores DRF e agrupamento sintético DBSCAN.

* **Testes de Integração (\~30%):** Transações com banco PostgreSQL \+ pgvector real via Testcontainers, enfileiramento e execução Celery, mocks da API do Google Drive e streaming ZIP via io.BytesIO.

* **Benchmarks Acadêmicos E2E (\~10%):** Validação de métricas de agrupamento (*Silhouette Score*, *Adjusted Rand Index*) e testes empíricos de equidade (*Fairness Tests* para avaliação de viés demográfico).

## **2.2. Categorias e Cenários de Teste**

* **Testes Unitários (tests/unit/):**

  * Verificação matemática do cálculo de distância de cosseno:

    $$d\_{\\cos}(\\mathbf{u}, \\mathbf{v}) \= 1 \- (\\mathbf{u} \\cdot \\mathbf{v})$$  
  * Validação estrita de isolamento multi-tenant: garantir que centróides do Usuário A nunca sejam consultados ao processar pastas do Usuário B.

  * Validação das regras de ACL ($R\_6$): autorização para Owner, autorização para Viewer presente na whitelist e retorno estrito de 403 Forbidden para e-mails não autorizados.

  * Agrupamento DBSCAN sintético com vetores pré-definidos para validação de formação de clusters e categorização de ruído.

  * Validação de serializadores DRF e formatação de tokens JWT.

* **Testes de Integração (tests/integration/):**

  * Banco de dados via **Testcontainers** (PostgreSQL 16 com extensão pgvector habilitada).

  * Teste de integridade e transição de estados dos jobs na fila Celery (PENDING $\\to$ PROCESSING $\\to$ COMPLETED).

  * Simulação da API do Google Drive via *Mocks/Stubs* (respostas HTTP de listagem, download de stream e criação de pastas).

  * Geração de pacote .zip em memória (io.BytesIO) via StreamingHttpResponse sem escrita de arquivos temporários em disco.

* **Testes E2E & Avaliação Acadêmica de Doutorado (tests/academic\_benchmarks/):**

  * **Métricas de Clusterização:** Cálculo automatizado de *Silhouette Score*, *Davies-Bouldin Index* e *Adjusted Rand Index (ARI)* sobre *dataset* de teste controlado (ex: LFW / CelebA).

  * **Avaliação de Equidade (Fairness Test):** Comparação empírica das taxas de falso positivo (FPR) e falso negativo (FNR) entre diferentes subgrupos demográficos e tons de pele (escala Fitzpatrick).

# **3\. Estrutura de Pastas (Monorepo Django Modular)**

driveface-ai/  
├── .github/  
│   └── workflows/  
│       ├── ci.yml                 \# Lint, Testes Unitários e Integração  
│       └── benchmarks.yml         \# Pipeline de Métricas Acadêmicas  
├── docker/  
│   ├── Dockerfile.web            \# Imagem Django / DRF  
│   ├── Dockerfile.worker         \# Imagem Worker Celery com CUDA  
│   └── docker-compose.yml        \# Setup local (Postgres/pgvector, Redis, Web, Worker)  
├── docs/  
│   ├── Constitution.md  
│   ├── Spec.md  
│   ├── Plan.md  
│   └── Tasks.md  
├── notebooks/  
│   └── colab\_experimentation.ipynb  \# Notebook para execução no Google Colab T4/V100  
├── src/  
│   ├── backend/  
│   │   ├── manage.py  
│   │   ├── config/                \# Configurações do Projeto Django  
│   │   │   ├── \_\_init\_\_.py  
│   │   │   ├── asgi.py  
│   │   │   ├── celery.py          \# Configuração Celery \+ Redis  
│   │   │   ├── settings/  
│   │   │   │   ├── base.py  
│   │   │   │   ├── development.py  
│   │   │   │   └── production.py  
│   │   │   ├── urls.py            \# Roteamento Central da API v1  
│   │   │   └── wsgi.py  
│   │   └── apps/                  \# Módulos / Django Apps Isolados  
│   │       ├── authentication/    \# Cadastro, Login, JWT, Custom User Model  
│   │       │   ├── models.py  
│   │       │   ├── serializers.py  
│   │       │   ├── views.py  
│   │       │   └── urls.py  
│   │       ├── google\_integration/ \# OAuth2, Tokens Criptografados, Drive Client  
│   │       │   ├── services.py  
│   │       │   ├── views.py  
│   │       │   └── urls.py  
│   │       ├── albums/            \# Albums, AlbumShares, Permissões ACL, Jobs  
│   │       │   ├── models.py  
│   │       │   ├── permissions.py \# IsAlbumOwner, IsAlbumViewerOrOwner  
│   │       │   ├── serializers.py  
│   │       │   ├── views.py  
│   │       │   └── urls.py  
│   │       ├── faces/             \# Photos, Faces (pgvector), Clusters, Identities  
│   │       │   ├── models.py  
│   │       │   ├── serializers.py  
│   │       │   ├── views.py  
│   │       │   └── urls.py  
│   │       ├── export/            \# Exportação ZIP em memória e Google Drive Copy  
│   │       │   ├── services.py  
│   │       │   ├── views.py  
│   │       │   └── urls.py  
│   │       └── vision\_pipeline/   \# Tarefas Celery e Motores de Visão  
│   │           ├── tasks.py       \# Celery Task: process\_album\_task  
│   │           ├── detector.py    \# RetinaFace / SCRFD wrapper  
│   │           ├── extractor.py   \# ArcFace embedding extractor (512-d)  
│   │           ├── aligner.py     \# Transformação afim com 5 pontos anatômicos  
│   │           ├── clustering.py  \# DBSCAN sobre matriz de distância de cosseno  
│   │           └── suggester.py   \# Centroid-based suggestion engine (isolado por user\_id)  
│   └── frontend/  
│       ├── public/  
│       ├── src/  
│       │   ├── components/        \# FolderCard, ClusterAvatar, FaceInspectorLightbox, etc.  
│       │   ├── pages/             \# Dashboard, SharedAlbum, Gallery, 403Forbidden  
│       │   ├── services/api.ts    \# Cliente Axios com interceptores JWT  
│       │   └── types/             \# Interfaces TypeScript  
├── tests/  
│   ├── unit/  
│   ├── integration/  
│   └── academic\_benchmarks/  
├── .env.example  
├── pyproject.toml  
└── README.md

# **4\. Diagramas de Arquitetura**

## **4.1. Diagrama de Entidade-Relacionamento (ERD com pgvector)**

Snippet de código  
erDiagram  
    USERS ||--o{ GOOGLE\_TOKENS : "possui"  
    USERS ||--o{ ALBUMS : "é proprietário"  
    USERS ||--o{ IDENTITIES : "cadastra centróides"  
    ALBUMS ||--o{ ALBUM\_SHARES : "compartilhado via"  
    ALBUMS ||--o{ JOBS : "processado por"  
    ALBUMS ||--o{ PHOTOS : "contém"  
    ALBUMS ||--o{ CLUSTERS : "possui"  
    PHOTOS ||--o{ FACES : "detecta"  
    CLUSTERS ||--o{ FACES : "agrupa"  
    IDENTITIES ||--o{ CLUSTERS : "rotula"

    USERS {  
        uuid id PK  
        string email UK  
        string password "Hashed Argon2id"  
        string full\_name  
        timestamp date\_joined  
    }

    GOOGLE\_TOKENS {  
        uuid id PK  
        uuid user\_id FK  
        string encrypted\_access\_token  
        string encrypted\_refresh\_token  
        timestamp token\_expiry  
    }

    ALBUMS {  
        uuid id PK  
        uuid owner\_id FK  
        string google\_drive\_folder\_id  
        string folder\_name  
        string share\_token UK  
        boolean is\_share\_active  
        timestamp created\_at  
        timestamp last\_synced\_at  
    }

    ALBUM\_SHARES {  
        uuid id PK  
        uuid album\_id FK  
        string invited\_email  
        string role "VIEWER"  
        timestamp invited\_at  
    }

    JOBS {  
        uuid id PK  
        uuid album\_id FK  
        string status "PENDING, PROCESSING, COMPLETED, FAILED"  
        int total\_images  
        int processed\_images  
        string error\_message  
        timestamp started\_at  
        timestamp finished\_at  
    }

    PHOTOS {  
        uuid id PK  
        uuid album\_id FK  
        string google\_file\_id  
        string filename  
        int width  
        int height  
        int faces\_count  
    }

    CLUSTERS {  
        uuid id PK  
        uuid album\_id FK  
        uuid identity\_id FK "nullable"  
        string label "Ex: Pessoa \#1 ou Nome Manual"  
        string avatar\_crop\_webp "Base64 ou Storage Path"  
        int face\_count  
    }

    FACES {  
        uuid id PK  
        uuid photo\_id FK  
        uuid cluster\_id FK  
        vector\_512 embedding "pgvector(512)"  
        float bbox\_xmin  
        float bbox\_ymin  
        float bbox\_xmax  
        float bbox\_ymax  
        float detection\_confidence  
    }

    IDENTITIES {  
        uuid id PK  
        uuid user\_id FK  
        string person\_name  
        vector\_512 centroid\_embedding "pgvector(512)"  
        int total\_samples  
        timestamp updated\_at  
    }

## **4.2. Diagrama de Sequência do Pipeline de Processamento Assíncrono**

Snippet de código  
sequenceDiagram  
    autonumber  
    actor User as Usuário (Proprietário)  
    participant API as Django REST Framework API  
    participant DB as PostgreSQL (pgvector)  
    participant Broker as Redis (Celery Broker)  
    participant Worker as Celery Vision Worker (GPU)  
    participant GDrive as Google Drive API v3

    User-\>\>API: POST /api/v1/albums/process/ (google\_drive\_folder\_id)  
    API-\>\>DB: Cria Album e Job (status \= 'PENDING')  
    API-\>\>Broker: Enfileira Task: process\_album\_task.delay(job\_id)  
    API--\>\>User: 202 Accepted { job\_id, status: "PENDING" }

    Broker-\>\>Worker: Consome process\_album\_task(job\_id)  
    Worker-\>\>DB: Atualiza Job (status \= 'PROCESSING')  
    Worker-\>\>GDrive: List & Stream Imagens (BytesIO)  
      
    loop Para cada lote de imagens (Processamento em RAM)  
        Worker-\>\>Worker: RetinaFace: Detecta Faces, Bounding Boxes & Landmarks  
        Worker-\>\>Worker: Alinha Face & Recorta Avatar (160x160 px)  
        Worker-\>\>Worker: ArcFace: Extrai Embedding Normalizado (512-d)  
        Worker-\>\>Worker: Libera Buffer da Imagem Original da Memória  
    end

    Worker-\>\>Worker: Executa Agrupamento DBSCAN (Cosine Distance \<= 0.40)  
    Worker-\>\>DB: Busca Centróides Cadastrados (WHERE user\_id \= album.owner\_id)  
    Worker-\>\>Worker: Auto-sugestão de Identidade (Distância \<= 0.35)  
    Worker-\>\>DB: Persiste Photos, Faces (pgvector), Clusters e Vínculos  
    Worker-\>\>DB: Atualiza Job (status \= 'COMPLETED')  
      
    User-\>\>API: GET /api/v1/jobs/{job\_id}/status/ (Polling)  
    API--\>\>User: 200 OK { status: "COMPLETED", progress\_percentage: 100 }

# **5\. Contratos de API (RESTful Endpoints & JSON DTOs)**

## **5.1. Autenticação & Usuários**

### **POST /api/v1/auth/register/**

* **Request:**

JSON  
{  
  "email": "usuario@exemplo.com",  
  "password": "Password123\!\#",  
  "full\_name": "Jales Monteiro"  
}

* **Response (201 Created):**

JSON  
{  
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",  
  "email": "usuario@exemplo.com",  
  "full\_name": "Jales Monteiro",  
  "date\_joined": "2026-08-28T20:00:00Z"  
}

### **POST /api/v1/auth/token/**

* **Request:**

JSON  
{  
  "email": "usuario@exemplo.com",  
  "password": "Password123\!\#"  
}

* **Response (200 OK):**

JSON  
{  
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  
  "expires\_in": 86400  
}

## **5.2. Gestão de Álbuns e Processamento**

### **POST /api/v1/albums/process/**

* **Headers:** Authorization: Bearer \<JWT\_ACCESS\_TOKEN\>

* **Request:**

JSON  
{  
  "google\_drive\_folder\_id": "1A2B3C4D5E6F\_drive\_folder\_id",  
  "folder\_name": "Formatura Turma 2026"  
}

* **Response (202 Accepted):**

JSON  
{  
  "job\_id": "8c91a34d-1768-45a2-9bfe-b7654321cba9",  
  "album\_id": "7b80a23c-0657-44a1-8aed-a6543210fedc",  
  "status": "PENDING",  
  "message": "Processamento facial agendado na fila com sucesso."  
}

### **GET /api/v1/jobs/{job\_id}/status/**

* **Headers:** Authorization: Bearer \<JWT\_ACCESS\_TOKEN\>

* **Response (200 OK):**

JSON  
{  
  "job\_id": "8c91a34d-1768-45a2-9bfe-b7654321cba9",  
  "status": "PROCESSING",  
  "total\_images": 250,  
  "processed\_images": 175,  
  "progress\_percentage": 70.0,  
  "error\_message": null  
}

## **5.3. Compartilhamento Seguro (ACL Whitelist)**

### **POST /api/v1/albums/{album\_id}/shares/**

* **Headers:** Authorization: Bearer \<JWT\_ACCESS\_TOKEN\> (Restrito ao Owner)

* **Request:**

JSON  
{  
  "is\_share\_active": true,  
  "invited\_emails": \[  
    "participante1@email.com",  
    "participante2@email.com"  
  \]  
}

* **Response (200 OK):**

JSON  
{  
  "album\_id": "7b80a23c-0657-44a1-8aed-a6543210fedc",  
  "share\_token": "sh\_9a8b7c6d5e4f3a2b1",  
  "share\_url": "\[https://driveface.ai/shared/album/sh\_9a8b7c6d5e4f3a2b1\](https://driveface.ai/shared/album/sh\_9a8b7c6d5e4f3a2b1)",  
  "is\_share\_active": true,  
  "whitelist": \[  
    {  
      "invited\_email": "participante1@email.com",  
      "role": "VIEWER",  
      "invited\_at": "2026-08-28T20:10:00Z"  
    },  
    {  
      "invited\_email": "participante2@email.com",  
      "role": "VIEWER",  
      "invited\_at": "2026-08-28T20:10:00Z"  
    }  
  \]  
}

### **GET /api/v1/albums/shared/{share\_token}/**

* **Headers:** Authorization: Bearer \<JWT\_ACCESS\_TOKEN\> (Convidado autenticado)

* **Response (200 OK \- Autorizado):**

JSON  
{  
  "album\_id": "7b80a23c-0657-44a1-8aed-a6543210fedc",  
  "folder\_name": "Formatura Turma 2026",  
  "user\_role": "VIEWER",  
  "total\_photos": 250,  
  "total\_people": 18,  
  "clusters": \[  
    {  
      "cluster\_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",  
      "label": "Pessoa \#1",  
      "avatar\_url": "/api/v1/clusters/c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c/avatar/",  
      "photo\_count": 34  
    }  
  \]  
}

* **Response (403 Forbidden \- E-mail fora da Whitelist):**

JSON  
{  
  "error\_code": "ACL\_FORBIDDEN",  
  "detail": "O e-mail autenticado não possui autorização para visualizar este álbum. Solicite acesso ao proprietário."  
}

## **5.4. Gestão de Clusters e Nomeação**

### **POST /api/v1/clusters/{cluster\_id}/name/**

* **Headers:** Authorization: Bearer \<JWT\_ACCESS\_TOKEN\> (Restrito ao Owner)

* **Request:**

JSON  
{  
  "person\_name": "Jales Monteiro"  
}

* **Response (200 OK):**

JSON  
{  
  "cluster\_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",  
  "person\_name": "Jales Monteiro",  
  "identity\_id": "id\_5f4e3d2c-1b0a-9f8e-7d6c-5b4a3a2a1a0b",  
  "centroid\_updated": true  
}

## **5.5. Exportação**

### **GET /api/v1/clusters/{cluster\_id}/export/zip/**

* **Headers:** Authorization: Bearer \<JWT\_ACCESS\_TOKEN\> (Owner ou Viewer autorizado)

* **Response:** 200 OK com cabeçalhos:

  * Content-Type: application/zip

  * Content-Disposition: attachment; filename="DriveFace\_Jales\_Monteiro.zip"

  * *Streaming de buffer binário em memória (StreamingHttpResponse)*.

### **POST /api/v1/clusters/{cluster\_id}/export/drive/**

* **Headers:** Authorization: Bearer \<JWT\_ACCESS\_TOKEN\>

* **Request:**

JSON  
{  
  "target\_folder\_name": "DriveFace \- Jales Monteiro"  
}

* **Response (200 OK):**

JSON  
{  
  "target\_folder\_id": "1Z9Y8X7W6V5U\_exported\_drive\_id",  
  "copied\_files\_count": 34,  
  "drive\_web\_view\_link": "\[https://drive.google.com/drive/folders/1Z9Y8X7W6V5U\](https://drive.google.com/drive/folders/1Z9Y8X7W6V5U)"  
}

# **6\. Estratégia de Deploy e Variáveis de Ambiente**

## **6.1. Variáveis de Ambiente (.env.example)**

Bash  
\# \=== Configurações do Django \===  
DJANGO\_ENV=development  
DJANGO\_SECRET\_KEY=change\_this\_to\_a\_very\_secure\_random\_64\_char\_secret\_key  
DJANGO\_DEBUG=True  
DJANGO\_ALLOWED\_HOSTS=localhost,127.0.0.1,api.driveface.ai

\# \=== Banco de Dados (PostgreSQL 16 \+ pgvector) \===  
POSTGRES\_DB=driveface\_db  
POSTGRES\_USER=driveface\_admin  
POSTGRES\_PASSWORD=driveface\_secure\_pass  
POSTGRES\_HOST=postgres  
POSTGRES\_PORT=5432  
DATABASE\_URL=postgres://driveface\_admin:driveface\_secure\_pass@postgres:5432/driveface\_db

\# \=== Cache & Celery Broker (Redis 7\) \===  
REDIS\_HOST=redis  
REDIS\_PORT=6379  
CELERY\_BROKER\_URL=redis://redis:6379/0  
CELERY\_RESULT\_BACKEND=redis://redis:6379/1

\# \=== Google Drive OAuth2 \===  
GOOGLE\_CLIENT\_ID=your\_google\_client\_id.apps.googleusercontent.com  
GOOGLE\_CLIENT\_SECRET=your\_google\_client\_secret  
GOOGLE\_REDIRECT\_URI=http://localhost:8000/api/v1/google/oauth/callback/

\# \=== Pipeline de Visão & Limiares Matemáticos \===  
DEVICE=cuda                               \# 'cuda' para GPU ou 'cpu' para fallback  
FACE\_DETECTION\_MODEL=buffalo\_l            \# InsightFace Model Zoo (RetinaFace \+ ArcFace)  
FACE\_DETECTION\_CONFIDENCE\_THRESHOLD=0.80  \# Limiar de confiança da detecção facial  
CLUSTERING\_COSINE\_EPS=0.40                \# Epsilon para agrupamento DBSCAN  
IDENTITY\_SUGGESTION\_THRESHOLD=0.35        \# Limiar para auto-sugestão de identidade

## **6.2. Estratégia de Execução**

1. **Ambiente Local / Docker Compose:**

   * docker-compose up \--build: Sobe PostgreSQL com pgvector, Redis, Django Web Server (Gunicorn) e Celery Worker.

2. **Ambiente Google Colab (Prototipagem & Benchmarks Acadêmicos):**

   * Execução do Worker e Django Server utilizando runtime com GPU (NVIDIA T4 / V100), conectando a um PostgreSQL em nuvem gerenciado (ex: Neon/Supabase com pgvector) ou local.

3. **Ambiente Google Cloud Platform (Produção):**

   * **API Web Server:** Google Cloud Run (instâncias gerenciadas com autoscale).

   * **AI Worker (GPU):** Google Kubernetes Engine (GKE) com GPU Node Pools escaláveis para execução dos workers Celery.

   * **Database & Cache:** Cloud SQL for PostgreSQL (com extensão vector) e Memorystore for Redis.

