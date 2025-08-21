import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Cadastro de Patrimônio",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Sistema de Cadastro de Patrimônio")
st.markdown("Aplicação para registrar novos itens, com armazenamento de dados no Google Sheets.")
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=5)
def carregar_dados():
    try:
        obras_df = conn.read(worksheet="Obras", usecols=[0], header=0)
        lista_obras = obras_df["Nome da Obra"].dropna().tolist()

        patrimonio_df = conn.read(worksheet="Página1", usecols=list(range(7))) 
        patrimonio_df = patrimonio_df.dropna(how="all")
        
        return lista_obras, patrimonio_df

    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return [], pd.DataFrame(columns=[
            "Obra", "N° de Tombamento", "Nome", "Especificações", 
            "Local de Uso / Responsável", "N° da Nota Fiscal", "Valor"
        ])

lista_obras, existing_data = carregar_dados()


def gerar_numero_tombamento():
    """Gera um número de tombamento aleatório e único entre 1 e 500."""
    if "N° de Tombamento" not in existing_data.columns:
        return random.randint(1, 500)
        
    numeros_existentes = existing_data["N° de Tombamento"].dropna().astype(int).tolist()
    
    if len(numeros_existentes) >= 500:
        return None

    numero_gerado = random.randint(1, 500)
    while numero_gerado in numeros_existentes:
        numero_gerado = random.randint(1, 500)
    
    return numero_gerado

st.header("Cadastrar Novo Item", divider='rainbow')

if lista_obras:
    obra_selecionada = st.selectbox(
        "Selecione a Obra",
        options=lista_obras,
        index=None, 
        placeholder="Escolha a obra para cadastrar o item"
    )
else:
    st.warning("Nenhuma obra encontrada na planilha. Verifique a aba 'Obras'.")
    obra_selecionada = None 

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
        if obra_selecionada and nome_produto and local_responsavel and num_nota_fiscal:
            novo_tombamento = gerar_numero_tombamento()
            
            if novo_tombamento is not None:
                novo_item_df = pd.DataFrame([{
                    "Obra": obra_selecionada, 
                    "N° de Tombamento": novo_tombamento,
                    "Nome": nome_produto,
                    "Especificações": especificacoes,
                    "Local de Uso / Responsável": local_responsavel,
                    "N° da Nota Fiscal": num_nota_fiscal,
                    "Valor": valor_produto
                }])
                
                updated_df = pd.concat([existing_data, novo_item_df], ignore_index=True)

                conn.update(worksheet="Página1", data=updated_df)
                
                st.success(f"✅ Item '{nome_produto}' cadastrado com sucesso na obra '{obra_selecionada}'! Tombamento: **{novo_tombamento}**")
                
                st.cache_data.clear()

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
    
    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df_to_csv(dados_filtrados)
    st.download_button(
        label="📥 Baixar dados filtrados como CSV",
        data=csv,
        file_name=f'inventario_{filtro_obra.lower().replace(" ", "_")}.csv',
        mime='text/csv',
    )
else:
    st.info("Nenhum item cadastrado ainda.")