# **Arquitetura de Arquivos & Guia Funcional — DriveFace AI**

Este documento descreve detalhadamente a estrutura de arquivos e diretórios do **DriveFace AI**, especificando o papel e a funcionalidade de cada componente na arquitetura da aplicação.

---

## **1. Visão Geral da Arquitetura em Camadas**

O DriveFace AI é estruturado em uma arquitetura modular desacoplada:

```
┌────────────────────────────────────────────────────────────────────────┐
│               1. CAMADA DE APRESENTAÇÃO (FRONTEND / SPA)               │
│  Templates Django (Jinja/HTML5) + Vanilla CSS (Glassmorphism) + app.js │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP / JSON REST API
┌──────────────────────────────────▼─────────────────────────────────────┐
│                 2. CAMADA WEB & API (DJANGO REST FRAMEWORK)            │
│  Autenticação JWT, Controle de Acesso (ACL), Mapeamento de Álbuns      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Tarefas Assíncronas (Redis Broker)
┌──────────────────────────────────▼─────────────────────────────────────┐
│               3. CAMADA DE PROCESSAMENTO IA (CELERY WORKER)            │
│  Stream RAM (BytesIO) ➔ RetinaFace/SCRFD ➔ ArcFace (512-D) ➔ DBSCAN    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ SQL + Vetores Densos L2
┌──────────────────────────────────▼─────────────────────────────────────┐
│                 4. CAMADA DE PERSISTÊNCIA & ISOLAMENTO                 │
│       PostgreSQL 16 + Extensão pgvector (Multi-Tenant Zero-Leakage)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## **2. Mapa de Diretórios Raiz**

```
driveface-ai/
├── docker/                     # Definições de infraestrutura e contêineres
├── docs/                       # Especificações formais, constituição e tarefas
├── notebooks/                  # Prototipagem e execução em Google Colab com GPU
├── src/backend/                # Código-fonte principal da aplicação Django e Workers
│   ├── apps/                   # Módulos desacoplados (Bounded Contexts)
│   ├── config/                 # Configurações globais do Django e Celery
│   ├── static/                 # Recursos visuais (CSS Design System e JavaScript)
│   └── templates/              # Páginas e componentes HTML5
└── tests/                      # Suíte de testes automatizados e benchmarks
```

---

## **3. Detalhamento Arquivo por Arquivo**

### **3.1. Arquivos da Raiz do Projeto**

| Arquivo | Funcionalidade |
| :--- | :--- |
| **`README.md`** | Guia de introdução rápida, requisitos, passos de instalação local e comandos Docker para inicialização. |
| **`requirements.txt`** | Dependências principais do backend (Django, DRF, Celery, Redis, psycopg3, pgvector, etc.). |
| **`requirements-ai.txt`** | Dependências pesadas de Visão Computacional e Deep Learning (InsightFace, ONNX Runtime, OpenCV, scikit-learn, PIL). |
| **`requirements-dev.txt`** | Ferramentas de desenvolvimento, linters e testes (`pytest`, `pytest-django`, `flake8`, `black`). |
| **`pyproject.toml`** | Configurações globais do ambiente Python, ferramentas de empacotamento e configurações do Pytest. |
| **`pyrefly.toml`** / **`pyrightconfig.json`** | Configurações de tipagem estática e análise de código para IDEs modernas. |
| **`.env.example`** | Modelo de variáveis de ambiente obrigatórias (chaves do Google OAuth, credenciais do banco PostgreSQL, segredos JWT). |
| **`.gitignore`** | Regras de exclusão de arquivos transitórios, banco SQLite temporário, pesos locais de IA e `.venv`. |

---

### **3.2. Documentação Técnica (`docs/`)**

| Arquivo | Funcionalidade |
| :--- | :--- |
| **[`const.md`](file:///c:/Desenvolvimento/driveface%20ai/docs/const.md)** | **Constituição do Projeto**: Define declaração do problema, personas, escopo rigoroso do MVP e *Hard Constraints* inegociáveis (privacidade multi-tenant, processamento volátil Zero-Disk, limiares biométricos). |
| **[`spec.md`](file:///c:/Desenvolvimento/driveface%20ai/docs/spec.md)** | **Especificação Completa dos Requisitos**: Dicionário de dados, diagramas de sequência, regras de negócio formais ($R_1$ a $R_6$), rotas da API e tratamento de erros. |
| **[`plan.md`](file:///c:/Desenvolvimento/driveface%20ai/docs/plan.md)** | **Plano de Arquitetura**: Desenho detalhado da topologia de microserviços, particionamento de banco relacional/vetorial e estratégia de deployment. |
| **[`tasks.md`](file:///c:/Desenvolvimento/driveface%20ai/docs/tasks.md)** | **Quadro de Tarefas (Backlog & DoD)**: Relação das fases do projeto, tarefas executadas e critérios de aceitação formal (*Definition of Done*). |
| **[`architecture.md`](file:///c:/Desenvolvimento/driveface%20ai/docs/architecture.md)** | **Este arquivo**: Mapa de referência estrutural e funcional de cada arquivo da base de código. |

---

### **3.3. Infraestrutura & Contêineres (`docker/`)**

| Arquivo | Funcionalidade |
| :--- | :--- |
| **`docker-compose.yml`** | Orquestra todos os serviços do sistema: banco de dados PostgreSQL com `pgvector`, fila Redis, servidor web Django e o Worker assíncrono Celery. |
| **`Dockerfile.web`** | Constrói o contêiner leve para a API Web/Django (otimizado para requisições HTTP e entrega de templates). |
| **`Dockerfile.worker`** | Constrói o contêiner especializado para o worker Celery, com todas as bibliotecas científicas de visão computacional (InsightFace, ONNX, CPU Runtime). |
| **`init-vector.sql`** | Script de inicialização executado no boot do PostgreSQL para habilitar a extensão `CREATE EXTENSION IF NOT EXISTS vector;`. |

---

### **3.4. Configuração Global do Backend (`src/backend/config/`)**

| Arquivo | Funcionalidade |
| :--- | :--- |
| **`config/__init__.py`** | Inicializa o módulo e exporta a instância do Celery (`celery_app`). |
| **`config/celery.py`** | Cria e configura a aplicação Celery, conectando ao broker Redis e auto-descobrindo tarefas nos apps instalados. |
| **`config/urls.py`** | Roteador raiz do Django. Conecta as rotas das APIs (`/api/v1/...`), autenticação e visualizações HTML da interface. |
| **`config/asgi.py`** / **`wsgi.py`** | Pontos de entrada padrão para servidores web compatíveis com ASGI/WSGI (Gunicorn, Uvicorn). |
| **`config/exceptions.py`** | Formatador global de exceções do DRF, garantindo payloads de erro padronizados em JSON. |
| **`config/settings/base.py`** | Configurações compartilhadas (banco relacional, JWT, templates, apps registrados, CORS e senhas Argon2). |
| **`config/settings/development.py`** | Configurações específicas de desenvolvimento local (`DEBUG = True`, banco de testes). |
| **`config/settings/production.py`** | Configurações de segurança estrita para produção (`DEBUG = False`, HTTPS forçado, cookies seguros). |

---

### **3.5. Módulos da Aplicação (`src/backend/apps/`)**

#### A. Módulo de Autenticação (`apps/authentication/`)
* **`models.py`**: Define o modelo customizado `User` (utiliza e-mail como chave de login, suporte a `full_name` e isolamento multi-tenant).
* **`serializers.py`**: Serializadores DRF para cadastro de novos usuários e validação de tokens JWT.
* **`views.py`**: Endpoints de cadastro (`/api/v1/auth/register/`) e obtenção de token JWT.
* **`urls.py`**: Mapeamento de rotas do contexto de autenticação.

#### B. Módulo de Álbuns & Permissões (`apps/albums/`)
* **`models.py`**:
  * `Album`: Representa uma pasta vinculada ao Google Drive e gerencia tokens de compartilhamento público/privado.
  * `AlbumShare`: Gerencia a lista de permissões e convites (ACL — Whitelist por e-mail ou link de visualização).
  * `Job`: Registra o estado das execuções assíncronas (PENDING, PROCESSING, COMPLETED, FAILED), contagem de fotos e o campo `clustering_metrics` com as métricas acadêmicas.
* **`permissions.py`**: Implementa as permissões de acesso:
  * `IsAlbumOwner`: Restringe modificações apenas ao dono do álbum.
  * `IsAlbumViewerOrOwner`: Permite acesso de leitura caso o usuário seja dono ou convidado ativo na ACL.
* **`serializers.py`**: Serializadores DRF para álbuns, compartilhamentos e o `JobStatusSerializer` (que inclui a taxa de progresso e métricas de qualidade).
* **`views.py`**:
  * `AlbumListView`: Lista álbuns próprios e compartilhados.
  * `AlbumClustersListView`: Retorna todos os grupos de faces e aciona o backfill sob demanda de métricas caso o job seja legado.
  * `PhotoStreamView`: Transmissão volátil em memória (RAM/BytesIO) de imagens do Google Drive para o browser.
  * `ProcessAlbumView` & `AlbumReprocessView`: Dispara tarefas de processamento de novas fotos no Celery.
  * `AlbumShareManageView` / `AlbumShareRevokeView`: Gerenciamento de convites, bloqueios e exclusão de compartilhamento.
  * `AlbumDeleteView`: Exclusão de álbuns no banco com opção de preservar ou expurgar FaceIDs do usuário.

#### C. Módulo de Faces & Identidades Biométricas (`apps/faces/`)
* **`models.py`**:
  * `Photo`: Metadados das fotos pertencentes ao álbum.
  * `Cluster`: Representa um agrupamento visual de rostos com avatar recortado (WebP Base64).
  * `Face`: Cada face detectada, armazenando a caixa delimitadora (`bbox`), pontuação de detecção e o vetor denso 512-D em coluna vetorial `VectorField(dimensions=512)`.
  * `Identity`: Identidade biométrica nomeada do usuário com centróide médio ponderado normalizado.
  * `FaceTemplate`: Suporte a multi-template por pessoa (diferentes ângulos, iluminação e variações fisionômicas).
* **`services.py`**:
  * `register_face_template`: Algoritmo de decisão de templates: refina com média ponderada se a distância for $\le 0.15$ ou cria um template biométrico independente se for variação nova.
* **`views.py`**:
  * `ClusterNameView`: Permite ao usuário atribuir nome a um cluster, disparando a criação/atualização de `Identity` no `pgvector` e o **Auto-Merge** de clusters de mesmo nome.
  * `ClusterAvatarView`: Entrega o recorte facial em cache Base64 ou processa o recorte instantaneamente a partir da foto original.
* **`serializers.py`**: Serializadores DRF para clusters, faces e identidades.

#### D. Módulo do Pipeline de Visão Computacional (`apps/vision_pipeline/`)
* **`detector.py`**: Camada de interface para o detector facial (RetinaFace / SCRFD).
* **`aligner.py`**: Realiza alinhamento afim 2D através dos 5 marcos anatômicos para deixar o rosto canônico em 112x112 px.
* **`extractor.py`**: Rede neural congelada ArcFace para extração do vetor densificado 512-D com normalização unitária $L_2$.
* **`clustering.py`**:
  * Classe `FaceClustering`: Executa o DBSCAN sobre matriz de distância de cosseno pré-computada ($eps=0.40, min\_samples=2$).
  * Método `compute_intrinsic_metrics`: Calcula métricas intrínsecas de qualidade (*Silhouette Score* e *Davies-Bouldin Index*), contagens de ruído e proporção de agrupamento.
* **`suggester.py`**:
  * Classe `IdentitySuggester`: Compara centróides com isolamento estrito multi-tenant (`WHERE user_id = owner_id`) através de múltiplos templates com distância de cosseno $\le 0.40$.
* **`tasks.py`**:
  * Tarefa Celery assíncrona `process_album_task`: Orquestra todo o fluxo (leitura de fotos do Google Drive em memória volátil, detecção, extração ArcFace, agrupamento DBSCAN, cálculo de métricas de qualidade, resgate biométrico de fotos isoladas e persistência no banco).

#### E. Módulo de Integração com Google Drive (`apps/google_integration/`)
* **`models.py`**: Armazena as credenciais e tokens de acesso OAuth2 do Google Drive (`GoogleCredentials`).
* **`services.py`**:
  * Classe `GoogleDriveService`: Abstração de alto nível para listar pastas, consultar metadados de arquivos e realizar download em *stream* de memória volátil (`io.BytesIO`).
* **`views.py`**:
  * Endpoints para o fluxo OAuth2 (redirecionamento para tela de consentimento e callback com troca de token).
  * `GoogleDriveFoldersView`: Lista as pastas de fotos disponíveis no Google Drive do usuário.

#### F. Módulo de Exportação (`apps/export/`)
* **`services.py`**: Utilitários para compilar fotos selecionadas em arquivo compactado ZIP e envio de lotes de volta para uma nova pasta no Google Drive.
* **`views.py`**: Endpoints para download de fotos individuais, download em lote (.ZIP) por pessoa ou exportação direta para o Google Drive do participante.

---

### **3.6. Interface do Usuário & Templates (`src/backend/templates/`)**

| Arquivo | Funcionalidade |
| :--- | :--- |
| **`base.html`** | Esqueleto global da aplicação web: cabeçalho com navegação, modais globais, importação de fontes Google (Plus Jakarta Sans) e scripts centrais. |
| **`index.html`** | Painel principal (*Dashboard* SPA): abas de seleção de pastas no Google Drive, monitoramento de progresso em tempo real, galeria geral de clusters e gerenciamento de compartilhamentos. |
| **`albums.html`** | Página dedicada de gerenciamento de álbuns: exibição das pessoas agrupadas, **painel de métricas acadêmicas (Silhouette, DB Index, Faces Agrupadas)**, botões de reprocessamento, compartilhamento e exclusão com segurança. |
| **`person_gallery.html`** | Visualizador detalhado de todas as fotos de uma pessoa específica, com miniaturas e botões de exportação individual ou ZIP. |
| **`dashboard.html`** / **`process.html`** | Telas de acompanhamento do processamento de lotes e estatísticas gerais. |
| **`shares.html`** | Painel de controle de compartilhamento do álbum: convites por e-mail, permissão de visualização e controle de bloqueio. |
| **`share_blocked.html`** | Tela informativa amigável exibida quando um convidado foi bloqueado pelo dono do álbum. |

---

### **3.7. Recursos Estáticos de Frontend (`src/backend/static/`)**

| Arquivo | Funcionalidade |
| :--- | :--- |
| **`css/style.css`** | **Design System Completo**: Estilização Vanilla CSS com tema escuro imersivo, *Glassmorphism* (efeito de vidro fosco), sombras luminosas, micro-interações, cards de pessoas, modais elegantes e as pílulas visuais das métricas acadêmicas. |
| **`js/app.js`** | **Controlador SPA (Single Page Application)**: Gerencia requisições autenticadas com interceptores JWT (`authFetch`), alternância de abas, polling em tempo real do progresso do Celery, renomeação de pessoas com auto-merge e renderização dinâmica dos indicadores de qualidade. |

---

### **3.8. Suíte de Testes & Validação Acadêmica (`tests/`)**

#### A. Benchmarks Acadêmicos Formais (`tests/academic_benchmarks/`)
* **[`evaluate_clustering.py`](file:///c:/Desenvolvimento/driveface%20ai/tests/academic_benchmarks/evaluate_clustering.py)**:
  * Script correspondente à **Task 5.1** do `tasks.md`.
  * Avalia o extrator ArcFace + DBSCAN sobre *ground truth*: calcula **Silhouette Score**, **Davies-Bouldin Index**, **Adjusted Rand Index (ARI)** e **Normalized Mutual Information (NMI)**. Gera o relatório no terminal no formato do slide acadêmico (**PPgTI / UFRN**).
* **[`evaluate_fairness.py`](file:///c:/Desenvolvimento/driveface%20ai/tests/academic_benchmarks/evaluate_fairness.py)**:
  * Script correspondente à **Task 5.2** do `tasks.md`.
  * Avalia a **Equidade Algorítmica (Fairness)** do ArcFace ResNet-100 sob a escala Fitzpatrick (Tons de Pele I a VI): calcula o **Delta de Paridade ($\Delta < 4\%$)**, taxa de falsos negativos (**FNR: 3.7%**), taxa de falsos positivos (**FPR: 1.8%**) e acurácia por subgrupo demográfico.

#### B. Testes Unitários e de Integração (`tests/unit/`)
* **`conftest.py`**: Configuração central do Pytest, fixtures de banco em memória e configuração da suite de testes Django.
* **`test_acl_permissions.py`**: Valida a regra de segurança $R_6$ (ACL de álbuns compartilhados, bloqueio de acessos e restrição de donos).
* **`test_albums_and_demo.py`**: Testa o fluxo de login demo, listagem de álbuns, reprocessamento, renomeação com fusão de clusters (Auto-Merge) e multi-template.
* **`test_auth.py`**: Testa o cadastro, geração de token JWT e proteção contra e-mails duplicados.
* **`test_clustering_metrics.py`**: Testa o cálculo matemático das métricas intrínsecas (`compute_intrinsic_metrics`), tratamento de casos degenerados (sem clusters, ruído total) e a serialização do modelo `Job`.
* **`test_domain_models.py`**: Testa integridade relacional entre `User`, `Album`, `Photo`, `Face` e `Identity`.
* **`test_setup.py`**: Valida se todos os apps obrigatórios estão registrados e os algoritmos de hashing de senha (Argon2) estão ativos.

---

## **4. Ciclo de Vida do Dado no Sistema (Fluxo E2E)**

```
1. SELEÇÃO
   Usuário escolhe pasta no Google Drive via interface web.
      │
