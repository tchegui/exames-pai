import streamlit as st
import os
from supabase import create_client
from datetime import datetime, date
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

    with st.form("login"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if user == USUARIO and password == SENHA:
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
# EXTRAÇÃO PDF (MELHORADA)
# =========================
def extrair_dados_pdf(file):

    resultados = []
    texto = ""

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

    # 📅 tentar pegar data do exame
    data_match = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
    if data_match:
        data_exame = datetime.strptime(data_match.group(1), "%d/%m/%Y").date()
    else:
        data_exame = date.today()

    # 🧪 exames
    padrao = re.findall(r"([A-Za-z ]+)[\.: ]+([\d,.]+)\s*(mg/dL|g/dL|%)", texto)

    for exame, valor, unidade in padrao:
        try:
            valor = float(valor.replace(",", "."))
            resultados.append({
                "paciente": "Pai",
                "data": data_exame,
                "exame": exame.strip(),
                "valor": valor,
                "unidade": unidade
            })
        except:
            continue

    return resultados, data_exame

# =========================
# BANCO
# =========================
def salvar_exames(lista):
    supabase.table("exames").insert(lista).execute()

def salvar_upload(nome_arquivo, data_exame):
    supabase.table("uploads").insert({
        "arquivo": nome_arquivo,
        "data_envio": datetime.now().isoformat(),
        "data_exame": data_exame.isoformat()
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

# =========================
# UPLOAD
# =========================
st.subheader("📤 Enviar exame")

arquivo = st.file_uploader("Upload PDF", type=["pdf"])

if arquivo:

    df_uploads = carregar_uploads()

    if not df_uploads.empty and arquivo.name in df_uploads["arquivo"].values:
        st.warning("⚠️ Este arquivo já foi enviado anteriormente")
    else:
        if st.button("Processar exame"):

            dados, data_exame = extrair_dados_pdf(arquivo)

            if not dados:
                st.error("Não foi possível identificar exames no PDF")
            else:
                salvar_exames(dados)
                salvar_upload(arquivo.name, data_exame)

                st.success(f"{len(dados)} exames salvos!")
                st.rerun()

# =========================
# UPLOADS (FULL WIDTH)
# =========================
st.subheader("📁 Histórico de uploads")

df_up = carregar_uploads()

if not df_up.empty:
    df_up = df_up.sort_values("data_envio", ascending=False)
    st.dataframe(df_up, use_container_width=True)
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

        st.line_chart(pivot, use_container_width=True)

        # tabela abaixo ajuda muito na leitura
        st.dataframe(df_f.sort_values("data", ascending=False), use_container_width=True)

else:
    st.info("Nenhum exame disponível")
