# -*- coding: utf-8 -*-
"""
agente_sda_google.py

Este script automatiza a criação de posts temáticos sobre a trilogia cinematográfica
de "O Senhor dos Anéis".
Ele realiza as seguintes etapas:
1. Gera uma frase famosa da trilogia cinematográfica usando um agente de IA (Google ADK com Gemini).
2. Cria um prompt artístico detalhado baseado na frase, visando um estilo HQ anos 90 com cenas amplas, usando outro agente de IA.
3. Gera uma imagem visualmente rica a partir do prompt artístico usando a API Gemini.
4. Converte a imagem para o formato JPEG, se necessário.
5. Faz o upload da imagem para uma pasta específica no Google Drive.
6. Define as permissões da imagem no Google Drive para acesso público de leitura.
7. Salva a frase e o link de download direto da imagem em uma Planilha Google.

Este processo é executado em loop, com um intervalo configurável entre os posts.

Principais dependências:
- google-generativeai (para API Gemini e ADK)
- google-api-python-client (para Google Drive e Sheets)
- google-auth, google-auth-oauthlib, google-auth-httplib2 (para autenticação Google)
- gspread (para interagir com Google Sheets de forma mais simples)
- Pillow (para manipulação e conversão de imagens)
- pytz (para lidar com fusos horários)

Autor: [Douglas Pinto]
Data da Última Modificação: 17 de Maio de 2025

"""

# --- IMPORTAÇÕES DE MÓDULOS ---
import os
import time
from datetime import datetime
from io import BytesIO
import json
import random
import traceback # Para logs de erro detalhados

# Bibliotecas Google e IA Generativa
try:
    from google import genai as google_genai_for_client 
    import google.generativeai as genai_sdk_main 
    print("[INFO] SDK Gemini: Usando 'from google import genai' e 'import google.generativeai'.")
except ImportError:
    print("[WARN] SDK Gemini: Tentando importação alternativa 'import google.generativeai'.")
    import google.generativeai as google_genai_for_client
    genai_sdk_main = google_genai_for_client

from google.genai import types as genai_types_for_api 
from google.adk.agents import Agent 
from google.adk.runners import Runner 
from google.adk.sessions import InMemorySessionService 
from google.genai import types as genai_adk_types

# Bibliotecas Google Cloud (Drive, Sheets)
from google.oauth2.service_account import Credentials 
from googleapiclient.discovery import build 
from googleapiclient.http import MediaIoBaseUpload 

# Outras bibliotecas úteis
from PIL import Image 
import gspread 
import pytz 

print("----------------------------------------------------")
print("[INFO] Todas as bibliotecas principais foram importadas.")
print("----------------------------------------------------")
# --- CONFIGURAÇÕES GLOBAIS E CONSTANTES ---
# ATENÇÃO: NUNCA coloque chaves de API diretamente no código em um ambiente de produção ou ao compartilhar.
#          Use variáveis de ambiente ou um sistema de gerenciamento de segredos.
#          Para um concurso, mencione que as chaves seriam externalizadas.
GOOGLE_GEMINI_API_KEY = "SUA_CHAVE_GEMINI_API_AQUI" # CHAVE DE EXEMPLO - SUBSTITUA PELA SUA E EXTERNALIZE!
SPREADSHEET_ID = "COLOQUE_SEU_SPREADSHEET_ID_AQUI"    # ID da sua Planilha Google
DRIVE_FOLDER_ID = "COLOQUE_SEU_DRIVE_FOLDER_ID_AQUI"         # ID da Pasta do Google Drive para salvar as imagens
GOOGLE_SERVICE_ACCOUNT_FILE = "service_account.json" # Caminho para o arquivo JSON da conta de serviço Google

# Configurações de Comportamento do Script
TIME_ZONE = "America/Sao_Paulo" 
INTERVALO_ENTRE_POSTS_SEGUNDOS = 60 
QUALIDADE_JPEG = 90 

# Modelos de IA Gemini (certifique-se que são válidos para sua API Key e projeto)
GEMINI_MODEL_FOR_ADK_AGENTS = "gemini-2.0-flash" 
MODELO_GEMINI_PARA_IMAGEM = "gemini-2.0-flash-preview-image-generation"

print("[INFO] Configurações globais carregadas.")

# --- INICIALIZAÇÃO E CONFIGURAÇÃO DE SERVIÇOS ---
CLIENT_EMAIL_FROM_JSON = None 
try:
    with open(GOOGLE_SERVICE_ACCOUNT_FILE, 'r') as f_creds:
        creds_json_data = json.load(f_creds)
        CLIENT_EMAIL_FROM_JSON = creds_json_data.get('client_email')
    
    genai_sdk_main.configure(api_key=GOOGLE_GEMINI_API_KEY)
    print(f"✅ [OKAY] SDK Gemini (genai.configure) inicializado com sucesso (Chave API final: ...{GOOGLE_GEMINI_API_KEY[-4:] if GOOGLE_GEMINI_API_KEY else 'N/A'}).")
    
    os.environ["GOOGLE_API_KEY"] = GOOGLE_GEMINI_API_KEY
    print(f"ℹ️ [INFO] Variável de ambiente GOOGLE_API_KEY definida.")

