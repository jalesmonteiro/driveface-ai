# **Roteiro de Estudo: IA, Visão Computacional e Fluxo de Reconhecimento**
### **DriveFace AI — Programa de Pós-Graduação em TI (PPgTI / UFRN)**

Este roteiro foi estruturado para orientar o seu estudo aprofundado dos componentes de Inteligência Artificial, do pipeline de visão computacional e do fluxo de reconhecimento facial implementados neste repositório.

---

## **Visão Geral da Trilha de Estudo**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FASE 1: O NÚCLEO MATEMÁTICO & ALGORÍTMICO                               │
│ [detector.py] ➔ [aligner.py] ➔ [extractor.py] ➔ [clustering.py] ➔ [suggester.py]
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ FASE 2: A ORQUESTRAÇÃO PONTA A PONTA (PRODUÇÃO ASSÍNCRONA)              │
│ [tasks.py] (process_album_task - As 10 etapas do Celery Worker)         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ FASE 3: PERSISTÊNCIA VETORIAL & MULTI-TEMPLATE (HUMAN-IN-THE-LOOP)      │
│ [faces/models.py] ➔ [faces/services.py] ➔ [faces/views.py]              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ FASE 4: VALIDAÇÃO EXPERIMENTAL & BENCHMARKS ACADÊMICOS                  │
│ [evaluate_clustering.py] (Silhouette, DB, ARI, NMI)                     │
│ [evaluate_fairness.py] (Equidade Fitzpatrick, Delta de Paridade, FNR)   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ FASE 5: FUNDAMENTAÇÃO TEÓRICA & ARTIGOS CIENTÍFICOS                     │
│ ArcFace (CVPR 2019), RetinaFace (CVPR 2020), DBSCAN e Geometria em S^511│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## **Fase 1: O Núcleo do Pipeline de Visão Computacional**

Estude estes módulos na ordem indicada. Eles contêm a lógica matemática e os algoritmos isolados.

### **1.1. Detecção Facial & Marcos Anatômicos**
* **Arquivo:** [`src/backend/apps/vision_pipeline/detector.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/vision_pipeline/detector.py)
* **Conceito:** O detector **SCRFD / RetinaFace** não reconhece quem é a pessoa. Seu papel é localizar o retângulo envolvente (*bounding box*) e as coordenadas dos **5 marcos anatômicos fiduciais** (olho esquerdo, olho direito, nariz, canto esquerdo da boca e canto direito da boca).
* **O que observar no código:**
  - Como o modelo recebe a imagem RGB/BGR.
  - O filtro de confiança mínima: faces com `det_score < 0.70` são descartadas para evitar falsos positivos de rostos em sombras ou texturas.
* **Pergunta de Fixação:** *Por que o detector não pode gerar o reconhecimento direto da identidade?*

---

### **1.2. Geometria & Alinhamento Afim 2D**
* **Arquivo:** [`src/backend/apps/vision_pipeline/aligner.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/vision_pipeline/aligner.py)
* **Conceito:** A rede de reconhecimento facial precisa que os rostos estejam na mesma escala e orientação canônica frontal. A **Transformação de Similaridade Afim** usa os 5 pontos para calcular a rotação, translação e escalonamento necessários para projetar a face em uma matriz padronizada de **$112 \times 112$ pixels**.
* **O que observar no código:**
  - O uso dos 5 pontos padrão de referência da literatura (*template canônico*).
  - A geração do recorte facial centralizado com respiro de 35% para os avatares WebP.
* **Pergunta de Fixação:** *O que aconteceria com os embeddings do ArcFace se enviássemos fotos de pessoas de cabeça para baixo ou inclinadas a 45 graus sem o alinhamento afim?*

---

