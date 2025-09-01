import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import base64

st.set_page_config(
    page_title="Cadastro de Patrimônio",
    page_icon="Lavie1.png",
    layout="wide"
)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'selected_obra' not in st.session_state:
    st.session_state.selected_obra = None
if 'edit_item_id' not in st.session_state:
    st.session_state.edit_item_id = None
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False

@st.cache_data
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

OBRA_COL = "Obra"
TOMBAMENTO_COL = "N° de Tombamento"
NOME_COL = "Nome"
STATUS_COL = "Status"
NF_NUM_COL = "N° da Nota Fiscal"
NF_LINK_COL = "Nota Fiscal (Link)"
ESPEC_COL = "Especificações"
OBS_COL = "Observações"
LOCAL_COL = "Local de Uso" 
RESPONSAVEL_COL = "Responsável" 
VALOR_COL = "Valor"

COLUNAS_PATRIMONIO = [
    OBRA_COL, TOMBAMENTO_COL, NOME_COL, ESPEC_COL, OBS_COL, 
    LOCAL_COL, RESPONSAVEL_COL,
    NF_NUM_COL, NF_LINK_COL, VALOR_COL, STATUS_COL
]

def upload_to_gdrive(file_data, file_name):
    try:
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["connections"]["gsheets"], scopes=scopes)
        service = build('drive', 'v3', credentials=creds)
        folder_id = st.secrets["connections"]["gsheets"]["gdrive_folder_id"]
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype='application/pdf', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        file_id = file.get('id')
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Erro no upload para o Google Drive: {e}")
        return None

conn = st.connection("gsheets", type=GSheetsConnection)

def tela_de_login():
    st.title("Controle de Patrimônio - Acesso por Obra")
    st.write("---")
    
    try:
        obras_df = conn.read(worksheet="Obras", usecols=[0], header=0)
        lista_obras = obras_df["Nome da Obra"].dropna().tolist()

        codigos_obras = st.secrets.obra_codes

        obra_selecionada = st.selectbox("Selecione a Obra para continuar", options=lista_obras, index=None, placeholder="Escolha a obra...")
        
        if obra_selecionada:
            codigo_acesso = st.text_input("Código de Acesso da Obra", type="password")
            if st.button("Entrar"):
                if codigo_acesso == codigos_obras.get(obra_selecionada):
                    st.session_state.logged_in = True
                    st.session_state.selected_obra = obra_selecionada
                    st.rerun()
                else:
                    st.error("Código de acesso incorreto.")

    except Exception as e:
        st.error(f"Não foi possível carregar a lista de obras. Verifique a planilha 'Obras'. Erro: {e}")