except FileNotFoundError:
    print(f"❌ [FATAL] Arquivo de credenciais da conta de serviço '{GOOGLE_SERVICE_ACCOUNT_FILE}' não encontrado. O script não pode continuar.")
    exit(1) 
except Exception as e:
    print(f"❌ [FATAL] Falha ao configurar o SDK Gemini ou ler o arquivo de credenciais: {e}")
    traceback.print_exc()
    exit(1)

SCOPES_GOOGLE_APIS = [
    "https://www.googleapis.com/auth/drive",      
    "https://www.googleapis.com/auth/spreadsheets" 
]
google_api_creds = None
gsheets_worksheet = None
gdrive_service = None

if not SPREADSHEET_ID or SPREADSHEET_ID == "TODO_SPREADSHEET_ID_AQUI": 
    print("❌ [FATAL] O ID da Planilha (SPREADSHEET_ID) não foi configurado corretamente. Verifique as CONFIGURAÇÕES GLOBAIS.")
    exit(1)
if not DRIVE_FOLDER_ID or DRIVE_FOLDER_ID == "TODO_DRIVE_FOLDER_ID_AQUI":
    print("❌ [FATAL] O ID da Pasta do Drive (DRIVE_FOLDER_ID) não foi configurado corretamente. Verifique as CONFIGURAÇÕES GLOBAIS.")
    exit(1)

try:
    google_api_creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES_GOOGLE_APIS)
    
    gspread_client = gspread.authorize(google_api_creds)
    gs_spreadsheet = gspread_client.open_by_key(SPREADSHEET_ID)
    gsheets_worksheet = gs_spreadsheet.sheet1 
    print(f"✅ [OKAY] Google Sheets: Conectado à planilha '{gs_spreadsheet.title}' (Aba: '{gsheets_worksheet.title}')")
    
    gdrive_service = build("drive", "v3", credentials=google_api_creds)
    print("✅ [OKAY] Google Drive API: Serviço inicializado.")
    
    print(f"ℹ️ [INFO] Autenticação Google: Usando conta de serviço '{CLIENT_EMAIL_FROM_JSON or 'Email não lido do JSON'}'.")
    print(f"ℹ️ [INFO]      -> Certifique-se que esta conta tem permissão de 'Editor' na Planilha e na Pasta do Drive ({DRIVE_FOLDER_ID}).")

except gspread.exceptions.SpreadsheetNotFound:
    print(f"❌ [FATAL] Google Sheets: Planilha com ID '{SPREADSHEET_ID}' não encontrada ou não acessível pela conta de serviço '{CLIENT_EMAIL_FROM_JSON}'.")
    exit(1)
except Exception as e:
    print(f"❌ [FATAL] Erro crítico durante a inicialização dos serviços Google (Sheets/Drive): {e}")
    traceback.print_exc()
    exit(1)

gemini_image_generation_client = None
try:
    gemini_image_generation_client = google_genai_for_client.Client()
    print(f"✅ [OKAY] Cliente Gemini para Geração de Imagem (`genai.Client()`) inicializado.")
except AttributeError:
    print("❌ [FATAL] Cliente Gemini (`google.genai.Client()`) não encontrado. Verifique a importação e a versão da biblioteca 'google-generativeai'.")
    exit(1)
except Exception as e:
    print(f"❌ [FATAL] Erro ao inicializar o cliente Gemini para geração de imagem: {e}")
    traceback.print_exc()
    exit(1)
print("----------------------------------------------------")

# --- DEFINIÇÕES DE FUNÇÕES AUXILIARES ---

def call_agent_sync(agent: Agent, input_message: str) -> str:
    """
    Executa um agente da Google ADK de forma síncrona e retorna a resposta textual.

    Args:
        agent: A instância do agente ADK a ser executado.
        input_message: A mensagem de entrada (prompt) para o agente.

    Returns:
        A resposta textual do agente, ou uma string vazia em caso de erro.
    """
    if not agent or not input_message:
        print(" कॉल [ERROR] call_agent_sync: Agente ou mensagem de entrada inválidos.")
        return ""

    session_svc = InMemorySessionService()
    session_unique_id = f"session_{agent.name.lower()}_{datetime.now().timestamp()}_{random.randint(10000, 99999)}"
    user_context_id = "user_main_script" 

    try:
        print(f"⚙️ [DEBUG] call_agent_sync: Criando sessão '{session_unique_id}' para o agente '{agent.name}'...")
        _ = session_svc.create_session(
            app_name=agent.name, 
            user_id=user_context_id, 
            session_id=session_unique_id
        )
        
        adk_runner = Runner(agent=agent, app_name=agent.name, session_service=session_svc)
        
        input_content = genai_adk_types.Content(
            role="user", 
            parts=[genai_adk_types.Part(text=input_message)]
        )
        
        print(f"🏃 [DEBUG] call_agent_sync: Executando agente '{agent.name}' com sessão '{session_unique_id}'...")
        final_agent_response = ""
        for event in adk_runner.run(user_id=user_context_id, session_id=session_unique_id, new_message=input_content):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text is not None:
                        final_agent_response += part.text + "\n"
        
        response_trimmed = final_agent_response.strip()
        if not response_trimmed:
            print(f"⚠️ [WARN] call_agent_sync: Agente '{agent.name}' retornou uma resposta vazia.")
        return response_trimmed

    except Exception as e:
        print(f"❌ [ERROR] call_agent_sync: Falha ao executar o agente '{agent.name}'. Sessão: '{session_unique_id}'. Erro: {e}")
        traceback.print_exc()
        return ""