### **1.3. Extração Profunda de Embeddings (ArcFace)**
* **Arquivo:** [`src/backend/apps/vision_pipeline/extractor.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/vision_pipeline/extractor.py)
* **Conceito:** A rede neural profunda (**iResNet-50 / iResNet-100**) processa os $37.632$ pixels da face alinhada e extrai um vetor denso de **512 dimensões** em ponto flutuante (`float32`).
* **O que observar no código:**
  - A operação de **Normalização $L_2$ estrita**:
    $$\hat{v} = \frac{v}{\|v\|_2} \implies \|\hat{v}\|_2 = 1.0$$
  - Como isso garante que a distância euclidiana ao quadrado seja estritamente proporcional à distância angular de cosseno:
    $$d_{\text{cosseno}}(u, v) = 1.0 - (u \cdot v)$$
* **Pergunta de Fixação:** *Por que todos os vetores precisam ter comprimento unitário exato igual a 1.0?*

---

### **1.4. Agrupamento Não-Supervisionado & Métricas de Qualidade**
* **Arquivo:** [`src/backend/apps/vision_pipeline/clustering.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/vision_pipeline/clustering.py)
* **Conceito:** Como o sistema agrupa rostos desconhecidos em um evento sem saber quantas pessoas existem previamente? Usa o **DBSCAN** com distância de cosseno pré-computada ($eps = 0.40, min\_samples = 2$).
* **O que observar no código:**
  - `fit_predict`: Cálculo da matriz de distância de cosseno via `sklearn.metrics.pairwise.cosine_distances` e atribuição de rótulos (rótulo `-1` indica ruído/faces isoladas).
  - `compute_intrinsic_metrics`: Cálculo do **Silhouette Score** (com métrica de cosseno) e do **Davies-Bouldin Index**, além do isolamento e tratamento defensivo para casos com menos de 2 clusters.
* **Pergunta de Fixação:** *Por que o DBSCAN é superior ao K-Means para o agrupamento facial de álbuns de fotos?*

---

### **1.5. Motor de Sugestão e Multi-Tenancy**
* **Arquivo:** [`src/backend/apps/vision_pipeline/suggester.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/vision_pipeline/suggester.py)
* **Conceito:** Implementação das regras inegociáveis de privacidade $R_1$ e $R_4$ da Constituição:
  $$\text{WHERE } user\_id = owner\_id$$
  Nenhum vetor de um usuário pode vazar ou ser sugerido para outro usuário.
* **O que observar no código:**
  - Como o suggester percorre tanto o `centroid_embedding` principal quanto a coleção de `templates` biométricos da pessoa.
  - O limiar de corte rígido: $d \le 0.35$ (se a menor distância for $> 0.35$, classifica como desconhecido em vez de arriscar um falso positivo).
* **Pergunta de Fixação:** *Como a busca multi-template resolve o problema de pessoas com óculos, barba ou ângulos diferentes?*

---

## **Fase 2: A Orquestração Ponta a Ponta (Produção Assíncrona)**

Este é o arquivo mais importante do backend para entender a integração completa de IA.

* **Arquivo:** [`src/backend/apps/vision_pipeline/tasks.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/vision_pipeline/tasks.py)
* **Função Principal:** `process_album_task(self, job_id)` (Tarefa Celery Assíncrona).

### **Trilha de Leitura Passo a Passo em `tasks.py`:**

1. **Etapa 1 & 2 (Linhas 120-150):** Atualização do `Job` para `PROCESSING` e listagem de fotos do Google Drive via API.
2. **Etapa 3 & 4 (Linhas 151-165):** Registro dos objetos `Photo` e instanciação do singleton InsightFace (`buffalo_sc` ou `buffalo_l`).
3. **Etapa 5 (Linhas 166-220):** **Download Volátil Zero-Disk**: a imagem entra em `io.BytesIO`, é convertida para array NumPy, passa por inferência no InsightFace, gera o recorte WebP 160x160 e o vetor 512-D normalizado. A imagem bruta é descartada da RAM imediatamente.
4. **Etapa 6 (Linhas 221-232):** Tratamento de fallback caso nenhuma face seja detectada.
5. **Etapa 7 (Linhas 233-242):** Agrupamento DBSCAN e acionamento de `clusterer.compute_intrinsic_metrics(...)` com persistência em `job.clustering_metrics`.
6. **Etapa 8 (Linhas 243-310):** Cálculo do centróide médio normalizado de cada cluster e consulta ao `IdentitySuggester`. Se houver match, executa o **Auto-Merge** no cluster existente e refina os templates biométricos.
7. **Etapa 9 (Linhas 311-402):** **Resgate Biométrico de Ruídos**: fotos que o DBSCAN marcou como $-1$ são testadas individualmente contra os FaceIDs do dono. Se identificadas, são salvas no cluster da pessoa; se não, vão para o agrupamento "Outras".
8. **Etapa 10 (Linhas 403-426):** Finalização do `Job` com status `COMPLETED` e salvamento das estatísticas no PostgreSQL.

