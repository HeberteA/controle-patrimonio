import streamlit as st
import pandas as pd
import io
import qrcode
import tempfile
from fpdf import FPDF
import database as db

def aplicar_css():
    APP_STYLE_CSS = """
    <style>
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 10% 20%, #1e1e24 0%, #050505 90%);
        background-attachment: fixed;
    }
    /* Ajustes de Inputs para contraste */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input {
        color: white !important;
    }
    /* Estilos extras dos cards */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: white !important;
        border: none !important;
        font-weight: 500 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
    """
    st.markdown(APP_STYLE_CSS, unsafe_allow_html=True)

def clean_text(text):
    if text is None: return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def gerar_ficha_qr_code(row_series):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_fill_color(227, 112, 38)
        pdf.rect(0, 0, 210, 20, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.text(10, 14, "Ficha de Identificação de Ativo - LAVIE")
        
        qr_data = f"ID: {row_series[db.ID_COL]}\nItem: {row_series[db.NOME_COL]}\nTombamento: {row_series[db.TOMBAMENTO_COL]}\nObra: {row_series[db.OBRA_COL]}"
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            img_qr.save(tmp_file.name)
            qr_path = tmp_file.name

        pdf.set_text_color(0, 0, 0)
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, f"Produto: {str(row_series[db.NOME_COL]).upper()}", ln=True)
        pdf.set_font('Helvetica', '', 11)
        pdf.cell(0, 8, f"Tombamento: {row_series[db.TOMBAMENTO_COL]}", ln=True)
        pdf.cell(0, 8, f"Obra Atual: {row_series[db.OBRA_COL]}", ln=True)
        pdf.cell(0, 8, f"Responsável: {row_series[db.RESPONSAVEL_COL]}", ln=True)
        pdf.cell(0, 8, f"Status: {row_series[db.STATUS_COL]}", ln=True)
        
        pdf.ln(5)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 8, "Especificações / Obs:", ln=True)
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(110, 6, f"{str(row_series[db.ESPEC_COL])}\n{str(row_series[db.OBS_COL])}")
        pdf.image(qr_path, x=130, y=30, w=60)
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Erro ao gerar Ficha QR: {e}")
        return None

def gerar_excel(df, sheet_name="Relatorio"):
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
            worksheet = writer.sheets[sheet_name]
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max() if not df[col].empty else 0, len(str(col))) + 2
                worksheet.set_column(i, i, min(max_len, 50)) 
    except ModuleNotFoundError:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

def gerar_pdf(df, tipo="patrimonio", obra_nome="Geral"):
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        try: pdf.image("Lavie.png", x=10, y=5, w=35)
        except: pass 
        pdf.set_y(15)
        pdf.set_font('Arial', 'B', 14)
        titulo = f'Relatório de {tipo.title()} - {obra_nome}'
        pdf.cell(0, 10, clean_text(titulo), 0, 1, 'C')
        pdf.ln(5)

        if tipo == "patrimonio":
            col_map = [
                (db.TOMBAMENTO_COL, 25, "Tomb."),
                (db.NOME_COL, 80, "Item / Descrição"),
                (db.STATUS_COL, 25, "Status"),
                (db.LOCAL_COL, 40, "Local"),
                (db.RESPONSAVEL_COL, 40, "Responsável"),
                (db.VALOR_COL, 30, "Valor (R$)")
            ]
        else:
            col_map = [
                ('equipamento', 70, "Equipamento"),
                ('obra_destino', 50, "Obra"),
                ('data_inicio', 30, "Início"),
                ('data_fim', 30, "Fim"),
                ('valor_mensal', 30, "Valor"),
                ('status', 30, "Status")
            ]

        valid_cols = [c for c in col_map if c[0] in df.columns]
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(220, 220, 220) 
        
        for _, width, header in valid_cols:
            pdf.cell(width, 8, clean_text(header), 1, 0, 'C', fill=True)
        pdf.ln()
        pdf.set_font('Arial', '', 8)
        
        for _, row in df.iterrows():
            for col_key, width, _ in valid_cols:
                texto = clean_text(row[col_key])
                limit = int(width / 1.8)
                if len(texto) > limit: texto = texto[:limit] + "..."
                pdf.cell(width, 7, texto, 1, 0, 'C')
            pdf.ln()
        return bytes(pdf.output()) 
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None
