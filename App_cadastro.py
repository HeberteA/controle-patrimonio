import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Cadastro de Patrimônio",
    page_icon="📦",
    layout="wide"
)

if 'edit_item_id' not in st.session_state:
    st.session_state.edit_item_id = None
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False

st.title("📦 Sistema de Cadastro de Patrimônio")
st.markdown("Aplicação para registrar novos itens.")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        obras_df = conn.read(worksheet="Obras", usecols=[0], header=0)
        lista_obras = obras_df["Nome da Obra"].dropna().tolist()

        patrimonio_df = conn.read(worksheet="Página1", usecols=list(range(7)))
        patrimonio_df = patrimonio_df.dropna(how="all")
        
        if "N° de Tombamento" in patrimonio_df.columns:
            patrimonio_df["N° de Tombamento"] = patrimonio_df["N° de Tombamento"].astype(str)

        return lista_obras, patrimonio_df

    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return [], pd.DataFrame(columns=[
            "Obra", "N° de Tombamento", "Nome", "Especificações", 
            "Local de Uso / Responsável", "N° da Nota Fiscal", "Valor"
        ])

lista_obras, existing_data = carregar_dados()

def gerar_numero_tombamento():
    if "N° de Tombamento" not in existing_data.columns or existing_data.empty:
        return str(random.randint(1, 500))
    numeros_numericos = pd.to_numeric(existing_data["N° de Tombamento"], errors='coerce')
    
    numeros_existentes = numeros_numericos.dropna().astype(int).tolist()
    
    if len(numeros_existentes) >= 500:
        return None

    numero_gerado = random.randint(1, 500)
    while numero_gerado in numeros_existentes:
        numero_gerado = random.randint(1, 500)
    
    return str(numero_gerado)

st.header("Cadastrar Novo Item", divider='rainbow')

if lista_obras:
    obra_selecionada_cadastro = st.selectbox(
        "Selecione a Obra para o novo item",
        options=lista_obras,
        index=None,
        placeholder="Escolha a obra para cadastrar o item",
        key="sb_obra_cadastro"
    )
else:
    st.warning("Nenhuma obra encontrada na planilha. Verifique a aba 'Obras'.")
    obra_selecionada_cadastro = None