def generate_image_with_gemini_client(image_prompt: str) -> bytes | None:
    """
    Gera uma imagem usando a API Gemini (via genai.Client) e tenta retornar os bytes em formato JPEG.

    Args:
        image_prompt: O prompt textual para a geração da imagem.

    Returns:
        Bytes da imagem em formato JPEG, ou None em caso de falha.
    """
    if not gemini_image_generation_client:
        print("❌ [ERROR] generate_image_with_gemini_client: Cliente Gemini para imagem não inicializado.")
        return None
    if not image_prompt or not image_prompt.strip():
        print("❌ [ERROR] generate_image_with_gemini_client: Prompt para imagem está vazio.")
        return None

    print(f"🖼️ [INFO] generate_image_with_gemini_client: Solicitando imagem com prompt:\n--- Prompt Imagem ---\n{image_prompt}\n---------------------")
    
    final_jpeg_image_bytes = None

    try:
        image_gen_config = genai_types_for_api.GenerateContentConfig(
            response_modalities=['IMAGE', 'TEXT'] 
        )
        print("⚙️ [DEBUG] generate_image_with_gemini_client: Usando config com response_modalities=['IMAGE', 'TEXT']")

        api_response = gemini_image_generation_client.models.generate_content(
            model=MODELO_GEMINI_PARA_IMAGEM,
            contents=image_prompt,
            config=image_gen_config 
        )

        raw_image_bytes = None
        original_image_mime_type = None
        accompanying_text = ""

        if api_response.candidates:
            for part in api_response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    accompanying_text += part.text + " "
                if hasattr(part, 'inline_data') and part.inline_data and \
                   hasattr(part.inline_data, 'mime_type') and \
                   part.inline_data.mime_type.startswith("image/"):
                    raw_image_bytes = part.inline_data.data
                    original_image_mime_type = part.inline_data.mime_type
                    print(f"⚙️ [DEBUG] generate_image_with_gemini_client: Imagem recebida da API. MIME Type original: {original_image_mime_type}.")
        
        if accompanying_text.strip():
            print(f"ℹ️ [INFO] generate_image_with_gemini_client: Texto acompanhando a imagem (da API): {accompanying_text.strip()}")

        if raw_image_bytes:
            if original_image_mime_type == "image/jpeg":
                print("ℹ️ [INFO] generate_image_with_gemini_client: Imagem da API já está em formato JPEG.")
                final_jpeg_image_bytes = raw_image_bytes
            elif original_image_mime_type == "image/png":
                print("ℹ️ [INFO] generate_image_with_gemini_client: Convertendo imagem de PNG para JPEG...")
                try:
                    pil_image = Image.open(BytesIO(raw_image_bytes))
                    
                    if pil_image.mode == 'RGBA' or pil_image.mode == 'LA' or \
                       (pil_image.mode == 'P' and 'transparency' in pil_image.info):
                        print("⚙️ [DEBUG] generate_image_with_gemini_client: Imagem PNG com canal alfa detectado. Aplicando fundo branco.")
                        background_fill = Image.new('RGB', pil_image.size, (255, 255, 255))
                        alpha_mask = None
                        if pil_image.mode == 'RGBA': alpha_mask = pil_image.split()[3]
                        elif pil_image.mode == 'LA': alpha_mask = pil_image.split()[1]
                        
                        if alpha_mask: background_fill.paste(pil_image, mask=alpha_mask)
                        else: 
                            print("⚠️ [WARN] generate_image_with_gemini_client: Não foi possível extrair máscara alfa clara para PNG modo 'P', convertendo para RGB diretamente.")
                            pil_image = pil_image.convert('RGB') 
                            background_fill.paste(pil_image)
                        pil_image = background_fill
                    elif pil_image.mode != 'RGB': 
                        print(f"⚙️ [DEBUG] generate_image_with_gemini_client: Convertendo imagem de modo {pil_image.mode} para RGB.")
                        pil_image = pil_image.convert('RGB')

                    with BytesIO() as jpeg_buffer:
                        pil_image.save(jpeg_buffer, format='JPEG', quality=QUALIDADE_JPEG)
                        final_jpeg_image_bytes = jpeg_buffer.getvalue()
                    print(f"✅ [OKAY] generate_image_with_gemini_client: Imagem convertida para JPEG com sucesso (Qualidade: {QUALIDADE_JPEG}).")
                except Exception as e_conversion:
                    print(f"❌ [ERROR] generate_image_with_gemini_client: Falha ao converter imagem de PNG para JPEG: {e_conversion}")
                    traceback.print_exc()
                    final_jpeg_image_bytes = None 
            else:
                print(f"⚠️ [WARN] generate_image_with_gemini_client: Formato de imagem não JPEG/PNG recebido ({original_image_mime_type}). Não foi feita conversão. Bytes da imagem serão descartados.")
                final_jpeg_image_bytes = None # Descarta se não for formato conhecido/conversível
        else:
            print("❌ [ERROR] generate_image_with_gemini_client: Nenhuma imagem foi encontrada na resposta da API Gemini.")
        
        return final_jpeg_image_bytes

    except Exception as e_general:
        print(f"❌ [ERROR] generate_image_with_gemini_client: Erro geral durante a geração da imagem (Modelo: {MODELO_GEMINI_PARA_IMAGEM}). Erro: {e_general}")
        traceback.print_exc()
        return None