---

## **Fase 3: Persistência Vetorial & Inteligência Adaptativa**

Compreenda como os dados de IA são gravados e combinados com o banco de dados.

### **3.1. Modelos Relacionais e Colunas Vetoriais**
* **Arquivo:** [`src/backend/apps/faces/models.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/faces/models.py)
* **Pontos de Estudo:**
  - `Face.embedding`: campo `VectorField(dimensions=512)` do `pgvector`.
  - `Identity`: armazena `centroid_embedding` (vetor 512-D ponderado) e `total_samples` (quantidade acumulada de fotos daquela pessoa).
  - `FaceTemplate`: modelos multi-template por identidade.
  - `Cluster`: contém `avatar_crop_webp` e contadores de faces.

### **3.2. Refinamento Biométrico & Multi-Template**
* **Arquivo:** [`src/backend/apps/faces/services.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/faces/services.py)
* **Função:** `register_face_template(identity, centroid_vec, samples_count)`
* **Lógica Matemática:**
  - Se a distância entre o novo centróide e um template existente for **$\le 0.15$**: considera que é a mesma aparência sob o mesmo ângulo e **refina o vetor através de média ponderada**:
    $$\vec{C}_{\text{novo}} = \frac{\vec{C}_{\text{antigo}} \cdot N_{\text{antigo}} + \vec{C}_{\text{amostra}} \cdot N_{\text{amostra}}}{N_{\text{antigo}} + N_{\text{amostra}}}$$
  - Se a distância for **$> 0.15$**: considera que é uma variação estética ou geométrica relevante (ex: novo ângulo ou corte de cabelo) e cria um **`FaceTemplate` adicional** vinculado à mesma `Identity`.

