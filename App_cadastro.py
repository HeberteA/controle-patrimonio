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
    page_icon="📦",
    layout="wide"
)

if 'edit_item_id' not in st.session_state:
    st.session_state.edit_item_id = None
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False

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
        patrimonio_df = conn.read(worksheet="Página1", usecols=list(range(10)))
        patrimonio_df = patrimonio_df.dropna(how="all")
        if "N° de Tombamento" in patrimonio_df.columns:
            patrimonio_df["N° de Tombamento"] = patrimonio_df["N° de Tombamento"].astype(str)
        return lista_obras, lista_status, patrimonio_df
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return [], [], pd.DataFrame(columns=[
            "Obra", "N° de Tombamento", "Nome", "Especificações", "Observações",
            "Local de Uso / Responsável", "N° da Nota Fiscal", "Nota Fiscal (Link)", "Valor", "Status"
        ])

lista_obras, lista_status, existing_data = carregar_dados()

st.header("Cadastrar Novo Item", divider='rainbow')
if lista_obras and lista_status:
    col_form1, col_form2 = st.columns(2)
    obra_selecionada_cadastro = col_form1.selectbox("Selecione a Obra", options=lista_obras, index=None, placeholder="Escolha a obra...")
    status_selecionado = col_form2.selectbox("Status do Item", options=lista_status, index=0)
else:
    st.warning("Verifique as abas 'Obras' e 'Status'.")
    obra_selecionada_cadastro = None
    status_selecionado = None

