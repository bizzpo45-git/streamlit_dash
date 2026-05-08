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

LIM_FRIO       = 18.0
LIM_NORMAL_MAX = 26.0
LIM_ALERTA_MAX = 32.0
STALE_MIN      = 5

# =========================================================
# CSS — apenas overrides de widgets nativos do Streamlit
# (não usamos classes CSS para estrutura de conteúdo)
# =========================================================
SCADA_CSS = """
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

.stTextInput input, .stPasswordInput input {
    background: #0a0e1a !important;
    border: 1px solid #2a3142 !important;
    color: #e0e6ed !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 2px !important;
}
.stTextInput input:focus, .stPasswordInput input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 1px #00d4ff !important;
}
.stTextInput label, .stPasswordInput label {
    color: #6c7a89 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
}
.stButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
    color: #0a0e1a; border: none; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.5px;
    font-size: 0.78rem; border-radius: 2px; transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00ffff 0%, #00d4ff 100%);
    box-shadow: 0 0 16px rgba(0,212,255,0.45);
    transform: translateY(-1px);
}
.stForm { border: none; padding: 0; background: transparent; }

[data-testid="stExpander"] {
    background: #131722 !important;
    border: 1px solid #2a3142 !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary {
    color: #e0e6ed !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}
.stDataFrame { background: #131722; border: 1px solid #2a3142; border-radius: 4px; }
.stAlert {
    background: #131722 !important;
    border: 1px solid #2a3142 !important;
    border-left: 3px solid #ff3860 !important;
    color: #e0e6ed !important;
    border-radius: 2px !important;
}
.js-plotly-plot, .plot-container { background: transparent !important; }

@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
.led-pulse { animation: pulse 1.6s ease-in-out infinite; }
</style>
"""
st.markdown(SCADA_CSS, unsafe_allow_html=True)

# =========================================================
# SESSION
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def classificar_temperatura(valor):
    if valor is None or pd.isna(valor):
        return "offline", "Offline", "#6c7a89"
    if valor < LIM_FRIO:
        return "cold", "Frio", "#00b4d8"
    if valor <= LIM_NORMAL_MAX:
        return "normal", "Normal", "#06ffa5"
    if valor <= LIM_ALERTA_MAX:
        return "warn", "Alerta", "#ffaa00"
    return "hot", "Crítico", "#ff3860"