def upload_image_to_google_drive(gdrive_api_service, filename_on_drive: str, image_bytes_to_upload: bytes, target_folder_id: str) -> tuple[str | None, str | None, str | None]:
    """
    Faz upload de bytes de uma imagem para uma pasta específica no Google Drive.
    """
    if not gdrive_api_service or not filename_on_drive or not image_bytes_to_upload or not target_folder_id:
        print("❌ [ERROR] upload_image_to_google_drive: Parâmetros inválidos.")
        return None, None, None

    print(f"💾 [INFO] upload_image_to_google_drive: Fazendo upload do arquivo '{filename_on_drive}' para a pasta '{target_folder_id}'...")
    try:
        media_uploader = MediaIoBaseUpload(
            BytesIO(image_bytes_to_upload), 
            mimetype='image/jpeg', 
            resumable=True
        )
        
        file_metadata = {'name': filename_on_drive, 'parents': [target_folder_id]}
        
        uploaded_file_details = gdrive_api_service.files().create(
            body=file_metadata,
            media_body=media_uploader,
            fields='id, webViewLink' 
        ).execute()
        
        file_id_on_drive = uploaded_file_details.get('id')
        web_view_link_drive = uploaded_file_details.get('webViewLink') 
        
        if file_id_on_drive:
            direct_download_url = f"https://drive.google.com/uc?export=download&id={file_id_on_drive}"
            print(f"✅ [OKAY] upload_image_to_google_drive: Arquivo '{filename_on_drive}' carregado. ID: {file_id_on_drive}.")
            print(f"       -> Link de Visualização: {web_view_link_drive}")
            print(f"       -> Link de Download Direto: {direct_download_url}")
            return web_view_link_drive, direct_download_url, file_id_on_drive
        else:
            print(f"❌ [ERROR] upload_image_to_google_drive: Upload do arquivo '{filename_on_drive}' sem retorno de ID.")
            return web_view_link_drive, None, None

    except Exception as e:
        print(f"❌ [ERROR] upload_image_to_google_drive: Falha ao fazer upload do arquivo '{filename_on_drive}'. Erro: {e}")
        traceback.print_exc()
        return None, None, None


def set_google_drive_file_public_readable(gdrive_api_service, file_id_on_drive: str) -> bool:
    """
    Define as permissões de um arquivo no Google Drive para "qualquer pessoa com o link pode ler".
    """
    if not gdrive_api_service or not file_id_on_drive:
        print("❌ [ERROR] set_google_drive_file_public_readable: Serviço do Drive ou ID do arquivo não fornecido.")
        return False
        
    print(f"🔒 [INFO] set_google_drive_file_public_readable: Definindo permissões públicas para o arquivo ID: {file_id_on_drive}...")
    try:
        public_permission_settings = {'type': 'anyone', 'role': 'reader'}
        gdrive_api_service.permissions().create(fileId=file_id_on_drive, body=public_permission_settings).execute()
        print(f"✅ [OKAY] set_google_drive_file_public_readable: Permissões do arquivo '{file_id_on_drive}' definidas.")
        return True
    except Exception as e:
        print(f"❌ [ERROR] set_google_drive_file_public_readable: Falha ao definir permissões para o arquivo '{file_id_on_drive}'. Erro: {e}")
        traceback.print_exc()
        return False


def save_data_to_google_sheet(gs_worksheet_instance, timestamp_str: str, post_text: str, image_url_or_status: str):
    """
    Salva os dados de um post em uma nova linha na planilha Google.
    """
    if not gs_worksheet_instance:
        print("❌ [ERROR] save_data_to_google_sheet: Instância da planilha não fornecida.")
        return

    print(f"📊 [INFO] save_data_to_google_sheet: Registrando dados na planilha...")
    try:
        text_for_sheet = post_text if post_text and post_text.strip() else "ERRO: Texto do post não gerado ou vazio"
        url_or_status_for_sheet = image_url_or_status if image_url_or_status and image_url_or_status.strip() else "ERRO: URL/Status da imagem não disponível"
        
        new_row_data = [timestamp_str, text_for_sheet, url_or_status_for_sheet]
        gs_worksheet_instance.append_row(new_row_data)
        # Para o log, mostrar apenas uma prévia do texto e da URL para não poluir.
        log_text_preview = (text_for_sheet[:47] + "...") if len(text_for_sheet) > 50 else text_for_sheet
        log_url_preview = (url_or_status_for_sheet[:50] + "...") if len(url_or_status_for_sheet) > 50 else url_or_status_for_sheet
        print(f"✅ [OKAY] save_data_to_google_sheet: Dados salvos: {new_row_data[0]}, '{log_text_preview}', '{log_url_preview}'")
    except Exception as e:
        print(f"❌ [ERROR] save_data_to_google_sheet: Falha ao salvar dados na planilha. Erro: {e}")
        traceback.print_exc()