def app_principal():
    obra_logada = st.session_state.selected_obra

    try:
        caminho_imagem = "Lavie.png"
        img_base64 = get_img_as_base64(caminho_imagem)
        tipo_imagem = "image/png"
        st.markdown(f"""<style>[data-testid="stBlockContainer"]:first-child {{background-image: url("data:{tipo_imagem};base64,{img_base64}"); background-size: cover; background-position: center; border-radius: 10px; padding: 2rem;}} [data-testid="stBlockContainer"]:first-child h1, [data-testid="stBlockContainer"]:first-child p {{color: white;}} </style>""", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Arquivo 'Lavie.png' não encontrado.")

    st.title(f"📦 Sistema de Cadastro de Patrimônio")
    st.subheader(f"Obra: **{obra_logada}**")

    # --- CARREGAMENTO DOS DADOS ---
    @st.cache_data(ttl=5)
    def carregar_dados_app():
        try:
            status_df = conn.read(worksheet="Status", usecols=[0], header=0)
            lista_status = status_df["Nome do Status"].dropna().tolist()
            
            patrimonio_df = conn.read(worksheet="Página1")
            
            if patrimonio_df.empty:
                patrimonio_df = pd.DataFrame(columns=COLUNAS_PATRIMONIO)
            else:
                patrimonio_df = patrimonio_df.dropna(how="all")
                patrimonio_df.columns = patrimonio_df.columns.str.strip()
                
            return lista_status, patrimonio_df
        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            return [], pd.DataFrame(columns=COLUNAS_PATRIMONIO)

    lista_status, existing_data = carregar_dados_app()
    
    # Filtra os dados apenas para a obra logada
    dados_da_obra = existing_data[existing_data[OBRA_COL] == obra_logada].copy()

    def gerar_numero_tombamento_sequencial():
        if dados_da_obra.empty: return "1"
        numeros_numericos = pd.to_numeric(dados_da_obra[TOMBAMENTO_COL], errors='coerce').dropna()
        if numeros_numericos.empty: return "1"
        return str(int(numeros_numericos.max()) + 1)

    # --- FORMULÁRIO DE CADASTRO ---
    st.header("Cadastrar Novo Item", divider='rainbow')
    
    with st.form("cadastro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome_produto = st.text_input("Nome do Produto*")
            num_tombamento_manual = st.text_input("N° de Tombamento (Opcional, deixa em branco para automático)")
            num_nota_fiscal = st.text_input("N° da Nota Fiscal*")
            valor_produto = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            status_selecionado = st.selectbox("Status do Item", options=lista_status, index=0)
        with col2:
            especificacoes = st.text_area("Especificações")
            observacoes = st.text_area("Observações (Opcional)")
            ## ALTERADO - Campos separados
            local_uso = st.text_input("Local de Uso*")
            responsavel = st.text_input("Responsável (Opcional)")
        
        uploaded_pdf = st.file_uploader("Anexar PDF da Nota Fiscal (Opcional)", type="pdf")
        submitted = st.form_submit_button("✔️ Cadastrar Item")

        if submitted:
            ## ALTERADO - Validação com o novo campo obrigatório
            if nome_produto and num_nota_fiscal and local_uso:
                input_limpo = num_tombamento_manual.strip() if num_tombamento_manual else ""
                num_tombamento_final = ""
                is_valid = False

                if input_limpo:
                    coluna_limpa = dados_da_obra[TOMBAMENTO_COL].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    if input_limpo in coluna_limpa.values:
                        st.error(f"Erro: O N° de Tombamento '{input_limpo}' já existe para esta obra.")
                    else:
                        num_tombamento_final = input_limpo
                        is_valid = True
                else:
                    num_tombamento_final = gerar_numero_tombamento_sequencial()
                    is_valid = True
                
                if is_valid:
                    link_nota_fiscal = ""
                    if uploaded_pdf:
                        link_nota_fiscal = upload_to_gdrive(uploaded_pdf.getvalue(), f"NF_{num_tombamento_final}_{obra_logada.replace(' ', '_')}.pdf")
                    
                    novo_item_df = pd.DataFrame([{
                        OBRA_COL: obra_logada, TOMBAMENTO_COL: num_tombamento_final,
                        NOME_COL: nome_produto, ESPEC_COL: especificacoes, OBS_COL: observacoes,
                        LOCAL_COL: local_uso, RESPONSAVEL_COL: responsavel, ## ALTERADO
                        NF_NUM_COL: num_nota_fiscal, NF_LINK_COL: link_nota_fiscal, 
                        VALOR_COL: valor_produto, STATUS_COL: status_selecionado
                    }])
                    
                    updated_df = pd.concat([existing_data, novo_item_df], ignore_index=True)
                    conn.update(worksheet="Página1", data=updated_df)
                    st.success(f"Item '{nome_produto}' cadastrado! Tombamento: {num_tombamento_final}")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.warning("⚠️ Preencha os campos obrigatórios (*).")
    
    # ... O resto do seu código (Gerenciar Itens, etc.) precisa ser adaptado para usar 'dados_da_obra' em vez de 'existing_data'
    # ... e também os novos campos de Local de Uso e Responsável no formulário de edição.

# --- CONTROLE DE FLUXO PRINCIPAL ---
if not st.session_state.logged_in:
    tela_de_login()
else:
    app_principal()
