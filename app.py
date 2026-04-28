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

TEMPERATURAS = ["Temperatura1", "Temperatura2", "Temperatura3", "Temperatura4"]


# =========================
# FUNÇÕES AUXILIARES
# =========================
def tratar_coluna_temperatura(df, col):
    df[col] = df[col].astype(str).str.strip()
    df[col] = df[col].str.replace(",", ".", regex=False)
    df[col] = df[col].str.replace("°C", "", regex=False)
    df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def criar_gauge(valor_atual, valor_min, valor_max, titulo):
    gauge_min = min(0, int(valor_min) - 5)
    gauge_max = max(50, int(valor_max) + 5)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor_atual,
        number={"suffix": " °C", "valueformat": ".2f"},
        title={"text": titulo},
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
                "value": valor_atual
            }
        }
    ))

    fig.update_layout(height=320, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def criar_grafico_sensor(df_sensor, nome_sensor):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_sensor["DataHora"],
        y=df_sensor[nome_sensor],
        mode="lines",
        name=nome_sensor
    ))

    fig.update_layout(
        title=f"Evolução - {nome_sensor}",
        xaxis_title="Data/Hora",
        yaxis_title="Temperatura (°C)",
        height=320,
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h")
    )
    return fig


def criar_grafico_geral(df_valid):
    fig = go.Figure()

    for sensor in TEMPERATURAS:
        fig.add_trace(go.Scatter(
            x=df_valid["DataHora"],
            y=df_valid[sensor],
            mode="lines",
            name=sensor
        ))

    fig.update_layout(
        title="Evolução das Temperaturas - Todos os Sensores",
        xaxis_title="Data/Hora",
        yaxis_title="Temperatura (°C)",
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h")
    )
    return fig


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
    df.columns = df.columns.str.strip()

    # =========================
    # TRATAMENTO DE DATA/HORA
    # =========================
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
        st.error("A planilha precisa ter as colunas DataHora e Temperatura1..Temperatura4, ou Data, Hora e Temperatura1..Temperatura4.")
        return

    # =========================
    # VALIDAÇÃO DAS COLUNAS
    # =========================
    colunas_faltando = [col for col in TEMPERATURAS if col not in df.columns]
    if colunas_faltando:
        st.error(f"As seguintes colunas de temperatura não foram encontradas: {', '.join(colunas_faltando)}")
        return

    # =========================
    # TRATAMENTO DAS TEMPERATURAS
    # =========================
    for col in TEMPERATURAS:
        df = tratar_coluna_temperatura(df, col)

    # =========================
    # FILTRAGEM
    # =========================
    #df_valid = df.dropna(subset=["DataHora"]).sort_values("DataHora").copy()
    #df_valid = df_valid.dropna(subset=TEMPERATURAS, how="all")

    df_valid = df.dropna(subset=["DataHora"]).sort_values("DataHora").copy()
    df_valid = df_valid.dropna(subset=TEMPERATURAS, how="all")

    # Filtrar somente últimas 24 horas
    agora = pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None)
    limite_24h = agora - pd.Timedelta(hours=24)

    df_valid = df_valid[df_valid["DataHora"] >= limite_24h]

    if df_valid.empty:
        st.error("Os dados existem, mas nenhuma linha válida foi encontrada após o tratamento.")
        return

    datahora_atual = df_valid.iloc[-1]["DataHora"]
    st.write(f"Última leitura: **{datahora_atual.strftime('%d/%m/%Y %H:%M:%S')}**")

    # =========================
    # MÉTRICAS ATUAIS
    # =========================
    st.subheader("Temperaturas Atuais")
    cols_metric = st.columns(4)

    for i, sensor in enumerate(TEMPERATURAS):
        serie_valida = df_valid[sensor].dropna()
        if not serie_valida.empty:
            valor_atual = float(serie_valida.iloc[-1])
            cols_metric[i].metric(sensor, f"{valor_atual:.2f} °C")
        else:
            cols_metric[i].metric(sensor, "Sem dado")

    # =========================
    # 1 GAUGE + 1 GRÁFICO POR SENSOR
    # =========================
    st.subheader("Painel por Sensor")

    for sensor in TEMPERATURAS:
        df_sensor = df_valid[["DataHora", sensor]].dropna().copy()

        st.markdown(f"### {sensor}")

        col_gauge, col_grafico = st.columns([1, 2])

        with col_gauge:
            if df_sensor.empty:
                st.warning(f"{sensor} sem dados válidos.")
            else:
                valor_atual = float(df_sensor.iloc[-1][sensor])
                valor_min = float(df_sensor[sensor].min())
                valor_max = float(df_sensor[sensor].max())

                fig_gauge = criar_gauge(
                    valor_atual=valor_atual,
                    valor_min=valor_min,
                    valor_max=valor_max,
                    titulo=sensor
                )
                st.plotly_chart(fig_gauge, use_container_width=True)

        with col_grafico:
            if df_sensor.empty:
                st.warning(f"{sensor} sem dados para gráfico.")
            else:
                fig_sensor = criar_grafico_sensor(df_sensor, sensor)
                st.plotly_chart(fig_sensor, use_container_width=True)

    # =========================
    # GRÁFICO GERAL COM OS 4 SENSORES
    # =========================
    st.subheader("Gráfico Geral dos 4 Sensores")
    fig_geral = criar_grafico_geral(df_valid)
    st.plotly_chart(fig_geral, use_container_width=True)

    # =========================
    # TABELA OPCIONAL
    # =========================
    with st.expander("Ver dados tratados"):
        st.dataframe(df_valid[["DataHora"] + TEMPERATURAS], use_container_width=True)


painel_temperatura()
