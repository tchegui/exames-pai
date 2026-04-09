import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
import os

st.set_page_config(layout="wide")

# =========================
# LOGIN
# =========================
USUARIO = "familia"
SENHA = "1234"

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == USUARIO and pwd == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Login inválido")

    st.stop()

# =========================
# ARQUIVOS
# =========================
ARQ_DADOS = "historico_exames.csv"
ARQ_UPLOADS = "uploads.csv"

# =========================
# CARREGAR
# =========================
if os.path.exists(ARQ_DADOS):
    historico = pd.read_csv(ARQ_DADOS, parse_dates=["data"])
else:
    historico = pd.DataFrame(columns=["paciente", "data", "exame", "valor", "unidade"])

if os.path.exists(ARQ_UPLOADS):
    uploads = pd.read_csv(ARQ_UPLOADS, parse_dates=["data_envio", "data_exame"])
else:
    uploads = pd.DataFrame(columns=["arquivo", "data_envio", "data_exame"])

# =========================
# PADRONIZAÇÃO
# =========================
MAPA_EXAMES = {
    "HEMOGLOBINA": "HEMOGLOBINA",
    "LEUCÓCITOS": "LEUCOCITOS",
    "PLAQUETAS": "PLAQUETAS",
    "POTASSIO": "POTASSIO",
    "SODIO": "SODIO",
    "PROTEINA C-REATIVA": "PCR",
}

LIMITES = {
    "HEMOGLOBINA": (12, 17),
    "LEUCOCITOS": (4000, 10000),
    "PCR": (0, 0.5),
}

def normalizar(nome):
    nome = nome.upper()
    for k in MAPA_EXAMES:
        if k in nome:
            return MAPA_EXAMES[k]
    return nome

# =========================
# EXTRAÇÃO
# =========================
def extrair(pdf):
    texto = ""
    with pdfplumber.open(pdf) as p:
        for page in p.pages:
            t = page.extract_text()
            if t:
                texto += t + "\n"

    linhas = texto.split("\n")

    paciente = "Paciente"
    data = datetime.now()
    dados = []

    for l in linhas:

        if "OBERON" in l.upper():
            paciente = l.strip()

        if "COLETADO EM:" in l:
            m = re.search(r'(\d{2}/\d{2}/\d{4})', l)
            if m:
                data = datetime.strptime(m.group(1), "%d/%m/%Y")

        match = re.search(
            r'([A-ZÇÃÉÍÓÚ\s]+?)\s*[:]\s*([\d\.,]+)\s*(mg/dL|mEq/L|mmol/L|g/dL|U/L|%|mmHg|/mm3)',
            l
        )

        if match:
            nome = normalizar(match.group(1))
            valor = float(match.group(2).replace(".", "").replace(",", "."))
            unidade = match.group(3)

            dados.append({
                "paciente": paciente,
                "data": data,
                "exame": nome,
                "valor": valor,
                "unidade": unidade
            })

    return pd.DataFrame(dados), data

# =========================
# INTERPRETAÇÃO
# =========================
def interpretar(df, exame):
    if exame not in LIMITES or len(df) < 1:
        return "Sem interpretação"

    min_v, max_v = LIMITES[exame]
    atual = df.iloc[-1]["valor"]

    texto = ""

    if atual < min_v:
        texto += "🔴 Baixo. "
    elif atual > max_v:
        texto += "🔴 Alto. "
    else:
        texto += "🟢 Normal. "

    if len(df) >= 2:
        anterior = df.iloc[-2]["valor"]
        if atual > anterior:
            texto += "📈 Subindo."
        elif atual < anterior:
            texto += "📉 Caindo."

    return texto

# =========================
# UPLOAD
# =========================
st.subheader("📤 Enviar novo exame")

arquivo = st.file_uploader("PDF", type="pdf")

if arquivo:
    df_novo, data_exame = extrair(arquivo)

    if not df_novo.empty:

        historico = pd.concat([historico, df_novo]).drop_duplicates()
        historico.to_csv(ARQ_DADOS, index=False)

        novo_upload = pd.DataFrame([{
            "arquivo": arquivo.name,
            "data_envio": datetime.now(),
            "data_exame": data_exame
        }])

        uploads = pd.concat([uploads, novo_upload])
        uploads.to_csv(ARQ_UPLOADS, index=False)

        st.success("Exame adicionado!")
        st.rerun()

# =========================
# DASHBOARD AUTOMÁTICO
# =========================
if not historico.empty:

    paciente = historico["paciente"].iloc[0]

    exames = historico["exame"].unique()
    exame = st.selectbox("🧪 Exame", exames)

    df_f = historico[historico["exame"] == exame].sort_values("data")

    fig = px.line(df_f, x="data", y="valor", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧠 Interpretação")
    st.info(interpretar(df_f, exame))

    st.subheader("📋 Histórico")
    st.dataframe(df_f.sort_values("data", ascending=False))

# =========================
# LISTA DE PDFs
# =========================
if not uploads.empty:
    st.subheader("📁 PDFs enviados")

    st.dataframe(
        uploads.sort_values("data_envio", ascending=False)
    )
