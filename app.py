import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# =========================================================
# CONFIGURAÇÃO INICIAL
# =========================================================
st.set_page_config(
    page_title="SCADA | Monitor de Temperatura",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

USERNAME = "admin"
PASSWORD = "admin"

TEMPERATURAS = ["Temperatura1", "Temperatura2", "Temperatura3", "Temperatura4"]

CORES_SENSORES = {
    "Temperatura1": "#00d4ff",
    "Temperatura2": "#06ffa5",
    "Temperatura3": "#ffaa00",
    "Temperatura4": "#ff3860",
}

# Limites operacionais — ajuste conforme processo
LIM_FRIO = 18.0
LIM_NORMAL_MAX = 26.0
LIM_ALERTA_MAX = 32.0
STALE_MIN = 5  # min sem leitura -> dado estagnado

# =========================================================
# CSS - TEMA SCADA DARK
# =========================================================
SCADA_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

.stApp {
    background: radial-gradient(ellipse at top, #0f1419 0%, #0a0e1a 60%, #060912 100%);
    color: #e0e6ed;
    font-family: 'Inter', -apple-system, sans-serif;
}
[data-testid="stHeader"] { background: transparent; height: 0; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding: 1rem 1.5rem 2rem 1.5rem; max-width: 100%; }

.scada-header {
    background: linear-gradient(90deg, #131722 0%, #1a1f2e 100%);
    border: 1px solid #2a3142; border-left: 4px solid #00d4ff;
    border-radius: 4px; padding: 14px 22px; margin-bottom: 16px;
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 12px;
}
.scada-title-block { display: flex; flex-direction: column; gap: 2px; }
.scada-title { font-size: 1.25rem; font-weight: 700; color: #fff; letter-spacing: 2.5px; text-transform: uppercase; margin: 0; }
.scada-subtitle { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #00d4ff; letter-spacing: 1.5px; margin: 0; }
.scada-status-block { display: flex; gap: 18px; align-items: center; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; flex-wrap: wrap; }
.status-item { display: flex; align-items: center; gap: 8px; color: #6c7a89; text-transform: uppercase; letter-spacing: 1px; }
.status-led { width: 10px; height: 10px; border-radius: 50%; background: #06ffa5; box-shadow: 0 0 8px #06ffa5, 0 0 16px rgba(6,255,165,0.4); animation: pulse 1.6s ease-in-out infinite; }
.status-led.warn { background: #ffaa00; box-shadow: 0 0 8px #ffaa00, 0 0 16px rgba(255,170,0,0.4); }
.status-led.error { background: #ff3860; box-shadow: 0 0 8px #ff3860, 0 0 16px rgba(255,56,96,0.4); }
.status-value { color: #e0e6ed; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-tile { background: linear-gradient(135deg, #131722 0%, #1a1f2e 100%); border: 1px solid #2a3142; border-radius: 4px; padding: 14px 16px; position: relative; overflow: hidden; }
.kpi-tile::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: #00d4ff; }
.kpi-tile.cold::before { background: #00b4d8; }
.kpi-tile.normal::before { background: #06ffa5; }
.kpi-tile.warn::before { background: #ffaa00; }
.kpi-tile.hot::before { background: #ff3860; }
.kpi-tile.offline::before { background: #6c7a89; }
.kpi-label { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: #6c7a89; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
.kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 1.85rem; font-weight: 700; color: #fff; line-height: 1.1; }
.kpi-unit { font-size: 0.95rem; color: #6c7a89; margin-left: 4px; font-weight: 500; }
.kpi-tag { display: inline-block; padding: 2px 8px; border-radius: 2px; font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; text-transform: uppercase; letter-spacing: 1.2px; margin-top: 8px; border: 1px solid; }
.kpi-tag.cold { background: rgba(0,180,216,0.12); color: #00b4d8; border-color: #00b4d8; }
.kpi-tag.normal { background: rgba(6,255,165,0.12); color: #06ffa5; border-color: #06ffa5; }
.kpi-tag.warn { background: rgba(255,170,0,0.12); color: #ffaa00; border-color: #ffaa00; }
.kpi-tag.hot { background: rgba(255,56,96,0.12); color: #ff3860; border-color: #ff3860; }
.kpi-tag.offline { background: rgba(108,122,137,0.12); color: #6c7a89; border-color: #6c7a89; }

.scada-section { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #00d4ff; text-transform: uppercase; letter-spacing: 2.5px; margin: 20px 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid #2a3142; display: flex; align-items: center; gap: 8px; }
.scada-section::before { content: '▸'; color: #00d4ff; }

.sensor-panel { background: #131722; border: 1px solid #2a3142; border-radius: 4px; padding: 12px 16px; margin-bottom: 8px; }
.sensor-panel-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.sensor-panel-title { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 600; color: #fff; letter-spacing: 1.5px; }
.sensor-stats { display: flex; gap: 16px; flex-wrap: wrap; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; }
.sensor-stat-item { color: #6c7a89; }
.sensor-stat-value { color: #e0e6ed; font-weight: 600; }

.login-wrapper { max-width: 380px; margin: 80px auto; background: linear-gradient(135deg, #131722 0%, #1a1f2e 100%); border: 1px solid #2a3142; border-top: 3px solid #00d4ff; padding: 32px 28px; border-radius: 4px; box-shadow: 0 8px 32px rgba(0, 212, 255, 0.08); }
.login-title { font-size: 1.3rem; font-weight: 700; color: #fff; letter-spacing: 3px; text-transform: uppercase; margin: 0 0 4px 0; text-align: center; }
.login-sub { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #00d4ff; letter-spacing: 1.5px; margin: 0 0 24px 0; text-align: center; }

.stTextInput input, .stPasswordInput input { background: #0a0e1a !important; border: 1px solid #2a3142 !important; color: #e0e6ed !important; font-family: 'JetBrains Mono', monospace !important; border-radius: 2px !important; }
.stTextInput input:focus, .stPasswordInput input:focus { border-color: #00d4ff !important; box-shadow: 0 0 0 1px #00d4ff !important; }
.stTextInput label, .stPasswordInput label { color: #6c7a89 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.7rem !important; text-transform: uppercase !important; letter-spacing: 1.5px !important; }
.stButton > button { background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%); color: #0a0e1a; border: none; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; font-size: 0.78rem; border-radius: 2px; padding: 8px 20px; transition: all 0.2s; }
.stButton > button:hover { background: linear-gradient(135deg, #00ffff 0%, #00d4ff 100%); color: #0a0e1a; box-shadow: 0 0 16px rgba(0,212,255,0.45); transform: translateY(-1px); }
.stForm { border: none; padding: 0; background: transparent; }

[data-testid="stExpander"] { background: #131722 !important; border: 1px solid #2a3142 !important; border-radius: 4px !important; }
[data-testid="stExpander"] summary { color: #e0e6ed !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 1.5px; }
.stDataFrame { background: #131722; border: 1px solid #2a3142; border-radius: 4px; }
.js-plotly-plot, .plot-container { background: transparent !important; }
.stAlert { background: #131722 !important; border: 1px solid #2a3142 !important; border-left: 3px solid #ff3860 !important; color: #e0e6ed !important; border-radius: 2px !important; }

.scada-footer { background: linear-gradient(90deg, #0a0e1a, #131722); border: 1px solid #2a3142; border-radius: 4px; padding: 8px 16px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: #6c7a89; text-transform: uppercase; letter-spacing: 1.2px; margin-top: 16px; }
.scada-footer .footer-item { display: flex; gap: 6px; }
.scada-footer .footer-value { color: #e0e6ed; }

@media (max-width: 1024px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) {
    .kpi-grid { grid-template-columns: 1fr; }
    .scada-title { font-size: 1rem; letter-spacing: 1.5px; }
    .scada-status-block { gap: 10px; }
    .kpi-value { font-size: 1.5rem; }
    .block-container { padding: 0.5rem 0.75rem 1rem 0.75rem; }
    .sensor-stats { gap: 10px; }
}
</style>
"""
st.markdown(SCADA_CSS, unsafe_allow_html=True)

# =========================================================
# SESSION + LOGIN
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def classificar_temperatura(valor):
    if valor is None or pd.isna(valor):
        return "offline", "Offline"
    if valor < LIM_FRIO:
        return "cold", "Frio"
    if valor <= LIM_NORMAL_MAX:
        return "normal", "Normal"
    if valor <= LIM_ALERTA_MAX:
        return "warn", "Alerta"
    return "hot", "Crítico"


def login():
    st.markdown(
        '<div class="login-wrapper">'
        '<div class="login-title">◉ SCADA</div>'
        '<div class="login-sub">Sistema de Supervisão · v1.0</div>',
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Autenticar")
        if submitted:
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    st.markdown("</div>", unsafe_allow_html=True)


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
# COMPONENTES VISUAIS
# =========================================================
def render_header(status_sistema, ultima_leitura, idade_min):
    led_class = {"online": "", "warn": "warn", "error": "error"}[status_sistema]
    label_status = {"online": "ONLINE", "warn": "STALE", "error": "OFFLINE"}[status_sistema]
    ts = ultima_leitura.strftime("%d/%m/%Y %H:%M:%S") if ultima_leitura is not None else "--"
    idade = f"{idade_min:.1f} min" if idade_min is not None else "--"
    st.markdown(
        f"""
        <div class="scada-header">
            <div class="scada-title-block">
                <p class="scada-title">◉ Monitor de Temperatura</p>
                <p class="scada-subtitle">SCADA · CONTROL ROOM · CH-01..04</p>
            </div>
            <div class="scada-status-block">
                <div class="status-item"><div class="status-led {led_class}"></div><span>Status:</span><span class="status-value">{label_status}</span></div>
                <div class="status-item"><span>Última leitura:</span><span class="status-value">{ts}</span></div>
                <div class="status-item"><span>Idade:</span><span class="status-value">{idade}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(valores_atuais):
    cards = []
    for sensor in TEMPERATURAS:
        v = valores_atuais.get(sensor)
        cls, tag = classificar_temperatura(v)
        valor_txt = f"{v:.2f}" if v is not None and not pd.isna(v) else "--"
        cards.append(
            f"""
            <div class="kpi-tile {cls}">
                <div class="kpi-label">{sensor.upper()}</div>
                <div class="kpi-value">{valor_txt}<span class="kpi-unit">°C</span></div>
                <span class="kpi-tag {cls}">● {tag}</span>
            </div>
            """
        )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def criar_gauge_scada(valor_atual, valor_min, valor_max):
    gauge_min = min(0, int(valor_min) - 5)
    gauge_max = max(50, int(valor_max) + 5)
    cls, _ = classificar_temperatura(valor_atual)
    cor_map = {"cold": "#00b4d8", "normal": "#06ffa5", "warn": "#ffaa00", "hot": "#ff3860", "offline": "#6c7a89"}
    cor_bar = cor_map[cls]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor_atual,
        number={"suffix": " °C", "valueformat": ".2f",
                "font": {"family": "JetBrains Mono, monospace", "size": 26, "color": "#ffffff"}},
        gauge={
            "axis": {"range": [gauge_min, gauge_max], "tickwidth": 1, "tickcolor": "#3a4256",
                     "tickfont": {"family": "JetBrains Mono, monospace", "size": 9, "color": "#6c7a89"}},
            "bar": {"color": cor_bar, "thickness": 0.28},
            "bgcolor": "#0a0e1a", "borderwidth": 1, "bordercolor": "#2a3142",
            "steps": [
                {"range": [gauge_min, LIM_FRIO], "color": "rgba(0, 180, 216, 0.18)"},
                {"range": [LIM_FRIO, LIM_NORMAL_MAX], "color": "rgba(6, 255, 165, 0.18)"},
                {"range": [LIM_NORMAL_MAX, LIM_ALERTA_MAX], "color": "rgba(255, 170, 0, 0.18)"},
                {"range": [LIM_ALERTA_MAX, gauge_max], "color": "rgba(255, 56, 96, 0.18)"},
            ],
            "threshold": {"line": {"color": cor_bar, "width": 3}, "thickness": 0.85, "value": valor_atual},
        },
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font={"color": "#e0e6ed"})
    return fig


def criar_grafico_sensor_scada(df_sensor, nome_sensor):
    cor = CORES_SENSORES[nome_sensor]
    r, g, b = int(cor[1:3], 16), int(cor[3:5], 16), int(cor[5:7], 16)
    fill_rgba = f"rgba({r},{g},{b},0.07)"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sensor["DataHora"], y=df_sensor[nome_sensor], mode="lines", name=nome_sensor,
        line=dict(color=cor, width=2), fill="tozeroy", fillcolor=fill_rgba,
        hovertemplate="%{x|%d/%m %H:%M:%S}<br>%{y:.2f} °C<extra></extra>",
    ))
    for lim, cor_lim in [(LIM_FRIO, "#00b4d8"), (LIM_NORMAL_MAX, "#06ffa5"), (LIM_ALERTA_MAX, "#ffaa00")]:
        fig.add_hline(y=lim, line_dash="dot", line_color=cor_lim, opacity=0.4, line_width=1)
    fig.update_layout(
        height=220, margin=dict(l=44, r=16, t=10, b=36),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0a0e1a",
        font=dict(family="JetBrains Mono, monospace", size=9, color="#6c7a89"),
        xaxis=dict(gridcolor="#1a1f2e", zerolinecolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89")),
        yaxis=dict(gridcolor="#1a1f2e", zerolinecolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89"), ticksuffix=" °C"),
        showlegend=False, hovermode="x unified",
        hoverlabel=dict(bgcolor="#131722", bordercolor=cor, font=dict(family="JetBrains Mono, monospace", color="#fff")),
    )
    return fig


def criar_grafico_geral_scada(df_valid):
    fig = go.Figure()
    for sensor in TEMPERATURAS:
        fig.add_trace(go.Scatter(
            x=df_valid["DataHora"], y=df_valid[sensor], mode="lines", name=sensor,
            line=dict(color=CORES_SENSORES[sensor], width=2),
            hovertemplate=f"<b>{sensor}</b><br>%{{x|%d/%m %H:%M}}<br>%{{y:.2f}} °C<extra></extra>",
        ))
    fig.add_hrect(y0=LIM_FRIO, y1=LIM_NORMAL_MAX, fillcolor="#06ffa5", opacity=0.05, line_width=0)
    fig.add_hrect(y0=LIM_NORMAL_MAX, y1=LIM_ALERTA_MAX, fillcolor="#ffaa00", opacity=0.05, line_width=0)
    fig.update_layout(
        height=380, margin=dict(l=44, r=20, t=20, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0a0e1a",
        font=dict(family="JetBrains Mono, monospace", size=10, color="#6c7a89"),
        xaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89")),
        yaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89"), ticksuffix=" °C"),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
                    font=dict(family="JetBrains Mono, monospace", color="#e0e6ed", size=10),
                    bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#131722", bordercolor="#00d4ff", font=dict(family="JetBrains Mono, monospace", color="#fff")),
    )
    return fig


def render_footer(n_amostras, modo_atual):
    agora = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(
        f"""
        <div class="scada-footer">
            <div class="footer-item"><span>SYS:</span><span class="footer-value">SCADA-TEMP-01</span></div>
            <div class="footer-item"><span>MODE:</span><span class="footer-value">{modo_atual}</span></div>
            <div class="footer-item"><span>AMOSTRAS (24H):</span><span class="footer-value">{n_amostras}</span></div>
            <div class="footer-item"><span>REFRESH:</span><span class="footer-value">30s</span></div>
            <div class="footer-item"><span>SERVER:</span><span class="footer-value">{agora}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# LOGOUT (canto)
# =========================================================
col_top1, col_top2 = st.columns([10, 1])
with col_top2:
    if st.button("Sair", use_container_width=True):
        logout()


# =========================================================
# PAINEL PRINCIPAL
# =========================================================
@st.fragment(run_every="30s")
def painel_temperatura():
    df = conn.read(
        spreadsheet="https://docs.google.com/spreadsheets/d/13i86WpmQ62Bu9nF0LTeH_NgSpQeagO1VTY8ad2XUQL8/edit#gid=1592592023",
        ttl=20,
    )

    if df is None or len(df) == 0:
        render_header("error", None, None)
        st.error("Falha ao carregar dados da planilha ou planilha vazia.")
        return

    df = pd.DataFrame(df)
    df.columns = df.columns.str.strip()

    if "DataHora" in df.columns:
        df["DataHora"] = pd.to_datetime(df["DataHora"].astype(str).str.strip(), errors="coerce", dayfirst=True)
    elif "Data" in df.columns and "Hora" in df.columns:
        df["DataHora"] = pd.to_datetime(
            df["Data"].astype(str).str.strip() + " " + df["Hora"].astype(str).str.strip(),
            errors="coerce", dayfirst=True,
        )
    else:
        render_header("error", None, None)
        st.error("Colunas obrigatórias ausentes.")
        return

    colunas_faltando = [c for c in TEMPERATURAS if c not in df.columns]
    if colunas_faltando:
        render_header("error", None, None)
        st.error(f"Colunas ausentes: {', '.join(colunas_faltando)}")
        return

    for col in TEMPERATURAS:
        df = tratar_coluna_temperatura(df, col)

    df_valid = df.dropna(subset=["DataHora"]).sort_values("DataHora").copy()
    df_valid = df_valid.dropna(subset=TEMPERATURAS, how="all")

    agora = pd.Timestamp.now()
    df_valid = df_valid[df_valid["DataHora"] >= agora - pd.Timedelta(hours=24)]

    if df_valid.empty:
        render_header("error", None, None)
        st.error("Sem amostras válidas nas últimas 24h.")
        return

    ultima = df_valid.iloc[-1]["DataHora"]
    idade_min = (agora - ultima).total_seconds() / 60.0
    if idade_min <= STALE_MIN:
        status = "online"
    elif idade_min <= STALE_MIN * 3:
        status = "warn"
    else:
        status = "error"

    render_header(status, ultima, idade_min)

    valores_atuais = {}
    for sensor in TEMPERATURAS:
        serie = df_valid[sensor].dropna()
        valores_atuais[sensor] = float(serie.iloc[-1]) if not serie.empty else None
    render_kpis(valores_atuais)

    st.markdown('<div class="scada-section">Painel por Sensor</div>', unsafe_allow_html=True)
    for sensor in TEMPERATURAS:
        df_sensor = df_valid[["DataHora", sensor]].dropna().copy()
        if df_sensor.empty:
            st.markdown(
                f'<div class="sensor-panel"><div class="sensor-panel-header">'
                f'<div class="sensor-panel-title">▸ {sensor.upper()}</div>'
                f'<div class="sensor-stats"><span class="sensor-stat-item">SEM DADOS</span></div>'
                f'</div></div>', unsafe_allow_html=True,
            )
            continue

        v_min = float(df_sensor[sensor].min())
        v_max = float(df_sensor[sensor].max())
        v_avg = float(df_sensor[sensor].mean())
        v_now = float(df_sensor.iloc[-1][sensor])
        n_pts = len(df_sensor)

        st.markdown(
            f"""
            <div class="sensor-panel">
                <div class="sensor-panel-header">
                    <div class="sensor-panel-title">▸ {sensor.upper()}</div>
                    <div class="sensor-stats">
                        <div class="sensor-stat-item">MIN: <span class="sensor-stat-value">{v_min:.2f} °C</span></div>
                        <div class="sensor-stat-item">AVG: <span class="sensor-stat-value">{v_avg:.2f} °C</span></div>
                        <div class="sensor-stat-item">MAX: <span class="sensor-stat-value">{v_max:.2f} °C</span></div>
                        <div class="sensor-stat-item">N: <span class="sensor-stat-value">{n_pts}</span></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True,
        )

        col_gauge, col_grafico = st.columns([1, 2.2])
        with col_gauge:
            st.plotly_chart(criar_gauge_scada(v_now, v_min, v_max),
                            use_container_width=True, config={"displayModeBar": False})
        with col_grafico:
            st.plotly_chart(criar_grafico_sensor_scada(df_sensor, sensor),
                            use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="scada-section">Trend Consolidado · 4 Canais</div>', unsafe_allow_html=True)
    st.plotly_chart(criar_grafico_geral_scada(df_valid),
                    use_container_width=True, config={"displayModeBar": False})

    with st.expander("◉ Histórico bruto (últimas 24h)"):
        st.dataframe(
            df_valid[["DataHora"] + TEMPERATURAS].sort_values("DataHora", ascending=False),
            use_container_width=True, height=300,
        )

    render_footer(len(df_valid), "AUTO · 30s")


painel_temperatura()
