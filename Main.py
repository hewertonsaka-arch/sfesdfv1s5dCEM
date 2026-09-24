import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from db.database import init_db, stats_gerais, top_materiais_retirados, retiradas_por_status, listar_retiradas
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    page_title="Controle de Materiais | MKT",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS customizado
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(160deg, #1a56db 0%, #1e40af 100%);
    }
    [data-testid="stSidebar"] * { color: #fff !important; }
    [data-testid="stSidebar"] .stRadio label { color: #fff !important; }

    /* Métricas */
    [data-testid="metric-container"] {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(26,86,219,.08);
    }
    [data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700; }

    /* Headings */
    h1 { color: #1a2332 !important; }
    h2, h3 { color: #1a56db !important; }

    /* Botões primários */
    .stButton > button[kind="primary"] {
        background: #1a56db;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: background .2s;
    }
    .stButton > button[kind="primary"]:hover { background: #1e40af; }

    /* Tabela */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# Inicializa banco
init_db()

# ── Sidebar ──
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/box.png", width=64)
    st.markdown("## 📦 Controle de Materiais")
    st.markdown("**Marketing**")
    st.divider()
    st.markdown("Use o menu acima para navegar entre as páginas.")

# ── Cabeçalho ──
st.title("📦 Controle de Materiais")
st.markdown("Painel de acompanhamento em tempo real — **Marketing**")
st.divider()

# ── KPIs ──
stats = stats_gerais()
c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Materiais Cadastrados", stats['total_materiais'])
c2.metric("📤 Retiradas em Aberto",   stats['retiradas_abertas'], delta=None)
c3.metric("⚠️ Itens Pendentes",       stats['itens_pendentes'])
c4.metric("👤 Responsáveis Ativos",   stats['total_responsaveis'])

st.divider()

# ── Gráficos ──
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("🏆 Materiais Mais Retirados")
    top = top_materiais_retirados(10)
    if top.empty:
        st.info("Nenhuma retirada registrada ainda.")
    else:
        fig = px.bar(
            top,
            x="total_retirado",
            y="nome",
            orientation="h",
            color="total_retirado",
            color_continuous_scale=["#bfdbfe", "#1a56db"],
            labels={"total_retirado": "Total Retirado", "nome": "Material"},
            text="total_retirado",
        )
        fig.update_layout(
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(autorange="reversed"),
            font=dict(family="sans-serif"),
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("📊 Status das Retiradas")
    por_status = retiradas_por_status()
    if por_status.empty:
        st.info("Nenhuma retirada registrada.")
    else:
        STATUS_COLORS = {
            "aberto":    "#f59e0b",
            "parcial":   "#3b82f6",
            "devolvido": "#10b981",
        }
        colors = [STATUS_COLORS.get(s, "#94a3b8") for s in por_status["status"]]
        fig2 = go.Figure(go.Pie(
            labels=por_status["status"].str.capitalize(),
            values=por_status["qtd"],
            marker=dict(colors=colors),
            hole=0.55,
            textinfo="label+value",
        ))
        fig2.update_layout(
            showlegend=True,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            font=dict(family="sans-serif"),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── Retiradas Abertas Recentes ──
st.divider()
st.subheader("🔔 Retiradas em Aberto")
abertas = listar_retiradas(status="aberto")
if abertas.empty:
    st.success("✅ Nenhuma retirada em aberto no momento.")
else:
    # Destaque de atraso
    if "previsao_devolucao" in abertas.columns:
        hoje = pd.Timestamp.today().normalize()
        abertas["previsao_devolucao"] = pd.to_datetime(abertas["previsao_devolucao"], errors="coerce")
        abertas["⚠️ Atrasado"] = abertas["previsao_devolucao"].apply(
            lambda d: "Sim" if pd.notna(d) and d < hoje else "Não"
        )
    st.dataframe(
        abertas.rename(columns={
            "id": "ID", "responsavel": "Responsável",
            "setor": "Setor", "data_retirada": "Data Retirada",
            "previsao_devolucao": "Previsão Dev.", "status": "Status"
        }),
        use_container_width=True,
        hide_index=True,
    )
