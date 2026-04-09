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

# ================= FUNÇÕES =================

def gerar_hash(arquivo):
    return hashlib.md5(arquivo.read()).hexdigest()


def extrair_texto(pdf):
    texto = ""
    with pdfplumber.open(pdf) as pdf_file:
        for page in pdf_file.pages:
            texto += page.extract_text() + "\n"
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
        # nome do exame (linha em maiúsculo + vírgula)
        if re.match(r"^[A-ZÇÃÕÁÉÍÓÚ ,\-()]+$", linha) and "," in linha:

            nome = linha.strip()

            # procura valor nas próximas linhas
            for j in range(i+1, i+6):
                if j < len(linhas):
                    valor_match = re.search(r"(\d+[\.,]?\d*)\s*(mg/dL|mmol/L|U/L|mEq/L|%)", linhas[j])

                    if valor_match:
                        valor = float(valor_match.group(1).replace(",", "."))
                        unidade = valor_match.group(2)

                        exames.append({
                            "nome_exame": nome,
                            "valor": valor,
                            "unidade": unidade
                        })
                        break

    return exames


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

    hash_arquivo = gerar_hash(arquivo)

    # verificar duplicado
    existente = supabase.table("exames").select("*").eq("arquivo_hash", hash_arquivo).execute()

    if existente.data:
        st.warning("⚠️ Este arquivo já foi enviado.")
    else:
        texto = extrair_texto(arquivo)

        dados = {
            "paciente": extrair_paciente(texto),
            "data": extrair_data(texto),
            "exames": extrair_exames(texto)
        }

        st.subheader("📋 Dados do exame")

        st.markdown(f"""
        **Paciente:** {dados['paciente']}  
        **Data do exame:** {dados['data']}
        """)

        df_preview = pd.DataFrame(dados["exames"])
        st.dataframe(df_preview)

        if st.button("Salvar no banco"):
            salvar_exames(dados, hash_arquivo)
            st.success("Salvo com sucesso!")


# ================= DASHBOARD =================

st.subheader("📈 Evolução dos exames")

dados_db = supabase.table("exames").select("*").execute().data

if dados_db:
    df = pd.DataFrame(dados_db)

    exame_escolhido = st.selectbox(
        "Selecione o exame",
        df["nome_exame"].unique()
    )

    df_filtrado = df[df["nome_exame"] == exame_escolhido]

    fig = px.line(
        df_filtrado,
        x="data_exame",
        y="valor",
        markers=True  # 🔥 CORREÇÃO DO GRÁFICO
    )

    st.plotly_chart(fig, use_container_width=True)
