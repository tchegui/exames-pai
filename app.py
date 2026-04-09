import streamlit as st
import pdfplumber
import io
import re
import hashlib
from datetime import datetime
from supabase import create_client
import pandas as pd
import plotly.express as px

# =============================
# CONFIG
# =============================
SUPABASE_URL = "SUA_URL"
SUPABASE_KEY = "SUA_KEY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# LOGIN
# =============================
USUARIO = "admin"
SENHA = "1234"

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == USUARIO and password == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# =============================
# FUNÇÕES
# =============================
def hash_arquivo(conteudo):
    return hashlib.md5(conteudo).hexdigest()


def extrair_texto(conteudo):
    texto_total = ""
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for pagina in pdf.pages:
            texto_total += pagina.extract_text() + "\n"
    return texto_total


def parse_pdf(texto):
    linhas = texto.split("\n")

    paciente = ""
    data_exame = None

    exames = []

    grupo = None

    datas_laudo = []

    for i, linha in enumerate(linhas):

        # PACIENTE
        if "Cliente:" in linha:
            paciente = linha.split("Cliente:")[1].strip()

        # DATA CORRETA
        if "Data da Ficha:" in linha:
            data_str = linha.split("Data da Ficha:")[1].strip()
            data_exame = datetime.strptime(data_str, "%d/%m/%Y").date()

        # DETECTAR GRUPOS
        if "HEMOGRAMA" in linha:
            grupo = "Hemograma"

        elif "GASOMETRIA ARTERIAL" in linha:
            grupo = "Gasometria"

        elif "LAUDO EVOLUTIVO" in linha:
            grupo = "Evolutivo"

        # =============================
        # HEMOGRAMA / GASOMETRIA
        # =============================
        match = re.match(r"([A-Za-zÇÃÉÍÓÚÔÊÕçãéíóúôêõ ]+)\s*:\s*([\d,.-]+)", linha)

        if match and grupo in ["Hemograma", "Gasometria"]:
            nome = match.group(1).strip()
            valor = float(match.group(2).replace(",", "."))

            exames.append({
                "grupo": grupo,
                "nome_exame": nome,
                "valor": valor,
                "unidade": "",
                "ref_min": None,
                "ref_max": None,
                "data_referencia": data_exame
            })

        # =============================
        # EXAMES SIMPLES
        # =============================
        match2 = re.search(r"([\d,]+)\s*(mg/dL|mEq/L|mmol/L|%)", linha)

        if match2:
            valor = float(match2.group(1).replace(",", "."))
            unidade = match2.group(2)

            nome = linhas[i-2].strip() if i > 2 else "Exame"

            exames.append({
                "grupo": "Simples",
                "nome_exame": nome,
                "valor": valor,
                "unidade": unidade,
                "ref_min": None,
                "ref_max": None,
                "data_referencia": data_exame
            })

        # =============================
        # LAUDO EVOLUTIVO
        # =============================
        if grupo == "Evolutivo":

            if re.match(r"\d{2}/\d{2}/\d{4}", linha):
                datas_laudo = [
                    datetime.strptime(d, "%d/%m/%Y").date()
                    for d in linha.split()
                ]

            elif ":" in linha and len(datas_laudo) > 0:
                partes = linha.split()
                nome = partes[0]

                valores = re.findall(r"[\d,]+", linha)

                for j, v in enumerate(valores):
                    if j < len(datas_laudo):
                        exames.append({
                            "grupo": "Evolutivo",
                            "nome_exame": nome,
                            "valor": float(v.replace(",", ".")),
                            "unidade": "",
                            "ref_min": None,
                            "ref_max": None,
                            "data_referencia": datas_laudo[j]
                        })

    return paciente, data_exame, exames


# =============================
# UI
# =============================
st.title("📊 Dashboard de Exames")

arquivo = st.file_uploader("Upload PDF", type="pdf")

if arquivo:
    conteudo = arquivo.read()
    hash_arq = hash_arquivo(conteudo)

    texto = extrair_texto(conteudo)
    paciente, data_exame, exames = parse_pdf(texto)

    st.write("Paciente:", paciente)
    st.write("Data:", data_exame)
    st.write("Exames extraídos:", len(exames))

    # SALVAR PDF
    supabase.table("uploads").upsert({
        "nome_arquivo": arquivo.name,
        "arquivo_hash": hash_arq
    }).execute()

    # SALVAR EXAMES
    for ex in exames:
        supabase.table("exames").upsert({
            "paciente": paciente,
            "data_exame": data_exame,
            "grupo": ex["grupo"],
            "nome_exame": ex["nome_exame"],
            "valor": ex["valor"],
            "unidade": ex["unidade"],
            "ref_min": ex["ref_min"],
            "ref_max": ex["ref_max"],
            "data_referencia": ex["data_referencia"],
            "arquivo_hash": hash_arq
        }).execute()

    st.success("Dados salvos!")

# =============================
# DASHBOARD
# =============================
dados = supabase.table("exames").select("*").execute().data

if dados:
    df = pd.DataFrame(dados)

    exame_escolhido = st.selectbox("Escolha o exame", df["nome_exame"].unique())

    df_filtrado = df[df["nome_exame"] == exame_escolhido]

    fig = px.line(
        df_filtrado,
        x="data_referencia",
        y="valor",
        markers=True
    )

    # FAIXA DE REFERÊNCIA (visual)
    fig.add_hrect(
        y0=df_filtrado["ref_min"].min() if df_filtrado["ref_min"].notnull().any() else 0,
        y1=df_filtrado["ref_max"].max() if df_filtrado["ref_max"].notnull().any() else 0,
        fillcolor="green",
        opacity=0.1,
        line_width=0,
    )

    st.plotly_chart(fig)
