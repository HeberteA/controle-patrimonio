import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

st.set_page_config(
    page_title="Cadastro de Patrimônio",
    page_icon="📦",
    layout="wide"
)

if 'edit_item_id' not in st.session_state:
    st.session_state.edit_item_id = None
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False

OBRA_COL = "Obra"
TOMBAMENTO_COL = "N° de Tombamento"
NOME_COL = "Nome"
STATUS_COL = "Status"
NF_NUM_COL = "N° da Nota Fiscal"
NF_LINK_COL = "Nota Fiscal (Link)"
ESPEC_COL = "Especificações"
OBS_COL = "Observações"
LOCAL_COL = "Local de Uso / Responsável"
VALOR_COL = "Valor"

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

st.title("📦 Sistema de Cadastro de Patrimônio")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        obras_df = conn.read(worksheet="Obras", usecols=[0], header=0)
        lista_obras = obras_df["Nome da Obra"].dropna().tolist()
        status_df = conn.read(worksheet="Status", usecols=[0], header=0)
        lista_status = status_df["Nome do Status"].dropna().tolist()
        
        patrimonio_df = conn.read(worksheet="Página1")
        patrimonio_df = patrimonio_df.dropna(how="all")
        if not patrimonio_df.empty:
            patrimonio_df.columns = patrimonio_df.columns.str.strip()
            
        return lista_obras, lista_status, patrimonio_df
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return [], [], pd.DataFrame()

lista_obras, lista_status, existing_data = carregar_dados()

def gerar_numero_tombamento_sequencial(obra_selecionada):
    if obra_selecionada is None: return None
    itens_da_obra = existing_data[existing_data[OBRA_COL] == obra_selecionada]
    if itens_da_obra.empty: return "1"
    
    numeros_numericos = pd.to_numeric(itens_da_obra[TOMBAMENTO_COL], errors='coerce')
    numeros_existentes = numeros_numericos.dropna()
    
    if numeros_existentes.empty: return "1"
    ultimo_numero = int(numeros_existentes.max())
    proximo_numero = ultimo_numero + 1
    return str(proximo_numero)

st.header("Cadastrar Novo Item", divider='rainbow')
if lista_obras and lista_status:
    col_form1, col_form2 = st.columns(2)
    obra_selecionada_cadastro = col_form1.selectbox("Selecione a Obra", options=lista_obras, index=None, placeholder="Escolha a obra...")
    status_selecionado = col_form2.selectbox("Status do Item", options=lista_status, index=0)
else:
    st.warning("Verifique se as abas 'Obras' e 'Status' estão preenchidas.")
    obra_selecionada_cadastro = None
    status_selecionado = None

