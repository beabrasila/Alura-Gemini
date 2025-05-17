# Agente Gerador de Conteúdo "O Senhor dos Anéis" para Instagram (Imersão IA Alura + Google)

Este projeto automatiza a criação de posts temáticos para Instagram sobre a trilogia cinematográfica de "O Senhor dos Anéis". Ele foi desenvolvido como parte da Imersão IA da Alura em parceria com o Google.

Confira o resultado final em https://www.instagram.com/tododiasda/

## Funcionalidades Principais

* **Geração de Citações:** Utiliza um agente de IA (Google ADK com Gemini) para selecionar citações EXATAS e memoráveis dos filmes da trilogia "O Senhor dos Anéis".
* **Criação de Prompts Artísticos:** Um segundo agente de IA (Google ADK com Gemini) gera prompts detalhados para imagens, baseados nas citações.
* **Geração de Imagens:** Usa a API Gemini (através do modelo `gemini-2.0-flash-preview-image-generation`) para gerar imagens a partir dos prompts artísticos. As imagens são processadas para tentar um formato 1:1.
* **Armazenamento em Nuvem:** Faz upload das imagens geradas para uma pasta específica no Google Drive.
* **Logging Detalhado:** Registra a citação, o link da imagem no Drive (ou status de erro) e o horário em uma Planilha Google.
* **Operação Contínua:** O script roda em um loop, gerando conteúdo em intervalos configuráveis.

## Tecnologias Utilizadas

* **Python 3.11+**
* **Google Gemini API:**
     * Para geração de texto (citações e prompts de imagem) através dos modelos `gemini-1.5-flash-latest`.
     * Para geração de imagens através do modelo `gemini-2.0-flash-preview-image-generation` (via `genai.Client()`).
* **Google Agent Development Kit (ADK):** Para orquestrar os agentes de IA.
* **Google Drive API:** Para armazenamento das imagens.
* **Google Sheets API:** Para logging e monitoramento.
* **Bibliotecas Python:** `google-generativeai`, `google-api-python-client`, `google-auth`, `gspread`, `Pillow`, `pytz`.

## Relevância para a Imersão IA Alura e Google

Este projeto demonstra a aplicação prática dos conceitos da **Aula 05: "Construindo agentes que resolvem tarefas por você"**. Ele utiliza uma arquitetura com múltiplos agentes de IA que colaboram para realizar a tarefa complexa de curadoria, conceituação criativa e geração de conteúdo multimídia, tudo de forma automatizada e utilizando as mais recentes ferramentas de IA do Google.

## Como Configurar e Rodar o Projeto

### Pré-requisitos

