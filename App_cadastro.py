import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection 
from streamlit_option_menu import option_menu 
import base64
import io
from datetime import datetime
import plotly.express as px 
from fpdf import FPDF         
import openpyxl      

st.set_page_config(
    page_title="Controle de Patrimônio Lavie",
    page_icon="Lavie1.png", 
    layout="wide"
)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'selected_obra' not in st.session_state:
    st.session_state.selected_obra = None
if 'edit_item_id' not in st.session_state:
    st.session_state.edit_item_id = None 
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False
if 'movement_item_id' not in st.session_state:
    st.session_state.movement_item_id = None

ID_COL = "id"
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

def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

def upload_to_supabase_storage(file_data, file_name, file_type='application/pdf'):
    try:
        conn_storage = st.connection(
            "supabase",
            type=SupabaseConnection,
            url=st.secrets["connections"]["supabase"]["url"],
            key=st.secrets["connections"]["supabase"]["key"]
        )
        bucket_name = "notas-fiscais"
        
        conn_storage.storage.from_(bucket_name).upload(
            file=file_data,
            path=file_name,
            file_options={"content-type": file_type, "x-upsert": "true"}
        )
        
        response = conn_storage.storage.from_(bucket_name).get_public_url(file_name)
        return response
    
    except Exception as e:
        st.error(f"Erro no upload para o Supabase Storage: {e}")
        return None

def gerar_numero_tombamento_sequencial(existing_data, obra_para_gerar):
    if not obra_para_gerar: return None
    itens = existing_data[existing_data[OBRA_COL] == obra_para_gerar]
    if itens.empty: return "1"
    numeros_numericos = pd.to_numeric(itens[TOMBAMENTO_COL], errors='coerce').dropna()
    if numeros_numericos.empty: return "1"
    return str(int(numeros_numericos.max()) + 1)

try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error("ERRO GRAVE NA CONEXÃO COM O SUPABASE. Verifique os secrets.")
    st.exception(e)
    st.stop()


@st.cache_data(ttl=60) 
def carregar_dados_app():
    try:
        status_resp = conn.table("status").select("*").execute()
        lista_status = [row['Nome do Status'] for row in status_resp.data]

        obras_resp = conn.table("obras").select("*").execute()
        lista_obras = [row['Nome da Obra'] for row in obras_resp.data]
        
        patrimonio_resp = conn.table("patrimonio").select("*").execute()
        patrimonio_df = pd.DataFrame(patrimonio_resp.data)
        if patrimonio_df.empty: 
             patrimonio_df = pd.DataFrame(columns=[ID_COL, OBRA_COL, TOMBAMENTO_COL, NOME_COL, ESPEC_COL, OBS_COL, LOCAL_COL, RESPONSAVEL_COL, NF_NUM_COL, NF_LINK_COL, VALOR_COL, STATUS_COL])
        if VALOR_COL in patrimonio_df.columns:
            patrimonio_df[VALOR_COL] = pd.to_numeric(patrimonio_df[VALOR_COL], errors='coerce').fillna(0)

        movimentacoes_resp = conn.table("movimentacoes").select("*").execute()
        movimentacoes_df = pd.DataFrame(movimentacoes_resp.data)
        if movimentacoes_df.empty:
            movimentacoes_df = pd.DataFrame(columns=[ID_COL, OBRA_COL, TOMBAMENTO_COL, "tipo_movimentacao", "data_hora", "responsavel_movimentacao", "observacoes"])

        return lista_status, lista_obras, patrimonio_df, movimentacoes_df
    
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return [], [], pd.DataFrame(), pd.DataFrame()

@st.cache_data
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Patrimonio')
    processed_data = output.getvalue()
    return processed_data

