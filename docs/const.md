# **Constitution: DriveFace AI (Sistema de Agrupamento Facial para Google Drive)**

## **1\. Visão do Produto & Declaração do Problema**

O Google Drive não oferece nativamente o recurso de agrupamento e indexação facial automática presente em sistemas de galeria móveis modernos (como Apple Photos e Google Photos). Participantes de eventos, comunidades acadêmicas, fotógrafos e equipes de trabalho enfrentam alta sobrecarga cognitiva para encontrar manualmente suas fotos em meio a centenas ou milhares de arquivos desorganizados.  
O **DriveFace AI** é uma aplicação web multi-usuário integrada ao Google Drive via OAuth2. O sistema processa imagens de pastas selecionadas por meio de um pipeline de Aprendizado Profundo (Detecção Facial \+ Alinhamento \+ Extração de Embeddings com redes neurais congeladas \+ Agrupamento Não-Supervisionado), gerando uma galeria indexada por pessoa com capacidade de nomeação, auto-sugestão restrita ao próprio usuário e exportação flexível.

## **2\. Personas e Proposta de Valor**

> * **Usuário / Participante Cadastrado:** Cria sua conta na plataforma, conecta seu Google Drive, localiza instantaneamente todas as fotos em que aparece em eventos/pastas compartilhadas e realiza o download em lote (ZIP/individual) ou salva uma pasta organizada diretamente no seu próprio Google Drive.  
> * **Fotógrafo / Gestor da Pasta:** Organiza grandes volumes de fotos de eventos sem necessidade de triagem manual exaustiva, garantindo acesso facilitado aos participantes.  
> * **Pesquisador / Avaliador Acadêmico (Doutorado em TI):** Exige reprodutibilidade metodológica, métricas formais de clusterização (ex: *Silhouette*, *ARI*), equidade (*Fairness*) entre grupos demográficos e conformidade rigorosa com privacidade de dados faciais.

## **3\. Escopo do MVP (Scope Boundaries)**

### **3.1. Dentro do Escopo (In-Scope)**

> 1. **Autenticação, Cadastro e Isolamento de Usuários:**  
   * Sistema de cadastro e login de usuários na plataforma.  
   * Conexão com Google Drive via OAuth2 (escopo restrito para leitura de pastas selecionadas e gravação de pastas de exportação).  
> 2. **Pipeline de Deep Learning Assíncrono:**  
   * Detecção facial e extração de *landmarks* anatômicos.  
   * Alinhamento, corte e normalização de faces.  
   * Extração de *embeddings* faciais densos utilizando rede neural convolucional/transformer pré-treinada e estática (*Feature Extractor* fixo).  
   * Agrupamento não-supervisionado (*Clustering*) e rotulagem por pasta analisada.  
> 3. **Auto-sugestão e Nomeação Inteligente (Isolamento por Usuário):**  
   * Interface para nomeação de clusters de faces.  
   * Auto-sugestão de nomes para novos clusters e fotos baseada exclusivamente no histórico e nos rótulos atribuídos pelo **próprio usuário logado**.  
> 4. **Interface da Galeria Web:**  
   * Visualização de pessoas/clusters com avatares representativos.  
   * Grade de fotos filtrada por indivíduo.  
   * Visualizador de foto com *bounding boxes* e nomes associados.  
> 5. **Múltiplas Modalidades de Exportação:**  
   * Download direto da foto individual.  
   * Download de todas as fotos de uma pessoa compiladas em arquivo .zip.  
   * Criação de nova pasta/cópia das fotos filtradas diretamente no Google Drive do usuário.  
> 6. **Processamento Incremental:**  
   * Sincronização diferencial para processar somente novas fotos inseridas na pasta monitorada, evitando reprocessamento redundante.

### **3.2. Fora do Escopo (Out-of-Scope)**

> 1. Retreinamento online/ajuste fino (*fine-tuning*) dos pesos da rede neural extratora de características por pasta ou por usuário.  
> 2. Reconhecimento e processamento facial em fluxos de vídeo.  
> 3. Edição, aplicação de filtros ou modificação destrutiva dos arquivos originais.  
> 4. Integração com outros serviços de nuvem (OneDrive, Dropbox, iCloud) no MVP.  
> 5. Compartilhamento público de galerias não autenticadas no MVP.