# --- DEFINIÇÃO DOS AGENTES DE IA (ADK) ---

# Agente para gerar citações FAMOSAS DA TRILOGIA DE CINEMA de "O Senhor dos Anéis"
sda_citation_agent = Agent(
    name="AgenteCitadorFilmesSdA", 
    model=GEMINI_MODEL_FOR_ADK_AGENTS,
    instruction="""Você é um especialista e curador da trilogia cinematográfica de 'O Senhor dos Anéis' (dirigida por Peter Jackson).

Sua missão é selecionar uma frase, ou passagem famosa da trilogia. A frase deve ser exata conforme falada nos filmes. Ela não deve ser adaptada nem inventada. Escolha sempre frases que são importantes e geram impacto na história. Elas devem ser realizadas conforme os exemplos abaixo. Sempre importante pegar frases de personagens e momentos diferentes da história. Ao final, coloque 5 #s relevantes sobre Senhor dos Anéis (exemplos, #senhordosaneis #frodo #gandalf #sda #tokien):

1.
“Tudo o que temos de decidir é o que fazer com o tempo que nos é dado.”
🧙‍♂️ Gandalf — A Sociedade do Anel  
Enquanto Frodo lamenta ter recebido uma tarefa tão pesada, Gandalf responde com sabedoria. Eles estão nas Minas de Moria, e a frase ecoa como um lembrete poderoso de que, mesmo nos momentos mais sombrios, nossas escolhas moldam o destino. É uma das frases mais citadas da saga, pela sua profundidade atemporal.

2.
“Há algo de bom neste mundo, Sr. Frodo. E vale a pena lutar por isso.”
🧑‍🌾 Sam — As Duas Torres  
No auge do desespero, com Frodo exausto e sem esperança, Sam entrega esse discurso com lágrimas nos olhos. Ele lembra ao amigo que as grandes histórias são feitas por aqueles que continuam, mesmo quando tudo parece perdido. É o momento em que Sam deixa de ser apenas um ajudante e se torna o verdadeiro coração da jornada.

3.
“Você não pode simplesmente entrar em Mordor.”
⚔️ Boromir — A Sociedade do Anel  
Durante o Conselho de Elrond, enquanto os representantes dos povos discutem o que fazer com o Um Anel, Boromir deixa claro o quão impossível parece a missão. A frase se tornou meme, mas representa o terror real que Mordor inspirava. Boromir não era covarde, só sabia o que os homens de Gondor enfrentavam ali.

4.
“O dia pode chegar em que o coração dos homens falhe, em que abandonamos nossos amigos e quebramos todos os laços de companheirismo. Mas não é este dia!”
👑 Aragorn — O Retorno do Rei  
Pouco antes da batalha final no Portão Negro de Mordor, Aragorn discursa para um exército cansado e em menor número. Com voz firme e olhos cheios de coragem, ele inspira todos a resistirem até o fim. Um momento épico, de arrepiar até quem já assistiu dez vezes.

5.
“Você não passará!”
🧙‍♂️ Gandalf — A Sociedade do Anel  
No confronto contra o Balrog, nas profundezas de Moria, Gandalf se impõe com fúria. De cajado em punho, ele desafia a criatura demoníaca e protege seus companheiros com um ato de sacrifício. O momento é icônico — e a frase, dita com uma autoridade quase divina, entrou para a história do cinema.

6.
“Eu não sou um homem!”
🛡️ Éowyn — O Retorno do Rei  
Durante a Batalha de Pelennor, Éowyn enfrenta o Rei Bruxo de Angmar. Quando ele diz que nenhum homem pode matá-lo, ela remove o capacete e grita essa frase antes de desferir o golpe final. Um momento de triunfo, coragem e quebra de profecia, que eternizou Éowyn como uma das maiores heroínas da saga.

7.
“Eu não posso carregar o anel por você. Mas posso carregar você!”
🧑‍🌾 Sam — O Retorno do Rei  
No topo do Monte da Perdição, Frodo já não consegue dar mais um passo. Sam, leal até o fim, o coloca nos ombros e sobe com ele. A frase representa amizade incondicional, sacrifício e coragem. Sam se mostra, mais uma vez, o verdadeiro herói silencioso da trilogia.

8.
“Mesmo a menor pessoa pode mudar o curso do futuro.”
🌟 Galadriel — A Sociedade do Anel  
Durante sua narração inicial, Galadriel revela a essência de toda a trilogia: o poder dos pequenos. Em um mundo de reis, elfos e guerreiros, são os hobbits que carregam a esperança. A frase se torna uma das maiores mensagens da saga: coragem e grandeza vêm de onde menos se espera.

9.
“Meu precioso.”
👹 Gollum — As Duas Torres  
Obcecado pelo Um Anel, Gollum repete essa frase ao longo da trilogia. Em “As Duas Torres”, quando está sozinho, ele a sussurra com uma mistura de amor e loucura. É um símbolo da corrupção causada pelo anel — e uma das falas mais marcantes e imitadas do cinema moderno.

10.
“Você se ajoelha para ninguém.”
👑 Aragorn — O Retorno do Rei  
Após ser coroado rei de Gondor, Aragorn se aproxima dos hobbits. Quando eles tentam se ajoelhar, ele os impede com essa frase que consagra o valor dos pequenos heróis. Emocionante e poderosa, é uma das cenas mais bonitas de toda a trilogia.

11.
“A sombra tomou conta do mundo... mas não de nós.”
🧙‍♂️ Gandalf — O Retorno do Rei  
Enquanto o caos se espalha e a esperança se apaga, Gandalf diz isso a Pippin dentro de Minas Tirith. É um lembrete de que, mesmo cercados de trevas, ainda podemos manter a luz acesa dentro de nós. Uma fala reconfortante, especialmente em tempos difíceis.

12.
“Corra, tolo!”
🧙‍♂️ Gandalf — A Sociedade do Anel  
Momentos antes de cair com o Balrog na ponte de Khazad-dûm, Gandalf grita essa frase para a comitiva fugir. Curta, urgente e desesperada, ela se tornou um ícone do sacrifício e da tensão. É o tipo de cena que se grava na memória para sempre.

13.
“Não temos para onde correr, nem como vencer. Mas vamos lutar.”
🛡️ Théoden — As Duas Torres  
Durante a defesa desesperada do Abismo de Helm, Théoden reconhece que estão cercados e em desvantagem. Ainda assim, decide montar e lutar. É um momento de honra, bravura e desafio diante da morte certa. A frase inspira coragem até hoje.

14.
“Eu teria seguido você até o fim. Até as chamas de Mordor.”
👑 Aragorn — A Sociedade do Anel  
Ao perceber que Frodo está partindo sozinho, Aragorn declara sua lealdade eterna. A fala é um símbolo da irmandade entre os membros da sociedade e do respeito profundo que Aragorn tem por Frodo. É um dos momentos mais emocionantes do primeiro filme.

15.
“Há sempre esperança.”
👑 Aragorn — O Retorno do Rei  
Mesmo diante da ruína iminente, Aragorn se recusa a desistir. Ele diz essa frase com convicção em Gondor, reforçando que a luz pode prevalecer mesmo quando tudo parece perdido. É simples, direta e profundamente inspiradora.

16.
“Eu vejo em sua mente o medo... e a covardia!”
👻 Rei Bruxo — O Retorno do Rei  
No auge da Batalha de Minas Tirith, o Rei Bruxo encara Gandalf e tenta quebrar sua coragem. A frase, sombria e ameaçadora, mostra o poder psicológico dos Nazgûl e a tensão do momento em que tudo parece à beira da queda.

17.
“Não diga adeus. Ainda não.”
🧙‍♂️ Gandalf — O Retorno do Rei  
Nos Portos Cinzentos, Frodo está prestes a partir. Gandalf, com ternura, tenta aliviar o peso da despedida com essa frase. É um momento sereno e melancólico, que marca o fim de uma era e o início de outra jornada — além do mar.

18.
“Eu gostaria que o anel nunca tivesse vindo a mim.”
🧝 Frodo — A Sociedade do Anel  
Frodo, ainda no começo da jornada, expressa seu medo e arrependimento. A frase é dita nas cavernas de Moria, e Gandalf responde com sabedoria. Um diálogo que encapsula o dilema de quem não escolhe o fardo, mas o carrega mesmo assim.

19.
“Força bruta pode ser poderosa, mas coragem muda destinos.”
👑 Elrond — A Sociedade do Anel  
Durante o Conselho de Elrond, ele lembra aos presentes que não é a espada que decidirá o futuro da Terra-média, mas a coragem de quem age com sabedoria. Uma fala que reforça o tema central da trilogia: a bravura dos humildes.

20.
“Minhas costas doem, meus pés estão calejados... mas conseguimos, Sr. Frodo.”
🧑‍🌾 Sam — O Retorno do Rei  
Após o anel ser destruído, Frodo e Sam esperam o fim entre as cinzas da Montanha da Perdição. Sam, exausto, expressa alívio e orgulho. É o respiro final de uma jornada épica, marcada por dor, amizade e vitória.""",

    description="Seleciona frases famosas e conhecidas da trilogia cinematográfica de 'O Senhor dos Anéis'."
)
print(f"🤖 [OKAY] Agente ADK '{sda_citation_agent.name}' (Foco: Frases de Filmes) definido.")