def to_pdf(df, obra_nome):
    """Converte DataFrame para um arquivo PDF simples em memória."""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    
    pdf.cell(0, 10, f'Relatorio de Patrimonio - Obra: {obra_nome}', 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 8)
    col_widths = {TOMBAMENTO_COL: 25, NOME_COL: 60, STATUS_COL: 30, LOCAL_COL: 40, RESPONSAVEL_COL: 40, VALOR_COL: 25}
    cols_to_export = list(col_widths.keys())
    
    for col_name in cols_to_export:
        pdf.cell(col_widths[col_name], 7, col_name.replace("_", " ").title(), 1, 0, 'C')
    pdf.ln()

    pdf.set_font('Arial', '', 8)
    df_pdf = df[cols_to_export].fillna('') 
    
    for _, row in df_pdf.iterrows():
        for col_name in cols_to_export:
            text = str(row[col_name]).encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(col_widths[col_name], 6, text, 1)
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1') 

def tela_de_login():
    logo_path = "Lavie.png"
    st.title("Controle de Patrimônio")

    tab1, tab2 = st.tabs(["Acesso por Obra", "Acesso de Administrador"])

    with tab1:
        st.subheader("Login da Obra")
        try:
            _, lista_obras, _, _ = carregar_dados_app()
            
            if not lista_obras:
                st.error("Nenhuma obra cadastrada no sistema.")
                return

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

def pagina_dashboard(dados_da_obra, df_movimentacoes):
    st.header("Dashboard de Patrimônio", divider='rainbow')

    if dados_da_obra.empty:
        st.info("Nenhum dado disponível para exibir no dashboard.")
        return

    total_itens = dados_da_obra.shape[0]
    valor_total = dados_da_obra[VALOR_COL].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Itens", f"{total_itens} un.")
    with col2:
        st.metric("Valor Total do Patrimônio", f"R$ {valor_total:,.2f}")

    st.write("---")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("Itens por Status")
        status_counts = dados_da_obra[STATUS_COL].value_counts().reset_index()
        
        fig_status = px.pie(status_counts, names=STATUS_COL, values='count', 
                            title="Distribuição de Itens por Status")
        st.plotly_chart(fig_status, use_container_width=True)

    with col_graf2:
        st.subheader("Valor por Local de Uso")
        df_valor_local = dados_da_obra.groupby(LOCAL_COL)[VALOR_COL].sum().reset_index().sort_values(by=VALOR_COL, ascending=False)
        
        fig_local = px.bar(df_valor_local, x=LOCAL_COL, y=VALOR_COL, 
                           title="Valor Total (R$) por Local de Uso", text_auto='.2s')
        fig_local.update_traces(textposition='outside')
        st.plotly_chart(fig_local, use_container_width=True)

