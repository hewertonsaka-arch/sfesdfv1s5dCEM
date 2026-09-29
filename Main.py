import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from db.database import init_db, stats_gerais, top_materiais_retirados, retiradas_por_mes, listar_retiradas, materiais_estoque_baixo
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    page_title="Controle de Materiais",
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
c2.metric("📤 Retiradas Registradas", stats['total_retiradas'])
c3.metric("👤 Responsáveis Ativos", stats['total_responsaveis'])
c4.metric("⚠️ Alertas de Estoque", stats['alertas_estoque'])

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
    st.subheader("📈 Retiradas por Mês")
    por_mes = retiradas_por_mes(6)
    if por_mes.empty:
        st.info("Nenhuma retirada registrada.")
    else:
        fig2 = px.line(
            por_mes,
            x="mes",
            y="total_unidades",
            markers=True,
            labels={"mes": "Mês", "total_unidades": "Unidades Retiradas"}
        )
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            font=dict(family="sans-serif"),
            xaxis=dict(autorange="reversed")
        )
        fig2.update_traces(line_color="#1a56db", marker=dict(size=8))
        st.plotly_chart(fig2, use_container_width=True)

# ── Seção Inferior ──
st.divider()
col_inf1, col_inf2 = st.columns([2, 2])

with col_inf1:
    st.subheader("🔔 Alertas de Estoque Baixo")
    baixo = materiais_estoque_baixo()
    if baixo.empty:
        st.success("✅ Todos os materiais estão com estoque acima do mínimo.")
    else:
        st.dataframe(
            baixo.rename(columns={
                "id": "ID", "nome": "Material", "categoria": "Categoria",
                "quantidade_estoque": "Estoque Atual", "estoque_minimo": "Mínimo", "unidade": "Unid."
            }),
            use_container_width=True,
            hide_index=True,
        )

with col_inf2:
    st.subheader("📄 Últimas Retiradas")
    recentes = listar_retiradas(limit=5)
    if recentes.empty:
        st.info("Nenhuma retirada registrada.")
    else:
        st.dataframe(
            recentes[['id', 'responsavel', 'setor', 'data_retirada', 'total_unidades']].rename(columns={
                "id": "ID", "responsavel": "Responsável",
                "setor": "Setor", "data_retirada": "Data", "total_unidades": "Qtd. Itens"
            }),
            use_container_width=True,
            hide_index=True,
        )