# =========================================================
# LOGIN
# =========================================================
def login():
    st.markdown(
        """
        <div style="max-width:380px;margin:80px auto;background:linear-gradient(135deg,#131722,#1a1f2e);
        border:1px solid #2a3142;border-top:3px solid #00d4ff;padding:32px 28px;border-radius:4px;
        box-shadow:0 8px 32px rgba(0,212,255,0.08);">
            <div style="font-size:1.3rem;font-weight:700;color:#fff;letter-spacing:3px;
            text-transform:uppercase;text-align:center;margin-bottom:4px;">◉ SCADA</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#00d4ff;
            letter-spacing:1.5px;text-align:center;margin-bottom:24px;">
            Sistema de Supervisão · v1.0</div>
        </div>
        """,
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
# HEADER  — inline styles, sem classes externas
# =========================================================
def render_header(status_sistema, ultima_leitura, idade_min):
    cor_led   = {"online": "#06ffa5", "warn": "#ffaa00", "error": "#ff3860"}[status_sistema]
    label_st  = {"online": "ONLINE",  "warn": "STALE",   "error": "OFFLINE"}[status_sistema]
    ts        = ultima_leitura.strftime("%d/%m/%Y %H:%M:%S") if ultima_leitura else "--"
    idade     = f"{idade_min:.1f} min" if idade_min is not None else "--"

    st.markdown(
        f"""
        <div style="background:linear-gradient(90deg,#131722,#1a1f2e);border:1px solid #2a3142;
        border-left:4px solid #00d4ff;border-radius:4px;padding:14px 22px;margin-bottom:16px;
        display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">

            <div>
                <div style="font-size:1.2rem;font-weight:700;color:#fff;letter-spacing:2.5px;
                text-transform:uppercase;">◉ Monitor de Temperatura</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                color:#00d4ff;letter-spacing:1.5px;">SCADA · CONTROL ROOM · CH-01..04</div>
            </div>

            <div style="display:flex;gap:20px;align-items:center;flex-wrap:wrap;
            font-family:'JetBrains Mono',monospace;font-size:0.72rem;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <div class="led-pulse" style="width:10px;height:10px;border-radius:50%;
                    background:{cor_led};box-shadow:0 0 8px {cor_led};"></div>
                    <span style="color:#6c7a89;text-transform:uppercase;">Status:</span>
                    <span style="color:#e0e6ed;">{label_st}</span>
                </div>
                <div>
                    <span style="color:#6c7a89;text-transform:uppercase;">Última leitura:&nbsp;</span>
                    <span style="color:#e0e6ed;">{ts}</span>
                </div>
                <div>
                    <span style="color:#6c7a89;text-transform:uppercase;">Idade:&nbsp;</span>
                    <span style="color:#e0e6ed;">{idade}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# KPIs — st.columns + um markdown simples por célula
# =========================================================
def render_kpis(valores_atuais):
    cols = st.columns(4)
    for i, sensor in enumerate(TEMPERATURAS):
        v                = valores_atuais.get(sensor)
        _, tag, cor      = classificar_temperatura(v)
        valor_txt        = f"{v:.2f}" if v is not None and not pd.isna(v) else "--"
        with cols[i]:
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#131722,#1a1f2e);"
                f"border:1px solid #2a3142;border-left:3px solid {cor};"
                f"border-radius:4px;padding:14px 16px;'>"
                f"<div style='font-family:JetBrains Mono,monospace;font-size:0.68rem;"
                f"color:#6c7a89;text-transform:uppercase;letter-spacing:1.5px;"
                f"margin-bottom:6px;'>{sensor}</div>"
                f"<div style='font-family:JetBrains Mono,monospace;font-size:1.85rem;"
                f"font-weight:700;color:#fff;line-height:1.1;'>{valor_txt}"
                f"<span style='font-size:0.95rem;color:#6c7a89;margin-left:4px;'>°C</span></div>"
                f"<span style='display:inline-block;padding:2px 8px;border-radius:2px;"
                f"font-family:JetBrains Mono,monospace;font-size:0.62rem;text-transform:uppercase;"
                f"letter-spacing:1.2px;margin-top:8px;border:1px solid {cor};"
                f"background:rgba(0,0,0,0.2);color:{cor};'>● {tag}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


# =========================================================
# DIVISOR DE SEÇÃO — inline style
# =========================================================
def render_section(titulo):
    st.markdown(
        f"<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#00d4ff;"
        f"text-transform:uppercase;letter-spacing:2.5px;margin:20px 0 10px 0;"
        f"padding-bottom:6px;border-bottom:1px solid #2a3142;'>▸ {titulo}</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# LABEL DO SENSOR — inline style
# =========================================================
def render_sensor_label(sensor, v_min, v_max, v_avg, n_pts):
    cor = CORES_SENSORES[sensor]
    st.markdown(
        f"<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;"
        f"color:{cor};letter-spacing:1.5px;text-transform:uppercase;"
        f"margin:10px 0 4px 0;'>"
        f"▸ {sensor}&nbsp;&nbsp;&nbsp;"
        f"<span style='color:#6c7a89;'>MIN</span>&nbsp;"
        f"<span style='color:#e0e6ed;font-weight:600;'>{v_min:.2f} °C</span>&nbsp;&nbsp;"
        f"<span style='color:#6c7a89;'>AVG</span>&nbsp;"
        f"<span style='color:#e0e6ed;font-weight:600;'>{v_avg:.2f} °C</span>&nbsp;&nbsp;"
        f"<span style='color:#6c7a89;'>MAX</span>&nbsp;"
        f"<span style='color:#e0e6ed;font-weight:600;'>{v_max:.2f} °C</span>&nbsp;&nbsp;"
        f"<span style='color:#6c7a89;'>N</span>&nbsp;"
        f"<span style='color:#e0e6ed;font-weight:600;'>{n_pts}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# PLOTLY — GAUGE
# =========================================================
def criar_gauge_scada(valor_atual, valor_min, valor_max):
    gauge_min = min(0, int(valor_min) - 5)
    gauge_max = max(50, int(valor_max) + 5)
    _, _, cor_bar = classificar_temperatura(valor_atual)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor_atual,
        number={
            "suffix": " °C", "valueformat": ".2f",
            "font": {"family": "JetBrains Mono, monospace", "size": 26, "color": "#ffffff"},
        },
        gauge={
            "axis": {
                "range": [gauge_min, gauge_max], "tickwidth": 1, "tickcolor": "#3a4256",
                "tickfont": {"family": "JetBrains Mono, monospace", "size": 9, "color": "#6c7a89"},
            },
            "bar": {"color": cor_bar, "thickness": 0.28},
            "bgcolor": "#0a0e1a", "borderwidth": 1, "bordercolor": "#2a3142",
            "steps": [
                {"range": [gauge_min, LIM_FRIO],        "color": "rgba(0,180,216,0.18)"},
                {"range": [LIM_FRIO, LIM_NORMAL_MAX],   "color": "rgba(6,255,165,0.18)"},
                {"range": [LIM_NORMAL_MAX, LIM_ALERTA_MAX], "color": "rgba(255,170,0,0.18)"},
                {"range": [LIM_ALERTA_MAX, gauge_max],  "color": "rgba(255,56,96,0.18)"},
            ],
            "threshold": {"line": {"color": cor_bar, "width": 3}, "thickness": 0.85, "value": valor_atual},
        },
    ))
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e0e6ed"},
    )
    return fig


# =========================================================
# PLOTLY — TREND INDIVIDUAL
# =========================================================
def criar_grafico_sensor_scada(df_sensor, nome_sensor):
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
        height=220, margin=dict(l=44, r=16, t=10, b=36),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0a0e1a",
        font=dict(family="JetBrains Mono, monospace", size=9, color="#6c7a89"),
        xaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89")),
        yaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89"), ticksuffix=" °C"),
        showlegend=False, hovermode="x unified",
        hoverlabel=dict(bgcolor="#131722", bordercolor=cor,
                        font=dict(family="JetBrains Mono, monospace", color="#fff")),
    )
    return fig


# =========================================================
# PLOTLY — TREND CONSOLIDADO
# =========================================================
def criar_grafico_geral_scada(df_valid):
    fig = go.Figure()
    for sensor in TEMPERATURAS:
        fig.add_trace(go.Scatter(
            x=df_valid["DataHora"], y=df_valid[sensor],
            mode="lines", name=sensor,
            line=dict(color=CORES_SENSORES[sensor], width=2),
            hovertemplate=f"<b>{sensor}</b><br>%{{x|%d/%m %H:%M}}<br>%{{y:.2f}} °C<extra></extra>",
        ))
    fig.add_hrect(y0=LIM_FRIO, y1=LIM_NORMAL_MAX,   fillcolor="#06ffa5", opacity=0.05, line_width=0)
    fig.add_hrect(y0=LIM_NORMAL_MAX, y1=LIM_ALERTA_MAX, fillcolor="#ffaa00", opacity=0.05, line_width=0)
    fig.update_layout(
        height=380, margin=dict(l=44, r=20, t=20, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0a0e1a",
        font=dict(family="JetBrains Mono, monospace", size=10, color="#6c7a89"),
        xaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89")),
        yaxis=dict(gridcolor="#1a1f2e", showgrid=True, tickfont=dict(color="#6c7a89"), ticksuffix=" °C"),
        legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
            font=dict(family="JetBrains Mono, monospace", color="#e0e6ed", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#131722", bordercolor="#00d4ff",
                        font=dict(family="JetBrains Mono, monospace", color="#fff")),
    )
    return fig


# =========================================================
# FOOTER — inline style
# =========================================================
def render_footer(n_amostras, modo_atual):
    agora = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
    itens = [
        ("SYS", "SCADA-TEMP-01"),
        ("MODE", modo_atual),
        ("AMOSTRAS (24H)", str(n_amostras)),
        ("REFRESH", "30s"),
        ("SERVER", agora),
    ]
    itens_html = "".join(
        f"<div style='display:flex;gap:6px;'>"
        f"<span style='color:#6c7a89;text-transform:uppercase;'>{k}:</span>"
        f"<span style='color:#e0e6ed;'>{v}</span></div>"
        for k, v in itens
    )
    st.markdown(
        f"<div style='background:linear-gradient(90deg,#0a0e1a,#131722);border:1px solid #2a3142;"
        f"border-radius:4px;padding:8px 16px;display:flex;justify-content:space-between;"
        f"flex-wrap:wrap;gap:8px;font-family:JetBrains Mono,monospace;font-size:0.68rem;"
        f"margin-top:16px;'>{itens_html}</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# LOGOUT
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
        df["DataHora"] = pd.to_datetime(
            df["DataHora"].astype(str).str.strip(), errors="coerce", dayfirst=True
        )
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

    agora     = pd.Timestamp.now()
    df_valid  = df_valid[df_valid["DataHora"] >= agora - pd.Timedelta(hours=24)]

    if df_valid.empty:
        render_header("error", None, None)
        st.error("Sem amostras válidas nas últimas 24h.")
        return

    ultima    = df_valid.iloc[-1]["DataHora"]
    idade_min = (agora - ultima).total_seconds() / 60.0
    status    = "online" if idade_min <= STALE_MIN else ("warn" if idade_min <= STALE_MIN * 3 else "error")

    # ── Header ───────────────────────────────────────────
    render_header(status, ultima, idade_min)

    # ── KPIs ─────────────────────────────────────────────
    valores_atuais = {}
    for sensor in TEMPERATURAS:
        serie = df_valid[sensor].dropna()
        valores_atuais[sensor] = float(serie.iloc[-1]) if not serie.empty else None
    render_kpis(valores_atuais)

    # ── Painéis por sensor ────────────────────────────────
    render_section("Painel por Sensor")

    for sensor in TEMPERATURAS:
        df_sensor = df_valid[["DataHora", sensor]].dropna().copy()

        if df_sensor.empty:
            st.caption(f"▸ {sensor} — sem dados")
            continue

        v_min = float(df_sensor[sensor].min())
        v_max = float(df_sensor[sensor].max())
        v_avg = float(df_sensor[sensor].mean())
        v_now = float(df_sensor.iloc[-1][sensor])
        n_pts = len(df_sensor)

        render_sensor_label(sensor, v_min, v_max, v_avg, n_pts)

        col_gauge, col_grafico = st.columns([1, 2.2])
        with col_gauge:
            st.plotly_chart(
                criar_gauge_scada(v_now, v_min, v_max),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        with col_grafico:
            st.plotly_chart(
                criar_grafico_sensor_scada(df_sensor, sensor),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    # ── Trend consolidado ────────────────────────────────
    render_section("Trend Consolidado · 4 Canais")
    st.plotly_chart(
        criar_grafico_geral_scada(df_valid),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # ── Tabela ───────────────────────────────────────────
    with st.expander("◉ Histórico bruto (últimas 24h)"):
        st.dataframe(
            df_valid[["DataHora"] + TEMPERATURAS].sort_values("DataHora", ascending=False),
            use_container_width=True,
            height=300,
        )

    render_footer(len(df_valid), "AUTO · 30s")


painel_temperatura()
