import streamlit as st
import pandas as pd
import time
import base64
import textwrap
import plotly.express as px
from datetime import datetime
from streamlit_option_menu import option_menu
import database as db
import utils

@st.dialog("Editar Patrimônio")
def modal_editar_patrimonio(item_series, lista_status):
    st.write(f"Editando: **{item_series[db.NOME_COL]}**")
    with st.form("form_edit_patr_modal"):
        c1, c2 = st.columns(2)
        with c1:
            novo_nome = st.text_input("Nome", value=item_series[db.NOME_COL])
            novo_tombamento = st.text_input("Tombamento", value=item_series[db.TOMBAMENTO_COL])
            novo_valor = st.number_input("Valor (R$)", value=float(item_series[db.VALOR_COL]) if item_series[db.VALOR_COL] else 0.0, format="%.2f")
        with c2:
            idx_status = lista_status.index(item_series[db.STATUS_COL]) if item_series[db.STATUS_COL] in lista_status else 0
            novo_status = st.selectbox("Status", options=lista_status, index=idx_status)
            novo_local = st.text_input("Local", value=item_series[db.LOCAL_COL])
            novo_resp = st.text_input("Responsável", value=item_series[db.RESPONSAVEL_COL])
            
        nova_nf = st.text_input("Nota Fiscal (N°)", value=item_series[db.NF_NUM_COL])
        novas_specs = st.text_area("Especificações", value=item_series[db.ESPEC_COL])
        novas_obs = st.text_area("Observações", value=item_series[db.OBS_COL])
        if item_series.get(db.FOTO_COL):
            st.image(item_series[db.FOTO_COL], width=200, caption="Foto Atual")
        
        nova_foto_file = st.file_uploader("Substituir Foto", type=["jpg", "png"])
        st.write("---")
        
        if st.form_submit_button("Salvar"):
            try:
                conn = db.get_db_connection()
                conn.table("patrimonio").update({
                    db.NOME_COL: novo_nome,
                    db.TOMBAMENTO_COL: novo_tombamento,
                    db.VALOR_COL: novo_valor,
                    db.STATUS_COL: novo_status,
                    db.LOCAL_COL: novo_local,
                    db.RESPONSAVEL_COL: novo_resp,
                    db.NF_NUM_COL: nova_nf,
                    db.ESPEC_COL: novas_specs,
                    db.OBS_COL: novas_obs
                }).eq(db.ID_COL, int(item_series[db.ID_COL])).execute()
                if nova_foto_file:
                    img_name = f"EDIT_{int(item_series[db.ID_COL])}_{datetime.now().strftime('%H%M%S')}.jpg"
                    url_foto = db.upload_to_storage(
                        nova_foto_file.getvalue(), 
                        img_name, 
                        bucket_name="fotos-patrimonio",
                        file_type=nova_foto_file.type
                    )
                    update_dict[db.FOTO_COL] = url_foto

                conn.table("patrimonio").update(update_dict).eq(db.ID_COL, int(item_series[db.ID_COL])).execute()
                st.success("Patrimônio atualizado!")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")

@st.dialog("Editar Locação")
def modal_editar_locacao(row, lista_obras):
    st.write(f"Gerenciando Locação: **{row['equipamento']}**")
    def parse_date(date_str):
        if not date_str or pd.isna(date_str): return None
        try: return pd.to_datetime(date_str).date()
        except: return None

    dt_inicio_val = parse_date(row['data_inicio'])
    dt_fim_val = parse_date(row['data_previsao_fim'])

    with st.form("form_edit_loc_modal"):
        l1, l2 = st.columns(2)
        with l1:
            n_equip = st.text_input("Equipamento", value=row['equipamento'])
            n_contrato = st.text_input("Contrato Sienge", value=row['contrato_sienge'])
            n_valor = st.number_input("Valor Mensal", value=float(row['valor_mensal']) if row['valor_mensal'] else 0.0, format="%.2f")
        with l2:
            n_resp = st.text_input("Responsável", value=row['responsavel'])
            opcoes_status_loc = ["ATIVO", "MANUTENÇÃO", "DEVOLVIDO"]
            idx_st_loc = opcoes_status_loc.index(row['status']) if row['status'] in opcoes_status_loc else 0
            n_status = st.selectbox("Status", opcoes_status_loc, index=idx_st_loc)
            idx_obra = lista_obras.index(row['obra_destino']) if row['obra_destino'] in lista_obras else 0
            n_obra = st.selectbox("Obra Destino", options=lista_obras, index=idx_obra)

        d1, d2 = st.columns(2)
        with d1: n_inicio = st.date_input("Início", value=dt_inicio_val)
        with d2: n_fim = st.date_input("Previsão Fim", value=dt_fim_val)
        
        st.write("---")
        if st.form_submit_button("Salvar Edição", type="primary", use_container_width=True):
            conn = db.get_db_connection()
            conn.table("locacoes").update({
                "equipamento": n_equip, "contrato_sienge": n_contrato,
                "valor_mensal": n_valor, "responsavel": n_resp, "status": n_status,
                "obra_destino": n_obra, "data_inicio": n_inicio.isoformat() if n_inicio else None,
                "data_previsao_fim": n_fim.isoformat() if n_fim else None
            }).eq("id", int(row['id'])).execute()
            st.success("Locação salva!")
            time.sleep(1)
            st.cache_data.clear()
            st.rerun()