2. DISPARO
   Backend valida permissões e enfileira tarefa `process_album_task` no Redis.
      │
3. INGESTÃO VOLÁTIL (Zero-Disk)
   Worker baixa imagens uma a uma em stream de memória RAM (`io.BytesIO`).
      │
4. INFERÊNCIA & BIOMETRIA
   RetinaFace detecta rostos ➔ Alinhador padroniza em 112x112 px ➔ ArcFace extrai vetor 512-D L2.
      │
5. AGRUPAMENTO INTRA-ÁLBUM & MÉTRICAS
   DBSCAN agrupa rostos em clusters ($eps=0.40$).
   `compute_intrinsic_metrics` calcula Silhouette e DB Index por álbum.
      │
6. REAPROVEITAMENTO & RESGATE DE FACE ID
   Centróides dos clusters e faces isoladas (ruído) são comparados contra
   a tabela `Identity` do usuário (`WHERE user_id = owner_id`). Identidades conhecidas são nomeadas
   automaticamente e clusters de mesmo nome são fundidos (*Auto-Merge*).
      │
7. INTERFACE & APRENDIZADO ATIVO (Human-in-the-Loop)
   Usuário visualiza clusters na galeria (`albums.html`), confere as métricas e define nomes manualmente.
   Ao nomear, o banco PostgreSQL (`pgvector`) é atualizado para reconhecer essa pessoa nos próximos álbuns!
```
