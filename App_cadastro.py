import streamlit as st
import pandas as pd
import random
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Cadastro de Patrimônio",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Sistema de Cadastro de Patrimônio")

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    existing_data = conn.read(worksheet="Página1", usecols=list(range(6)), ttl=5)
    existing_data = existing_data.dropna(how="all")
except Exception as e:
    st.error(f"Erro ao ler a planilha: {e}")
    existing_data = pd.DataFrame(columns=[
        "N° de Tombamento", "Nome", "Especificações", "Local de Uso / Responsável", 
        "N° da Nota Fiscal", "Valor"
    ])

def gerar_numero_tombamento():
    """Gera um número de tombamento aleatório e único entre 1 e 500."""
    numeros_existentes = existing_data["N° de Tombamento"].dropna().astype(int).tolist()
    
    if len(numeros_existentes) >= 500:
        return None

    numero_gerado = random.randint(1, 500)
    while numero_gerado in numeros_existentes:
        numero_gerado = random.randint(1, 500)
    
    return numero_gerado

st.header("Cadastrar Novo Item", divider='rainbow')

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
        if nome_produto and local_responsavel and num_nota_fiscal:
            novo_tombamento = gerar_numero_tombamento()
            
            if novo_tombamento is not None:
                novo_item_df = pd.DataFrame([{
                    "N° de Tombamento": novo_tombamento,
                    "Nome": nome_produto,
                    "Especificações": especificacoes,
                    "Local de Uso / Responsável": local_responsavel,
                    "N° da Nota Fiscal": num_nota_fiscal,
                    "Valor": valor_produto
                }])
                
                updated_df = pd.concat([existing_data, novo_item_df], ignore_index=True)

                conn.update(worksheet="cadastro", data=updated_df)
                
                st.success(f"✅ Item '{nome_produto}' cadastrado com sucesso! Tombamento: **{novo_tombamento}**")
            else:
                st.error("🚨 Todos os números de tombamento (1-500) já foram utilizados!")
        else:
            st.warning("⚠️ Por favor, preencha todos os campos obrigatórios.")

st.header("Itens Cadastrados", divider='rainbow')

if not existing_data.empty:
    st.dataframe(existing_data, use_container_width=True, hide_index=True)
    
    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df_to_csv(existing_data)
    st.download_button(
        label="📥 Baixar dados como CSV",
        data=csv,
        file_name='inventario_patrimonio.csv',
        mime='text/csv',
    )
else:

    st.info("Nenhum item cadastrado ainda.")
