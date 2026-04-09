import streamlit as st
import pdfplumber
import re
import hashlib
from datetime import datetime
import pandas as pd
import plotly.express as px
from supabase import create_client

# ================= CONFIG =================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= LOGIN =================
if "logado" not in st.session_state:
    st.session_state.logado = False

def login():
    st.title("🔐 Login")
    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == "admin" and senha == "123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Erro no login")

if not st.session_state.logado:
    login()
    st.stop()

st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logado": False}))

# ================= FUNÇÕES =================

def gerar_hash(arquivo):
    conteudo = arquivo.read()
    arquivo.seek(0)
    return hashlib.md5(conteudo).hexdigest(), conteudo


def extrair_texto_bytes(conteudo):
    texto = ""
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for p in pdf.pages:
            texto += p.extract_text() + "\n"
    return texto


def extrair_data(texto):
    match = re.search(r"Data da Ficha:\s*\n?\s*\d+\n(\d{2}/\d{2}/\d{4})", texto)
    if match:
        return datetime.strptime(match.group(1), "%d/%m/%Y").date()
    return None


def extrair_paciente(texto):
    linhas = texto.split("\n")
    for i, linha in enumerate(linhas):
        if "Cliente:" in linha:
            return linhas[i+1].strip()
    return "Paciente"


def extrair_exames(texto):
    exames = []
    linhas = texto.split("\n")

    for i, linha in enumerate(linhas):
        if re.match(r"^[A-ZÇÃÕÁÉÍÓÚ ,\-()]+$", linha) and "," in linha:
            nome = linha.strip()

            for j in range(i+1, i+6):
                if j < len(linhas):
                    m = re.search(r"(\d+[\.,]?\d*)\s*(mg/dL|mmol/L|U/L|mEq/L|%)", linhas[j])
                    if m:
                        exames.append({
                            "nome_exame": nome,
                            "valor": float(m.group(1).replace(",", ".")),
                            "unidade": m.group(2)
                        })
                        break
    return exames


def salvar_upload(paciente, data, hash_arquivo, nome):
    supabase.table("uploads").insert({
        "paciente": paciente,
        "data_exame": str(data),
        "arquivo_hash": hash_arquivo,
        "nome_arquivo": nome
    }).execute()


def salvar_exames(dados, hash_arquivo):
    lista = []
    for ex in dados["exames"]:
        lista.append({
            "paciente": dados["paciente"],
            "data_exame": str(dados["data"]),
            "nome_exame": ex["nome_exame"],
            "valor": ex["valor"],
            "unidade": ex["unidade"],
            "arquivo_hash": hash_arquivo
        })

    if lista:
        supabase.table("exames").insert(lista).execute()

# ================= UI =================

st.title("📊 Dashboard de Exames")

arquivo = st.file_uploader("Envie o PDF", type="pdf")

if arquivo:

    hash_arquivo, conteudo = gerar_hash(arquivo)

    existe = supabase.table("uploads").select("*").eq("arquivo_hash", hash_arquivo).execute()

    if existe.data:
        st.warning("Arquivo já enviado")
    else:
        texto = extrair_texto_bytes(conteudo)

        dados = {
            "paciente": extrair_paciente(texto),
            "data": extrair_data(texto),
            "exames": extrair_exames(texto)
        }

        st.write(dados)

        if st.button("Salvar"):
            salvar_upload(dados["paciente"], dados["data"], hash_arquivo, arquivo.name)
            salvar_exames(dados, hash_arquivo)
            st.success("Salvo!")

# ================= DASHBOARD =================

dados_db = supabase.table("exames").select("*").execute().data

if dados_db:
    df = pd.DataFrame(dados_db)

    exame = st.selectbox("Exame", df["nome_exame"].unique())

    df_f = df[df["nome_exame"] == exame]

    fig = px.line(df_f, x="data_exame", y="valor", markers=True)
    st.plotly_chart(fig, use_container_width=True)
