import streamlit as st
import pdfplumber
import re
import hashlib
import io
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

if not st.session_state.logado:

    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario == "admin" and senha == "123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

st.sidebar.button(
    "Logout",
    on_click=lambda: st.session_state.update({"logado": False})
)

# ================= FUNÇÕES =================

def gerar_hash(arquivo):
    conteudo = arquivo.read()
    arquivo.seek(0)
    return hashlib.md5(conteudo).hexdigest(), conteudo


def extrair_texto_bytes(conteudo):
    texto = ""
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                texto += t + "\n"
    return texto


def extrair_paciente(texto):
    match = re.search(r"Cliente:\s*(.+)", texto)
    if match:
        return match.group(1).strip()
    return "Paciente"


def extrair_data(texto):
    match = re.search(r"Data da Ficha:.*?(\d{2}/\d{2}/\d{4})", texto)
    if match:
        return datetime.strptime(match.group(1), "%d/%m/%Y").date()
    return None


def extrair_exames(texto):
    exames = []
    linhas = texto.split("\n")

    nome_atual = None

    for linha in linhas:
        linha = linha.strip()

        # Detecta nome do exame
        if (
            len(linha) > 3 and
            linha.isupper() and
            not re.search(r"\d", linha) and
            "REFER" not in linha and
            "MATERIAL" not in linha and
            "INTERVALO" not in linha
        ):
            nome_atual = linha
            continue

        # Detecta valor
        match = re.search(r"(\d+[\.,]?\d*)\s*(mg/dL|mmol/L|U/L|mEq/L|%)", linha)

        if match and nome_atual:
            exames.append({
                "nome_exame": nome_atual.strip(),
                "valor": float(match.group(1).replace(",", ".")),
                "unidade": match.group(2)
            })
            nome_atual = None

    return exames


def salvar_upload(paciente, data, hash_arquivo, nome):
    supabase.table("uploads").insert({
        "paciente": paciente,
        "data_exame": str(data) if data else None,
        "arquivo_hash": hash_arquivo,
        "nome_arquivo": nome
    }).execute()


def salvar_exames(dados, hash_arquivo):
    lista = []

    for ex in dados["exames"]:
        lista.append({
            "paciente": dados["paciente"],
            "data_exame": str(dados["data"]) if dados["data"] else None,
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
        st.warning("⚠️ Esse arquivo já foi enviado.")
    else:
        texto = extrair_texto_bytes(conteudo)

        with st.expander("🔍 Texto extraído (debug)"):
            st.text(texto[:2000])

        dados = {
            "paciente": extrair_paciente(texto),
            "data": extrair_data(texto),
            "exames": extrair_exames(texto)
        }

        st.subheader("📋 Dados extraídos")
        st.json(dados)

        if st.button("💾 Salvar no banco"):
            salvar_upload(dados["paciente"], dados["data"], hash_arquivo, arquivo.name)
            salvar_exames(dados, hash_arquivo)
            st.success("✅ Dados salvos com sucesso!")

# ================= DASHBOARD =================

st.divider()
st.subheader("📈 Evolução dos Exames")

dados_db = supabase.table("exames").select("*").execute().data

if dados_db:
    df = pd.DataFrame(dados_db)

    df["data_exame"] = pd.to_datetime(df["data_exame"])

    exame = st.selectbox("Selecione o exame", df["nome_exame"].unique())

    df_f = df[df["nome_exame"] == exame].sort_values("data_exame")

    fig = px.line(
        df_f,
        x="data_exame",
        y="valor",
        markers=True
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_f)

else:
    st.info("Nenhum exame ainda salvo.")