with st.form("cadastro_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        nome_produto = st.text_input("Nome do Produto")
        num_tombamento = st.text_input("**N° de Tombamento (Obrigatório)**")
        num_nota_fiscal = st.text_input("**N° da Nota Fiscal (Obrigatório)**")
        valor_produto = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
    with col2:
        especificacoes = st.text_area("Especificações")
        observacoes = st.text_area("Observações (Opcional)")
        local_responsavel = st.text_input("Local de Uso / Responsável")
    
    uploaded_pdf = st.file_uploader("Anexar PDF da Nota Fiscal (Opcional)", type="pdf")
    submitted = st.form_submit_button("✔️ Cadastrar Item")

    if submitted:
        if obra_selecionada_cadastro and nome_produto and num_nota_fiscal and num_tombamento:
            # Validação: Checar se o número de tombamento já existe para a obra selecionada
            condicao = (existing_data['Obra'] == obra_selecionada_cadastro) & (existing_data['N° de Tombamento'] == num_tombamento)
            if not existing_data[condicao].empty:
                st.error(f"Erro: O N° de Tombamento '{num_tombamento}' já existe para a obra '{obra_selecionada_cadastro}'. Por favor, escolha outro número.")
            else:
                link_nota_fiscal = ""
                if uploaded_pdf is not None:
                    pdf_data = uploaded_pdf.getvalue()
                    st.info("Fazendo upload da nota fiscal...")
                    link_nota_fiscal = upload_to_gdrive(pdf_data, f"NF_{num_tombamento}_{obra_selecionada_cadastro.replace(' ', '_')}.pdf")
                    if not link_nota_fiscal:
                        st.error("Falha ao fazer upload do PDF. O item será salvo sem o link.")
                
                novo_item_df = pd.DataFrame([{
                    "Obra": obra_selecionada_cadastro, "N° de Tombamento": num_tombamento,
                    "Nome": nome_produto, "Especificações": especificacoes, "Observações": observacoes,
                    "Local de Uso / Responsável": local_responsavel,
                    "N° da Nota Fiscal": num_nota_fiscal, "Nota Fiscal (Link)": link_nota_fiscal,
                    "Valor": valor_produto, "Status": status_selecionado
                }])
                
                updated_df = pd.concat([existing_data, novo_item_df], ignore_index=True)
                conn.update(worksheet="Página1", data=updated_df)
                st.success(f"Item '{nome_produto}' cadastrado com sucesso! Tombamento: {num_tombamento}")
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning("⚠️ Preencha todos os campos obrigatórios (Obra, Nome, N° de Tombamento, N° da Nota Fiscal).")

st.header("Itens Cadastrados", divider='rainbow')
if not existing_data.empty:
    col_filtro1, col_filtro2 = st.columns(2)
    filtro_obra = col_filtro1.selectbox("Filtrar por Obra", ["Todas"] + sorted(list(existing_data["Obra"].unique())))
    filtro_status = col_filtro2.selectbox("Filtrar por Status", ["Todos"] + sorted(list(existing_data["Status"].unique())))

    dados_filtrados = existing_data
    if filtro_obra != "Todas": dados_filtrados = dados_filtrados[dados_filtrados["Obra"] == filtro_obra]
    if filtro_status != "Todos": dados_filtrados = dados_filtrados[dados_filtrados["Status"] == filtro_status]
    
    st.dataframe(dados_filtrados, use_container_width=True, hide_index=True, column_config={
        "Nota Fiscal (Link)": st.column_config.LinkColumn("Anexo PDF", display_text="🔗 Abrir")
    })

st.header("Gerenciar Itens Cadastrados", divider='rainbow')
if not existing_data.empty:
    lista_itens = [f"{row['N° de Tombamento']} - {row['Nome']} (Obra: {row['Obra']})" for index, row in existing_data.sort_values(by=["Obra", pd.to_numeric(existing_data["N° de Tombamento"])]).iterrows()]
    item_selecionado_gerenciar = st.selectbox("Selecione um item para Editar ou Remover", options=lista_itens, index=None, placeholder="Escolha um item...")

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
        
        if st.session_state.confirm_delete:
            tomb, obra = st.session_state.edit_item_id
            st.warning(f"**Atenção!** Deseja remover o item **{tomb}** da obra **{obra}**?")
            if st.button("Sim, tenho certeza e quero remover"):
                condicao = ~((existing_data["N° de Tombamento"] == tomb) & (existing_data["Obra"] == obra))
                df_sem_item = existing_data[condicao]
                conn.update(worksheet="Página1", data=df_sem_item)
                st.success(f"Item {tomb} da obra {obra} removido!")
                st.session_state.confirm_delete = False
                st.session_state.edit_item_id = None
                st.cache_data.clear()
                st.rerun()

if st.session_state.edit_item_id and not st.session_state.confirm_delete:
    tomb_edit_original, obra_edit_key = st.session_state.edit_item_id
    st.subheader(f"Editando Item: {tomb_edit_original} (Obra: {obra_edit_key})")
    item_data = existing_data[(existing_data["N° de Tombamento"] == tomb_edit_original) & (existing_data["Obra"] == obra_edit_key)].iloc[0]

    with st.form("edit_form"):
        st.info(f"Obra: **{item_data['Obra']}** (não pode ser alterada)")
        
        tomb_edit_novo = st.text_input("**N° de Tombamento (Obrigatório)**", value=item_data.get("N° de Tombamento", ""))
        status_edit = st.selectbox("Status", options=lista_status, index=lista_status.index(item_data.get("Status")) if item_data.get("Status") in lista_status else 0)
        nome_edit = st.text_input("Nome do Produto", value=item_data.get("Nome", ""))
        num_nota_fiscal_edit = st.text_input("**N° da Nota Fiscal (Obrigatório)**", value=item_data.get("N° da Nota Fiscal", ""))
        especificacoes_edit = st.text_area("Especificações", value=item_data.get("Especificações", ""))
        observacoes_edit = st.text_area("Observações (Opcional)", value=item_data.get("Observações", ""))
        local_edit = st.text_input("Local de Uso / Responsável", value=item_data.get("Local de Uso / Responsável", ""))
        valor_edit = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=float(item_data.get("Valor", 0)))
        
        link_atual = item_data.get("Nota Fiscal (Link)", "")
        if link_atual and pd.notna(link_atual):
            st.markdown(f"**Anexo Atual:** [Abrir PDF]({link_atual})")
        
        submitted_edit = st.form_submit_button("💾 Salvar Alterações")
        if submitted_edit:
            if num_nota_fiscal_edit and tomb_edit_novo:
                # Validação: Checar se o NOVO número de tombamento já existe em OUTRO item da mesma obra
                condicao_outro_item = (existing_data['Obra'] == obra_edit_key) & \
                                      (existing_data['N° de Tombamento'] == tomb_edit_novo) & \
                                      (existing_data['N° de Tombamento'] != tomb_edit_original)
                
                if not existing_data[condicao_outro_item].empty:
                    st.error(f"Erro: O N° de Tombamento '{tomb_edit_novo}' já existe para outro item nesta obra.")
                else:
                    condicao_update = (existing_data["N° de Tombamento"] == tomb_edit_original) & (existing_data["Obra"] == obra_edit_key)
                    idx_to_update = existing_data.index[condicao_update].tolist()[0]

                    existing_data.loc[idx_to_update, "N° de Tombamento"] = tomb_edit_novo
                    existing_data.loc[idx_to_update, "Status"] = status_edit
                    existing_data.loc[idx_to_update, "Nome"] = nome_edit
                    existing_data.loc[idx_to_update, "N° da Nota Fiscal"] = num_nota_fiscal_edit
                    existing_data.loc[idx_to_update, "Especificações"] = especificacoes_edit
                    existing_data.loc[idx_to_update, "Observações"] = observacoes_edit
                    existing_data.loc[idx_to_update, "Local de Uso / Responsável"] = local_edit
                    existing_data.loc[idx_to_update, "Valor"] = valor_edit
                    
                    conn.update(worksheet="Página1", data=existing_data)
                    st.success(f"Item {tomb_edit_novo} atualizado com sucesso!")
                    st.session_state.edit_item_id = None
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.warning("Os campos 'N° de Tombamento' e 'N° da Nota Fiscal' são obrigatórios.")