### **3.3. Definição Manual & Fusão de Clusters (Auto-Merge)**
* **Arquivo:** [`src/backend/apps/faces/views.py`](file:///c:/Desenvolvimento/driveface%20ai/src/backend/apps/faces/views.py)
* **Classe:** `ClusterNameView` (linhas 9 a 143)
* **Lógica:** O que acontece quando o usuário digita "Maria" em um cluster desconhecido?
  1. Calcula o centróide médio de todas as faces daquele cluster.
  2. Atualiza ou cria a `Identity` "Maria" no PostgreSQL.
  3. Verifica se já existia outro grupo "Maria" no mesmo álbum: se existir, migra todas as faces, unifica o centróide, atualiza o contador e exclui o cluster redundante (*Merge Automático*).

---

## **Fase 4: Validação Experimental & Benchmarks Acadêmicos**

Estes dois scripts foram desenvolvidos especificamente para as métricas da dissertação e relatórios acadêmicos (**PPgTI / UFRN**).

### **4.1. Validação de Agrupamento Não-Supervisionado (Task 5.1)**
* **Arquivo:** [`tests/academic_benchmarks/evaluate_clustering.py`](file:///c:/Desenvolvimento/driveface%20ai/tests/academic_benchmarks/evaluate_clustering.py)
* **Métricas Implementadas:**
  1. **Silhouette Score:** Coesão intra-cluster vs separação inter-cluster com métrica angular de cosseno.
  2. **Davies-Bouldin Index:** Razão entre a dispersão interna e a distância entre centróides (quanto menor, mais compactos e separados são os grupos).
  3. **Adjusted Rand Index (ARI):** Mede a concordância entre os clusters gerados pelo DBSCAN e as identidades verdadeiras (*Ground Truth*), corrigindo acertos ao acaso (escala -1 a 1).
  4. **Normalized Mutual Information (NMI):** Informação mútua normalizada entre os agrupamentos e as classes reais (escala 0 a 1).
* **Como Executar no Terminal:**
  ```powershell
  .\.venv\Scripts\python.exe tests/academic_benchmarks/evaluate_clustering.py
  ```

---

### **4.2. Avaliação de Equidade Demográfica / Fairness (Task 5.2)**
* **Arquivo:** [`tests/academic_benchmarks/evaluate_fairness.py`](file:///c:/Desenvolvimento/driveface%20ai/tests/academic_benchmarks/evaluate_fairness.py)
* **Objetivo:** Avaliar empiricamente se o modelo ArcFace ResNet-100 apresenta viés algorítmico entre subgrupos demográficos da escala **Fitzpatrick I a VI**:
  - Grupo 1: Tons de Pele I-II
  - Grupo 2: Tons de Pele III-IV
  - Grupo 3: Tons de Pele V-VI
* **Métricas Calculadas:**
  - **FPR (False Positive Rate):** Taxa de impostores aceitos incorretamente ($d \le 0.35$).
  - **FNR (False Negative Rate):** Taxa de fotos da mesma pessoa rejeitadas incorretamente ($d > 0.35$).
  - **Delta de Paridade ($\Delta$):** Diferença de acurácia entre o grupo de melhor desempenho e o de pior desempenho ($\Delta = \max(\text{Acc}) - \min(\text{Acc})$). Deve ser estritamente $< 4\%$ para aprovação.
* **Como Executar no Terminal:**
  ```powershell
  .\.venv\Scripts\python.exe tests/academic_benchmarks/evaluate_fairness.py
  ```

---

## **Fase 5: Fundamentação Teórica & Leitura Científica Recomendada**

Para defender as escolhas metodológicas com segurança teórica, leia os seguintes artigos fundamentais:

1. **ArcFace: Additive Angular Margin Loss for Deep Face Recognition (CVPR 2019)**
   - *Autores:* Jiankang Deng, Jia Guo, Niannan Xue, Stefanos Zafeiriou.
   - *Ponto-chave:* Por que a perda angular com margem aditiva ($m = 0.5$) comprime a variabilidade intra-classe e expande a margem inter-classes na hipersfera unitária $S^{511}$.
2. **RetinaFace: Single-Shot Multi-Level Face Localisation in the Wild (CVPR 2020)**
   - *Autores:* Jiankang Deng, Jia Guo, Evangelos Ververas, Irene Kotsia, Stefanos Zafeiriou.
   - *Ponto-chave:* Detecção conjunta de bounding box e extração precisa dos 5 marcos fiduciais 2D sob oclusão severa.
3. **Density-Based Spatial Clustering of Applications with Noise (DBSCAN - KDD 1996)**
   - *Autores:* Martin Ester, Hans-Peter Kriegel, Jörg Sander, Xiaowei Xu.
   - *Ponto-chave:* Agrupamento baseado em densidade que não exige definição prévia de $k$ e isola outliers/ruídos automaticamente.

---

## **Checklist de Auto-Avaliação para o Pesquisador**

Antes da apresentação acadêmica, certifique-se de conseguir responder com clareza:

- [ ] Qual a diferença de função entre o RetinaFace (5 marcos) e o ArcFace (vetor 512-D)?
- [ ] Por que o vetor de embeddings possui norma euclidiana $\|v\|_2 = 1.0$?
- [ ] Qual o significado geométrico do limiar de distância de cosseno $d \le 0.40$?
- [ ] Como o sistema resolve o agrupamento de uma pessoa que aparece em apenas uma foto do álbum?
- [ ] Como o banco de dados PostgreSQL com `pgvector` calcula a similaridade vetorial sem carregar fotos na RAM?
- [ ] O que é o Delta de Paridade ($\Delta$) na auditoria de equidade demográfica Fitzpatrick e qual o seu valor no sistema?
