# DriveFace AI

Sistema inteligente multi-usuário para agrupamento facial e indexação automática em fotos do Google Drive.

## Arquitetura
- **Backend:** Django 5.x, Django REST Framework, Celery
- **Banco de Dados & Vetores:** PostgreSQL 16 com extensão `pgvector` (vetores de 512 dimensões)
- **Broker / Cache:** Redis 7
- **Pipeline de Visão:** RetinaFace (Detecção & Landmarks), ArcFace (Deep Embeddings 512-d), DBSCAN (Clustering por Distância de Cosseno)
- **Integração:** Google Drive API v3 (streaming volátil em RAM via `io.BytesIO`)

Consulte a pasta `docs/` para especificações completas (`const.md`, `spec.md`, `plan.md`, `tasks.md`).

### Por que PostgreSQL 16 com pgvector (e não MySQL)?

A escolha do **PostgreSQL 16 com a extensão `pgvector`** em vez de bancos relacionais tradicionais (como MySQL) é uma decisão arquitetural fundamental para sistemas modernos de Inteligência Artificial:

1. **Tipo Nativo de Vetor de Alta Dimensão (`vector(512)`):**  
   O pipeline de visão (ArcFace) extrai embeddings faciais de 512 dimensões para cada rosto detectado. O `pgvector` armazena esses vetores como um tipo primitivo no banco de dados com suporte direto no Django ORM (`pgvector.django.VectorField`). No MySQL tradicional, seria necessário converter vetores para BLOBs ou strings JSON desestruturadas.

2. **Cálculo de Similaridade de Cosseno Direto no Banco:**  
   O `pgvector` realiza operações matemáticas vetoriais (distância de cosseno `<=>`, produto interno `<#>`, distância euclidiana `<->`) diretamente na camada do banco, utilizando índices vetoriais avançados (**HNSW** e **IVFFlat**). Isso permite consultar e sugerir identidades (`Identity.objects.order_by(CosineDistance(...))`) em milissegundos mesmo com centenas de milhares de fotos, sem precisar carregar todos os vetores para a memória RAM do Python.

3. **Arquitetura Unificada e ACID (Sem Complexidade de Dois Bancos):**  
   Ao usar o PostgreSQL, evitamos a necessidade de gerenciar um banco de dados relacional (ex: MySQL) + um banco de dados vetorial dedicado separado (ex: Pinecone, Milvus ou Qdrant). Todas as relações (usuários, permissões, álbuns, fotos, clusters e centróides faciais) compartilham a mesma integridade referencial, transações ACID e rotina de backup simples.

---

## Pré-requisitos

- **Python 3.11+**
- **Docker** e **Docker Compose**
- **Git**

---

## Configuração do Ambiente

### 1. Clonar o repositório e criar o ambiente virtual

**No Windows (PowerShell):**
```powershell
git clone <url-do-repositorio>
cd "driveface ai"

python -m venv .venv
.venv\Scripts\Activate.ps1
```

**No Linux / macOS:**
```bash
git clone <url-do-repositorio>
cd "driveface ai"

python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar as dependências

> **Atenção:** Se for rodar a aplicação localmente no host (fora dos contêineres Docker) ou executar testes, a instalação das dependências no ambiente virtual (`.venv`) **é obrigatória**.  
> *(Caso execute tudo 100% via Docker Compose, o Docker cuidará da instalação automaticamente dentro das imagens).*

Você pode instalar as dependências de duas maneiras equivalentes:

#### Opção A: Usando `requirements.txt` (Tradicional)
```bash
pip install --upgrade pip

# Dependências principais (Django, DRF, Celery, Redis, pgvector, etc.):
pip install -r requirements.txt

# Dependências de desenvolvimento e testes (pytest, flake8, black):
pip install -r requirements-dev.txt

# (Opcional) Bibliotecas de IA para pipeline de visão (InsightFace / ONNX Runtime):
pip install -r requirements-ai.txt
```

#### Opção B: Usando `pyproject.toml` (PEP 621 / Modo Editável)
```bash
pip install --upgrade pip

# Dependências principais:
pip install -e .

# Dependências de desenvolvimento e testes:
pip install -e ".[dev]"

