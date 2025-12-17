import streamlit as st
import pandas as pd
import io
import qrcode
import tempfile
from fpdf import FPDF
from datetime import datetime

def aplicar_css():
    APP_STYLE_CSS = """
    <style>
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 10% 20%, #1e1e24 0%, #050505 90%);
        background-attachment: fixed;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input {
        color: white !important;
    }
    /* Estilo para cartões de inventário */
    .card-inventario {
        background-color: transparent; 
        background-image: linear-gradient(160deg, #1e1e1f 0%, #0a0a0c 100%); 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        padding: 20px; 
        margin-bottom: 20px;
        border-radius: 8px;
    }
    </style>
    """
    st.markdown(APP_STYLE_CSS, unsafe_allow_html=True)


def clean_text(text):
    if text is None: return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def gerar_excel(df, sheet_name="Relatorio"):
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
            worksheet = writer.sheets[sheet_name]
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max() if not df[col].empty else 0, len(str(col))) + 2
                worksheet.set_column(i, i, min(max_len, 50))
    except:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

def gerar_pdf(df, titulo="Relatório", col_map=[]):

    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        try: pdf.image("Lavie.png", x=10, y=5, w=35)
        except: pass
        
        pdf.set_y(20)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, clean_text(titulo), 0, 1, 'C')
        pdf.ln(5)

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

def gerar_ficha_qr_code(row, config_cols):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        pdf.set_fill_color(227, 112, 38) 
        pdf.rect(0, 0, 210, 20, 'F')
        
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.text(10, 14, "Ficha de Identificação de Ativo - LAVIE")
        
        id_col, nome_col, tomb_col, obra_col = config_cols['id'], config_cols['nome'], config_cols['tomb'], config_cols['obra']
        qr_data = f"ID: {row[id_col]}\nItem: {row[nome_col]}\nTombamento: {row[tomb_col]}"
        
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            img_qr.save(tmp.name)
            qr_path = tmp.name

        pdf.set_text_color(0, 0, 0)
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, f"Produto: {clean_text(str(row[nome_col]).upper())}", ln=True)
        
        pdf.image(qr_path, x=130, y=30, w=60)
        return bytes(pdf.output())
    except Exception as e:
        return None