with st.form("cadastro_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        nome_produto = st.text_input("Nome do Produto", placeholder="Ex: Cadeira de Escritório")
        num_nota_fiscal = st.text_input("N° da Nota Fiscal", placeholder="Ex: 001234")
        valor_produto = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
    with col2:
        especificacoes = st.text_area("Especificações", placeholder="Ex: Cor preta, material de couro, giratória")
        local_responsavel = st.text_input("Local de Uso / Responsável", placeholder="Ex: Sala de Reuniões / João Silva")

    submitted = st.form_submit_button("✔️ Cadastrar Item")

    if submitted:
        if obra_selecionada_cadastro and nome_produto and local_responsavel and num_nota_fiscal:
            novo_tombamento = gerar_numero_tombamento()
            
            if novo_tombamento is not None:
                novo_item_df = pd.DataFrame([{
                    "Obra": obra_selecionada_cadastro,
                    "N° de Tombamento": novo_tombamento,
                    "Nome": nome_produto,
                    "Especificações": especificacoes,
                    "Local de Uso / Responsável": local_responsavel,
                    "N° da Nota Fiscal": num_nota_fiscal,
                    "Valor": valor_produto
                }])
                
                updated_df = pd.concat([existing_data, novo_item_df], ignore_index=True)
                conn.update(worksheet="Página1", data=updated_df)
                
                st.success(f"✅ Item '{nome_produto}' cadastrado com sucesso! Tombamento: **{novo_tombamento}**")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("🚨 Todos os números de tombamento (1-500) já foram utilizados!")
        else:
            st.warning("⚠️ Por favor, selecione uma obra e preencha todos os campos obrigatórios.")

st.header("Itens Cadastrados", divider='rainbow')

if not existing_data.empty:
    obras_para_filtrar = ["Todas"] + sorted(existing_data["Obra"].unique().tolist())
    filtro_obra = st.selectbox("Filtrar por Obra", options=obras_para_filtrar)

    if filtro_obra == "Todas":
        dados_filtrados = existing_data
    else:
        dados_filtrados = existing_data[existing_data["Obra"] == filtro_obra]
    
    st.dataframe(dados_filtrados, use_container_width=True, hide_index=True)
    
else:
    st.info("Nenhum item cadastrado ainda.")

st.header("Gerenciar Itens Cadastrados", divider='rainbow')

if not existing_data.empty:
    lista_itens = [f"{row['N° de Tombamento']} - {row['Nome']}" for index, row in existing_data.iterrows()]
    
    item_selecionado_gerenciar = st.selectbox(
        "Selecione um item para Editar ou Remover",
        options=lista_itens,
        index=None,
        placeholder="Escolha um item..."
    )

    if item_selecionado_gerenciar:
        tombamento_selecionado = item_selecionado_gerenciar.split(" - ")[0]
        
        col_edit, col_delete = st.columns(2)

        if col_edit.button("✏️ Editar Item Selecionado", use_container_width=True):
            st.session_state.edit_item_id = tombamento_selecionado
            st.session_state.confirm_delete = False
            st.rerun()

        if col_delete.button("🗑️ Remover Item Selecionado", use_container_width=True):
            st.session_state.confirm_delete = True
            st.session_state.edit_item_id = tombamento_selecionado

        if st.session_state.confirm_delete:
            st.warning(f"**Atenção!** Você tem certeza que deseja remover o item **{st.session_state.edit_item_id}**? Esta ação não pode ser desfeita.")
            if st.button("Sim, tenho certeza e quero remover"):
                df_sem_item = existing_data[existing_data["N° de Tombamento"] != st.session_state.edit_item_id]
                conn.update(worksheet="Página1", data=df_sem_item)
                st.success(f"Item {st.session_state.edit_item_id} removido com sucesso!")
                st.session_state.confirm_delete = False
                st.session_state.edit_item_id = None
                st.cache_data.clear()
                st.rerun()

if st.session_state.edit_item_id and not st.session_state.confirm_delete:
    st.subheader(f"Editando Item: {st.session_state.edit_item_id}")

    item_data = existing_data[existing_data["N° de Tombamento"] == st.session_state.edit_item_id].iloc[0]

    with st.form("edit_form"):
        obra_edit = st.selectbox("Obra", options=lista_obras, index=lista_obras.index(item_data["Obra"]))
        nome_edit = st.text_input("Nome do Produto", value=item_data["Nome"])
        especificacoes_edit = st.text_area("Especificações", value=item_data["Especificações"])
        local_edit = st.text_input("Local de Uso / Responsável", value=item_data["Local de Uso / Responsável"])
        nota_fiscal_edit = st.text_input("N° da Nota Fiscal", value=item_data["N° da Nota Fiscal"])
        valor_edit = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=float(item_data["Valor"]))
        
        submitted_edit = st.form_submit_button("💾 Salvar Alterações")

        if submitted_edit:
            idx_to_update = existing_data.index[existing_data["N° de Tombamento"] == st.session_state.edit_item_id].tolist()[0]
            
            existing_data.loc[idx_to_update, "Obra"] = obra_edit
            existing_data.loc[idx_to_update, "Nome"] = nome_edit
            existing_data.loc[idx_to_update, "Especificações"] = especificacoes_edit
            existing_data.loc[idx_to_update, "Local de Uso / Responsável"] = local_edit
            existing_data.loc[idx_to_update, "N° da Nota Fiscal"] = nota_fiscal_edit
            existing_data.loc[idx_to_update, "Valor"] = valor_edit
            
            conn.update(worksheet="Página1", data=existing_data)
            
            st.success(f"Item {st.session_state.edit_item_id} atualizado com sucesso!")
            
            st.session_state.edit_item_id = None
            st.cache_data.clear()

            st.rerun()