# (Opcional) Bibliotecas de IA:
pip install -e ".[ai]"
```

### 3. Configurar variáveis de ambiente

Copie o arquivo de exemplo `.env.example` para `.env` e preencha as variáveis (especialmente as credenciais do Google OAuth2 se for utilizar a sincronização com Google Drive):

**No Windows:**
```powershell
Copy-Item .env.example .env
```

**No Linux / macOS:**
```bash
cp .env.example .env
```

---

## Execução da Aplicação

Você pode executar o projeto de duas formas:
1. **Modo Híbrido / Desenvolvimento Local** (Recomendado: banco e Redis no Docker, API e Celery no host).
2. **Modo 100% Docker** (Toda a stack em contêineres).

---

### Opção 1: Desenvolvimento Local (Recomendado)

#### Passo 1: Subir os serviços de infraestrutura (PostgreSQL com pgvector + Redis)

```bash
docker compose -f docker/docker-compose.yml up -d postgres redis
```

Verifique se os contêineres estão saudáveis com `docker ps`.

#### Passo 2: Executar as migrações do banco de dados

```bash
python src/backend/manage.py migrate
```

*(Opcional)* Crie um superusuário para acessar o Django Admin:
```bash
python src/backend/manage.py createsuperuser
```

#### Passo 3: Iniciar o servidor da API (Django REST Framework)

```bash
python src/backend/manage.py runserver 0.0.0.0:8000
```

- **API Base:** `http://localhost:8000/`
- **Django Admin:** `http://localhost:8000/admin/`

#### Passo 4: Iniciar o worker assíncrono (Celery)

Abra um novo terminal com o ambiente virtual ativado:

**No Windows (PowerShell):**
```powershell
$env:PYTHONPATH="src/backend;src/backend/apps"
celery -A config worker --loglevel=info -P solo
```
> *Nota: No Windows, utilize o pool `-P solo` ou `-P threads` devido à ausência de `fork` nativo.*

**No Linux / macOS:**
```bash
export PYTHONPATH="src/backend:src/backend/apps"
celery -A config worker --loglevel=info
```

---

### Opção 2: Execução 100% via Docker Compose

Para subir todos os serviços (PostgreSQL + pgvector, Redis, API Web e Worker Celery):

```bash
# Construir e iniciar os contêineres
docker compose -f docker/docker-compose.yml up --build

# Ou para rodar em segundo plano (detached):
docker compose -f docker/docker-compose.yml up -d --build
```

Para aplicar migrações dentro do contêiner Docker:
```bash
docker compose -f docker/docker-compose.yml exec web python manage.py migrate
```

Para recarregar alterações nos serviços da aplicação sem reiniciar o banco de dados:
```bash
docker compose -f docker/docker-compose.yml up -d --force-recreate web worker
```

Para parar os serviços:
```bash
docker compose -f docker/docker-compose.yml down
```

---

## Testes Automatizados

Com os serviços de banco e cache rodando, execute a suíte de testes com `pytest`:

```bash
# Executar todos os testes
pytest

# Executar com relatório de cobertura
pytest --cov=src/backend
```

---

## Resolução de Módulos no Editor / IDE (VS Code / Pyright)

Os submódulos da aplicação residem no diretório `src/backend/apps` (ex.: `faces`, `albums`, `export`, `vision_pipeline`). 

Para que editores como o **VS Code**, **Antigravity IDE** e o analisador **Pyright/Pylance** reconheçam as importações diretas (`from faces.models import ...`, `from albums.permissions import ...`) sem warnings de *"Cannot find module"*:
- As configurações de caminhos extras já estão definidas em `.vscode/settings.json` (`python.analysis.extraPaths`), em `pyrightconfig.json` e no `pyproject.toml` (`[tool.pyright] extraPaths`).
- No ambiente virtual local, o arquivo `.venv/Lib/site-packages/driveface.pth` adiciona automaticamente `src/backend` e `src/backend/apps` ao `sys.path`.

---

## Guia Extra: Criação das Credenciais no Google Cloud Console

