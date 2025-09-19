import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import base64
from datetime import datetime

st.set_page_config(
    page_title="Cadastro de Patrimônio",
    page_icon="Lavie1.png",
    layout="wide"
)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'selected_obra' not in st.session_state:
    st.session_state.selected_obra = None
if 'admin_login_attempt' not in st.session_state:
    st.session_state.admin_login_attempt = False
if 'edit_item_id' not in st.session_state:
    st.session_state.edit_item_id = None
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False
if 'movement_item_id' not in st.session_state: 
    st.session_state.movement_item_id = None

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

COLUNAS_MOVIMENTACOES = [
    "Obra", "N° de Tombamento", "Tipo de Movimentação", "Data e Hora",
    "Responsável pela Movimentação", "Observações"
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
    logo_path = "Lavie.png"
    try:
        img_base64 = get_img_as_base64(logo_path)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{img_base64}" alt="Logo" width="900">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        st.warning(f"Logo '{logo_path}' não encontrada.")
    
    st.title("Controle de Patrimônio")

    tab1, tab2 = st.tabs(["👤 Acesso por Obra", "🔑 Acesso de Administrador"])

    with tab1:
        st.subheader("Login da Obra")
        try:
            obras_df = conn.read(worksheet="Obras", usecols=[0], header=0)
            lista_obras = obras_df["Nome da Obra"].dropna().tolist()
            codigos_obras = st.secrets.obra_codes
            obra_selecionada = st.selectbox("Selecione a Obra", options=lista_obras, index=None, placeholder="Escolha a obra...")
            if obra_selecionada:
                codigo_acesso = st.text_input("Código de Acesso", type="password", key="obra_password")
                if st.button("Entrar na Obra"):
                    if codigo_acesso == codigos_obras.get(obra_selecionada):
                        st.session_state.logged_in = True
                        st.session_state.is_admin = False
                        st.session_state.selected_obra = obra_selecionada
                        st.rerun()
                    else:
                        st.error("Código de acesso incorreto.")
        except Exception as e:
            st.error(f"Não foi possível carregar a lista de obras. Erro: {e}")

    with tab2:
        st.subheader("Login de Administrador")
        admin_password = st.text_input("Senha do Administrador", type="password", key="admin_password")
        if st.button("Entrar como Administrador"):
            if admin_password == st.secrets.admin.password:
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Senha de administrador incorreta.")

def app_principal():
    is_admin = st.session_state.is_admin
    
    logo_path = "Lavie.png"
    try:
        st.sidebar.image(logo_path, width=400)
    except Exception:
        pass
    st.sidebar.header("Navegação")
    if is_admin:
        st.sidebar.info("Logado como **Administrador**.")
    else:
        st.sidebar.info(f"Logado na obra: **{st.session_state.selected_obra}**")
    st.sidebar.write("---")
    if st.sidebar.button("Sair / Trocar Obra"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.cache_data.clear()
        st.rerun()

    try:
        caminho_imagem = "Lavie.png"
        img_base64 = get_img_as_base64(caminho_imagem)
        tipo_imagem = "image/png"
        st.markdown(f"""<style>[data-testid="stBlockContainer"]:first-child {{background-image: url("data:{tipo_imagem};base64,{img_base64}"); background-size: cover; background-position: center; border-radius: 10px; padding: 2rem;}} [data-testid="stBlockContainer"]:first-child h1, [data-testid="stBlockContainer"]:first-child p {{color: white;}} </style>""", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Arquivo de fundo 'Lavie.png' não encontrado.")

    st.title("📦 Sistema de Cadastro de Patrimônio")

    @st.cache_data(ttl=5)
    def carregar_dados_app():
        try:
            status_df = conn.read(worksheet="Status", usecols=[0], header=0)
            lista_status = status_df["Nome do Status"].dropna().tolist()
            obras_df = conn.read(worksheet="Obras", usecols=[0], header=0)
            lista_obras = obras_df["Nome da Obra"].dropna().tolist()
            
            patrimonio_df = conn.read(worksheet="Página1")
            if patrimonio_df.empty:
                patrimonio_df = pd.DataFrame(columns=COLUNAS_PATRIMONIO)
            else:
                patrimonio_df = patrimonio_df.dropna(how="all")
                patrimonio_df.columns = patrimonio_df.columns.str.strip()

            movimentacoes_df = conn.read(worksheet="Movimentacoes")
            if movimentacoes_df.empty:
                movimentacoes_df = pd.DataFrame(columns=COLUNAS_MOVIMENTACOES)
            else:
                movimentacoes_df = movimentacoes_df.dropna(how="all")

            return lista_status, lista_obras, patrimonio_df, movimentacoes_df
        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            return [], [], pd.DataFrame(columns=COLUNAS_PATRIMONIO), pd.DataFrame(columns=COLUNAS_MOVIMENTACOES)

    lista_status, lista_obras_app, existing_data, df_movimentacoes = carregar_dados_app()

    if is_admin:
        st.sidebar.subheader("Visão do Administrador")
        obra_selecionada_admin = st.sidebar.selectbox("Selecione uma Obra para Visualizar", ["Todas"] + lista_obras_app)
        st.subheader(f"Visão da Obra: **{obra_selecionada_admin}**")
        if obra_selecionada_admin == "Todas":
            dados_da_obra = existing_data
        else:
            dados_da_obra = existing_data[existing_data[OBRA_COL] == obra_selecionada_admin].copy()
        obra_para_cadastro = obra_selecionada_admin if obra_selecionada_admin != "Todas" else None
    else:
        obra_logada = st.session_state.selected_obra
        st.subheader(f"Obra: **{obra_logada}**")
        dados_da_obra = existing_data[existing_data[OBRA_COL] == obra_logada].copy()
        obra_para_cadastro = obra_logada

    def gerar_numero_tombamento_sequencial(obra_para_gerar):
        if not obra_para_gerar: return None
        itens = existing_data[existing_data[OBRA_COL] == obra_para_gerar]
        if itens.empty: return "1"
        numeros_numericos = pd.to_numeric(itens[TOMBAMENTO_COL], errors='coerce').dropna()
        if numeros_numericos.empty: return "1"
        return str(int(numeros_numericos.max()) + 1)

    st.header("Cadastrar Novo Item", divider='rainbow')
    
    if is_admin:
        if obra_para_cadastro:
            st.info(f"Cadastrando novo item para a obra: **{obra_para_cadastro}**")
        else:
            obra_para_cadastro = st.selectbox("Selecione a Obra para o novo item", options=lista_obras_app, index=None)

    with st.form("cadastro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome_produto = st.text_input("Nome do Produto*")
            num_tombamento_manual = st.text_input("N° de Tombamento (Opcional)")
            num_nota_fiscal = st.text_input("N° da Nota Fiscal*")
            valor_produto = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            status_selecionado = st.selectbox("Status do Item", options=lista_status, index=0)
        with col2:
            especificacoes = st.text_area("Especificações")
            observacoes = st.text_area("Observações")
            local_uso = st.text_input("Local de Uso")
            responsavel = st.text_input("Responsável ")
        
        uploaded_pdf = st.file_uploader("Anexar PDF da Nota Fiscal ", type="pdf")
        submitted = st.form_submit_button("✔️ Cadastrar Item")

        if submitted:
            if nome_produto and num_nota_fiscal and local_uso and responsavel:
                input_limpo = num_tombamento_manual.strip() if num_tombamento_manual else ""
                num_tombamento_final = ""
                is_valid = False

                if input_limpo:
                    coluna_limpa = existing_data[
                        (existing_data[OBRA_COL] == obra_para_cadastro)
                    ][TOMBAMENTO_COL].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    
                    if input_limpo in coluna_limpa.values:
                        st.error(f"Erro: O N° de Tombamento '{input_limpo}' já existe para esta obra.")
                    else:
                        num_tombamento_final = input_limpo
                        is_valid = True
                else:
                    num_tombamento_final = gerar_numero_tombamento_sequencial(obra_para_cadastro)
                    is_valid = True

                if is_valid:
                    link_nota_fiscal = ""
                    if uploaded_pdf:
                        link_nota_fiscal = upload_to_gdrive(uploaded_pdf.getvalue(), f"NF_{num_tombamento_final}_{obra_para_cadastro.replace(' ', '_')}.pdf")
                    
                    novo_item_df = pd.DataFrame([{
                        OBRA_COL: obra_para_cadastro, TOMBAMENTO_COL: num_tombamento_final,
                        NOME_COL: nome_produto, ESPEC_COL: especificacoes, OBS_COL: observacoes,
                        LOCAL_COL: local_uso, RESPONSAVEL_COL: responsavel,
                        NF_NUM_COL: num_nota_fiscal, NF_LINK_COL: link_nota_fiscal,
                        VALOR_COL: valor_produto, STATUS_COL: status_selecionado
                    }])
                    
                    updated_df = pd.concat([existing_data, novo_item_df], ignore_index=True)
                    conn.update(worksheet="Página1", data=updated_df)
                    st.success(f"Item '{nome_produto}' cadastrado para a obra {obra_para_cadastro}! Tombamento: {num_tombamento_final}")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.warning("⚠️ Preencha os campos obrigatórios (*) e selecione uma obra.")

    st.header("Itens Cadastrados", divider='rainbow')
    if not dados_da_obra.empty:
        filtro_status = st.selectbox("Filtrar por Status", ["Todos"] + sorted(list(dados_da_obra[STATUS_COL].unique())))
        dados_filtrados = dados_da_obra
        if filtro_status != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados[STATUS_COL] == filtro_status]
        
        st.dataframe(dados_filtrados, use_container_width=True, hide_index=True, column_config={
            NF_LINK_COL: st.column_config.LinkColumn("Anexo PDF", display_text="🔗 Abrir")
        })
    else:
        st.info("Nenhum item cadastrado para a obra selecionada ainda.")

    if is_admin:
        st.header("Gerenciar Itens Cadastrados", divider='rainbow')
        if not dados_da_obra.empty:
            dados_da_obra[TOMBAMENTO_COL] = dados_da_obra[TOMBAMENTO_COL].astype(str)
            required_cols = [TOMBAMENTO_COL, NOME_COL]
            if all(col in dados_da_obra.columns for col in required_cols):
                dados_da_obra[TOMBAMENTO_COL] = dados_da_obra[TOMBAMENTO_COL].astype(str)
                df_to_sort = dados_da_obra.copy()
                temp_col_name = '_tombamento_numeric'
                df_to_sort[temp_col_name] = pd.to_numeric(df_to_sort[TOMBAMENTO_COL], errors='coerce')
                sorted_data = df_to_sort.sort_values(by=[temp_col_name])
                sorted_data = sorted_data.drop(columns=[temp_col_name])
                
                lista_itens = [f"{row[TOMBAMENTO_COL]} - {row[NOME_COL]}" for index, row in dados_da_obra.iterrows()]
        
                item_selecionado_gerenciar = st.selectbox("Selecione um item para Gerenciar", options=lista_itens, index=None, placeholder="Escolha um item...")
                
                if item_selecionado_gerenciar:
                    tombamento_selecionado = item_selecionado_gerenciar.split(" - ")[0].strip()
                    obra_do_item = obra_para_cadastro if not is_admin or obra_selecionada_admin != "Todas" else dados_da_obra[dados_da_obra[TOMBAMENTO_COL] == tombamento_selecionado][OBRA_COL].iloc[0]

                    col_mov, col_edit, col_delete = st.columns(3)
            
                    if col_mov.button("📥 Registrar Entrada/Saída", use_container_width=True):
                        st.session_state.movement_item_id = (tombamento_selecionado, obra_do_item)
                        st.session_state.edit_item_id = None
                        st.session_state.confirm_delete = False
                        st.rerun()

                    if col_edit.button("✏️ Editar Item", use_container_width=True):
                        st.session_state.edit_item_id = (tombamento_selecionado, obra_do_item)
                        st.session_state.movement_item_id = None
                        st.session_state.confirm_delete = False
                        st.rerun()

                    if col_delete.button("🗑️ Remover Item", use_container_width=True):
                        st.session_state.confirm_delete = True
                        st.session_state.edit_item_id = (tombamento_selecionado, obra_do_item)
                        st.session_state.movement_item_id = None
                        st.rerun()

                    if st.session_state.movement_item_id == (tombamento_selecionado, obra_do_item):
                        with st.form("movement_form"):
                            st.subheader(f"Registrar Movimentação para: {item_selecionado_gerenciar}")
                            tipo_mov = st.radio("Tipo de Movimentação", ["Entrada", "Saída"], horizontal=True)
                            responsavel_mov = st.text_input("Responsável pela Movimentação")
                            obs_mov = st.text_area("Observações da Movimentação")
                            submitted_mov = st.form_submit_button("✔️ Registrar Movimentação")
                    
                            if submitted_mov and responsavel_mov:
                                nova_movimentacao = pd.DataFrame([{
                                    "Obra": obra_do_item,
                                    "N° de Tombamento": tombamento_selecionado,
                                    "Tipo de Movimentação": tipo_mov,
                                    "Data e Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Responsável pela Movimentação": responsavel_mov,
                                    "Observações": obs_mov
                                }])
                                df_movimentacoes_atualizado = pd.concat([df_movimentacoes, nova_movimentacao], ignore_index=True)
                                conn.update(worksheet="Movimentacoes", data=df_movimentacoes_atualizado)
                        
                                idx_to_update = existing_data[(existing_data[OBRA_COL] == obra_do_item) & (existing_data[TOMBAMENTO_COL].astype(str) == tombamento_selecionado)].index
                                if not idx_to_update.empty:
                                    novo_status = "Disponível" if tipo_mov == "Entrada" else "Em Uso Externo" 
                                    existing_data.loc[idx_to_update, STATUS_COL] = novo_status
                                    conn.update(worksheet="Página1", data=existing_data)
                        
                                st.success("Movimentação registrada com sucesso!")
                                st.session_state.movement_item_id = None
                                st.cache_data.clear()
                                st.rerun()
                            elif submitted_mov:
                                st.warning("O campo 'Responsável pela Movimentação' é obrigatório.")
                                
                    st.write("---")
                    st.subheader(f"Histórico de Movimentações do Item: {tombamento_selecionado}")
                    historico_item = df_movimentacoes[
                        (df_movimentacoes["Obra"] == obra_do_item) &
                        (df_movimentacoes["N° de Tombamento"].astype(str) == tombamento_selecionado)
                    ].sort_values(by="Data e Hora", ascending=False)
            
                    if not historico_item.empty:
                        st.dataframe(historico_item, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nenhuma movimentação registrada para este item.")
            
            if st.session_state.edit_item_id and not st.session_state.confirm_delete:
                tomb_edit_original, obra_edit_key = st.session_state.edit_item_id
                item_data_list = existing_data[(existing_data[TOMBAMENTO_COL].astype(str) == str(tomb_edit_original)) & (existing_data[OBRA_COL] == obra_edit_key)]
            
                if not item_data_list.empty:
                    item_data = item_data_list.iloc[0]

                    with st.form("edit_form"):
                        st.subheader(f"Editando Item: {tomb_edit_original} (Obra: {obra_edit_key})")
                    
                        tomb_edit_novo = st.text_input(f"{TOMBAMENTO_COL}", value=item_data.get(TOMBAMENTO_COL, ""))
                        status_edit = st.selectbox(STATUS_COL, options=lista_status, index=lista_status.index(item_data.get(STATUS_COL)) if item_data.get(STATUS_COL) in lista_status else 0)
                        nome_edit = st.text_input(NOME_COL, value=item_data.get(NOME_COL, ""))
                        num_nota_fiscal_edit = st.text_input(f"{NF_NUM_COL}", value=item_data.get(NF_NUM_COL, ""))
                        especificacoes_edit = st.text_area(ESPEC_COL, value=item_data.get(ESPEC_COL, ""))
                        observacoes_edit = st.text_area(OBS_COL, value=item_data.get(OBS_COL, ""))
                        local_edit = st.text_input(LOCAL_COL, value=item_data.get(LOCAL_COL, ""))
                        responsavel_edit = st.text_input(RESPONSAVEL_COL, value=item_data.get(RESPONSAVEL_COL, ""))
                        valor_edit = st.number_input(f"{VALOR_COL} (R$)", min_value=0.0, format="%.2f", value=float(item_data.get(VALOR_COL, 0)))
                    
                        submitted_edit = st.form_submit_button("💾 Salvar Alterações")
                        if submitted_edit:
                            if num_nota_fiscal_edit and tomb_edit_novo:
                                edit_input_limpo = tomb_edit_novo.strip()
                                coluna_limpa_edit = existing_data[TOMBAMENTO_COL].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                            
                                condicao_outro_item = (existing_data[OBRA_COL] == obra_edit_key) & \
                                                      (coluna_limpa_edit == edit_input_limpo) & \
                                                      (existing_data.index != item_data.name)
                            
                                if not existing_data[condicao_outro_item].empty:
                                    st.error(f"Erro: O N° de Tombamento '{edit_input_limpo}' já existe para outro item nesta obra.")
                                else:
                                    idx_to_update = item_data.name
                                    existing_data.loc[idx_to_update, TOMBAMENTO_COL] = edit_input_limpo
                                    existing_data.loc[idx_to_update, STATUS_COL] = status_edit
                                    existing_data.loc[idx_to_update, NOME_COL] = nome_edit
                                    existing_data.loc[idx_to_update, NF_NUM_COL] = num_nota_fiscal_edit
                                    existing_data.loc[idx_to_update, ESPEC_COL] = especificacoes_edit
                                    existing_data.loc[idx_to_update, OBS_COL] = observacoes_edit
                                    existing_data.loc[idx_to_update, LOCAL_COL] = local_edit
                                    existing_data.loc[idx_to_update, RESPONSAVEL_COL] = responsavel_edit
                                    existing_data.loc[idx_to_update, VALOR_COL] = valor_edit
                                
                                    conn.update(worksheet="Página1", data=existing_data)
                                    st.success(f"Item {edit_input_limpo} atualizado com sucesso!")
                                    st.session_state.edit_item_id = None
                                    st.cache_data.clear()
                                    st.rerun()
                            else:
                                st.warning(f"Os campos '{TOMBAMENTO_COL}' e '{NF_NUM_COL}' são obrigatórios.")
                else:
                    st.error("O item selecionado para edição não foi encontrado.")
                    st.session_state.edit_item_id = None
                    st.rerun()

if not st.session_state.logged_in:
    tela_de_login()
else:
    app_principal()














