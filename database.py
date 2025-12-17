import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

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

def get_db_connection():
    try:
        return st.connection(
            "supabase",
            type=SupabaseConnection,
            url=st.secrets["connections"]["supabase"]["url"],
            key=st.secrets["connections"]["supabase"]["key"]
        )
    except Exception as e:
        st.error("Erro na conexão com Supabase.")
        st.stop()

def upload_to_storage(file_data, file_name, file_type='application/pdf'):
    conn = get_db_connection()
    try:
        bucket_name = "notas-fiscais"
        conn.storage.from_(bucket_name).upload(
            file=file_data,
            path=file_name,
            file_options={"content-type": file_type, "x-upsert": "true"}
        )
        return conn.storage.from_(bucket_name).get_public_url(file_name)
    except Exception as e:
        st.error(f"Erro no upload: {e}")
        return None

@st.cache_data(ttl=30)
def carregar_dados():
    conn = get_db_connection()
    try:
        status_resp = conn.table("status").select("*").execute()
        lista_status = [row['nome_do_status'] for row in status_resp.data]
        
        obras_resp = conn.table("obras").select("*").execute()
        lista_obras = [row['nome_da_obra'] for row in obras_resp.data]
        
        patrimonio_resp = conn.table("patrimonio").select("*").execute()
        df_patrimonio = pd.DataFrame(patrimonio_resp.data)
        
        if df_patrimonio.empty:
            cols = [ID_COL, OBRA_COL, TOMBAMENTO_COL, NOME_COL, ESPEC_COL, OBS_COL, 
                    LOCAL_COL, RESPONSAVEL_COL, NF_NUM_COL, NF_LINK_COL, VALOR_COL, STATUS_COL]
            df_patrimonio = pd.DataFrame(columns=cols)
        
        if VALOR_COL in df_patrimonio.columns:
            df_patrimonio[VALOR_COL] = pd.to_numeric(df_patrimonio[VALOR_COL], errors='coerce').fillna(0)
            
        mov_resp = conn.table("movimentacoes").select("*").execute()
        df_mov = pd.DataFrame(mov_resp.data)
        if df_mov.empty:
            df_mov = pd.DataFrame(columns=[ID_COL, OBRA_COL, TOMBAMENTO_COL, "tipo_movimentacao", "data_hora"])

        loc_resp = conn.table("locacoes").select("*").execute()
        df_loc = pd.DataFrame(loc_resp.data)
        
        colunas_loc = ["id", "equipamento", "obra_destino", "responsavel", "quantidade", 
                       "unidade", "valor_mensal", "contrato_sienge", "status", "data_inicio", "data_previsao_fim"]
        
        if df_loc.empty:
            df_loc = pd.DataFrame(columns=colunas_loc)
        else:
            for col in ['data_inicio', 'data_previsao_fim']:
                if col in df_loc.columns:
                    df_loc[col] = pd.to_datetime(df_loc[col], errors='coerce')

        return lista_status, lista_obras, df_patrimonio, df_mov, df_loc
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return [], [], pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
