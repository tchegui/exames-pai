import streamlit as st
import pdfplumber
import io

st.title("🔎 INSPEÇÃO DE PDF (DEBUG PROFISSIONAL)")

arquivo = st.file_uploader("Envie o PDF", type="pdf")

if arquivo:
    conteudo = arquivo.read()

    texto_total = ""

    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for i, pagina in enumerate(pdf.pages):
            texto = pagina.extract_text()

            st.markdown(f"---")
            st.subheader(f"📄 Página {i+1}")

            if texto:
                linhas = texto.split("\n")

                # 🔢 MOSTRA LINHAS NUMERADAS
                for idx, linha in enumerate(linhas):
                    st.text(f"{idx:03d} | {linha}")

            else:
                st.warning("Página sem texto extraído")

            texto_total += (texto or "") + "\n"

    # TEXTO COMPLETO (opcional)
    with st.expander("📜 Texto completo"):
        st.text(texto_total[:5000])