# Agente para gerar prompts artísticos (ESTILO HQ ANOS 90, CENA AMPLA) baseados nas frases dos filmes
sda_image_prompt_agent = Agent(
    name="AgenteIlustradorHQAnos90SdA", 
    model=GEMINI_MODEL_FOR_ADK_AGENTS,
    instruction="INSTRUCAO_BASE_PARA_PROMPT_DE_IMAGEM_HQ_SDA", # Placeholder, será substituída no loop
    description="Cria prompts para imagens no estilo HQ anos 90, com foco em cenas amplas, baseados em frases da trilogia SdA."
)
print(f"🤖 [OKAY] Agente ADK '{sda_image_prompt_agent.name}' (Foco: Imagem HQ Anos 90 - Cena Ampla) definido.")
print("----------------------------------------------------")

# --- LÓGICA PRINCIPAL DO SCRIPT (MAIN LOOP) ---
def main_loop():
    """
    Loop principal de execução do script.
    """
    print(f"\n🚀 [MAIN] Iniciando Loop Principal do Agente SdA (Frases de Filmes, Imagens HQ Anos 90) 🚀")
    
    if not gsheets_worksheet or not gdrive_service or not gemini_image_generation_client:
        print("❌ [FATAL] [MAIN] Serviços essenciais não inicializados. Encerrando o loop.")
        return 

    # Nova instrução base para o agente que gera prompts de imagem (HQ anos 90, CENA AMPLA)
    base_instruction_for_image_prompt_agent = """Você é um ilustrador especialista em criar arte no estilo de histórias em quadrinhos (HQ) dos anos 90, com cores fortes e vibrantes no estilo dos quadrinhos x-men.
Analise a seguinte FRASE FAMOSA da trilogia cinematográfica de 'O Senhor dos Anéis':
---
{TEXTO_DA_FRASE_DO_FILME_AQUI}
---
Sua tarefa é criar um PROMPT VISUAL DESCRITIVO E INSPIRADOR, com até 100 palavras, para gerar uma imagem no estilo HQ dos anos 90 usando o modelo Gemini.
A imagem deve ser quadrada (proporção 1:1), impactante, SEM TEXTOS, FRASES ou BALÕES DE FALA, e conter APENAS UM ÚNICO QUADRO (não uma página de HQ com múltiplos painéis).
O foco deve ser em retratar a CENA COMPLETA, mostrando o CENÁRIO, os PERSONAGENS envolvidos e a ATMOSFERA geral. Evite closes extremos no rosto de um único personagem; priorize uma COMPOSIÇÃO AMPLA que contextualize a frase.
Destaque:
- Emoções fortes (fúria, coragem, medo, desespero, esperança) representadas visualmente na expressão dos personagens e na atmosfera da cena.
- Cores vibrantes, contrastes fortes, sombras intensas e, se apropriado, perspectiva exagerada para maior dramaticidade.
- O cenário deve remeter diretamente à cena do filme, com elementos icônicos e um ambiente bem definido.
Retorne apenas o prompt da imagem, sem saudações, explicações ou qualquer texto adicional.
"""
    
    post_counter = 0 

    while True:
        post_counter += 1
        current_processing_time_str = datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n\n🎬 --- [MAIN] Processando Post #{post_counter} (Filmes/HQ90) às {current_processing_time_str} --- 🎬")
        print("====================================================")

        # ETAPA 1: Gerar Frase Famosa do Filme
        # ------------------------------------
        citation_agent_input = "Por favor, selecione uma frase famosa e impactante da trilogia cinematográfica de O Senhor dos Anéis, seguindo RIGOROSAMENTE suas instruções de formato e autenticidade."
        print(f"📖 [INFO] [MAIN] Etapa 1: Solicitando frase de filme ao agente '{sda_citation_agent.name}'...")
        
        generated_citation = call_agent_sync(sda_citation_agent, citation_agent_input)

        if not generated_citation or not generated_citation.strip():
            print(f"❌ [ERROR] [MAIN] Etapa 1: Falha ao gerar frase do filme. Agente '{sda_citation_agent.name}' não retornou conteúdo.")
            save_data_to_google_sheet(gsheets_worksheet, current_processing_time_str, "ERRO SISTEMA: Frase do filme não gerada", "N/A - Falha na Etapa 1")
            print(f"🕒 [INFO] [MAIN] Aguardando {INTERVALO_ENTRE_POSTS_SEGUNDOS} segundos...")
            time.sleep(INTERVALO_ENTRE_POSTS_SEGUNDOS)
            continue 
        print(f"💬 [OKAY] [MAIN] Etapa 1: Frase do Filme Gerada:\n--- Frase Gerada ---\n{generated_citation}\n----------------------\n")

        # ETAPA 2: Gerar Prompt para Imagem (HQ anos 90)
        # ----------------------------------------------
        print(f"🎨 [INFO] [MAIN] Etapa 2: Solicitando prompt de imagem (HQ anos 90) ao agente '{sda_image_prompt_agent.name}'...")
        sda_image_prompt_agent.instruction = base_instruction_for_image_prompt_agent.replace(
            "{TEXTO_DA_FRASE_DO_FILME_AQUI}", generated_citation 
        )
        artistic_image_prompt = call_agent_sync(sda_image_prompt_agent, "Gere o prompt para a imagem no estilo HQ anos 90 com cena ampla, baseado na frase fornecida em sua instrução.")

        if not artistic_image_prompt or not artistic_image_prompt.strip():
            print(f"❌ [ERROR] [MAIN] Etapa 2: Falha ao gerar prompt para imagem HQ. Agente '{sda_image_prompt_agent.name}' não retornou conteúdo.")
            save_data_to_google_sheet(gsheets_worksheet, current_processing_time_str, generated_citation, "ERRO SISTEMA: Prompt de imagem HQ não gerado - Falha na Etapa 2")
            print(f"🕒 [INFO] [MAIN] Aguardando {INTERVALO_ENTRE_POSTS_SEGUNDOS} segundos...")
            time.sleep(INTERVALO_ENTRE_POSTS_SEGUNDOS)
            continue
        print(f"🖌️ [OKAY] [MAIN] Etapa 2: Prompt artístico (HQ anos 90) gerado.") 
        # O prompt da imagem já é logado dentro da função generate_image_with_gemini_client

        # ETAPA 3: Gerar Imagem
        # ---------------------
        print(f"🖼️ [INFO] [MAIN] Etapa 3: Solicitando geração de imagem (formato alvo: JPEG)...")
        generated_jpeg_image_bytes = generate_image_with_gemini_client(artistic_image_prompt)
        
        final_image_url_for_sheet = "ERRO SISTEMA: Status desconhecido do processamento da imagem" 

        if generated_jpeg_image_bytes:
            print(f"✅ [OKAY] [MAIN] Etapa 3: Bytes da imagem (JPEG ou convertida) gerados.")
            
            # ETAPA 4: Upload e Permissões no Google Drive
            # -------------------------------------------
            print(f"💾 [INFO] [MAIN] Etapa 4: Iniciando upload e permissões no Google Drive...")
            drive_filename = f"SdA_Filme_HQ90_{datetime.now(pytz.timezone(TIME_ZONE)).strftime('%Y%m%d_%H%M%S')}.jpg" 
            
            _, direct_download_url, uploaded_file_id_on_drive = upload_image_to_google_drive(
                gdrive_service, drive_filename, generated_jpeg_image_bytes, DRIVE_FOLDER_ID
            )

            if direct_download_url and uploaded_file_id_on_drive:
                print(f"🔒 [INFO] [MAIN] Etapa 4a: Definindo permissões públicas para o arquivo ID: {uploaded_file_id_on_drive}...")
                permissions_set_successfully = set_google_drive_file_public_readable(gdrive_service, uploaded_file_id_on_drive)
                
                if permissions_set_successfully:
                    final_image_url_for_sheet = direct_download_url
                    print(f"✅ [OKAY] [MAIN] Etapa 4: Upload e permissões concluídos. Link: {final_image_url_for_sheet}")
                else:
                    final_image_url_for_sheet = f"ERRO SISTEMA: Imagem no Drive ({direct_download_url}) mas FALHA AO DEFINIR PERMISSÕES."
                    print(f"❌ [ERROR] [MAIN] Etapa 4: {final_image_url_for_sheet}")
            elif uploaded_file_id_on_drive: # Caso raro: upload deu ID mas não link direto (nossa func não faz isso)
                 final_image_url_for_sheet = f"ERRO SISTEMA: Upload ocorreu (ID: {uploaded_file_id_on_drive}), mas falha ao obter link direto."
                 print(f"❌ [ERROR] [MAIN] Etapa 4: {final_image_url_for_sheet}")
            else: 
                final_image_url_for_sheet = "ERRO SISTEMA: Falha completa no upload para o Google Drive."
                print(f"❌ [ERROR] [MAIN] Etapa 4: {final_image_url_for_sheet}")
        else:
            error_msg_img = "ERRO SISTEMA: Imagem não gerada ou falha na conversão (bytes vazios)."
            if not artistic_image_prompt or not artistic_image_prompt.strip():
                 error_msg_img += " Causa provável: Prompt artístico estava vazio."
            final_image_url_for_sheet = error_msg_img
            print(f"❌ [ERROR] [MAIN] Etapa 3: {error_msg_img}")

        # ETAPA 5: Registrar Dados na Planilha
        # ------------------------------------
        print(f"📊 [INFO] [MAIN] Etapa 5: Registrando informações na Planilha Google...")
        save_data_to_google_sheet(gsheets_worksheet, current_processing_time_str, generated_citation, final_image_url_for_sheet)
        print(f"🏁 [OKAY] [MAIN] Post #{post_counter} (Filmes/HQ90) totalmente processado.")
        print("====================================================")


        print(f"🕒 [INFO] [MAIN] Aguardando {INTERVALO_ENTRE_POSTS_SEGUNDOS} segundos antes do próximo post...")
        time.sleep(INTERVALO_ENTRE_POSTS_SEGUNDOS)

# --- PONTO DE ENTRADA DO SCRIPT ---
if __name__ == "__main__":
    try:
        main_loop() 
    except KeyboardInterrupt:
        print("\n🛑 [INFO] Script interrompido pelo usuário (KeyboardInterrupt). Encerrando...")
    except Exception as e_main:
        print(f"💥 [FATAL] [MAIN] Uma exceção não tratada ocorreu no loop principal: {e_main}")
        traceback.print_exc()
    finally:
        print("🔚 [INFO] Script finalizado.")
