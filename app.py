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
# LOGIN SIMPLES
# =========================
USUARIO = "familia"
SENHA = "1234"

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("Login")

    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
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
# FUNÇÃO LIMPEZA (resolve erro JSON)
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
# EXTRAÇÃO SIMPLES (mock)
# =========================
def extrair_dados_pdf(nome_arquivo):
    # Simulação — depois podemos ler PDF de verdade
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
# SALVAR NO BANCO
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
# BUSCAR DADOS
# =========================
def carregar_exames():
    res = supabase.table("exames").select("*").execute()
    return res.data if res.data else []

def carregar_uploads():
    res = supabase.table("uploads").select("*").execute()
    return res.data if res.data else []

# =========================
# UI
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
# DADOS
# =========================
st.subheader("📈 Histórico de exames")

dados = carregar_exames()

if dados:
    df = pd.DataFrame(dados)

    st.dataframe(df)

    # gráfico simples
    if "valor" in df.columns:
        st.line_chart(df["valor"])

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
