import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

ID_COL = "id"
OBRA_COL = "obra"
TOMBAMENTO_COL = "numero_tombamento"
NOME_COL = "nome"
STATUS_COL = "status"
NF_NUM_COL = "numero_nota_fiscal"
NF_LINK_COL = "link_nota_fiscal"
ESPEC_COL = "especificacoes"
OBS_COL = "observacoes"
LOCAL_COL = "local_de_uso"
RESPONSAVEL_COL = "responsavel"
VALOR_COL = "valor"
FOTO_COL = "foto_item"

def get_db_connection():
    try:
        return st.connection(
            "supabase",
            type=SupabaseConnection,
            url=st.secrets["connections"]["supabase"]["url"],
            key=st.secrets["connections"]["supabase"]["key"]
        )
    except Exception as e:
        st.error("ERRO GRAVE NA CONEXÃO COM O SUPABASE. Verifique os secrets.")
        st.stop()

def upload_nota_fiscal(file_data, file_name):
    conn = get_db_connection()
    try:
        bucket_name = "notas-fiscais"
        conn.storage.from_(bucket_name).upload(
            file=file_data,
            path=file_name,
            file_options={"content-type": "application/pdf", "x-upsert": "true"}
        )
        return conn.storage.from_(bucket_name).get_public_url(file_name)
    except Exception as e:
        st.error(f"Erro no upload da NF: {e}")
        return None

def upload_foto_patrimonio(file_data, file_name, file_type):
    conn = get_db_connection()
    try:
        bucket_name = "fotos-patrimonio"
        conn.storage.from_(bucket_name).upload(
            file=file_data,
            path=file_name,
            file_options={"content-type": file_type, "x-upsert": "true"}
        )
        return conn.storage.from_(bucket_name).get_public_url(file_name)
    except Exception as e:
        st.error(f"Erro no upload da Foto: {e}")
        return None

@st.cache_data(ttl=30) 
def carregar_dados_app():
    conn = get_db_connection()
    try:
        status_resp = conn.table("status").select("*").execute()
        lista_status = [row['nome_do_status'] for row in status_resp.data]
        
        obras_resp = conn.table("obras").select("*").execute()
        lista_obras = [row['nome_da_obra'] for row in obras_resp.data]
        
        patrimonio_resp = conn.table("patrimonio").select("*").execute()
        patrimonio_df = pd.DataFrame(patrimonio_resp.data)
        
        colunas_patrimonio = [
            ID_COL, OBRA_COL, TOMBAMENTO_COL, NOME_COL, ESPEC_COL, 
            OBS_COL, LOCAL_COL, RESPONSAVEL_COL, NF_NUM_COL, 
            NF_LINK_COL, VALOR_COL, STATUS_COL, FOTO_COL
        ]

        if patrimonio_df.empty: 
             patrimonio_df = pd.DataFrame(columns=colunas_patrimonio)
        
        for col in colunas_patrimonio:
            if col not in patrimonio_df.columns:
                patrimonio_df[col] = None
        
        if VALOR_COL in patrimonio_df.columns:
            patrimonio_df[VALOR_COL] = pd.to_numeric(patrimonio_df[VALOR_COL], errors='coerce').fillna(0)
        
        movimentacoes_resp = conn.table("movimentacoes").select("*").execute()
        movimentacoes_df = pd.DataFrame(movimentacoes_resp.data)
        if movimentacoes_df.empty:
            movimentacoes_df = pd.DataFrame(columns=[
                ID_COL, OBRA_COL, TOMBAMENTO_COL, "tipo_movimentacao", 
                "data_hora", "responsavel_movimentacao", "observacoes"
            ])
            
        locacoes_resp = conn.table("locacoes").select("*").execute()
        locacoes_df = pd.DataFrame(locacoes_resp.data)
        if locacoes_df.empty:
            locacoes_df = pd.DataFrame(columns=[
                "id", "equipamento", "obra_destino", "responsavel", "quantidade", 
                "unidade", "valor_mensal", "contrato_sienge", "status", 
                "data_inicio", "data_previsao_fim"
            ])
        else:
            locacoes_df['data_inicio'] = pd.to_datetime(locacoes_df['data_inicio'], errors='coerce')
            locacoes_df['data_previsao_fim'] = pd.to_datetime(locacoes_df['data_previsao_fim'], errors='coerce')

        return lista_status, lista_obras, patrimonio_df, movimentacoes_df, locacoes_df
    
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return [], [], pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