1.  Python 3.10 ou superior.
2.  Uma conta Google e um projeto no [Google Cloud Platform (GCP)](https://console.cloud.google.com/).
3.  Uma [API Key do Google Gemini](https://aistudio.google.com/makersuite/apikey).
4.  Um arquivo JSON de credenciais de uma Conta de Serviço do GCP.

### Configuração do Ambiente

1.  **Clone este repositório:**
    ```bash
    git clone [URL_DO_SEU_REPOSITORIO_AQUI]
    cd [NOME_DA_PASTA_DO_PROJETO]
    ```

2.  **Crie e ative um ambiente virtual Python:**
    ```bash
    python3 -m venv env
    source env/bin/activate  # Linux/macOS
    # .\env\Scripts\activate # Windows
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as Credenciais e IDs:**
    * **API Key do Gemini:**
        * Exporte sua API Key do Gemini como uma variável de ambiente:
            ```bash
            export GOOGLE_GEMINI_API_KEY="SUA_API_KEY_AQUI"
            ```
        * Alternativamente, edite o arquivo `agente_sda_google.py` e substitua o placeholder na variável `GOOGLE_GEMINI_API_KEY`.
    * **Arquivo JSON da Conta de Serviço:**
        1.  No GCP Console, crie uma Conta de Serviço com os seguintes papéis (no mínimo): `Editor` (para simplificar durante a Imersão) ou papéis mais granulares como "Acesso ao Drive" (para criar arquivos), "Editor do Sheets", e acesso ao Gemini se estiver usando autenticação de conta de serviço para ele (não é o caso aqui, estamos usando API Key para Gemini).
        2.  Crie uma chave JSON para esta conta de serviço e faça o download.
        3.  Renomeie o arquivo JSON baixado para `service_account.json` (conforme especificado em `GOOGLE_SERVICE_ACCOUNT_FILE` no script) e coloque-o na raiz do projeto.
        4.  **NÃO adicione este arquivo JSON ao Git (ele deve estar no seu `.gitignore`).**
    * **Google Sheets:**
        1.  Crie uma nova Planilha Google.
        2.  Compartilhe esta planilha com o email da sua Conta de Serviço (encontrado no arquivo JSON como `client_email`), concedendo permissão de **Editor**.
        3.  Copie o ID da Planilha da URL (a string entre `/d/` e `/edit`).
        4.  Exporte o ID como variável de ambiente `SPREADSHEET_ID="ID_DA_SUA_PLANILHA"` ou edite o placeholder em `SPREADSHEET_ID` no script `agente_sda_google.py`.
    * **Google Drive:**
        1.  Crie uma pasta no seu Google Drive onde as imagens serão salvas.
        2.  Compartilhe esta pasta com o email da sua Conta de Serviço, concedendo permissão de **Editor**.
        3.  Copie o ID da Pasta da URL (a string após `/folders/`).
        4.  Exporte o ID como variável de ambiente `DRIVE_FOLDER_ID="ID_DA_SUA_PASTA"` ou edite o placeholder em `DRIVE_FOLDER_ID` no script `agente_sda_google.py`.

### Rodando o Script

Com o ambiente virtual ativado e as configurações prontas:
```bash
python agente_sda_google.py

Extensões e Integrações: Automação da Publicação com Make.com
Este projeto foca na geração automatizada do conteúdo. Para completar o ciclo e automatizar a publicação no Instagram, uma integração com plataformas de automação como o Make.com pode ser facilmente implementada:

Monitoramento da Planilha Google:

No Make.com, crie um novo cenário.
Use o módulo "Google Sheets" como gatilho (trigger), selecionando a opção "Watch New Rows" (Observar Novas Linhas).
Conecte à sua conta Google e selecione a planilha e a aba onde o script salva os dados.
Obtenção e Preparação do Conteúdo:

A cada nova linha detectada, o Make.com obterá os dados: a citação gerada (para a legenda do Instagram) e o link da imagem no Google Drive.
Como o link do Drive fornecido pelo script já é um link de download direto (uc?export=download), use o módulo "HTTP" > "Get a file" do Make.com para baixar os bytes da imagem.
Publicação no Instagram:

Utilize o módulo "Instagram for Business" no Make.com.
Selecione a ação "Create a Photo Post".
Mapeie os dados:
Photo URL/File: Use o arquivo baixado pelo módulo HTTP.
Caption: Use a citação obtida da planilha.
Configure a conta do Instagram Business que será usada para postar.
Agendamento e Controle de Fluxo:

Configure o cenário no Make.com para rodar na frequência desejada (ex: a cada X horas, ou assim que uma nova linha for adicionada, com um pequeno delay para garantir que o upload da imagem no Drive foi concluído).
Adicione tratamento de erros e filtros no Make.com para garantir que apenas posts válidos sejam publicados (ex: verificar se o link da imagem não contém "ERRO").
Com essa integração, o sistema se torna um pipeline completo e 100% automatizado, desde a concepção e geração do conteúdo por IA até a sua publicação na rede social.

Autor
[Douglas Pinto]
Agradecimentos
Alura e Google pela Imersão IA, que proporcionou o conhecimento e a inspiração para este projeto.