@st.dialog("Registrar Nova Movimentação")
def form_movimentacoes():
    with st.form("form_movimentacao"):
        tipo = st.radio("Tipo", ["Entrada", "Saída"], horizontal=True)
        resp = st.text_input("Responsável pela Movimentação")
        obs = st.text_area("Observações")
        if st.form_submit_button("Salvar Movimentação", type="primary"):
            conn = db.get_db_connection()
            conn.table("movimentacoes").insert({
                db.OBRA_COL: row_sel[db.OBRA_COL], db.TOMBAMENTO_COL: row_sel[db.TOMBAMENTO_COL],
                "tipo_movimentacao": tipo, "data_hora": datetime.now().isoformat(),
                "responsavel_movimentacao": resp, db.OBS_COL: obs
            }).execute()
            novo_st = "ATIVO" if tipo == "Entrada" else "EMPRÉSTIMO"
            conn.table("patrimonio").update({db.STATUS_COL: novo_st}).eq(db.ID_COL, int(row_sel[db.ID_COL])).execute()
            st.success("Movimentação registrada com sucesso!")
            time.sleep(1.5)
            st.rerun()

def pagina_dashboard(df_patr, df_mov):
    st.header("Dashboard de Inteligência de Ativos", divider='orange')
    
    if df_patr.empty:
        st.info("Nenhum dado de patrimônio disponível para exibir no dashboard.")
        return

    COR_PRINCIPAL = "#E37026"
    LAYOUT_CLEAN = dict(
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',   
        font=dict(color="#FAFAFA"),     
        margin=dict(t=30, l=10, r=10, b=10)
    )
    
    dados_com_idade = df_patr.copy()
    idade_media_dias = None

    if not df_mov.empty:
        df_mov['data_hora'] = pd.to_datetime(df_mov['data_hora'])
        entradas = df_mov[df_mov['tipo_movimentacao'] == 'Entrada']
        if not entradas.empty:
            aquisicoes = entradas.groupby(db.TOMBAMENTO_COL)['data_hora'].min().reset_index()
            aquisicoes.rename(columns={'data_hora': 'data_aquisicao'}, inplace=True)
            dados_com_idade = pd.merge(dados_com_idade, aquisicoes, on=db.TOMBAMENTO_COL, how='left')
            if 'data_aquisicao' in dados_com_idade.columns:
                agora_utc = datetime.now(datetime.timezone.utc)
                dados_com_idade['data_aquisicao'] = pd.to_datetime(dados_com_idade['data_aquisicao'], utc=True)
                dados_com_idade['idade_dias'] = (agora_utc - dados_com_idade['data_aquisicao']).dt.days
                idade_media_dias = dados_com_idade['idade_dias'].mean()

    st.subheader("Visão Geral Executiva")
    total_itens = df_patr.shape[0]
    valor_total = df_patr[db.VALOR_COL].sum()
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1: st.metric("Total de Itens", f"{total_itens} un.")
    with kpi2: st.metric("Valor Patrimonial", f"R$ {valor_total:,.2f}")
    with kpi3: st.metric("Idade Média", f"{idade_media_dias:,.0f} dias" if idade_media_dias else "N/A")
    with kpi4:
        df_manut = df_patr[df_patr[db.STATUS_COL] == 'MANUTENÇÃO']
        valor_manut = df_manut[db.VALOR_COL].sum()
        perc_manut = (valor_manut / valor_total) * 100 if valor_total > 0 else 0
        st.metric("Em Manutenção", f"R$ {valor_manut:,.2f}", f"{perc_manut:.1f}%", delta_color="inverse")
            
    st.write("---")

    st.subheader("Estratégia e Priorização")
    
    df_abc = df_patr.copy()
    df_abc = df_abc.sort_values(by=db.VALOR_COL, ascending=False)
    df_abc['valor_acumulado'] = df_abc[db.VALOR_COL].cumsum()
    df_abc['perc_acumulado'] = df_abc['valor_acumulado'] / df_abc[db.VALOR_COL].sum()
    
    def classificar_abc(perc):
        if perc <= 0.8: return 'A (Crítico - 80%)'
        elif perc <= 0.95: return 'B (Médio - 15%)'
        else: return 'C (Baixo - 5%)'
    
    df_abc['Classe ABC'] = df_abc['perc_acumulado'].apply(classificar_abc)

    col_intel1, col_intel2 = st.columns([1.5, 1])

    with col_intel1:
        st.markdown("**Curva ABC (Dispersão de Valor)**")
        fig_abc = px.strip(
            df_abc, 
            x=db.VALOR_COL, 
            y='Classe ABC', 
            color='Classe ABC',
            custom_data=[db.NOME_COL, db.RESPONSAVEL_COL],
            stripmode='overlay',
            color_discrete_map={
                'A (Crítico - 80%)': '#FF8C00', 
                'B (Médio - 15%)': '#FFD700',  
                'C (Baixo - 5%)': '#A9A9A9'    
            }
        )
        fig_abc.update_traces(hovertemplate='<b>%{customdata[0]}</b><br>Valor: R$ %{x:,.2f}')
        fig_abc.update_layout(**LAYOUT_CLEAN) 
        fig_abc.update_layout(xaxis_title="Valor (R$)", showlegend=False, xaxis=dict(showgrid=True, gridcolor='#333'))
        st.plotly_chart(fig_abc, use_container_width=True)

    with col_intel2:
        st.markdown("**Mapa Financeiro (Treemap)**")
        if not df_patr.empty:
            fig_tree = px.treemap(
                df_patr, 
                path=[db.STATUS_COL, db.NOME_COL], 
                values=db.VALOR_COL,
                color=db.STATUS_COL,
                color_discrete_map={
                    'ATIVO': '#2E8B57',      
                    'MANUTENÇÃO': '#CD5C5C', 
                    'EMPRÉSTIMO': '#DAA520', 
                    'BAIXADO': '#696969'     
                }
            )
            fig_tree.update_traces(textinfo="label+value")
            fig_tree.update_layout(**LAYOUT_CLEAN) 
            st.plotly_chart(fig_tree, use_container_width=True)

    st.write("---")

    st.subheader("Evolução")
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("**Investimento Mensal (Aquisições)**")
        if 'data_aquisicao' in dados_com_idade.columns and not dados_com_idade['data_aquisicao'].isnull().all():
            aquisicoes_no_tempo = dados_com_idade.set_index('data_aquisicao').resample('ME')[db.VALOR_COL].sum().reset_index()
            aquisicoes_no_tempo = aquisicoes_no_tempo[aquisicoes_no_tempo[db.VALOR_COL] > 0]
            
            fig_aquisicao = px.area(aquisicoes_no_tempo, x='data_aquisicao', y=db.VALOR_COL)
            fig_aquisicao.update_traces(line_color=COR_PRINCIPAL, fillcolor="rgba(227, 112, 38, 0.3)")
            fig_aquisicao.update_layout(**LAYOUT_CLEAN) 
            fig_aquisicao.update_layout(xaxis_title=None, yaxis_title="R$", yaxis=dict(gridcolor='#333'))
            st.plotly_chart(fig_aquisicao, use_container_width=True)
        else:
            st.info("Sem dados temporais.")

    with col_t2:
        st.markdown("**Movimentações**")
        if not df_mov.empty:
            mov_no_tempo = df_mov.set_index('data_hora').groupby('tipo_movimentacao').resample('ME').size().reset_index(name='contagem')
            color_map = {'Entrada': COR_PRINCIPAL, 'Saída': '#A9A9A9'}
            
            fig_mov = px.line(mov_no_tempo, x='data_hora', y='contagem', color='tipo_movimentacao', color_discrete_map=color_map, markers=True)
            fig_mov.update_layout(**LAYOUT_CLEAN) 
            fig_mov.update_layout(xaxis_title=None, yaxis_title="Qtd", yaxis=dict(gridcolor='#333'))
            st.plotly_chart(fig_mov, use_container_width=True)
        else:
            st.info("Sem dados de movimentação.")
            
    st.markdown("**Top Responsáveis (Valor)**")
    valor_por_resp = df_patr.groupby(db.RESPONSAVEL_COL)[db.VALOR_COL].sum().sort_values(ascending=False).head(10).reset_index()
    
    fig_resp_val = px.bar(valor_por_resp, x=db.RESPONSAVEL_COL, y=db.VALOR_COL, text_auto='.2s')
    fig_resp_val.update_traces(marker_color=COR_PRINCIPAL, textposition='outside')
    fig_resp_val.update_layout(**LAYOUT_CLEAN) 
    fig_resp_val.update_layout(yaxis_title="R$", xaxis_title=None, yaxis=dict(gridcolor='#333'))
    st.plotly_chart(fig_resp_val, use_container_width=True)

