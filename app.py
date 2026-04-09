import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
import os

st.set_page_config(layout="wide")

# =========================
# LOGIN SIMPLES
# =========================
USUARIO = "familia"
SENHA = "1234"

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == USUARIO and pwd == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

    st.stop()

# =========================
# APP
# =========================
st.title("📊 Monitor de Exames")

ARQUIVO_DADOS = "historico_exames.csv"

if os.path.exists(ARQUIVO_DADOS):
    historico = pd.read_csv(ARQUIVO_DADOS, parse_dates=["data"])
else:
    historico = pd.DataFrame(columns=["paciente", "data", "exame", "valor", "unidade"])

uploaded_file = st.file_uploader("Envie PDF", type="pdf")

MAPA_EXAMES = {
    "HEMOGLOBINA": "HEMOGLOBINA",
    "LEUCÓCITOS": "LEUCOCITOS",
    "PLAQUETAS": "PLAQUETAS",
    "POTASSIO": "POTASSIO",
    "SODIO": "SODIO",
    "PROTEINA C-REATIVA": "PCR",
}

LIMITES = {
    "HEMOGLOBINA": (12, 17),
    "LEUCOCITOS": (4000, 10000),
    "PCR": (0, 0.5),
    "POTASSIO": (3.5, 5.1),
}

def normalizar_exame(nome):
    nome = nome.upper()
    for k in MAPA_EXAMES:
        if k in nome:
            return MAPA_EXAMES[k]
    return nome

def extrair_dados(pdf_file):
    texto = ""
    with pdfplumber.open(pdf_file) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                texto += t + "\n"

    linhas = texto.split("\n")
    dados = []

    paciente = "Paciente"
    data = datetime.now()

    for linha in linhas:
        if "OBERON" in linha.upper():
            paciente = linha.strip()

        if "COLETADO EM:" in linha:
            m = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
            if m:
                data = datetime.strptime(m.group(1), "%d/%m/%Y")

        match = re.search(
            r'([A-ZÇÃÉÍÓÚ\s]+?)\s*[:]\s*([\d\.,]+)\s*(mg/dL|mEq/L|mmol/L|g/dL|U/L|%|mmHg|/mm3)',
            linha
        )

        if match:
            nome = normalizar_exame(match.group(1))
            valor = float(match.group(2).replace(".", "").replace(",", "."))
            unidade = match.group(3)

            dados.append({
                "paciente": paciente,
                "data": data,
                "exame": nome,
                "valor": valor,
                "unidade": unidade
            })

    return pd.DataFrame(dados)

def interpretar(df, exame):
    if exame not in LIMITES or len(df) < 1:
        return "Sem interpretação disponível"

    min_v, max_v = LIMITES[exame]
    atual = df.iloc[-1]["valor"]

    texto = ""

    if atual < min_v:
        texto += "🔴 Abaixo do normal. "
    elif atual > max_v:
        texto += "🔴 Acima do normal. "
    else:
        texto += "🟢 Dentro do normal. "

    if len(df) >= 2:
        anterior = df.iloc[-2]["valor"]
        if atual > anterior:
            texto += "📈 Tendência de alta."
        elif atual < anterior:
            texto += "📉 Tendência de queda."

    return texto

# =========================
# PROCESSAR PDF
# =========================
if uploaded_file:
    novo = extrair_dados(uploaded_file)

    if not novo.empty:
        historico = pd.concat([historico, novo]).drop_duplicates()
        historico.to_csv(ARQUIVO_DADOS, index=False)
        st.success("Dados adicionados!")

# =========================
# VISUALIZAÇÃO
# =========================
if not historico.empty:

    paciente = st.selectbox("Paciente", historico["paciente"].unique())
    df_p = historico[historico["paciente"] == paciente]

    exame = st.selectbox("Exame", df_p["exame"].unique())
    df_f = df_p[df_p["exame"] == exame].sort_values("data")

    fig = px.line(df_f, x="data", y="valor", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧠 Interpretação")
    st.info(interpretar(df_f, exame))

    st.dataframe(df_f)

else:
    st.info("Envie exames para começar.")