with st.form("cadastro_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        nome_produto = st.text_input("Nome do Produto")
        num_tombamento_manual = st.text_input("N° de Tombamento (Opcional)")
        num_nota_fiscal = st.text_input("N° da Nota Fiscal")
        valor_produto = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
    with col2:
        especificacoes = st.text_area("Especificações")
        observacoes = st.text_area("Observações (Opcional)")
        local_responsavel = st.text_input("Local de Uso / Responsável")
    
    uploaded_pdf = st.file_uploader("Anexar PDF da Nota Fiscal (Opcional)", type="pdf")
    submitted = st.form_submit_button("✔️ Cadastrar Item")

    if submitted:
        if existing_data.empty:
            st.error("Não é possível adicionar um item pois a planilha está vazia ou não foi carregada.")
        elif obra_selecionada_cadastro and nome_produto and num_nota_fiscal:
            num_tombamento_final = ""
            is_valid = False

            if num_tombamento_manual:
                condicao = (existing_data[OBRA_COL] == obra_selecionada_cadastro) & (existing_data[TOMBAMENTO_COL] == num_tombamento_manual)
                if not existing_data[condicao].empty:
                    st.error(f"Erro: O N° de Tombamento '{num_tombamento_manual}' já existe para esta obra.")
                else:
                    num_tombamento_final = num_tombamento_manual
                    is_valid = True
            else:
                num_tombamento_final = gerar_numero_tombamento_sequencial(obra_selecionada_cadastro)
                is_valid = True
            
            if is_valid:
                link_nota_fiscal = ""
                if uploaded_pdf is not None:
                    pdf_data = uploaded_pdf.getvalue()
                    st.info("Fazendo upload da nota fiscal...")
                    link_nota_fiscal = upload_to_gdrive(pdf_data, f"NF_{num_tombamento_final}_{obra_selecionada_cadastro.replace(' ', '_')}.pdf")
                
                novo_item_df = pd.DataFrame([{
                    OBRA_COL: obra_selecionada_cadastro, TOMBAMENTO_COL: num_tombamento_final,
                    NOME_COL: nome_produto, ESPEC_COL: especificacoes, OBS_COL: observacoes,
                    LOCAL_COL: local_responsavel, NF_NUM_COL: num_nota_fiscal,
                    NF_LINK_COL: link_nota_fiscal, VALOR_COL: valor_produto, STATUS_COL: status_selecionado
                }])
                
                updated_df = pd.concat([existing_data, novo_item_df], ignore_index=True)
                conn.update(worksheet="Página1", data=updated_df)
                st.success(f"Item '{nome_produto}' cadastrado! Tombamento: {num_tombamento_final}")
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning("⚠️ Preencha os campos obrigatórios (Obra, Nome, N° da Nota Fiscal).")

st.header("Itens Cadastrados", divider='rainbow')
if not existing_data.empty:
    col_filtro1, col_filtro2 = st.columns(2)
    filtro_obra = col_filtro1.selectbox("Filtrar por Obra", ["Todas"] + sorted(list(existing_data[OBRA_COL].unique())))
    filtro_status = col_filtro2.selectbox("Filtrar por Status", ["Todos"] + sorted(list(existing_data[STATUS_COL].unique())))

    dados_filtrados = existing_data
    if filtro_obra != "Todas": dados_filtrados = dados_filtrados[dados_filtrados[OBRA_COL] == filtro_obra]
    if filtro_status != "Todos": dados_filtrados = dados_filtrados[dados_filtrados[STATUS_COL] == filtro_status]
    
    st.dataframe(dados_filtrados, use_container_width=True, hide_index=True, column_config={
        NF_LINK_COL: st.column_config.LinkColumn("Anexo PDF", display_text="🔗 Abrir")
    })

st.header("Gerenciar Itens Cadastrados", divider='rainbow')
if not existing_data.empty:
    required_cols = [OBRA_COL, TOMBAMENTO_COL, NOME_COL]
    if all(col in existing_data.columns for col in required_cols):
        
        existing_data[TOMBAMENTO_COL] = existing_data[TOMBAMENTO_COL].astype(str)
        df_to_sort = existing_data.copy()
        temp_col_name = '_tombamento_numeric'
        df_to_sort[temp_col_name] = pd.to_numeric(df_to_sort[TOMBAMENTO_COL], errors='coerce')
        sorted_data = df_to_sort.sort_values(
             by=[OBRA_COL, temp_col_name]
        )
        sorted_data = sorted_data.drop(columns=[temp_col_name])
        lista_itens = [f"{row[TOMBAMENTO_COL]} - {row[NOME_COL]} (Obra: {row[OBRA_COL]})" for index, row in sorted_data.iterrows()]
        
        item_selecionado_gerenciar = st.selectbox(
            "Selecione um item para Editar ou Remover", options=lista_itens, index=None, placeholder="Escolha um item..."
        )

        if item_selecionado_gerenciar:
            tombamento_selecionado = item_selecionado_gerenciar.split(" - ")[0]
            obra_do_item_selecionado = item_selecionado_gerenciar.split("(Obra: ")[1].replace(")", "")
            
            col_edit, col_delete = st.columns(2)
            if col_edit.button("✏️ Editar Item Selecionado", use_container_width=True):
                st.session_state.edit_item_id = (tombamento_selecionado, obra_do_item_selecionado)
                st.session_state.confirm_delete = False
                st.rerun()
            if col_delete.button("🗑️ Remover Item Selecionado", use_container_width=True):
                st.session_state.confirm_delete = True
                st.session_state.edit_item_id = (tombamento_selecionado, obra_do_item_selecionado)
                st.rerun()
            
            if st.session_state.confirm_delete and st.session_state.edit_item_id == (tombamento_selecionado, obra_do_item_selecionado):
                tomb, obra = st.session_state.edit_item_id
                st.warning(f"**Atenção!** Deseja remover o item **{tomb}** da obra **{obra}**?")
                c1, c2 = st.columns(2)
                if c1.button("Sim, tenho certeza e quero remover", use_container_width=True):
                    condicao = ~((existing_data[OBRA_COL] == obra) & (existing_data[TOMBAMENTO_COL] == tomb))
                    df_sem_item = existing_data[condicao]
                    conn.update(worksheet="Página1", data=df_sem_item)
                    st.success(f"Item {tomb} da obra {obra} removido!")
                    st.session_state.confirm_delete = False
                    st.session_state.edit_item_id = None
                    st.cache_data.clear()
                    st.rerun()
                if c2.button("Não, cancelar remoção", use_container_width=True):
                    st.session_state.confirm_delete = False
                    st.session_state.edit_item_id = None
                    st.rerun()
if st.session_state.edit_item_id and not st.session_state.confirm_delete:
    tomb_edit_original, obra_edit_key = st.session_state.edit_item_id
    item_data_list = existing_data[(existing_data[TOMBAMENTO_COL] == str(tomb_edit_original)) & (existing_data[OBRA_COL] == obra_edit_key)]
    
    if not item_data_list.empty:
        item_data = item_data_list.iloc[0]

        with st.form("edit_form"):
            st.subheader(f"Editando Item: {tomb_edit_original} (Obra: {obra_edit_key})")
            
            tomb_edit_novo = st.text_input(f"{TOMBAMENTO_COL} ", value=item_data.get(TOMBAMENTO_COL, ""))
            status_edit = st.selectbox(STATUS_COL, options=lista_status, index=lista_status.index(item_data.get(STATUS_COL)) if item_data.get(STATUS_COL) in lista_status else 0)
            nome_edit = st.text_input(NOME_COL, value=item_data.get(NOME_COL, ""))
            num_nota_fiscal_edit = st.text_input(f"{NF_NUM_COL} ", value=item_data.get(NF_NUM_COL, ""))
            especificacoes_edit = st.text_area(ESPEC_COL, value=item_data.get(ESPEC_COL, ""))
            observacoes_edit = st.text_area(OBS_COL, value=item_data.get(OBS_COL, ""))
            local_edit = st.text_input(LOCAL_COL, value=item_data.get(LOCAL_COL, ""))
            valor_edit = st.number_input(f"{VALOR_COL} (R$)", min_value=0.0, format="%.2f", value=float(item_data.get(VALOR_COL, 0)))
            
            submitted_edit = st.form_submit_button("💾 Salvar Alterações")
            if submitted_edit:
                if num_nota_fiscal_edit and tomb_edit_novo:
                    condicao_outro_item = (existing_data[OBRA_COL] == obra_edit_key) & \
                                          (existing_data[TOMBAMENTO_COL] == tomb_edit_novo) & \
                                          (existing_data.index != item_data.name)
                    
                    if not existing_data[condicao_outro_item].empty:
                        st.error(f"Erro: O N° de Tombamento '{tomb_edit_novo}' já existe para outro item nesta obra.")
                    else:
                        idx_to_update = item_data.name
                        existing_data.loc[idx_to_update, TOMBAMENTO_COL] = tomb_edit_novo
                        existing_data.loc[idx_to_update, STATUS_COL] = status_edit
                        existing_data.loc[idx_to_update, NOME_COL] = nome_edit
                        existing_data.loc[idx_to_update, NF_NUM_COL] = num_nota_fiscal_edit
                        existing_data.loc[idx_to_update, ESPEC_COL] = especificacoes_edit
                        existing_data.loc[idx_to_update, OBS_COL] = observacoes_edit
                        existing_data.loc[idx_to_update, LOCAL_COL] = local_edit
                        existing_data.loc[idx_to_update, VALOR_COL] = valor_edit
                        
                        conn.update(worksheet="Página1", data=existing_data)
                        st.success(f"Item {tomb_edit_novo} atualizado com sucesso!")
                        st.session_state.edit_item_id = None
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.warning(f"Os campos '{TOMBAMENTO_COL}' e '{NF_NUM_COL}' são obrigatórios.")
    else:
        st.error("O item selecionado para edição não foi encontrado.")
        st.session_state.edit_item_id = None
        st.rerun()




