def pagina_cadastrar_item(is_admin, lista_status, lista_obras_app, existing_data):
    st.header("Novo Cadastro", divider='orange')
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
                uploaded_img = st.file_uploader("Anexar Foto do Equipamento", type=["jpg", "jpeg", "png"])
                
                submitted = st.form_submit_button("Cadastrar Patrimônio", type="primary", use_container_width=True)

                if submitted:
                    if not (nome_produto and num_nota_fiscal and local_uso and responsavel):
                        st.error("Preencha os campos obrigatórios: Nome, NF, Local e Responsável.")
                    else:
                        link_nota_fiscal = ""
                        if uploaded_pdf:
                            file_name = f"NF_{obra_para_cadastro}_{datetime.now().strftime('%H%M%S')}.pdf"
                            link_nota_fiscal = db.upload_to_storage(uploaded_pdf.getvalue(), file_name)
                
                        link_foto = ""
                        if uploaded_img:
                            img_name = f"IMG_{obra_para_cadastro}_{datetime.now().strftime('%H%M%S')}.jpg"
                            link_foto = db.upload_to_storage(
                                uploaded_img.getvalue(), 
                                img_name, 
                                bucket_name="fotos-patrimonio", 
                                file_type=uploaded_img.type
                            )

                        if uploaded_pdf:
                            file_name = f"NF_{obra_para_cadastro}_{datetime.now().strftime('%H%M%S')}.pdf"
                            link_nota_fiscal = upload_to_supabase_storage(uploaded_pdf.getvalue(), file_name)

                        novo_item_dict = {
                            db.OBRA_COL: obra_para_cadastro,
                            db.TOMBAMENTO_COL: num_final_envio.upper() if num_final_envio else None,
                            db.NOME_COL: nome_produto.upper(),
                            db.ESPEC_COL: especificacoes.upper(),
                            db.OBS_COL: observacoes.upper(),
                            db.LOCAL_COL: local_uso.upper(),
                            db.RESPONSAVEL_COL: responsavel.upper(),
                            db.NF_NUM_COL: num_nota_fiscal.upper(),
                            db.NF_LINK_COL: link_nota_fiscal,
                            db.FOTO_COL: link_foto,
                            db.VALOR_COL: valor_produto,
                            db.STATUS_COL: status_selecionado 
                        }
                        
                        try:
                            db.get_db_connection().table("patrimonio").insert(novo_item_dict).execute()
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
                    calc_total = loc_qtd * loc_valor
                    
                    nova_locacao = {
                        "equipamento": loc_equipamento.upper(),
                        "responsavel": loc_responsavel.upper(),
                        "unidade": loc_unidade.upper(),
                        "contrato_sienge": loc_contrato.upper(),
                        "obra_destino": loc_obra if is_admin else st.session_state.selected_obra,
                        "quantidade": loc_qtd,
                        "valor_mensal": loc_valor,
                        "valor_total": calc_total, 
                        "status": loc_status,
                        "data_inicio": loc_inicio.isoformat() if loc_inicio else None,
                        "data_previsao_fim": loc_fim.isoformat() if loc_fim else None
                    }
                    
                    try:
                        conn.table("locacoes").insert(nova_locacao).execute()
                        st.success(f"Locação de '{loc_equipamento}' registrada! Total: R$ {calc_total:,.2f}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar locação: {e}")


