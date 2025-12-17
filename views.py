# views.py
import streamlit as st
import pandas as pd
import time
import base64
import plotly.express as px
from datetime import datetime
import database as db
import utils

@st.dialog("Editar Patrimônio")
def modal_editar_patrimonio(item, lista_status):
    with st.form("edit_patr"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome", value=item[db.NOME_COL])
        status = c2.selectbox("Status", lista_status, index=lista_status.index(item[db.STATUS_COL]) if item[db.STATUS_COL] in lista_status else 0)
        
        if st.form_submit_button("Salvar"):
            conn = db.get_db_connection()
            conn.table("patrimonio").update({
                db.NOME_COL: nome,
                db.STATUS_COL: status
            }).eq(db.ID_COL, int(item[db.ID_COL])).execute()
            st.success("Salvo!")
            time.sleep(1)
            st.rerun()

def pagina_dashboard(df_patr, df_mov):
    st.header("Análise de Ativos", divider='orange')
    if df_patr.empty:
        st.info("Sem dados.")
        return
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Itens", len(df_patr))
    c2.metric("Valor Total", f"R$ {df_patr[db.VALOR_COL].sum():,.2f}")
    
    fig = px.histogram(df_patr, x=db.VALOR_COL, nbins=30, title="Distribuição de Valor")
    fig.update_traces(marker_color="#E37026")
    st.plotly_chart(fig, use_container_width=True)

def pagina_cadastro(is_admin, lista_obras, lista_status):
    st.header("Novo Cadastro", divider='orange')

def pagina_inventario_unificado(is_admin, df_patrimonio, lista_status):
    st.header("Inventário & Gerenciamento", divider="orange")
    
    modo_visualizacao = st.radio("Modo de Visualização", ["Tabela (Gerencial)", "Cards (Visual)"], horizontal=True)
    
    c1, c2 = st.columns([2, 1])
    busca = c1.text_input("Buscar Item", placeholder="Nome, Tombamento...")
    filtro_status = c2.selectbox("Filtrar Status", ["Todos"] + lista_status)
    
    df_filt = df_patrimonio.copy()
    if busca:
        df_filt = df_filt[df_filt[db.NOME_COL].str.contains(busca, case=False, na=False)]
    if filtro_status != "Todos":
        df_filt = df_filt[df_filt[db.STATUS_COL] == filtro_status]

    if modo_visualizacao == "Tabela (Gerencial)":
        st.dataframe(df_filt, use_container_width=True, hide_index=True)
        
        st.write("---")
        col_exp1, col_exp2 = st.columns(2)
        if col_exp1.button("Baixar Excel"):
            xls = utils.gerar_excel(df_filt, "Inventario")
            st.download_button("Download .xlsx", xls, "inventario.xlsx")
            
        item_opts = df_filt.apply(lambda x: f"{x[db.TOMBAMENTO_COL]} - {x[db.NOME_COL]}", axis=1).tolist()
        sel = st.selectbox("Selecionar Item para Ação:", item_opts, index=None)
        
        if sel:
            tomb = sel.split(" - ")[0]
            row = df_filt[df_filt[db.TOMBAMENTO_COL].astype(str) == tomb].iloc[0]
            if st.button(f"Editar {row[db.NOME_COL]}", type="primary"):
                modal_editar_patrimonio(row, lista_status)

    else:
        for idx, row in df_filt.iterrows():
            with st.container(border=True):
                c_img, c_info, c_act = st.columns([1, 4, 1])
                with c_info:
                    st.markdown(f"### {row[db.NOME_COL]}")
                    st.caption(f"Tombamento: {row[db.TOMBAMENTO_COL]} | Local: {row[db.LOCAL_COL]}")
                    st.write(f"**Status:** {row[db.STATUS_COL]} | **Valor:** R$ {row[db.VALOR_COL]:,.2f}")
                with c_act:
                    if st.button("Editar", key=f"btn_{row[db.ID_COL]}"):
                        modal_editar_patrimonio(row, lista_status)
