import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from supabase import create_client

# =========================
# CONEXÃO SUPABASE
# =========================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# =========================
# LOGIN
# =========================
USUARIO = "familia"
SENHA = "1234"

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")

    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if u == USUARIO and s == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Login inválido")

    st.stop()

st.title("📊 Monitor de Exames")

# =========================
# PADRONIZAÇÃO
# =========================
MAPA = {
    "HEMOGLOBINA": "HEMOGLOBINA",
    "LEUCÓCITOS": "LEUCOCITOS",
    "PLAQUETAS": "PLAQUETAS",
    "PROTEINA C-REATIVA": "PCR",
}

LIMITES = {
    "HEMOGLOBINA": (12, 17),
    "LEUCOCITOS": (4000, 10000),
    "PCR": (0, 0.5),
}

def norm(nome):
    nome = nome.upper()
    for k in MAPA:
        if k in nome:
            return MAPA[k]
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
            r'([A-ZÇÃÉÍÓÚ\s]+?)\s*[:]\s*([\d\.,]+)\s*(mg/dL|mEq/L|g/dL|%)',
            l
        )

        if match:
            dados.append({
                "paciente": paciente,
                "data": data.date(),
                "exame": norm(match.group(1)),
                "valor": float(match.group(2).replace(".", "").replace(",", ".")),
                "unidade": match.group(3)
            })

    return dados, data.date()

# =========================
# SALVAR NO BANCO
# =========================
def salvar_exames(lista):
    supabase.table("exames").insert(lista).execute()

def salvar_upload(nome, data_exame):
    supabase.table("uploads").insert({
        "arquivo": nome,
        "data_envio": datetime.now().isoformat(),
        "data_exame": data_exame
    }).execute()

# =========================
# CARREGAR DO BANCO
# =========================
def carregar_exames():
    res = supabase.table("exames").select("*").execute()
    return pd.DataFrame(res.data)

def carregar_uploads():
    res = supabase.table("uploads").select("*").execute()
    return pd.DataFrame(res.data)

# =========================
# UPLOAD
# =========================
st.subheader("📤 Enviar exame")

file = st.file_uploader("PDF", type="pdf")

if file:
    dados, data_exame = extrair(file)

    if dados:
        salvar_exames(dados)
        salvar_upload(file.name, data_exame)

        st.success("Salvo no banco!")
        st.rerun()

# =========================
# DASHBOARD
# =========================
df = carregar_exames()

if not df.empty:

    exame = st.selectbox("Exame", df["exame"].unique())
    df_f = df[df["exame"] == exame].sort_values("data")

    fig = px.line(df_f, x="data", y="valor", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Histórico")
    st.dataframe(df_f)

# =========================
# UPLOADS
# =========================
up = carregar_uploads()

if not up.empty:
    st.subheader("📁 PDFs enviados")
    st.dataframe(up.sort_values("data_envio", ascending=False))
