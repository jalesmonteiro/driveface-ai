# TASKS: DRIVEFACE AI

**Versão:** 1.0  
**Data:** 28/08/2026  
**Status:** Aguardando Execução / Aprovação (Fase 4\)  
**Autor:** SDD Architect  
**Alvo:** Agentes de IA Autônomos (Cursor, Copilot, Devin, AntiGravity)

\---

# Agent Protocol (Regras para a IA Codificadora)

* **State Management:** Após concluir cada task com sucesso, marque o checkbox correspondente como \`\[x\]\` neste arquivo para sincronizar o progresso.  
* **Validation Loop (TDD / Verification First):** Ao finalizar qualquer tarefa, execute a suíte de testes unitários ou comandos de validação definidos na seção **Definition of Done**. É expressamente proibido avançar para a task seguinte se houver falha de execução, erro de compilação/lint ou teste quebrado.  
* **Autonomy Rules:**  
  * **\[AUTO\]**: Tarefas determinísticas com regras fechadas. O agente tem autorização para codificar, testar e avançar automaticamente.  
  * **\[HUMAN-CHECK\]**: Pontos de controle arquiteturais, configuração de credenciais sensíveis ou validação de métricas de pesquisa. O agente DEVE pausar a execução e solicitar a inspeção e confirmação do usuário.  
* **Zero Hallucination & Code Constraints:**  
  * Implementação obrigatória em **Python 3.11+** com **Django 5.x** e **Django REST Framework**.  
  * O processamento de imagens do Google Drive deve ocorrer **exclusivamente em memória volátil (**\`io.BytesIO\`**)**, sendo estritamente proibido salvar arquivos brutos em disco.  
  * Todas as consultas de centróides e identificação devem impor a cláusula de isolamento \`WHERE user\_id \= request.user.id\`.

\---

# Fase 0: Setup Profissional, Ambiente e Infraestrutura

**[x] Task 0.1: Inicializar Monorepo e Estrutura Modular Django [AUTO]**

* **Objetivo:** Criar a raiz do projeto \`driveface-ai\`, configurar o gerenciador de dependências (\`pyproject.toml\` com Poetry ou Pipenv/Pip-tools) incluindo as dependências centrais: \`Django\>=5.0\`, \`djangorestframework\`, \`djangorestframework-simplejwt\`, \`argon2-cffi\`, \`celery\>=5.3\`, \`redis\>=5.0\`, \`psycopg\[binary\]\>=3.1\`, \`pgvector\>=0.2\`, \`google-api-python-client\`, \`google-auth-oauthlib\`, \`insightface\`, \`onnxruntime-gpu\`, \`scikit-learn\`, \`numpy\`, \`pillow\`. Inicializar o projeto Django em \`src/backend/config\` e criar as aplicações vazias: \`authentication\`, \`google\_integration\`, \`albums\`, \`faces\`, \`export\`, \`vision\_pipeline\`.  
  * **Definition of Done:** Executar \`python \-m django \--version\` e verificar se \`manage.py check\` executa sem erros de importação.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 0.2: Configurar Docker Compose (PostgreSQL com pgvector e Redis 7\) \[AUTO\]**

  * **Objetivo:** Criar \`docker/docker-compose.yml\` contendo os serviços \`postgres\` (utilizando a imagem oficial \`pgvector/pgvector:pg16\`), \`redis\` (imagem \`redis:7-alpine\`), \`web\` (Django) e \`worker\` (Celery com suporte a GPU/CUDA via NVIDIA container toolkit). Mapear portas padrão (5432, 6379, 8000).  
  * **Definition of Done:** Executar \`docker compose \-f docker/docker-compose.yml up \-d postgres redis\` e validar a criação da extensão \`CREATE EXTENSION IF NOT EXISTS vector;\` conectando via \`psql\`.  
  * **Autonomia: \[AUTO\]**

  **[x] Task 0.3: Criar Arquivo de Variáveis de Ambiente e Checkpoint de Credenciais [HUMAN-CHECK]**

  * **Objetivo:** Criar o arquivo \`.env.example\` contendo todas as variáveis documentadas na Seção 6 do \`Plan.md\` (\`DJANGO\_SECRET\_KEY\`, \`DATABASE\_URL\`, \`CELERY\_BROKER\_URL\`, \`GOOGLE\_CLIENT\_ID\`, \`GOOGLE\_CLIENT\_SECRET\`, \`GOOGLE\_REDIRECT\_URI\`, limiares matemáticos). Solicitar ao usuário o preenchimento das chaves OAuth e configurações locais no \`.env\`.  
  * **Definition of Done:** O usuário confirma o preenchimento do \`.env\` e a aplicação lê com sucesso as variáveis via \`django-environ\` ou \`pydantic-settings\`.  
  * **Autonomia: \[HUMAN-CHECK\]**

\---

# Fase 1: Autenticação, Usuários, Permissões ACL & Modelagem Vetorial

**[x] Task 1.1: Implementar Custom User Model e Autenticação JWT com Argon2 [AUTO]**

* **Objetivo:** No app \`authentication\`, implementar \`User\` herdando de \`AbstractBaseUser\` e \`PermissionsMixin\`, utilizando \`email\` como chave natural única (\`USERNAME\_FIELD\`), \`id\` como \`UUIDField\` e senha hash com Argon2id. Configurar \`djangorestframework-simplejwt\` para emissão e rotação de tokens em \`/api/v1/auth/token/\` e criar o endpoint de cadastro \`/api/v1/auth/register/\`.  
  * **Definition of Done:** Executar suíte de testes unitários \`pytest tests/unit/test\_auth.py\` garantindo cadastro de usuário, rejeição de e-mail duplicado e obtenção de token JWT válido com status 200/201.  
  * **Autonomia: \[AUTO\]**

  **[x] Task 1.2: Modelagem ORM de Domínio com pgvector (albums e faces) [AUTO]**

  * **Objetivo:** Implementar os modelos relacionais e vetoriais conforme Seção 4.1 do \`Plan.md\`:  
    * \`albums.models\`: \`Album\` (id, owner FK, google\_drive\_folder\_id, folder\_name, share\_token, is\_share\_active), \`AlbumShare\` (album FK, invited\_email, role="VIEWER"), \`Job\` (album FK, status, total\_images, processed\_images).  
    * \`faces.models\`: \`Photo\` (album FK, google\_file\_id, filename, faces\_count), \`Cluster\` (album FK, identity FK nullable, label, avatar\_crop\_webp, face\_count), \`Face\` (photo FK, cluster FK, \`VectorField(dimensions=512)\`, bboxes, confidence), \`Identity\` (user FK, person\_name, \`VectorField(dimensions=512)\` para centróide, total\_samples).  
    * Gerar e aplicar as migrações Django (\`makemigrations\` e \`migrate\`).  
  * **Definition of Done:** Executar \`python src/backend/manage.py migrate\` e validar a criação das tabelas no PostgreSQL e o tipo \`vector(512)\` nas colunas correspondentes.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 1.3: Implementar Motor de Permissões Orientado a Objeto (ACL Whitelist R\_6) \[HUMAN-CHECK\]**

  * **Objetivo:** No app \`albums/permissions.py\`, implementar:  
    * \`IsAlbumOwner\`: Permite acesso total apenas se \`request.user \== obj.owner\`.  
    * \`IsAlbumViewerOrOwner\`: Permite acesso de leitura se o usuário for o proprietário OU se o \`request.user.email\` estiver registrado na tabela \`AlbumShare\` do álbum com o \`share\_token\` correspondente. Bloquear estritamente qualquer outro usuário com \`403 Forbidden\` (\`ACL\_FORBIDDEN\`).  
    * Escrever suíte de testes unitários exaustivos cobrindo: acesso de Owner, acesso de Viewer autorizado e tentativa de invasão por e-mail não cadastrado.  
  * **Definition of Done:** Rodar \`pytest tests/unit/test\_acl\_permissions.py\` e verificar aprovação de 100% dos cenários de autorização e negação. Apresentar os logs de teste para validação humana.  
  * **Autonomia: \[HUMAN-CHECK\]**

\---

# Fase 2: Integração Google Drive & Orquestração de Tarefas Celery

**\[  \] Task 2.1: Implementar Cliente de Leitura do Google Drive API v3 \[AUTO\]**

* **Objetivo:** No app \`google\_integration/services.py\`, criar \`GoogleDriveService\` para:  
  * Autenticação com credenciais OAuth2 do usuário.  
    * Listagem incremental e paginada de arquivos de imagem (\`mimeType\` igual a \`image/jpeg\`, \`image/png\`, \`image/heic\`) a partir de um \`folder\_id\`.  
    * Download de imagens em streaming direto para buffer em memória \`io.BytesIO\` sem gerar arquivos temporários no sistema de arquivos.  
  * **Definition of Done:** Executar testes unitários com mocks do Google Drive API v3 (\`tests/unit/test\_drive\_service.py\`), verificando tratamento de paginação e erro \`429 Too Many Requests\` com retentativas via exponential backoff.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 2.2: Configurar Orquestração Celery e Endpoint de Início de Job \[AUTO\]**

  * **Objetivo:** Configurar \`src/backend/config/celery.py\` apontando para o Redis. No app \`albums\`, criar a view \`POST /api/v1/albums/process/\` que valida o payload Pydantic/DRF, cria o registro \`Album\` e \`Job\` com status \`PENDING\`, e despacha a tarefa assíncrona \`process\_album\_task.delay(str(job.id))\`, retornando HTTP \`202 Accepted\` com o \`job\_id\`.  
  * **Definition of Done:** Teste de integração chamando a rota \`/api/v1/albums/process/\` e validando o enfileiramento da mensagem no Redis com status retornado \`202\`.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 2.3: Implementar Monitoramento e Polling de Jobs /api/v1/jobs/{job\_id}/status/ \[AUTO\]**

  * **Objetivo:** Criar endpoint \`GET /api/v1/jobs/{job\_id}/status/\` retornando o progresso percentual, quantidade de imagens processadas, total de imagens e status do processamento (\`PENDING\`, \`PROCESSING\`, \`COMPLETED\`, \`FAILED\`).  
  * **Definition of Done:** Teste de integração validando atualização de progresso simulada de 0% a 100%.  
  * **Autonomia: \[AUTO\]**

\---

# Fase 3: Pipeline de Visão Computacional, Embeddings & Agrupamento

**\[  \] Task 3.1: Implementar Wrappers de Detecção Facial e Alinhamento Anatômico \[AUTO\]**

* **Objetivo:** No app \`vision\_pipeline\`, construir os módulos:  
  * \`detector.py\`: Carregar modelo RetinaFace / SCRFD (InsightFace) com aceleração CUDA, detectando caixas delimitadoras e rejeitando predições com confiança \< 0.80.  
    * \`aligner.py\`: Aplicar transformação afim 2D baseada nos 5 pontos anatômicos fiduciais (olhos, nariz, cantos da boca) e gerar o recorte facial padronizado 160 x 160 px em formato WebP para uso como avatar.  
  * **Definition of Done:** Executar teste unitário com imagem de teste contendo múltiplas faces; verificar extração correta de coordenadas de bounding box e geração de miniaturas 160 x 160 px.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 3.2: Implementar Extrator de Características Profundas ArcFace (D \= 512\) \[AUTO\]**

  * **Objetivo:** No app \`vision\_pipeline/extractor.py\`, integrar o modelo ArcFace (ResNet50 backbone) para extrair o vetor de 512 dimensões com normalização L2 (||v||2 \= 1.0). Salvar cada detecção na tabela \`Face\` vinculando à \`Photo\`.  
  * **Definition of Done:** Validar via assert unitário se a norma Euclidiana do vetor retornado é igual a 1.0 ± 10^-5 e se a dimensão é estritamente 512\.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 3.3: Implementar Agrupamento Não-Supervisionado DBSCAN (Distância de Cosseno) \[AUTO\]**

  * **Objetivo:** No app \`vision\_pipeline/clustering.py\`, coletar todos os embeddings das faces processadas da pasta em uma matriz NumPy N x 512, computar a matriz de distâncias de cosseno e executar \`sklearn.cluster.DBSCAN(eps=0.40, min\_samples=2, metric='precomputed')\`:  
    * Agrupar faces com mesmo label numérico sob uma instância \`Cluster\`.  
    * Atribuir amostras marcadas como \`-1\` ao grupo de Ruído / Faces Não Agrupadas.  
  * **Definition of Done:** Teste unitário sintético com 3 grupos bem definidos de vetores unitários validando a criação exata de 3 clusters e separação correta de vetores ortogonais/ruído.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 3.4: Implementar Motor de Auto-Sugestão com Isolamento Multi-Tenant Estrito \[HUMAN-CHECK\]**

  * **Objetivo:** No app \`vision\_pipeline/suggester.py\`, após o agrupamento dos clusters:  
    * Calcular o centróide médio normalizado de cada cluster.

      $$\\mathbf{c}\_k \= \\frac{\\sum\_{\\mathbf{v} \\in C\_k} \\mathbf{v}}{\\left\\|\\sum\_{\\mathbf{v} \\in C\_k} \\mathbf{v}\\right\\|\_2}$$

* Executar consulta vetorial no \`pgvector\` sobre a tabela \`Identity\` aplicando obrigatoriamente o filtro de isolamento \`WHERE user\_id \= album.owner\_id\`.  
  * Se a menor distância de cosseno for menor ou igual a 0.35, associar o cluster à respectiva identidade com flag \`is\_suggested \= True\`.  
  * **Definition of Done:** Executar teste unitário cruzado simulando dois usuários distintos com faces idênticas; garantir matematicamente que o Usuário B nunca receba sugestões baseadas nos centróides cadastrados pelo Usuário A. Apresentar evidência de isolamento para validação humana.  
  * **Autonomia: \[HUMAN-CHECK\]**

  **\[  \] Task 3.5: Execução da Tarefa Celery Mestre process\_album\_task de Ponta a Ponta \[AUTO\]**

  * **Objetivo:** Integrar os passos 3.1, 3.2, 3.3 e 3.4 na tarefa Celery \`process\_album\_task(job\_id)\`. Adicionar atualização periódica do campo \`processed\_images\` no \`Job\` e tratamento de erros para transição segura para \`FAILED\` caso ocorra falha fatal.  
  * **Definition of Done:** Executar teste de integração assíncrono processando pasta mockada com 20 imagens, garantindo transição final do \`Job\` para \`COMPLETED\` e persistência íntegra no banco.  
  * **Autonomia: \[AUTO\]**

\---

# Fase 4: Exportação, Gestão de Compartilhamento & Endpoints da API

**\[  \] Task 4.1: Endpoints de Gestão de Álbuns, Clusters e Renomeação \[AUTO\]**

* **Objetivo:** No app \`albums\` e \`faces\`, implementar as views DRF:  
  * \`GET /api/v1/albums/{album\_id}/\`: Retorna detalhes da pasta, lista de clusters e contagem de fotos.  
    * \`POST /api/v1/clusters/{cluster\_id}/name/\`: Permite ao proprietário nomear uma pessoa, criando ou atualizando o registro na tabela \`Identity\` e recalculando o centróide ponderado.  
    * \`GET /api/v1/clusters/{cluster\_id}/photos/\`: Lista todas as fotos vinculadas àquela pessoa.  
  * **Definition of Done:** Testes unitários de API validando operações CRUD e cálculo incremental do centróide na renomeação.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 4.2: Endpoints de Compartilhamento Seguro (Whitelist & Token) \[AUTO\]**

  * **Objetivo:** Implementar:  
    * \`POST /api/v1/albums/{album\_id}/shares/\`: Proprietário ativa compartilhamento e adiciona lista de e-mails autorizados à whitelist.  
    * \`GET /api/v1/albums/shared/{share\_token}/\`: Visitante autenticado acessa o álbum. A view valida o e-mail via \`IsAlbumViewerOrOwner\` e retorna os clusters e fotos apenas se autorizado.  
  * **Definition of Done:** Testes de integração simulando requisição com usuário autorizado (HTTP 200\) e usuário não listado (HTTP 403 Forbidden).  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 4.3: Implementação dos Mecanismos de Exportação (ZIP em Memória e Google Drive Copy) \[HUMAN-CHECK\]**

  * **Objetivo:** No app \`export/services.py\`:  
    * \`GET /api/v1/clusters/{cluster\_id}/export/zip/\`: Gerar arquivo \`.zip\` dinamicamente em memória via \`io.BytesIO\` e \`zipfile.ZipFile\`, baixando as imagens correspondentes via stream e retornando \`StreamingHttpResponse(content\_type='application/zip')\`.  
    * \`POST /api/v1/clusters/{cluster\_id}/export/drive/\`: Criar pasta "DriveFace \- \[Nome\]" no Google Drive do usuário solicitante e invocar \`drive\_service.files().copy\` para cada imagem do cluster.  
  * **Definition of Done:** Validar o streaming do arquivo ZIP sem que haja escrita de arquivos no disco do servidor e verificar teste mockado de cópia no Drive. Apresentar resultado para validação humana.  
  * **Autonomia: \[HUMAN-CHECK\]**

\---

# Fase 5: Validação Acadêmica, Testes de Equidade & Finalização

**\[  \] Task 5.1: Implementar Script de Métricas de Agrupamento Acadêmico (Doutorado) \[AUTO\]**

* **Objetivo:** Criar \`tests/academic\_benchmarks/evaluate\_clustering.py\` para calcular automaticamente:  
  * *Silhouette Score* (coesão e separação intra/inter cluster).  
    * *Adjusted Rand Index (ARI)* e *Normalized Mutual Information (NMI)* comparando com ground truth de datasets acadêmicos abertos (LFW ou subconjunto CelebA).  
  * **Definition of Done:** Executar o script de avaliação e gerar relatório em tabela no terminal exibindo Silhouette ≥ 0.65 e ARI ≥ 0.85 para o conjunto de validação.  
  * **Autonomia: \[AUTO\]**

  **\[  \] Task 5.2: Implementar Pipeline de Avaliação de Equidade Demográfica (Fairness Benchmark) \[HUMAN-CHECK\]**

  * **Objetivo:** Criar \`tests/academic\_benchmarks/evaluate\_fairness.py\` para avaliar a paridade de desempenho do extrator/clusterizador entre subgrupos demográficos de gênero e diferentes tons de pele (escala Fitzpatrick). Medir as taxas de Falso Positivo (FPR) e Falso Negativo (FNR) em cada subgrupo.  
  * **Definition of Done:** Gerar relatório formal de paridade estatística comprovando que a variação de precisão entre os grupos não ultrapassa o limite aceitável (Δ \< 5%). Submeter relatório para validação humana.  
  * **Autonomia: \[HUMAN-CHECK\]**

  **\[  \] Task 5.3: Auditoria Final de Segurança, Cobertura de Testes e Documentação \[HUMAN-CHECK\]**

  * **Objetivo:** Executar suíte completa de testes com medição de cobertura via \`pytest \--cov=src/backend \--cov-report=term-missing\`. Garantir cobertura global ≥ 85%, zero violações de linter (\`flake8\`, \`black\`, \`isort\`) e validação de todas as regras inegociáveis do \`Constitution.md\`.  
  * **Definition of Done:** Cobertura comprovada ≥ 85% e todas as tasks anteriores marcadas como \`\[x\]\`. Apresentar resumo final para aprovação formal do pesquisador.

**Autonomia: \[HUMAN-CHECK\]**