> [!IMPORTANT]
> **Uma única chave (Client ID + Client Secret) serve para ambas as APIs!**
> Você **não precisa** criar credenciais separadas para a *Google Drive API* e para a *Google People API*. No ecossistema Google Cloud OAuth2, um único **ID do cliente OAuth** autentica o usuário e solicita permissões combinadas para múltiplos serviços através dos **Escopos (Scopes)** configurados.

---

### 1. Criar o Projeto e Ativar as APIs
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um novo projeto (ex: `DriveFace AI`).
2. Acesse o menu **APIs e Serviços** > **Biblioteca** e ative:
   - **Google Drive API**
   - **Google People API** (ou **Google Identity**)

### 2. Configurar a Tela de Consentimento OAuth
1. Vá em **APIs e Serviços** > **Tela de consentimento OAuth**.
2. Selecione o tipo de usuário **Externo** e clique em **Criar**.
3. Preencha o nome do aplicativo (`DriveFace AI`) e seu e-mail de suporte.
4. Na etapa **Escopos**, adicione os escopos de perfil e drive:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/drive.file`
5. Na etapa **Usuários de teste** (*Test Users*):
   - Adicione o seu e-mail do Google (e de qualquer outra pessoa que for testar). **Apenas e-mails listados aqui conseguirão fazer login** enquanto o aplicativo estiver com status *"Testing"*.

### 3. Criar a Chave de Credencial (Client ID)
1. Vá em **APIs e Serviços** > **Credenciais**.
2. Clique em **+ Criar Credenciais** > **ID do cliente OAuth**.
3. Se abrir o assistente com *"Qual API você usa?"*:
   - Escolha **Google Drive API**.
   - Em *"Que dados você acessará?"*, marque **Dados do usuário** (*User data*).
4. No tipo de aplicativo, selecione **Aplicativo da Web** (*Web Application*).
5. Nome: `DriveFace Web Local`.
6. Configure as URLs de desenvolvimento:
   - **Origens JavaScript autorizadas:**
     ```text
     http://localhost:8000
     ```
     *(Atenção: Não coloque barra `/` no final da URL).*
   - **URIs de redirecionamento autorizados:**
     ```text
     http://localhost:8000/api/v1/google/oauth/callback/
     ```
7. Clique em **Criar**.

### 4. Adicionar ao arquivo `.env`
Copie o **ID do cliente** e a **Chave secreta do cliente** (*Client Secret*) e adicione ao seu arquivo `.env`:

```ini
# === Google Drive & Identity OAuth2 (Uma única chave atende ambas APIs) ===
GOOGLE_CLIENT_ID=seu_client_id_aqui.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu_client_secret_aqui
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/google/oauth/callback/
```

---

### 5. Status do App: "Testing" vs "In Production" (Limitações)

Ao finalizar a criação, o Google exibe o aviso de que o aplicativo está com status de publicação **"Testing"**. 

**Vai dar certo testar?**
**Sim, perfeitamente!** O modo "Testing" foi feito justamente para você desenvolver, rodar localmente e validar toda a aplicação sem custos nem burocracias.

**Quais são as limitações do modo "Testing"?**
1. **Lista de Usuários de Teste (Whitelist restrita):** Apenas os e-mails adicionados na aba **Usuários de teste** da Tela de consentimento conseguirão logar. Qualquer outra conta receberá erro `403 (access_denied)`. O limite é de até 100 usuários de teste.
2. **Expiração do Refresh Token em 7 dias:** Por segurança em modo de desenvolvimento, os tokens de atualização expiram após 7 dias. Quando isso acontecer, basta clicar em "Conectar com Google" novamente para renovar a sessão.
3. **Aviso de "App não verificado":** Ao fazer login pela primeira vez, o Google exibirá uma tela avisando *"O Google não verificou este app"*. Para prosseguir normalmente:
   - Clique em **"Avançado"** (ou *Advanced*).
   - Clique em **"Acessar DriveFace AI (não seguro)"** (ou *Go to DriveFace AI (unsafe)*) e conceda as permissões.

> *Nota: Você só precisará mudar para "In Production" e submeter à verificação do Google (que leva de 4 a 6 semanas para aprovar escopos do Drive) caso decida publicar o sistema comercialmente para qualquer usuário anônimo na internet.*

