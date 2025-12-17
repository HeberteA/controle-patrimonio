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

    COR_PRINCIPAL = "#E37026"

    if dados_da_obra.empty:
        st.info("Nenhum dado de patrimônio disponível para exibir no dashboard.")
        return

    dados_com_idade = dados_da_obra.copy()
    idade_media_dias = None

    if not df_movimentacoes.empty:
        df_movimentacoes['data_hora'] = pd.to_datetime(df_movimentacoes['data_hora'])
        entradas = df_movimentacoes[df_movimentacoes['tipo_movimentacao'] == 'Entrada']
        
        if not entradas.empty:
            aquisicoes = entradas.groupby(TOMBAMENTO_COL)['data_hora'].min().reset_index()
            aquisicoes.rename(columns={'data_hora': 'data_aquisicao'}, inplace=True)
            
            dados_com_idade = pd.merge(
                dados_com_idade, 
                aquisicoes, 
                on=TOMBAMENTO_COL, 
                how='left'
            )
            
            if 'data_aquisicao' in dados_com_idade.columns:
                agora_utc = datetime.now(datetime.timezone.utc)
                dados_com_idade['data_aquisicao'] = pd.to_datetime(dados_com_idade['data_aquisicao'], utc=True)
                
                dados_com_idade['idade_dias'] = (agora_utc - dados_com_idade['data_aquisicao']).dt.days
                idade_media_dias = dados_com_idade['idade_dias'].mean()

    st.subheader("Visão Geral do Patrimônio")
    total_itens = dados_da_obra.shape[0]
    valor_total = dados_da_obra[VALOR_COL].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Itens", f"{total_itens} un.")
    with col2:
        st.metric("Valor Total do Patrimônio", f"R$ {valor_total:,.2f}")
    with col3:
        if idade_media_dias is not None:
            st.metric("Idade Média dos Ativos", f"{idade_media_dias:,.0f} dias")
        else:
            st.metric("Idade Média dos Ativos", "N/A")
            
    st.write("---")

    st.subheader("Análise de Custo e Valor")
    col_v1, col_v2 = st.columns([1, 2])
    
    with col_v1:
        st.markdown("**Top 10 Ativos Mais Valiosos**")
        top_10_valiosos = dados_da_obra.sort_values(by=VALOR_COL, ascending=False).head(10)
        st.dataframe(
            top_10_valiosos[[NOME_COL, VALOR_COL, RESPONSAVEL_COL]], 
            use_container_width=True,
            column_config={
                VALOR_COL: st.column_config.NumberColumn(format="R$ %.2f")
            }
        )
    
    with col_v2:
        st.markdown("**Distribuição do Valor dos Ativos**")
        fig_hist_valor = px.histogram(
            dados_da_obra, 
            x=VALOR_COL, 
            nbins=50, 
            title="Histograma: Frequência de Itens por Faixa de Valor",
            text_auto=True
        )
        fig_hist_valor.update_traces(marker_color=COR_PRINCIPAL)
        fig_hist_valor.update_layout(yaxis_title="Contagem de Itens", xaxis_title="Valor (R$)")
        st.plotly_chart(fig_hist_valor, use_container_width=True)

    st.write("---")

    st.subheader("Análise de Aquisição e Operações ao Longo do Tempo")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("**Aquisição de Ativos ao Longo do Tempo**")
        if 'data_aquisicao' in dados_com_idade.columns and not dados_com_idade['data_aquisicao'].isnull().all():
            aquisicoes_no_tempo = dados_com_idade.set_index('data_aquisicao').resample('M')[VALOR_COL].sum().reset_index()
            aquisicoes_no_tempo = aquisicoes_no_tempo[aquisicoes_no_tempo[VALOR_COL] > 0]
            
            fig_aquisicao = px.line(
                aquisicoes_no_tempo, 
                x='data_aquisicao', 
                y=VALOR_COL, 
                title="Valor Adquirido por Mês",
                markers=True
            )
            fig_aquisicao.update_traces(line_color=COR_PRINCIPAL, marker_color=COR_PRINCIPAL)
            fig_aquisicao.update_layout(xaxis_title="Data da Aquisição", yaxis_title="Valor Adquirido (R$)")
            st.plotly_chart(fig_aquisicao, use_container_width=True)
        else:
            st.info("Não há dados de 'Entrada' suficientes na tabela de movimentações para gerar a análise de aquisição.")

    with col_t2:
        st.markdown("**Fluxo de Movimentações (Entrada vs. Saída)**")
        if not df_movimentacoes.empty:
            mov_no_tempo = df_movimentacoes.set_index('data_hora').groupby('tipo_movimentacao').resample('M').size().reset_index(name='contagem')
            
            color_map = {'Entrada': COR_PRINCIPAL, 'Saída': '#bec8c3'}
            
            fig_mov = px.line(
                mov_no_tempo,
                x='data_hora',
                y='contagem',
                color='tipo_movimentacao',
                color_discrete_map=color_map, 
                title="Movimentações por Mês",
                markers=True
            )
            fig_mov.update_layout(xaxis_title="Data da Movimentação", yaxis_title="Número de Movimentações")
            st.plotly_chart(fig_mov, use_container_width=True)
        else:
            st.info("Não há dados na tabela de movimentações.")
            
    st.write("---")
    
    st.subheader("Análise de Responsabilidade e Risco")
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.markdown("**Valor Total (R$) por Responsável**")
        valor_por_resp = dados_da_obra.groupby(RESPONSAVEL_COL)[VALOR_COL].sum().sort_values(ascending=False).reset_index()
        fig_resp_val = px.bar(
            valor_por_resp,
            x=RESPONSAVEL_COL,
            y=VALOR_COL,
            title="Valor de Ativos por Responsável",
            text_auto='.2s'
        )
        fig_resp_val.update_traces(marker_color=COR_PRINCIPAL, textposition='outside')
        st.plotly_chart(fig_resp_val, use_container_width=True)

    with col_r2:
        st.markdown("**Análise de Status dos Ativos**")
        if not dados_com_idade.empty:
            status_counts = dados_com_idade[STATUS_COL].value_counts().reset_index()
            fig_status = px.pie(
                status_counts, 
                names=STATUS_COL, 
                values='count', 
                title="Distribuição de Itens por Status",
                color_discrete_sequence=px.colors.sequential.Oranges_r 
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Não há dados de status para analisar.")

def pagina_cadastro(is_admin, lista_obras, lista_status):
    st.header("Novo Cadastro", divider='rainbow')
    
    tab_patrimonio, tab_locacao = st.tabs(["Patrimônio", "Locação"])

    with tab_patrimonio:
        st.markdown("### Registrar Novo Ativo")
        
        if is_admin:
            obra_para_cadastro = st.selectbox("Obra de Destino", options=lista_obras_app, key="patr_obra_sel")
        else:
            obra_para_cadastro = st.session_state.selected_obra

        if not obra_para_cadastro:
            st.info("Selecione uma obra acima para liberar o formulário.")
        else:
            with st.form("cadastro_patrimonio_form", clear_on_submit=True):
                p1_c1, p1_c2, p1_c3 = st.columns([3, 1.5, 1.5])
                with p1_c1:
                    nome_produto = st.text_input("Nome do Produto/Ativo")
                with p1_c2:
                    num_tombamento_manual = st.text_input("Tombamento (Opcional)")
                with p1_c3:
                    status_selecionado = st.selectbox("Status Inicial", options=lista_status, index=0)

                p2_c1, p2_c2, p2_c3, p2_c4 = st.columns([2, 2, 1.5, 1.5])
                with p2_c1:
                    local_uso = st.text_input("Local de Uso (Ex: Almoxarifado)")
                with p2_c2:
                    responsavel = st.text_input("Responsável Pelo Ativo")
                with p2_c3:
                    num_nota_fiscal = st.text_input("N° Nota Fiscal")
                with p2_c4:
                    valor_produto = st.number_input("Valor (R$)", min_value=0.0, step=100.00, format="%.2f")

                p3_c1, p3_c2 = st.columns(2)
                with p3_c1:
                    especificacoes = st.text_area("Especificações Técnicas", height=100)
                with p3_c2:
                    observacoes = st.text_area("Observações Gerais", height=100)
            
                st.write("---")
                uploaded_pdf = st.file_uploader("Anexar PDF da Nota Fiscal", type="pdf")
                
                submitted = st.form_submit_button("Cadastrar Patrimônio", type="primary", use_container_width=True)

                if submitted:
                    if not (nome_produto and num_nota_fiscal and local_uso and responsavel):
                        st.error("⚠️ Preencha os campos obrigatórios: Nome, NF, Local e Responsável.")
                    else:
                        link_nota_fiscal = ""
                        num_final_envio = num_tombamento_manual.strip() if num_tombamento_manual else None

                        if uploaded_pdf:
                            file_name = f"NF_{obra_para_cadastro}_{datetime.now().strftime('%H%M%S')}.pdf"
                            link_nota_fiscal = upload_to_supabase_storage(uploaded_pdf.getvalue(), file_name)

                        novo_item_dict = {
                            OBRA_COL: obra_para_cadastro,
                            TOMBAMENTO_COL: num_final_envio,
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
                            st.success(f"Patrimônio '{nome_produto}' cadastrado com sucesso!")
                            st.cache_data.clear() 
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    with tab_locacao:
        st.markdown("### Registrar Nova Locação")
        
        with st.form("cadastro_locacao_form", clear_on_submit=True):
            l1_c1, l1_c2, l1_c3, l1_c4 = st.columns([2, 2, 2, 1])
            with l1_c1:
                loc_equipamento = st.text_input("Equipamento")
            with l1_c2:
                if is_admin:
                    loc_obra = st.selectbox("Obra Destino", options=lista_obras_app, key="loc_obra_select")
                else:
                    loc_obra = st.text_input("Obra Destino", value=st.session_state.selected_obra, disabled=True)
                    if not loc_obra: loc_obra = st.session_state.selected_obra
            with l1_c3:
                loc_responsavel = st.text_input("Responsável (Rastreio)")
            with l1_c4:
                loc_qtd = st.number_input("Quantidade", min_value=1, value=1, step=1)

            l2_c1, l2_c2, l2_c3, l2_c4 = st.columns([1, 1.5, 1.5, 2])
            with l2_c1:
                loc_unidade = st.text_input("Unidade (Ex: Mês)")
            with l2_c2:
                loc_valor = st.number_input("Valor Unitário/Mensal (R$)", min_value=0.0, format="%.2f")
            with l2_c3:
                loc_contrato = st.text_input("Contrato/PC (Sienge)")
            with l2_c4:
                loc_status = st.selectbox("Status Inicial", [ "ATIVO", "MANUTENÇÃO", "DEVOLVIDO"])

            l3_c1, l3_c2 = st.columns(2)
            with l3_c1:
                loc_inicio = st.date_input("Data de Início da Cobrança", value=None)
            with l3_c2:
                loc_fim = st.date_input("Previsão Fim da Locação", value=None)

            st.write("")
            submitted_loc = st.form_submit_button("Adicionar Locação", type="primary", use_container_width=True)

            if submitted_loc:
                if not (loc_equipamento and loc_obra):
                    st.error("Campos 'Equipamento' e 'Obra' são obrigatórios.")
                else:
                    nova_locacao = {
                        "equipamento": loc_equipamento,
                        "obra_destino": loc_obra if is_admin else st.session_state.selected_obra,
                        "responsavel": loc_responsavel,
                        "quantidade": loc_qtd,
                        "unidade": loc_unidade,
                        "valor_mensal": loc_valor,
                        "contrato_sienge": loc_contrato,
                        "status": loc_status,
                        "data_inicio": loc_inicio.isoformat() if loc_inicio else None,
                        "data_previsao_fim": loc_fim.isoformat() if loc_fim else None
                    }
                    try:
                        conn.table("locacoes").insert(nova_locacao).execute()
                        st.success(f"Locação de '{loc_equipamento}' registrada!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar locação: {e}")

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
