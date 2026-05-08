import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="SCADA | Monitor de Temperatura",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

USERNAME  = "admin"
PASSWORD  = "admin"
TEMPERATURAS = ["Temperatura1", "Temperatura2", "Temperatura3", "Temperatura4"]
CORES_SENSORES = {
    "Temperatura1": "#00d4ff",
    "Temperatura2": "#06ffa5",
    "Temperatura3": "#ffaa00",
    "Temperatura4": "#ff3860",
}
LIM_FRIO       = 18.0
LIM_NORMAL_MAX = 26.0
LIM_ALERTA_MAX = 32.0
STALE_MIN      = 5

# =========================================================
# CSS — injetado FORA do fragment (funciona normalmente)
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

.stApp {
    background: radial-gradient(ellipse at top, #0f1419 0%, #0a0e1a 60%, #060912 100%);
    color: #e0e6ed;
    font-family: 'Inter', sans-serif;
}
[data-testid="stHeader"] { background: transparent; height: 0; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding: 1rem 1.5rem 2rem 1.5rem; max-width: 100%; }

h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    color: #ffffff !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}
h3 { font-size: 1.1rem !important; font-weight: 700 !important; }

p, .stMarkdown p {
    color: #e0e6ed !important;
    font-family: 'Inter', sans-serif;
}

/* Caption / legenda */
.stCaption, [data-testid="stCaptionContainer"] p {
    color: #6c7a89 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* Metrics */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #131722, #1a1f2e) !important;
    border: 1px solid #2a3142 !important;
    border-left: 3px solid #00d4ff !important;
    border-radius: 4px !important;
    padding: 14px 16px !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem !important;
    color: #6c7a89 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.8rem !important;
    color: #ffffff !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}

/* Divider */
hr { border-color: #2a3142 !important; margin: 10px 0 !important; }

/* Button */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%) !important;
    color: #0a0e1a !important; border: none !important;
    font-weight: 700 !important; text-transform: uppercase !important;
    letter-spacing: 1.5px !important; font-size: 0.78rem !important;
    border-radius: 2px !important; transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00ffff 0%, #00d4ff 100%) !important;
    box-shadow: 0 0 16px rgba(0,212,255,0.45) !important;
}

/* Inputs */
.stTextInput input, .stPasswordInput input {
    background: #0a0e1a !important; border: 1px solid #2a3142 !important;
    color: #e0e6ed !important; font-family: 'JetBrains Mono', monospace !important;
    border-radius: 2px !important;
}
.stTextInput input:focus, .stPasswordInput input:focus {
    border-color: #00d4ff !important; box-shadow: 0 0 0 1px #00d4ff !important;
}
.stTextInput label, .stPasswordInput label {
    color: #6c7a89 !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem !important; text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: #131722 !important; border: 1px solid #2a3142 !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary {
    color: #e0e6ed !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important; text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
}

/* DataFrame / alerts / plotly */
.stDataFrame { background: #131722; border: 1px solid #2a3142; border-radius: 4px; }
.stAlert {
    background: #131722 !important; border: 1px solid #2a3142 !important;
    border-left: 3px solid #ff3860 !important; border-radius: 2px !important;
}
.js-plotly-plot, .plot-container { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# SESSION
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def classificar_temperatura(valor):
    if valor is None or pd.isna(valor):
        return "⚫ Offline", "#6c7a89"
    if valor < LIM_FRIO:
        return "❄ Frio", "#00b4d8"
    if valor <= LIM_NORMAL_MAX:
        return "✓ Normal", "#06ffa5"
    if valor <= LIM_ALERTA_MAX:
        return "⚠ Alerta", "#ffaa00"
    return "🔴 Crítico", "#ff3860"


# =========================================================
# LOGIN
# =========================================================
def login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("### ◉ SCADA")
        st.caption("Sistema de Supervisão · v1.0")
        st.divider()
        with st.form("login_form"):
            username  = st.text_input("Usuário")
            password  = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Autenticar", use_container_width=True)
            if submitted:
                if username == USERNAME and password == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")


def logout():
    st.session_state.logged_in = False
    st.rerun()


if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================================
# CONEXÃO
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)


def tratar_coluna_temperatura(df, col):
    df[col] = (
        df[col].astype(str).str.strip()
        .str.replace(",", ".", regex=False)
        .str.replace("°C", "", regex=False)
    )
    df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# =========================================================
# PLOTLY — GAUGE
# =========================================================
def criar_gauge(valor_atual, valor_min, valor_max, sensor):
    gauge_min = min(0, int(valor_min) - 5)
    gauge_max = max(50, int(valor_max) + 5)
    _, cor_bar = classificar_temperatura(valor_atual)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor_atual,
        number={
            "suffix": " °C", "valueformat": ".2f",
            "font": {"family": "JetBrains Mono, monospace", "size": 26, "color": "#ffffff"},
        },
        title={"text": sensor,
               "font": {"family": "JetBrains Mono, monospace", "size": 12, "color": "#6c7a89"}},
        gauge={
            "axis": {
                "range": [gauge_min, gauge_max], "tickwidth": 1,
                "tickcolor": "#3a4256",
                "tickfont": {"family": "JetBrains Mono, monospace", "size": 9, "color": "#6c7a89"},
            },
            "bar": {"color": cor_bar, "thickness": 0.28},
            "bgcolor": "#0a0e1a", "borderwidth": 1, "bordercolor": "#2a3142",
            "steps": [
                {"range": [gauge_min, LIM_FRIO],            "color": "rgba(0,180,216,0.18)"},
                {"range": [LIM_FRIO, LIM_NORMAL_MAX],       "color": "rgba(6,255,165,0.18)"},
                {"range": [LIM_NORMAL_MAX, LIM_ALERTA_MAX], "color": "rgba(255,170,0,0.18)"},
                {"range": [LIM_ALERTA_MAX, gauge_max],      "color": "rgba(255,56,96,0.18)"},
            ],
            "threshold": {"line": {"color": cor_bar, "width": 3}, "thickness": 0.85, "value": valor_atual},
        },
    ))
    fig.update_layout(
        height=240, margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e0e6ed"},
    )
    return fig


