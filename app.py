import streamlit as st
import os
from supabase import create_client
from datetime import datetime, date
import math
import pandas as pd
import pdfplumber
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Exames", layout="wide")

USUARIO = "familia"
SENHA = "1234"

if "logado" not in st.session_state:
    st.session_state.logado = False

# =========================
# LOGIN
# =========================
if not st.session_state.logado:
    st.title("🔐 Login")

    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if user.strip() == USUARIO and password.strip() == SENHA:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

    st.stop()

# =========================
# SUPABASE
# =========================
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# =========================
# LIMPEZA JSON
# =========================
def limpar_dados(lista):
    nova_lista = []
    for item in lista:
        novo = {}
        for k, v in item.items():
            if isinstance(v, (datetime, date)):
                novo[k] = v.isoformat()
            elif isinstance(v, float) and math.isnan(v):
                novo[k] = None
            else:
                novo[k] = v
        nova_lista.append(novo)
    return nova_lista

# =========================
# EXTRAÇÃO REAL PDF
# =========================
def extrair_dados_pdf(file):
    resultados = []

    with pdfplumber.open(file) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

    # padrões simples (ajustamos depois com seu PDF real)
    padrao = re.findall(r"([A-Za-z ]+)\s+([\d,.]+)\s+(mg/dL|g/dL|%)", texto)

    for exame, valor, unidade in padrao:
        try:
            valor = float(valor.replace(",", "."))
            resultados.append({
                "paciente": "Pai",
                "data": date.today(),
                "exame": exame.strip(),
                "valor": valor,
                "unidade": unidade
            })
        except:
            continue

    return resultados

# =========================
# BANCO
# =========================
def salvar_exames(lista):
    lista_limpa = limpar_dados(lista)
    supabase.table("exames").insert(lista_limpa).execute()

def salvar_upload(nome_arquivo):
    supabase.table("uploads").insert({
        "arquivo": nome_arquivo,
        "data_envio": datetime.now().isoformat(),
        "data_exame": date.today().isoformat()
    }).execute()

def carregar_exames():
    res = supabase.table("exames").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def carregar_uploads():
    res = supabase.table("uploads").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# =========================
# DASHBOARD
# =========================
st.title("📊 Dashboard de Exames")

col1, col2 = st.columns(2)

# =========================
# UPLOAD
# =========================
with col1:
    st.subheader("📤 Enviar novo exame")

    arquivo = st.file_uploader("Upload PDF", type=["pdf"])

    if arquivo:
        if st.button("Processar exame"):
            dados = extrair_dados_pdf(arquivo)

            if not dados:
                st.warning("Nenhum exame identificado no PDF")
            else:
                salvar_exames(dados)
                salvar_upload(arquivo.name)
                st.success(f"{len(dados)} exames salvos!")
                st.rerun()

# =========================
# ÚLTIMOS UPLOADS
# =========================
with col2:
    st.subheader("📁 Últimos uploads")

    df_up = carregar_uploads()

    if not df_up.empty:
        df_up = df_up.sort_values("data_envio", ascending=False)
        st.dataframe(df_up.head(5))
    else:
        st.info("Nenhum upload ainda")

# =========================
# GRÁFICO MELHORADO
# =========================
st.subheader("📈 Evolução dos exames")

df = carregar_exames()

if not df.empty:

    df["data"] = pd.to_datetime(df["data"])
    exames = df["exame"].unique()

    selecionados = st.multiselect(
        "Selecione exames",
        exames,
        default=list(exames[:2])
    )

    df_f = df[df["exame"].isin(selecionados)]

    if not df_f.empty:
        pivot = df_f.pivot_table(
            index="data",
            columns="exame",
            values="valor"
        )

        st.line_chart(pivot)

    st.dataframe(df.sort_values("data", ascending=False))

else:
    st.info("Nenhum exame disponível ainda")
