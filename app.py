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
SUPABASE_URL = "https://uizkcuwcraqqohfxjapw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVpemtjdXdjcmFxcW9oZnhqYXB3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MjEwMDgsImV4cCI6MjA5MTI5NzAwOH0.Pm3RC19zzkatXzsaqu6wjfQQBgleZ4Od5O1mSkanTyE"

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

    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        if user.strip() == USUARIO and password.strip() == SENHA:
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
            texto = pagina.extract_text()
            if texto:
                texto_total += texto + "\n"
    return texto_total


def limpar_numero(valor):
    if not valor:
        return None

    valor = re.sub(r"[^\d,.\-]", "", valor)
    valor = valor.replace(",", ".")

    try:
        return float(valor)
    except:
        return None


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

        # GRUPOS
        if "HEMOGRAMA" in linha:
            grupo = "Hemograma"

        elif "GASOMETRIA ARTERIAL" in linha:
            grupo = "Gasometria"

        elif "LAUDO EVOLUTIVO" in linha:
            grupo = "Evolutivo"

        # =============================
        # HEMOGRAMA / GASOMETRIA
        # =============================
        match = re.match(r"([A-Za-zÇÃÉÍÓÚÔÊÕçãéíóúôêõ ]+)\s*:\s*([\d,.\-]+)", linha)

        if match and grupo in ["Hemograma", "Gasometria"]:
            nome = match.group(1).strip()
            valor = limpar_numero(match.group(2))

            if valor is None:
                continue

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
        match2 = re.search(r"([\d,.\-]+)\s*(mg/dL|mEq/L|mmol/L|%)", linha)

        if match2:
            valor = limpar_numero(match2.group(1))
            unidade = match2.group(2)

            if valor is None:
                continue

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

            elif len(datas_laudo) > 0:

                valores = re.findall(r"[\d,.\-]+", linha)

                if len(valores) >= 2:
                    nome = linha.split()[0]

                    for j, v in enumerate(valores):
                        valor = limpar_numero(v)

                        if valor is None:
                            continue

                        if j < len(datas_laudo):
                            exames.append({
                                "grupo": "Evolutivo",
                                "nome_exame": nome,
                                "valor": valor,
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

    # SALVAR UPLOAD
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

    # faixa (placeholder até extrair referência real)
    fig.add_hrect(
        y0=df_filtrado["valor"].min(),
        y1=df_filtrado["valor"].max(),
        opacity=0.05,
        line_width=0,
    )

    st.plotly_chart(fig)