# =========================================================
# PLOTLY — TREND INDIVIDUAL
# =========================================================
def criar_grafico_sensor(df_sensor, nome_sensor):
    cor = CORES_SENSORES[nome_sensor]
    r, g, b = int(cor[1:3], 16), int(cor[3:5], 16), int(cor[5:7], 16)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sensor["DataHora"], y=df_sensor[nome_sensor],
        mode="lines", line=dict(color=cor, width=2),
        fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.07)",
        hovertemplate="%{x|%d/%m %H:%M:%S}<br>%{y:.2f} °C<extra></extra>",
    ))
    for lim, cl in [(LIM_FRIO, "#00b4d8"), (LIM_NORMAL_MAX, "#06ffa5"), (LIM_ALERTA_MAX, "#ffaa00")]:
        fig.add_hline(y=lim, line_dash="dot", line_color=cl, opacity=0.4, line_width=1)
    fig.update_layout(
        height=240, margin=dict(l=44, r=16, t=10, b=36),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0a0e1a",
        font=dict(family="JetBrains Mono, monospace", size=9, color="#6c7a89"),
        xaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89")),
        yaxis=dict(gridcolor="#1a1f2e", showgrid=True,
                   tickfont=dict(color="#6c7a89"), ticksuffix=" °C"),
        showlegend=False, hovermode="x unified",
        hoverlabel=dict(bgcolor="#131722", bordercolor=cor,
                        font=dict(family="JetBrains Mono, monospace", color="#fff")),
    )
    return fig


# =========================================================
# PLOTLY — TREND CONSOLIDADO
# =========================================================
def criar_grafico_geral(df_valid):
    fig = go.Figure()
    for sensor in TEMPERATURAS:
        fig.add_trace(go.Scatter(
            x=df_valid["DataHora"], y=df_valid[sensor],
            mode="lines", name=sensor,
            line=dict(color=CORES_SENSORES[sensor], width=2),
            hovertemplate=f"<b>{sensor}</b><br>%{{x|%d/%m %H:%M}}<br>%{{y:.2f}} °C<extra></extra>",
        ))
    fig.add_hrect(y0=LIM_FRIO, y1=LIM_NORMAL_MAX,       fillcolor="#06ffa5", opacity=0.05, line_width=0)
    fig.add_hrect(y0=LIM_NORMAL_MAX, y1=LIM_ALERTA_MAX, fillcolor="#ffaa00", opacity=0.05, line_width=0)
    fig.update_layout(
        height=380, margin=dict(l=44, r=20, t=20, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0a0e1a",
        font=dict(family="JetBrains Mono, monospace", size=10, color="#6c7a89"),
        xaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89")),
        yaxis=dict(gridcolor="#1a1f2e", showgrid=True,
                   tickfont=dict(color="#6c7a89"), ticksuffix=" °C"),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
                    font=dict(family="JetBrains Mono, monospace", color="#e0e6ed", size=10),
                    bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#131722", bordercolor="#00d4ff",
                        font=dict(family="JetBrains Mono, monospace", color="#fff")),
    )
    return fig


# =========================================================
# LOGOUT
# =========================================================
_, col_sair = st.columns([10, 1])
with col_sair:
    if st.button("Sair", use_container_width=True):
        logout()