def pagina_cadastrar_item(is_admin, lista_status, lista_obras_app, existing_data):
    st.header("Cadastrar Novo Item", divider='rainbow')
    obra_para_cadastro = None
    if is_admin:
        obra_para_cadastro = st.selectbox("Selecione a Obra para o novo item", options=lista_obras_app, index=None, placeholder="Escolha a obra...")
    else:
        obra_para_cadastro = st.session_state.selected_obra

    if not obra_para_cadastro:
        st.warning("Selecione uma obra para iniciar o cadastro.")
        return

    with st.form("cadastro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome_produto = st.text_input("Nome do Produto*")
            num_tombamento_manual = st.text_input("N° de Tombamento (deixe em branco para gerar)")
            num_nota_fiscal = st.text_input("N° da Nota Fiscal*")
            valor_produto = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            status_selecionado = st.selectbox("Status do Item", options=lista_status, index=0)
        with col2:
            especificacoes = st.text_area("Especificações")
            observacoes = st.text_area("Observações")
            local_uso = st.text_input("Local de Uso*")
            responsavel = st.text_input("Responsável*")
    
        uploaded_pdf = st.file_uploader("Anexar PDF da Nota Fiscal", type="pdf")
        submitted = st.form_submit_button("Cadastrar Item")

        if submitted:
            if not (nome_produto and num_nota_fiscal and local_uso and responsavel):
                st.error("⚠️ Preencha todos os campos obrigatórios (*)")
                return

            input_limpo = num_tombamento_manual.strip() if num_tombamento_manual else ""
            num_tombamento_final = ""
            is_valid = False

            dados_obra_atual = existing_data[existing_data[OBRA_COL] == obra_para_cadastro]

            if input_limpo:
                coluna_limpa = dados_obra_atual[TOMBAMENTO_COL].astype(str).str.strip()
                if input_limpo in coluna_limpa.values:
                    st.error(f"Erro: O N° de Tombamento '{input_limpo}' já existe para esta obra.")
                else:
                    num_tombamento_final = input_limpo
                    is_valid = True
            else:
                num_tombamento_final = gerar_numero_tombamento_sequencial(existing_data, obra_para_cadastro)
                is_valid = True

            if is_valid:
                link_nota_fiscal = ""
                if uploaded_pdf:
                    file_name = f"NF_{num_tombamento_final}_{obra_para_cadastro.replace(' ', '_')}.pdf"
                    link_nota_fiscal = upload_to_supabase_storage(uploaded_pdf.getvalue(), file_name)
                    if not link_nota_fiscal:
                        st.error("Falha no upload da Nota Fiscal. O item não foi cadastrado.")
                        return

                novo_item_dict = {
                    OBRA_COL: obra_para_cadastro,
                    TOMBAMENTO_COL: num_tombamento_final,
                    NOME_COL: nome_produto,
                    ESPEC_COL: especificacoes,
                    OBS_COL: observacoes,
                    LOCAL_COL: local_uso,
                    RESPONSAVEL_COL: responsavel,
                    NF_NUM_COL: num_nota_fiscal,
                    NF_LINK_COL: link_nota_fiscal,
                    VALOR_COL: valor_produto,
                    STATUS_COL: status_selecionado
                }
                
                try:
                    conn.table("patrimonio").insert(novo_item_dict).execute()
                    
                    st.success(f"Item '{nome_produto}' cadastrado para a obra {obra_para_cadastro}! Tombamento: {num_tombamento_final}")
                    st.cache_data.clear() 
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no Supabase: {e}")

def pagina_itens_cadastrados(is_admin, dados_da_obra, lista_status):
    st.header("Itens Cadastrados", divider='rainbow')
    
    if dados_da_obra.empty:
        st.info("Nenhum item cadastrado para a obra selecionada ainda.")
        return

    dados_filtrados = dados_da_obra.copy()
    
    with st.expander("Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            status_unicos = ["Todos"] + sorted(list(dados_da_obra[STATUS_COL].unique()))
            filtro_status = st.selectbox("Filtrar por Status", status_unicos, key="filter_status")
            if filtro_status != "Todos":
                dados_filtrados = dados_filtrados[dados_filtrados[STATUS_COL] == filtro_status]
        
        with col_f2:
            search_term = st.text_input("Buscar por Nome, Tombamento ou Responsável", key="filter_search")
            if search_term:
                dados_filtrados = dados_filtrados[
                    dados_filtrados[NOME_COL].str.contains(search_term, case=False, na=False) |
                    dados_filtrados[TOMBAMENTO_COL].astype(str).str.contains(search_term, case=False, na=False) |
                    dados_filtrados[RESPONSAVEL_COL].str.contains(search_term, case=False, na=False)
                ]
        
        with col_f3:
            min_val = float(dados_da_obra[VALOR_COL].min()) if not dados_da_obra.empty else 0.0
            max_val = float(dados_da_obra[VALOR_COL].max()) if not dados_da_obra.empty else 0.0
            
            if min_val < max_val: 
                filtro_valor = st.slider("Filtrar por Valor (R$)", 
                                         min_value=min_val, 
                                         max_value=max_val, 
                                         value=(min_val, max_val),
                                         key="filter_valor")
                dados_filtrados = dados_filtrados[
                    (dados_filtrados[VALOR_COL] >= filtro_valor[0]) &
                    (dados_filtrados[VALOR_COL] <= filtro_valor[1])
                ]
    st.write("---")

    if not dados_filtrados.empty:
        st.dataframe(dados_filtrados, use_container_width=True, hide_index=True, column_config={
            ID_COL: None, 
            NF_LINK_COL: st.column_config.LinkColumn("Anexo PDF", display_text="🔗 Abrir Link")
        })
    else:
        st.info("Nenhum item encontrado com os filtros aplicados.")

def pagina_gerenciar_itens(dados_da_obra, existing_data_full, df_movimentacoes, lista_status):
    st.header("Gerenciar Itens Cadastrados", divider='rainbow')

    if dados_da_obra.empty:
        st.info("Nenhum item cadastrado para a obra selecionada ainda.")
        return

    dados_filtrados_gerenciar = dados_da_obra.copy()
    
    with st.expander("Filtros", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            status_unicos_ger = ["Todos"] + sorted(list(dados_da_obra[STATUS_COL].unique()))
            filtro_status_ger = st.selectbox("Filtrar por Status", status_unicos_ger, key="filter_status_ger")
            if filtro_status_ger != "Todos":
                dados_filtrados_gerenciar = dados_filtrados_gerenciar[dados_filtrados_gerenciar[STATUS_COL] == filtro_status_ger]
        
        with col_f2:
            search_term_ger = st.text_input("Buscar por Nome, Tombamento ou Responsável", key="filter_search_ger")
            if search_term_ger:
                dados_filtrados_gerenciar = dados_filtrados_gerenciar[
                    dados_filtrados_gerenciar[NOME_COL].str.contains(search_term_ger, case=False, na=False) |
                    dados_filtrados_gerenciar[TOMBAMENTO_COL].astype(str).str.contains(search_term_ger, case=False, na=False) |
                    dados_filtrados_gerenciar[RESPONSAVEL_COL].str.contains(search_term_ger, case=False, na=False)
                ]
    
    st.dataframe(dados_filtrados_gerenciar, use_container_width=True, hide_index=True, height=250)
    st.write("---")
 
    lista_itens = [f"{row[TOMBAMENTO_COL]} - {row[NOME_COL]} (ID: {row[ID_COL]})" for _, row in dados_filtrados_gerenciar.iterrows()]
    item_selecionado_gerenciar = st.selectbox("Selecione um item para Gerenciar", options=lista_itens, index=None, placeholder="Escolha um item...")

    if item_selecionado_gerenciar:
        item_id_selecionado = int(item_selecionado_gerenciar.split("(ID: ")[1].replace(")", ""))
        
        item_data_series = dados_filtrados_gerenciar[dados_filtrados_gerenciar[ID_COL] == item_id_selecionado].iloc[0]
        tombamento_selecionado = item_data_series[TOMBAMENTO_COL]
        obra_do_item = item_data_series[OBRA_COL]
        
        if not st.session_state.get('confirm_delete'):
            col_mov, col_edit, col_delete = st.columns(3)
            
            if col_mov.button("Registrar Entrada/Saída", use_container_width=True):
                st.session_state.movement_item_id = item_id_selecionado
                st.session_state.edit_item_id = None
                st.session_state.confirm_delete = False
                st.rerun()

            if col_edit.button("Editar Item", use_container_width=True):
                st.session_state.edit_item_id = item_id_selecionado
                st.session_state.movement_item_id = None
                st.session_state.confirm_delete = False
                st.rerun()
        else:
            col_delete = st.container() 

        if col_delete.button("Remover Item", use_container_width=True):
            st.session_state.edit_item_id = item_id_selecionado
            st.session_state.confirm_delete = True
            st.session_state.movement_item_id = None
            st.rerun()

        if st.session_state.confirm_delete and st.session_state.edit_item_id == item_id_selecionado:
            st.warning(f"**Atenção!** Tem certeza que deseja remover permanentemente o item **{tombamento_selecionado}** da obra **{obra_do_item}**?")
            c1_del, c2_del = st.columns(2)
            
            if c1_del.button("Sim, tenho certeza e quero remover", use_container_width=True, type="primary"):
                try:
                    conn.table("patrimonio").delete().eq(ID_COL, item_id_selecionado).execute()
                    
                    st.success(f"Item {tombamento_selecionado} da obra {obra_do_item} removido!")
                    st.session_state.confirm_delete = False
                    st.session_state.edit_item_id = None
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao remover item: {e}")

            if c2_del.button("Cancelar", use_container_width=True):
                st.session_state.confirm_delete = False
                st.session_state.edit_item_id = None
                st.rerun()
        
        if st.session_state.movement_item_id == item_id_selecionado:
            with st.form("movement_form"):
                st.subheader(f"Registrar Movimentação para: {item_selecionado_gerenciar}")
                tipo_mov = st.radio("Tipo de Movimentação", ["Entrada", "Saída"], horizontal=True)
                responsavel_mov = st.text_input("Responsável pela Movimentação*")
                obs_mov = st.text_area("Observações da Movimentação")
                submitted_mov = st.form_submit_button("Registrar Movimentação")
            
                if submitted_mov:
                    if not responsavel_mov:
                        st.warning("O campo 'Responsável pela Movimentação' é obrigatório.")
                    else:
                        nova_movimentacao = {
                            OBRA_COL: obra_do_item,
                            TOMBAMENTO_COL: tombamento_selecionado,
                            "tipo_movimentacao": tipo_mov,
                            "data_hora": datetime.now().isoformat(),
                            "responsavel_movimentacao": responsavel_mov,
                            OBS_COL: obs_mov
                        }
                        
                        novo_status = "Disponível" if tipo_mov == "Entrada" else "Em Uso Externo"
                        
                        try:
                            conn.table("movimentacoes").insert(nova_movimentacao).execute()
                            conn.table("patrimonio").update({STATUS_COL: novo_status}).eq(ID_COL, item_id_selecionado).execute()
                            
                            st.success("Movimentação registrada com sucesso!")
                            st.session_state.movement_item_id = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao registrar movimentação: {e}")
                        
        if st.session_state.edit_item_id == item_id_selecionado and not st.session_state.confirm_delete:
            
            with st.form("edit_form"):
                st.subheader(f"Editando Item: {tombamento_selecionado} (Obra: {obra_do_item})")
                
                tomb_edit_novo = st.text_input(f"{TOMBAMENTO_COL}", value=item_data_series.get(TOMBAMENTO_COL, ""))
                status_edit = st.selectbox(STATUS_COL, options=lista_status, index=lista_status.index(item_data_series.get(STATUS_COL)) if item_data_series.get(STATUS_COL) in lista_status else 0)
                nome_edit = st.text_input(NOME_COL, value=item_data_series.get(NOME_COL, ""))
                num_nota_fiscal_edit = st.text_input(f"{NF_NUM_COL}*", value=item_data_series.get(NF_NUM_COL, ""))
                especificacoes_edit = st.text_area(ESPEC_COL, value=item_data_series.get(ESPEC_COL, ""))
                observacoes_edit = st.text_area(OBS_COL, value=item_data_series.get(OBS_COL, ""))
                local_edit = st.text_input(LOCAL_COL, value=item_data_series.get(LOCAL_COL, ""))
                responsavel_edit = st.text_input(RESPONSAVEL_COL, value=item_data_series.get(RESPONSAVEL_COL, ""))
                valor_edit = st.number_input(f"{VALOR_COL} (R$)", min_value=0.0, format="%.2f", value=float(item_data_series.get(VALOR_COL, 0)))
                
                submitted_edit = st.form_submit_button("Salvar Alterações")
                
                if submitted_edit:
                    if not num_nota_fiscal_edit or not tomb_edit_novo:
                        st.warning(f"Os campos '{TOMBAMENTO_COL}' e '{NF_NUM_COL}*' são obrigatórios.")
                        return

                    edit_input_limpo = tomb_edit_novo.strip()
                    
                    condicao_outro_item = (existing_data_full[OBRA_COL] == obra_do_item) & \
                                          (existing_data_full[TOMBAMENTO_COL].astype(str).str.strip() == edit_input_limpo) & \
                                          (existing_data_full[ID_COL] != item_id_selecionado)
                    
                    if not existing_data_full[condicao_outro_item].empty:
                        st.error(f"Erro: O N° de Tombamento '{edit_input_limpo}' já existe para outro item nesta obra.")
                    else:
                        update_dict = {
                            TOMBAMENTO_COL: edit_input_limpo,
                            STATUS_COL: status_edit,
                            NOME_COL: nome_edit,
                            NF_NUM_COL: num_nota_fiscal_edit,
                            ESPEC_COL: especificacoes_edit,
                            OBS_COL: observacoes_edit,
                            LOCAL_COL: local_edit,
                            RESPONSAVEL_COL: responsavel_edit,
                            VALOR_COL: valor_edit
                        }
                        
                        try:
                            conn.table("patrimonio").update(update_dict).eq(ID_COL, item_id_selecionado).execute()
                            
                            st.success(f"Item {edit_input_limpo} atualizado com sucesso!")
                            st.session_state.edit_item_id = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar item: {e}")
                            
            
        st.write("---")
        st.subheader(f"Histórico de Movimentações do Item: {tombamento_selecionado}")
        historico_item = df_movimentacoes[
            (df_movimentacoes[OBRA_COL] == obra_do_item) &
            (df_movimentacoes[TOMBAMENTO_COL].astype(str) == str(tombamento_selecionado))
        ].sort_values(by="data_hora", ascending=False)
    
        if not historico_item.empty:
            st.dataframe(historico_item, hide_index=True, use_container_width=True, column_config={ID_COL: None})
        else:
            st.info("Nenhuma movimentação registrada para este item.")

def app_principal():
    is_admin = st.session_state.is_admin
    lista_status, lista_obras_app, existing_data_full, df_movimentacoes = carregar_dados_app()
    with st.sidebar:
        logo_path = "Lavie.png"
        try:
            st.image(logo_path, width=150)
        except Exception:
            pass

        st.header("Navegação")
        if is_admin:
            st.info("Logado como **Administrador**.")
        else:
            st.info(f"Obra: **{st.session_state.selected_obra}**")

        menu_options = ["Cadastrar Item", "Itens Cadastrados", "Gerenciar Itens", "Dashboard"]
        icons = ["plus-circle-fill", "card-list", "pencil-square", "bar-chart-fill"]
        
        selected_page = option_menu(
            menu_title=None,
            options=menu_options,
            icons=icons,
            menu_icon="cast",
            default_index=0,
        )

        st.write("---")
        
        if is_admin:
            obras_disponiveis = ["Todas"] + lista_obras_app
            obra_selecionada_sidebar = st.selectbox("Filtrar Visão por Obra", obras_disponiveis)
            
            st.write("---")
            st.header("Relatórios da Visão")
            st.info(f"Gerando para: **{obra_selecionada_sidebar}**")
            
            dados_relatorio = existing_data_full
            if obra_selecionada_sidebar != "Todas":
                dados_relatorio = existing_data_full[existing_data_full[OBRA_COL] == obra_selecionada_sidebar].copy()

            excel_data = to_excel(dados_relatorio)
            st.download_button(
                label="📥 Baixar Relatório (Excel)",
                data=excel_data,
                file_name=f"relatorio_patrimonio_{obra_selecionada_sidebar.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            pdf_data = to_pdf(dados_relatorio, obra_selecionada_sidebar)
            st.download_button(
                label="📄 Baixar Relatório (PDF)",
                data=pdf_data,
                file_name=f"relatorio_patrimonio_{obra_selecionada_sidebar.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.write("---")
        if st.button("Sair / Trocar Obra"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.cache_data.clear()
            st.rerun()
    
    
    

    if selected_page == "Cadastrar Item":
        pagina_cadastrar_item(is_admin, lista_status, lista_obras_app, existing_data_full)
    elif selected_page == "Itens Cadastrados":
        pagina_itens_cadastrados(is_admin, dados_da_obra, lista_status)
    elif selected_page == "Gerenciar Itens":
        pagina_gerenciar_itens(dados_da_obra, existing_data_full, df_movimentacoes, lista_status)
    elif selected_page == "Dashboard":
        pagina_dashboard(dados_da_obra, df_movimentacoes)

if not st.session_state.logged_in:
    tela_de_login()
else:
    app_principal()
