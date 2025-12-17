import streamlit as st
from streamlit_option_menu import option_menu
import database as db
import utils
import views

st.set_page_config(page_title="Controle de Patrimônio Lavie", page_icon="Lavie1.png", layout="wide")
utils.aplicar_css()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'selected_obra' not in st.session_state: st.session_state.selected_obra = None

def tela_de_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2: st.image("Lavie.png", use_container_width=True) 
    st.title("Controle de Patrimônio")
    tab1, tab2 = st.tabs(["Acesso por Obra", "Acesso de Administrador"])
    
    with tab1:
        st.subheader("Login da Obra")
        try:
            _, lista_obras, _, _, _ = db.carregar_dados_app()
            if not lista_obras: st.info("Nenhuma obra cadastrada.")
            else:
                codigos_obras = st.secrets.obra_codes
                obra_selecionada = st.selectbox("Selecione a Obra", options=lista_obras, index=None)
                if obra_selecionada:
                    codigo_acesso = st.text_input("Código de Acesso", type="password", key="obra_password")
                    if st.button("Entrar na Obra", type="primary"):
                        if codigo_acesso == codigos_obras.get(obra_selecionada):
                            st.session_state.logged_in = True
                            st.session_state.is_admin = False
                            st.session_state.selected_obra = obra_selecionada
                            st.rerun()
                        else: st.error("Código incorreto.")
        except Exception as e: st.error(f"Erro ao carregar obras: {e}")

    with tab2:
        st.subheader("Login de Administrador")
        admin_password = st.text_input("Senha do Administrador", type="password", key="admin_password")
        if st.button("Entrar como Administrador", type="primary"):
            if admin_password == st.secrets.admin.password:
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.rerun()
            else: st.error("Senha incorreta.")

def app_principal():
    is_admin = st.session_state.is_admin
    lista_status, lista_obras_app, existing_data_full, df_movimentacoes, df_locacoes = db.carregar_dados_app()
    
    with st.sidebar:
        st.image("Lavie.png", use_container_width=True)
        st.header("Navegação")
        if is_admin: st.info("Logado como **Administrador**.")
        else: st.info(f"Obra: **{st.session_state.selected_obra}**")

        menu_options = ["Cadastrar Item", "Inventário", "Dashboard"]
        icons = ["plus-circle-fill", "card-list", "bar-chart-fill"]
        
        selected_page = option_menu(
            menu_title=None, options=menu_options, icons=icons,
            menu_icon="cast", default_index=1,
            styles={ 
                "container": {"padding": "5px !important", "background-color": "transparent"},
                "icon": {"font-size": "18px"}, "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px"},
                "nav-link-selected": {"background-color": "#E37026"}, 
            }
        )
        
        obra_selecionada_sidebar = None
        if is_admin:
            st.write("---")
            obras_disponiveis = ["Todas"] + lista_obras_app 
            obra_selecionada_sidebar = st.selectbox("Filtrar Visão por Obra", obras_disponiveis)
        
        st.write("---")
        if st.button("Sair / Trocar Obra", type="primary", use_container_width=True):
            st.session_state.clear()
            st.cache_data.clear()
            st.rerun()
            
    if is_admin:
        if obra_selecionada_sidebar == "Todas":
            dados_patrimonio = existing_data_full
            dados_locacoes_filt = df_locacoes
        else:
            dados_patrimonio = existing_data_full[existing_data_full[db.OBRA_COL] == obra_selecionada_sidebar].copy()
            dados_locacoes_filt = df_locacoes[df_locacoes["obra_destino"] == obra_selecionada_sidebar].copy()
    else: 
        obra_logada = st.session_state.selected_obra
        dados_patrimonio = existing_data_full[existing_data_full[db.OBRA_COL] == obra_logada].copy()
        dados_locacoes_filt = df_locacoes[df_locacoes["obra_destino"] == obra_logada].copy()

    if selected_page == "Dashboard":
        views.pagina_dashboard(dados_patrimonio, df_movimentacoes)
    elif selected_page == "Cadastrar Item":
        views.pagina_cadastrar_item(is_admin, lista_status, lista_obras_app, dados_patrimonio)
    elif selected_page == "Inventário Unificado":
        views.pagina_inventario_unificado(is_admin, dados_patrimonio, dados_locacoes_filt, lista_status, lista_obras_app)

if not st.session_state.logged_in:
    tela_de_login()
else:
    app_principal()
