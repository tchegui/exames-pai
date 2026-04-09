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

    dados = []

    # PEGAR NOME DO PACIENTE
    nome_match = re.search(r'\n([A-Z\s]+)\n\d{2}/\d{2}/\d{4}', texto)
    nome_paciente = nome_match.group(1).strip() if nome_match else "Paciente"

    # PEGAR DATA
    data_match = re.search(r'COLETADO EM: (\d{2}/\d{2}/\d{4})', texto)
    data = datetime.strptime(data_match.group(1), "%d/%m/%Y") if data_match else datetime.now()

    # EXAMES QUE QUEREMOS
    EXAMES_VALIDOS = [
        "PROTEINA C-REATIVA",
        "ACIDO LACTICO",
        "SODIO",
        "POTASSIO",
        "MAGNESIO",
        "UREIA",
        "CREATININA"
    ]

    # REGEX PRINCIPAL
    padrao = re.findall(
        r'([A-ZÁÉÍÓÚÇ\s,]+)\s*\n.*?RESULTADO.*?([\d,\.]+)\s*(mg/dL|mEq/L|mmol/L)',
        texto,
        re.DOTALL
    )

    for nome, valor, unidade in padrao:
        nome_limpo = nome.strip()

        if any(exame in nome_limpo for exame in EXAMES_VALIDOS):
            dados.append({
                "exame": nome_limpo,
                "valor": float(valor.replace(",", ".")),
                "unidade": unidade
            })

    # GASOMETRIA
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
