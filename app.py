import streamlit as st
import os
from supabase import create_client
from datetime import datetime, date
import math
import pandas as pd

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Exames", layout="wide")

# =========================
# LOGIN CONFIG
# =========================
USUARIO = "familia"
SENHA = "1234"

# =========================
# SESSION INIT
# =========================
if "logado" not in st.session_state:
    st.session_state.logado = False

# =========================
# TELA LOGIN (FORMA MAIS ESTÁVEL)
# =========================
if not st.session_state.logado:
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):

        # DEBUG VISÍVEL
        st.write("DEBUG USER:", user)
        st.write("DEBUG PASS:", password)

        if user.strip() == USUARIO and password.strip() == SENHA:
            st.session_state.logado = True
            st.success("Login realizado!")
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

            elif "numpy" in str(type(v)):
                novo[k] = float(v)

            else:
                novo[k] = v

        nova_lista.append(novo)

    return nova_lista

# =========================
# EXTRAÇÃO MOCK
# =========================
def extrair_dados_pdf(nome_arquivo):
    return [
        {
            "paciente": "Pai",
            "data": date.today(),
            "exame": "Glicose",
            "valor": 95.0,
            "unidade": "mg/dL"
        },
        {
            "paciente": "Pai",
            "data": date.today(),
            "exame": "Colesterol",
            "valor": 180.0,
            "unidade": "mg/dL"
        }
    ]

# =========================
# SALVAR
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

# =========================
# CARREGAR
# =========================
def carregar_exames():
    res = supabase.table("exames").select("*").execute()
    return res.data if res.data else []

def carregar_uploads():
    res = supabase.table("uploads").select("*").execute()
    return res.data if res.data else []

# =========================
# APP PRINCIPAL
# =========================
st.title("📊 Exames do Paciente")

# =========================
# UPLOAD
# =========================
st.subheader("📤 Enviar novo exame")

arquivo = st.file_uploader("Upload PDF", type=["pdf"])

if arquivo:
    if st.button("Processar exame"):
        dados = extrair_dados_pdf(arquivo.name)

        salvar_exames(dados)
        salvar_upload(arquivo.name)

        st.success("Exame salvo com sucesso!")
        st.rerun()

# =========================
# HISTÓRICO
# =========================
st.subheader("📈 Histórico de exames")

dados = carregar_exames()

if dados:
    df = pd.DataFrame(dados)

    st.dataframe(df)

    exames = df["exame"].unique()
    exame_sel = st.selectbox("Escolha o exame", exames)

    df_f = df[df["exame"] == exame_sel]
    df_f = df_f.sort_values("data")

    st.line_chart(df_f.set_index("data")["valor"])

else:
    st.info("Nenhum exame encontrado")

# =========================
# UPLOADS
# =========================
st.subheader("📁 Arquivos enviados")

uploads = carregar_uploads()

if uploads:
    df_up = pd.DataFrame(uploads)
    st.dataframe(df_up)
else:
    st.info("Nenhum upload ainda")