# =========================================================
# PAINEL PRINCIPAL — ZERO HTML dentro do fragment
# =========================================================
@st.fragment(run_every="30s")
def painel_temperatura():
    df = conn.read(
        spreadsheet="https://docs.google.com/spreadsheets/d/13i86WpmQ62Bu9nF0LTeH_NgSpQeagO1VTY8ad2XUQL8/edit#gid=1592592023",
        ttl=20,
    )

    if df is None or len(df) == 0:
        st.error("Falha ao carregar dados da planilha ou planilha vazia.")
        return

    df = pd.DataFrame(df)
    df.columns = df.columns.str.strip()

    if "DataHora" in df.columns:
        df["DataHora"] = pd.to_datetime(
            df["DataHora"].astype(str).str.strip(), errors="coerce", dayfirst=True
        )
    elif "Data" in df.columns and "Hora" in df.columns:
        df["DataHora"] = pd.to_datetime(
            df["Data"].astype(str).str.strip() + " " + df["Hora"].astype(str).str.strip(),
            errors="coerce", dayfirst=True,
        )
    else:
        st.error("Colunas obrigatórias ausentes.")
        return

    colunas_faltando = [c for c in TEMPERATURAS if c not in df.columns]
    if colunas_faltando:
        st.error(f"Colunas ausentes: {', '.join(colunas_faltando)}")
        return

    for col in TEMPERATURAS:
        df = tratar_coluna_temperatura(df, col)

    df_valid = df.dropna(subset=["DataHora"]).sort_values("DataHora").copy()
    df_valid = df_valid.dropna(subset=TEMPERATURAS, how="all")

    agora    = pd.Timestamp.now()
    df_valid = df_valid[df_valid["DataHora"] >= agora - pd.Timedelta(hours=24)]

    if df_valid.empty:
        st.error("Sem amostras válidas nas últimas 24h.")
        return

    ultima    = df_valid.iloc[-1]["DataHora"]
    idade_min = (agora - ultima).total_seconds() / 60.0

    if idade_min <= STALE_MIN:
        emoji_st, label_st = "🟢", "ONLINE"
    elif idade_min <= STALE_MIN * 3:
        emoji_st, label_st = "🟡", "STALE"
    else:
        emoji_st, label_st = "🔴", "OFFLINE"

    # ── HEADER ───────────────────────────────────────────
    col_titulo, col_status = st.columns([3, 1])
    with col_titulo:
        st.markdown("### ◉ Monitor de Temperatura")
        st.caption("SCADA · CONTROL ROOM · CH-01..04")
    with col_status:
        st.markdown(f"**{emoji_st} {label_st}**")
        st.caption(f"Última leitura: {ultima.strftime('%d/%m/%Y %H:%M:%S')}")
        st.caption(f"Idade: {idade_min:.1f} min")
    st.divider()

    # ── KPIs ─────────────────────────────────────────────
    cols_kpi = st.columns(4)
    for i, sensor in enumerate(TEMPERATURAS):
        serie = df_valid[sensor].dropna()
        v     = float(serie.iloc[-1]) if not serie.empty else None
        tag, _ = classificar_temperatura(v)
        valor_txt = f"{v:.2f} °C" if v is not None else "-- °C"
        with cols_kpi[i]:
            st.metric(label=sensor, value=valor_txt, delta=tag, delta_color="off")

    st.divider()

    # ── PAINEL POR SENSOR ────────────────────────────────
    st.markdown("**▸ PAINEL POR SENSOR**")
    for sensor in TEMPERATURAS:
        df_sensor = df_valid[["DataHora", sensor]].dropna().copy()
        if df_sensor.empty:
            st.caption(f"{sensor} — sem dados")
            continue

        v_min = float(df_sensor[sensor].min())
        v_max = float(df_sensor[sensor].max())
        v_avg = float(df_sensor[sensor].mean())
        v_now = float(df_sensor.iloc[-1][sensor])
        n_pts = len(df_sensor)

        st.caption(
            f"{sensor}   "
            f"min {v_min:.2f} °C   "
            f"avg {v_avg:.2f} °C   "
            f"max {v_max:.2f} °C   "
            f"n {n_pts}"
        )

        col_g, col_t = st.columns([1, 2.2])
        with col_g:
            st.plotly_chart(
                criar_gauge(v_now, v_min, v_max, sensor),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        with col_t:
            st.plotly_chart(
                criar_grafico_sensor(df_sensor, sensor),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    st.divider()

    # ── TREND CONSOLIDADO ────────────────────────────────
    st.markdown("**▸ TREND CONSOLIDADO · 4 CANAIS**")
    st.plotly_chart(
        criar_grafico_geral(df_valid),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # ── TABELA ───────────────────────────────────────────
    with st.expander("◉ Histórico bruto (últimas 24h)"):
        st.dataframe(
            df_valid[["DataHora"] + TEMPERATURAS].sort_values("DataHora", ascending=False),
            use_container_width=True,
            height=300,
        )

    # ── FOOTER ───────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.caption("SYS: SCADA-TEMP-01")
    c2.caption("MODE: AUTO · 30s")
    c3.caption(f"AMOSTRAS (24H): {len(df_valid)}")
    c4.caption("REFRESH: 30s")
    c5.caption(f"SERVER: {agora.strftime('%d/%m/%Y %H:%M:%S')}")


painel_temperatura()