def pagina_inventario_unificado(is_admin, dados_patrimonio, dados_locacoes, lista_status, lista_obras):
    st.header("Inventário & Gerenciamento", divider="orange")
    
    if 'movement_item_id' not in st.session_state: st.session_state.movement_item_id = None

    tab_patrimonio, tab_locacoes = st.tabs(["Patrimônio", "Locações Ativas"])

    with tab_patrimonio:
        modo_view_patr = option_menu(
            menu_title=None, 
            options=["Cards", "Tabela"], 
            icons=['grid-fill', 'table'], 
            default_index=0, 
            orientation="horizontal",
            styles={
                "container": {
                    "padding": "0!important", 
                    "background-color": "transparent",
                    "width": "100%",     
                    "max-width": "100%", 
                    "margin": "0"        
                },
                "icon": {"color": "white", "font-size": "16px"}, 
                "nav-link": {
                    "font-size": "14px", 
                    "text-align": "center", 
                    "margin": "0px", 
                    "--hover-color": "#eee",
                    "color": "#333"
                },
                "nav-link-selected": {"background-color": "#E37026", "color": "white"},
            },
            key="menu_patrimonio"
        )
        
        if dados_patrimonio.empty:
            st.info("Nenhum patrimônio cadastrado.")
        else:
            col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
            
            with col_f1:
                search_term = st.text_input("Buscar Patrimônio", key="search_patr_uni", placeholder="Nome, Tombamento ou Responsável...")
            
            with col_f2:
                if is_admin:
                    opcoes_obras = ["Todas"] + sorted(lista_obras)
                    filtro_obra = st.selectbox("Filtrar por Obra", opcoes_obras, key="filtro_obra_patr")
                else:
                    obra_logada = st.session_state.get("selected_obra", "Geral")
                    st.write(f"**Obra:** {obra_logada}")
                    filtro_obra = obra_logada

            with col_f3:
                filter_st = st.selectbox("Status", ["Todos"] + sorted(list(dados_patrimonio[db.STATUS_COL].unique())), key="filtro_st_patr")

            dados_filt = dados_patrimonio.copy()

            if is_admin and filtro_obra != "Todas":
                dados_filt = dados_filt[dados_filt[db.OBRA_COL] == filtro_obra]
            elif not is_admin:
                dados_filt = dados_filt[dados_filt[db.OBRA_COL] == filtro_obra]

            if search_term:
                dados_filt = dados_filt[
                    dados_filt[db.NOME_COL].str.contains(search_term, case=False, na=False) |
                    dados_filt[db.TOMBAMENTO_COL].astype(str).str.contains(search_term, case=False, na=False) |
                    dados_filt[db.RESPONSAVEL_COL].str.contains(search_term, case=False, na=False)
                ]

            if filter_st != "Todos":
                dados_filt = dados_filt[dados_filt[db.STATUS_COL] == filter_st]

            if modo_view_patr == "Cards":
                total_valor_patr = dados_filt[db.VALOR_COL].sum()
                qtd_patr = dados_filt.shape[0]
                st.markdown(textwrap.dedent(f"""
                <div style="background-color: transparent !important; background-image: linear-gradient(160deg, #1e1e1f 0%, #0a0a0c 100%) !important; border: 1px solid rgba(255, 255, 255, 0.9) !important;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4 style="margin:0; color: #E37026;">Resumo Patrimonial</h4>
                        <div style="text-align:right;">
                            <div style="font-size: 0.9em; color: #ccc;">VALOR TOTAL</div>
                            <div style="font-size: 1.4em; font-weight:bold;"><b>R$ {total_valor_patr:,.2f}</b></div>
                        </div>
                    </div>
                <div><b>{qtd_patr}</b> itens encontrados</div>
                </div>"""), unsafe_allow_html=True)

                for index, row in dados_filt.iterrows():
                    with st.container(border=False):
                        st_txt = str(row[db.STATUS_COL]).strip().upper()
                        if st_txt == "ATIVO": cor_status = "#35BE53" 
                        elif st_txt in ["MANUTENÇÃO", "EMPRÉSTIMO"]: cor_status = "#ffc107" 
                        else: cor_status = "#dc3545" 
                        bg_status = f"{cor_status}22" 
                        valor_fmt = f"R$ {row[db.VALOR_COL]:,.2f}"
                        nome_safe = str(row[db.NOME_COL]).replace('"', '&quot;')
                        espec_safe = str(row[db.ESPEC_COL])[:100] + "..."
                        
                        st.header("", divider="orange")
                        img_url = row[db.FOTO_COL] if pd.notnull(row.get(db.FOTO_COL)) and row.get(db.FOTO_COL) != "" else "https://via.placeholder.com/150?text=Sem+Foto"
                        html_content = f"""
                        <div style="margin-bottom: 10px; display: flex; justify-content: space-between; gap: 15px;">
                            <div style="flex-grow: 1;">
                                <h3 style="margin:0; color: white; font-size: 1.3em;">{nome_safe}</h3>
                                <div style="color: #E37026; font-weight: bold; font-size: 0.9em;">TOMBAMENTO: {row[db.TOMBAMENTO_COL]}</div>
                                
                                <div style="margin-top: 15px; display:flex; flex-wrap: wrap; gap: 20px; color: #CCC; font-size: 0.9em;">
                                    <div style="min-width: 120px;"><b style="color: #888; display:block;">OBRA</b>{row[db.OBRA_COL]}</div>
                                    <div style="min-width: 120px;"><b style="color: #888; display:block;">LOCAL</b>{row[db.LOCAL_COL]}</div>
                                    <div style="min-width: 120px;"><b style="color: #888; display:block;">RESPONSÁVEL</b>{row[db.RESPONSAVEL_COL]}</div>
                                    <div><b style="color: #888; display:block;">VALOR</b><span style="color: #E37026;">{valor_fmt}</span></div>
                                </div>
                                <div style="margin-top: 10px; font-size: 0.85em; color: #888; font-style: italic;">
                                    {espec_safe}
                                </div>
                            </div>
                        
                            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 10px; flex-shrink: 0;">
                                <span style="background-color: {bg_status}; color: {cor_status}; padding: 4px 12px; border-radius: 4px; font-size: 0.75em; border: 1px solid {cor_status}; font-weight: bold;">{st_txt}</span>
                                <img src="{img_url}" style="width: 130px; height: 130px; object-fit: cover; border-radius: 8px; border: 1px solid #333;">
                            </div>
                        </div>
                        <hr style="border-top: 1px solid #333; margin: 5px 0 10px 0;">
                        """
                        st.markdown(html_content, unsafe_allow_html=True)
                        
                        c_edit, c_nf, c_qr = st.columns(3)
                        with c_edit:
                            if st.button("Editar", key=f"ed_p_{row[db.ID_COL]}", type="primary", use_container_width=True):
                                modal_editar_patrimonio(row, lista_status)
                        with c_nf:
                            if row[db.NF_LINK_COL]: st.link_button("Nota Fiscal", row[db.NF_LINK_COL], type="primary", use_container_width=True)
                            else: st.button("Sem Nota", disabled=True, key=f"nf_{row[db.ID_COL]}", type="secondary", use_container_width=True)
                        with c_qr:
                            if st.button("Etiqueta QR", key=f"qr_{row[db.ID_COL]}", type="primary", use_container_width=True):
                                pdf_bytes = utils.gerar_ficha_qr_code(row)
                                if pdf_bytes:
                                    b64 = base64.b64encode(pdf_bytes).decode()
                                    href = f'<a href="data:application/pdf;base64,{b64}" download="Etiqueta_{row[db.TOMBAMENTO_COL]}.pdf" id="d_{row[db.ID_COL]}"></a><script>document.getElementById("d_{row[db.ID_COL]}").click();</script>'
                                    st.markdown(href, unsafe_allow_html=True)

            else:
                st.header("", divider='orange')
                st.dataframe(dados_filt, use_container_width=True, hide_index=True)
                
                dados_xls = utils.gerar_excel(dados_filt, sheet_name="Patrimonio")
                dados_pdf = utils.gerar_pdf(dados_filt, tipo="patrimonio", obra_nome=st.session_state.get("selected_obra", "Geral"))
                col_d1, col_d2 = st.columns([1, 1])
                with col_d1:
                    if dados_xls: st.download_button("Excel", dados_xls, "Patrimonio.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")
                with col_d2:
                    if dados_pdf: st.download_button("PDF", dados_pdf, "Patrimonio.pdf", "application/pdf", use_container_width=True, type="primary")

                st.header("", divider='orange')

                st.markdown("### Selecionar Item para Ação")
                opts = dados_filt.apply(lambda x: f"{x[db.TOMBAMENTO_COL]} - {x[db.NOME_COL]}", axis=1).tolist()
                sel_item = st.selectbox("Selecione o Item:", options=opts, index=None, placeholder="Clique para selecionar...")
                
                if sel_item:
                    tomb = sel_item.split(" - ")[0]
                    row_sel = dados_filt[dados_filt[db.TOMBAMENTO_COL].astype(str) == tomb].iloc[0]
                    
                    with st.container(border=True):
                        st.write(f"**Item Selecionado:** {row_sel[db.NOME_COL]} (ID: {row_sel[db.ID_COL]})")
                        b1, b2, b3 = st.columns(3)
                        with b1:
                            if st.button("Editar Dados Completos", use_container_width=True, type="primary", key="btn_edit_tab"):
                                modal_editar_patrimonio(row_sel, lista_status)
                        with b2:
                            if st.button("Registrar Movimentação", use_container_width=True, type="primary"):
                                form_movimentacoes()
                                
                        with b3:
                            if st.button("Excluir Item", use_container_width=True, type="secondary", key="btn_del_tab"):
                                 db.get_db_connection().table("patrimonio").delete().eq(db.ID_COL, int(row_sel[db.ID_COL])).execute()
                                 st.success("Removido.")
                                 time.sleep(1)
                                 st.cache_data.clear()
                                 st.rerun()

                    
    with tab_locacoes:
        modo_view_loc = option_menu(
            menu_title=None, 
            options=["Cards", "Tabela"], 
            icons=['grid-fill', 'table'], 
            default_index=0, 
            orientation="horizontal",
            styles={
                "container": {
                    "padding": "0!important", 
                    "background-color": "transparent",
                    "width": "100%",    
                    "max-width": "100%", 
                    "margin": "0"         
                },
                "icon": {"color": "white", "font-size": "16px"}, 
                "nav-link": {
                    "font-size": "14px", 
                    "text-align": "center", 
                    "margin": "0px", 
                    "--hover-color": "#eee",
                    "color": "#333"
                },
                "nav-link-selected": {"background-color": "#E37026", "color": "white"},
            },
            key="menu_locacoes"
        )
        
        if dados_locacoes.empty:
            st.info("Nenhuma locação registrada.")
        else: 
            col_lf1, col_lf2 = st.columns([1, 2])
            with col_lf1:
                obras_loc_disp = sorted(list(dados_locacoes["obra_destino"].unique()))
                filtro_obra_loc = st.selectbox("Filtrar por Obra", ["Todas"] + obras_loc_disp)
            with col_lf2:
                busca_loc = st.text_input("Busca Geral", key="search_loc", placeholder="Equipamento, contrato...")

            df_l = dados_locacoes.copy()
            if filtro_obra_loc != "Todas":
                df_l = df_l[df_l["obra_destino"] == filtro_obra_loc]
            if busca_loc:
                df_l = df_l[df_l["equipamento"].str.contains(busca_loc, case=False, na=False) | df_l["contrato_sienge"].str.contains(busca_loc, case=False, na=False)]

            if modo_view_loc == "Cards":
                total_mensal = df_l["valor_total"].sum() if "valor_total" in df_l.columns else 0.0
                qtd_equip = df_l.shape[0]
                
                st.markdown(textwrap.dedent(f"""
                <div style="background-color: transparent !important; background-image: linear-gradient(160deg, #1e1e1f 0%, #0a0a0c 100%) !important; border: 1px solid rgba(255, 255, 255, 0.9) !important;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4 style="margin:0; color: #E37026;">{filtro_obra_loc if filtro_obra_loc != 'Todas' else 'Resumo Locações'}</h4>
                        <div style="text-align:right;">
                            <div style="font-size: 0.9em; color: #ccc;">VALOR TOTAL MENSAL ESTIMADO</div>
                            <div style="font-size: 1.4em; font-weight:bold;">R$ {total_mensal:,.2f}</div>
                        </div>
                    </div>
                     <div><b>{qtd_equip}</b> equipamento(s) locado(s)</div>
                </div>"""), unsafe_allow_html=True)

                for index, row in df_l.iterrows():
                    with st.container(border=False):
                        d_inicio = pd.to_datetime(row['data_inicio']).strftime('%d/%m/%Y') if pd.notnull(row['data_inicio']) else '-'
                        d_fim = pd.to_datetime(row['data_previsao_fim']).strftime('%d/%m/%Y') if pd.notnull(row['data_previsao_fim']) else '-'
                        valor_loc_fmt = f"R$ {row['valor_mensal']:,.2f}"
                        equip_safe = str(row['equipamento']).replace('"', '&quot;')
                        
                        st_loc = str(row['status'])
                        if st_loc == "ATIVO": cor_loc = "#35BE53" 
                        elif st_loc in ["MANUTENÇÃO"]: cor_loc = "#ffc107" 
                        else: cor_loc = "#dc3545" 
                        bg_loc = f"{cor_loc}22"
                        st.header("", divider="orange")
                        
                        v_total_show = row['valor_total'] if row.get('valor_total') else (row['quantidade'] * row['valor_mensal'])

                        html_loc = f"""
                        <div style="margin-bottom: 10px;">
                            <div style="display:flex; justify-content:space-between; align-items:start;">
                                <div>
                                    <h3 style="margin:0; color: white; font-size: 1.3em;">{equip_safe}</h3>
                                    <span style="color: #888; font-size: 0.9em;">{row['contrato_sienge']}</span>
                                </div>
                                <span style="background-color: {bg_loc}; color: {cor_loc}; padding: 4px 12px; border-radius: 4px; font-size: 0.75em; border: 1px solid {cor_loc}; font-weight: bold;">{st_loc}</span>
                            </div>
                            <div style="margin-top: 15px; display:flex; flex-wrap:wrap; gap: 20px; color: #CCC; font-size: 0.9em;">
                                <div style="min-width: 140px;"><b style="color: #888; display:block;">OBRA</b>{row['obra_destino']}</div>
                                <div style="min-width: 50px;"><b style="color: #888; display:block;">QTD</b>{row['quantidade']}</div>
                                <div style="min-width: 140px;"><b style="color: #888; display:block;">RESPONSÁVEL</b>{row['responsavel']}</div>
                                <div><b style="color: #888; display:block;">VALOR UNIT.</b><span style="color: #aaa;">{valor_loc_fmt}</span></div>
                                <div><b style="color: #888; display:block;">VALOR TOTAL</b><span style="color: #E37026; font-weight:bold;">R$ {v_total_show:,.2f}</span></div>
                            </div>
                            <div style="margin-top: 10px; font-size: 0.85em; color: #aaa; display:flex; gap: 20px;">
                                <span>Início: {d_inicio}</span><span>Prev. Fim: {d_fim}</span>
                            </div>
                            <hr style="border-top: 1px solid #333; margin: 15px 0 10px 0;">
                        </div>
                        """
                        st.markdown(html_loc, unsafe_allow_html=True)
                    
                        c_edt, c_del = st.columns(2)
                    with c_edt:
                        if st.button("Editar Locação", key=f"ed_l_{row['id']}", type="primary", use_container_width=True):
                            modal_editar_locacao(row, lista_obras)
                    with c_del:
                        if st.button("Excluir", key=f"dl_l_{row['id']}", type="secondary", use_container_width=True):
                            if st.session_state.get(f"cf_l_{row['id']}"):
                                db.get_db_connection().table("locacoes").delete().eq("id", row['id']).execute()
                                st.rerun()
                            else:
                                st.session_state[f"cf_l_{row['id']}"] = True
                                st.warning("Confirmar?")

            else:
                st.header("", divider='orange')
                st.dataframe(df_l, use_container_width=True, hide_index=True)
                excel_data = utils.gerar_excel(df_l, sheet_name="locaçoes")
                pdf_data = utils.gerar_pdf(df_l, tipo="locaçoes", obra_nome=st.session_state.get("selected_obra", "Geral"))
                
                col_l1, col_l2 = st.columns([1, 1])
                with col_l1: st.download_button(label="Baixar Excel", data=excel_data, file_name="Locacoes.xlsx", type="primary", use_container_width=True)
                with col_l2: st.download_button(label="Baixar PDF", data=pdf_data, file_name="Locacoes.pdf", type="primary", use_container_width=True)

                st.header("", divider='orange')
                
                st.markdown("### Selecionar Locação")
                opts_l = df_l.apply(lambda x: f"{x['id']} - {x['equipamento']}", axis=1).tolist()
                sel_loc = st.selectbox("Selecione:", options=opts_l, index=None, placeholder="Clique para selecionar...")
                
                if sel_loc:
                    lid = int(sel_loc.split(" - ")[0])
                    r_loc = df_l[df_l["id"] == lid].iloc[0]
                    bl1, bl2 = st.columns(2)
                    with bl1:
                        if st.button("Editar Locação", key="btn_g_el", type="primary", use_container_width=True):
                            modal_editar_locacao(r_loc, lista_obras)
                    with bl2:
                        if st.button("Excluir Locação", key="btn_g_dl", type="secondary", use_container_width=True):
                            db.get_db_connection().table("locacoes").delete().eq("id", lid).execute()
                            st.success("Excluído.")
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
