import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import matplotlib.pyplot as plt

st.title("📊 Leitor de Exames")

uploaded_file = st.file_uploader("Envie seu PDF", type="pdf")

def extrair_dados(pdf_file):
    texto = ""

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

    linhas = texto.split("\n")
    dados = []

    nome_paciente = "Paciente"
    data = datetime.now()

    # =========================
    # PEGAR NOME E DATA
    # =========================
    for i, linha in enumerate(linhas):
        linha_limpa = linha.strip()

        # detectar data e nome acima
        if re.match(r'\d{2}/\d{2}/\d{4}', linha_limpa):
            if i > 0:
                nome_paciente = linhas[i-1].strip()

        # detectar data coleta
        if "COLETADO EM:" in linha:
            match = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
            if match:
                data = datetime.strptime(match.group(1), "%d/%m/%Y")

    # =========================
    # EXTRAÇÃO POR BLOCOS
    # =========================
    for i in range(len(linhas)):

        linha = linhas[i].strip()

        # Nome de exame em caixa alta
        if linha.isupper() and len(linha) > 5:

            nome_exame = linha

            # procurar valor nas próximas linhas
            for j in range(i, min(i+10, len(linhas))):
                linha2 = linhas[j]

                match = re.search(r'([\d,\.]+)\s*(mg/dL|mEq/L|mmol/L)', linha2)

                if match:
                    valor = float(match.group(1).replace(",", "."))
                    unidade = match.group(2)

                    dados.append({
                        "exame": nome_exame,
                        "valor": valor,
                        "unidade": unidade
                    })
                    break

    # =========================
    # GASOMETRIA
    # =========================
    gasometria = re.findall(
        r'(pH|pO2|pCO2|HCO3|BE|SO2)\s*:\s*([\d,\.]+)',
        texto
    )

    for nome, valor in gasometria:
        dados.append({
            "exame": f"GASOMETRIA - {nome}",
            "valor": float(valor.replace(",", ".")),
            "unidade": ""
        })

    return dados, data, nome_paciente


# =========================
# INTERFACE
# =========================
if uploaded_file:
    dados, data, nome_paciente = extrair_dados(uploaded_file)

    st.subheader(f"👤 {nome_paciente}")
    st.write(f"📅 Data do exame: {data.strftime('%d/%m/%Y')}")

    df = pd.DataFrame(dados)

    st.dataframe(df)

    if not df.empty:
        exame = st.selectbox("Escolha o exame", df["exame"].unique())

        df_f = df[df["exame"] == exame]

        plt.figure()
        plt.plot(df_f.index, df_f["valor"], marker="o")
        plt.title(exame)

        st.pyplot(plt)