## **4\. Hard Constraints (Restrições Inegociáveis)**

> 1. **Privacidade & Isolamento Estrito de Dados (*Multi-Tenancy Zero-Leakage*):**  
   * Vetores de características (*embeddings*), identidades e nomes cadastrados por um usuário ![][image1] são estritamente isolados e inacessíveis para qualquer outro usuário ![][image2].  
   * **É terminantemente proibido o vazamento cruzado de identidades:** uma pessoa nomeada por um usuário jamais poderá ser sugerida automaticamente para outro usuário, preservando o consentimento e a privacidade individual.  
> 2. **Armazenamento Volátil de Imagens (Zero Permanent Raw Storage):**  
   * Nenhuma fotografia bruta em alta resolução deve ser armazenada permanentemente no servidor da aplicação. O download é feito sob demanda na memória (*stream/buffer*), processado para inferência/corte de avatar e descartado imediatamente.  
> 3. **Desacoplamento Assíncrono (Non-Blocking UI):**  
   * O pipeline de Deep Learning opera em filas de tarefas em segundo plano (*background workers*). A interface web comunica-se por polling/WebSockets e nunca bloqueia durante o processamento de lotes.  
> 4. **Tolerância a Falsos Positivos:**  
   * Limiar de corte rígido de similaridade: o sistema deve classificar faces ambíguas como desconhecidas/ruído em vez de associá-las incorretamente a uma pessoa errada.  
> 5. **Stack Tecnológica & Ambientes de Execução:**  
   * Backend e Pipeline em **Python**.  
   * Banco de dados relacional e vetorial com suporte a isolamento por *tenant* (User ID).  
   * Suporte operacional planejado: ambiente Google Colab (com aceleração por GPU T4/V100) para prototipagem/testes de benchmark acadêmico e Google Cloud Platform (GCP) para implantação final.

## **5\. Critérios de Sucesso e Avaliação Acadêmica**

> * **Acurácia e Coerência de Agrupamento:** Mensuração com métricas de validação de clusterização (*Silhouette Score*, *Davies-Bouldin*, *Adjusted Rand Index*) e verificação facial (*ROC-AUC*, *Cosine Distance Thresholds*).  
> * **Equidade (Fairness):** Avaliação empírica de desempenho e taxa de erro controlada entre subgrupos (gênero, faixas etárias e tons de pele/escala Fitzpatrick).  
> * **Eficiência Computacional:** Processamento e indexação de lotes de centenas de imagens em poucos minutos via processamento assíncrono em GPU.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAaCAYAAACpSkzOAAAA70lEQVR4Xu2UURHCMAyGqwELaJgFLGABC1iYAyQgAQc4wAEGEAD92HKXC01TNu546XeXl2bN3z9Nl1KnYxhyXAshbAu5o8o3Q6Fzjuccpxx7ld/kOMy5S5pE2LMIClAIQQ8OsJpHmoQ4uYd2uRhpm9cS2kesBpG7XVT8xA1EbbvZhQJ0Y2cXNYx31DbyETKRLjiJ2hY5wglTOdqEhiSn8aBANNrsx3lVCEdeIf4CtbujuD6k/qN8wMe8Izu+tKv2gIE890LriKoQUBQxNmI/cgIMEW74XqJlaN6XLhta3o3ci6ZJ6FtKo4yQFe90/sALVjI8HQBrEaoAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAaCAYAAABGiCfwAAAA+ElEQVR4Xu2TURHCMAyGqwELaMACFrCABSzgAAlIwAEOcICBCYB+14XLckk7xh546HeXO2i7pP+fNKVOZwa7HHcnhK2zd1L7X0Gya47XGJccB7W/yXEc926pFOKbxZCEZBSN4BKrMKRSDAURWu1PiIWRPVhJrAKFnnZRsZoqaFn4sAupKBX7ZUo5R99DFxj9loXse3jPpDpoKGpZ6CkDEp/NGrn0BSZwmNGPYOSjsafYXv3nt3eBDyiLknHDWi9RQWIdYb9AGm0PSbNrWAVVCwUSU5DkJGgpAizTFgLfRcM0gUEQK+a8K6sKuHBT2RJsUmkHT6nT+WPe1LBHmlR3HQEAAAAASUVORK5CYII=>