import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# =========================
# CONFIGURAÇÃO INICIAL
# =========================
st.set_page_config(page_title="Dashboard", layout="wide")

# Credenciais simples para teste
USERNAME = "admin"
PASSWORD = "admin"

# =========================
# CONTROLE DE SESSÃO
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def login():
    st.title("Acesso ao Dashboard")

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
                st.success("Login realizado com sucesso.")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")


def logout():
    st.session_state.logged_in = False
    st.rerun()


# =========================
# TELA DE LOGIN
# =========================
if not st.session_state.logged_in:
    login()
    st.stop()

# =========================
# CABEÇALHO
# =========================
st.title("Dashboard de Temperatura")

col_top1, col_top2 = st.columns([6, 1])
with col_top2:
    if st.button("Sair"):
        logout()

conn = st.connection("gsheets", type=GSheetsConnection)


# =========================
# PAINEL COM AUTOATUALIZAÇÃO
# =========================
@st.fragment(run_every="30s")
def painel_temperatura():
    df = conn.read(
        spreadsheet="https://docs.google.com/spreadsheets/d/13i86WpmQ62Bu9nF0LTeH_NgSpQeagO1VTY8ad2XUQL8/edit#gid=1592592023",
        ttl=0
    )

    if df is None or len(df) == 0:
        st.error("Erro ao carregar dados da planilha ou planilha vazia.")
        return

    df = pd.DataFrame(df)

    # DEBUG
    st.subheader("1. Colunas encontradas")
    st.write(list(df.columns))

    st.subheader("2. Dados brutos lidos da planilha")
    st.dataframe(df, use_container_width=True)

    st.subheader("3. Tipos das colunas")
    st.write(df.dtypes)

    # =========================
    # TRATAMENTO DE DADOS
    # =========================
    df.columns = df.columns.str.strip()

    if "Temperatura" in df.columns:
        df["Temperatura"] = df["Temperatura"].astype(str).str.strip()
        df["Temperatura"] = df["Temperatura"].str.replace(",", ".", regex=False)
        df["Temperatura"] = df["Temperatura"].str.replace("°C", "", regex=False)
        df["Temperatura"] = pd.to_numeric(df["Temperatura"], errors="coerce")

    if "DataHora" in df.columns:
        df["DataHora"] = df["DataHora"].astype(str).str.strip()
        df["DataHora"] = pd.to_datetime(df["DataHora"], errors="coerce", dayfirst=True)
    elif "Data" in df.columns and "Hora" in df.columns:
        df["DataHora"] = pd.to_datetime(
            df["Data"].astype(str).str.strip() + " " + df["Hora"].astype(str).str.strip(),
            errors="coerce",
            dayfirst=True
        )
    else:
        st.error("A planilha precisa ter as colunas DataHora e Temperatura, ou Data, Hora e Temperatura.")
        return

    st.subheader("4. Dados após tratamento")
    st.dataframe(df, use_container_width=True)

    df_valid = df.dropna(subset=["DataHora", "Temperatura"]).sort_values("DataHora")

    st.subheader("5. Dados válidos para gráfico")
    st.dataframe(df_valid, use_container_width=True)

    if df_valid.empty:
        st.error("Os dados existem, mas nenhum registro ficou válido após o tratamento.")
        return

    # =========================
    # INDICADORES
    # =========================
    temperatura_atual = float(df_valid.iloc[-1]["Temperatura"])
    datahora_atual = df_valid.iloc[-1]["DataHora"]
    temperatura_media = float(df_valid["Temperatura"].mean())
    temperatura_maxima = float(df_valid["Temperatura"].max())
    temperatura_minima = float(df_valid["Temperatura"].min())

    gauge_min = min(0, int(temperatura_minima) - 5)
    gauge_max = max(50, int(temperatura_maxima) + 5)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Temperatura Atual", f"{temperatura_atual:.2f} °C")
    col2.metric("Temperatura Média", f"{temperatura_media:.2f} °C")
    col3.metric("Temperatura Máxima", f"{temperatura_maxima:.2f} °C")
    col4.metric("Temperatura Mínima", f"{temperatura_minima:.2f} °C")

    st.write(f"Última leitura: **{datahora_atual.strftime('%d/%m/%Y %H:%M:%S')}**")

    # =========================
    # GAUGE
    # =========================
    st.subheader("Gauge da Temperatura Atual")

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temperatura_atual,
        number={"suffix": " °C", "valueformat": ".2f"},
        title={"text": "Temperatura Atual"},
        gauge={
            "axis": {"range": [gauge_min, gauge_max]},
            "steps": [
                {"range": [gauge_min, 18], "color": "lightblue"},
                {"range": [18, 26], "color": "lightgreen"},
                {"range": [26, gauge_max], "color": "salmon"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": temperatura_atual
            }
        }
    ))

    fig_gauge.update_layout(height=350)
    st.plotly_chart(fig_gauge, use_container_width=True)

    # =========================
    # GRÁFICOS
    # =========================
    st.subheader("Evolução da Temperatura")
    st.line_chart(df_valid.set_index("DataHora")["Temperatura"])

    st.subheader("Temperatura por leitura")
    st.bar_chart(df_valid.set_index("DataHora")["Temperatura"])


painel_temperatura()