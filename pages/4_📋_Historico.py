import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db.database import init_db, historico_completo, movimentacoes_completas

st.set_page_config(page_title="Histórico | MKT", page_icon="📋", layout="wide")
init_db()

st.title("📋 Histórico & Relatórios")
st.markdown("Consulte e exporte o histórico completo de retiradas e movimentações de estoque.")
st.divider()

tab_ret, tab_mov = st.tabs(["📤 Retiradas", "📦 Movimentações de Estoque"])

# ══════════════════════════════════════════════
# TAB — HISTÓRICO DE RETIRADAS
# ══════════════════════════════════════════════
with tab_ret:
    df = historico_completo()

    if df.empty:
        st.info("Nenhuma retirada registrada ainda.")
    else:
        df['data_retirada'] = pd.to_datetime(df['data_retirada'], errors='coerce')

        # ── Filtros ──
        st.subheader("🔍 Filtros")
        fc1, fc2, fc3, fc4 = st.columns(4)

        status_opts = ["Todos"] + sorted(df['status_item'].dropna().unique().tolist())
        fil_status = fc1.selectbox("Status", status_opts, key="hret_status")

        resp_opts = ["Todos"] + sorted(df['responsavel'].dropna().unique().tolist())
        fil_resp  = fc2.selectbox("Responsável", resp_opts, key="hret_resp")

        mat_opts  = ["Todos"] + sorted(df['material'].dropna().unique().tolist())
        fil_mat   = fc3.selectbox("Material", mat_opts, key="hret_mat")

        data_min = df['data_retirada'].min().date() if pd.notna(df['data_retirada'].min()) else date.today() - timedelta(days=365)
        data_max = df['data_retirada'].max().date() if pd.notna(df['data_retirada'].max()) else date.today()
        fil_data = fc4.date_input(
            "Período",
            value=(data_min, data_max),
            key="hret_data"
        )

        df_view = df.copy()
        if fil_status != "Todos":
            df_view = df_view[df_view['status_item'] == fil_status]
        if fil_resp != "Todos":
            df_view = df_view[df_view['responsavel'] == fil_resp]
        if fil_mat != "Todos":
            df_view = df_view[df_view['material'] == fil_mat]
        if isinstance(fil_data, (list, tuple)) and len(fil_data) == 2:
            d_ini, d_fim = pd.Timestamp(fil_data[0]), pd.Timestamp(fil_data[1])
            df_view = df_view[df_view['data_retirada'].between(d_ini, d_fim)]

        st.divider()

        # ── Totais resumidos ──
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de registros",    len(df_view))
        c2.metric("Total retirado",        df_view['quantidade'].sum())
        c3.metric("Total devolvido",       df_view['quantidade_devolvida'].sum())

        st.subheader(f"📄 Resultados ({len(df_view)} linhas)")

        colunas_exibir = ['retirada_id', 'data_retirada', 'responsavel', 'setor',
                          'material', 'categoria', 'unidade',
                          'quantidade', 'quantidade_devolvida', 'pendente',
                          'status_item', 'previsao_devolucao', 'observacao']

        df_exib = df_view[colunas_exibir].rename(columns={
            'retirada_id': 'Ret. #', 'data_retirada': 'Data Retirada',
            'responsavel': 'Responsável', 'setor': 'Setor',
            'material': 'Material', 'categoria': 'Categoria', 'unidade': 'Unid.',
            'quantidade': 'Retirado', 'quantidade_devolvida': 'Devolvido',
            'pendente': 'Pendente', 'status_item': 'Status',
            'previsao_devolucao': 'Prev. Dev.', 'observacao': 'Obs.',
        })

        # Colorir status
        def color_status(val):
            colors = {'aberto': '#fef9c3', 'parcial': '#dbeafe', 'devolvido': '#d1fae5'}
            return f'background-color: {colors.get(val, "")}'

        st.dataframe(
            df_exib.style.map(color_status, subset=['Status']),
            use_container_width=True,
            hide_index=True,
        )

        # ── Exportar CSV ──
        csv_data = df_exib.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Exportar CSV",
            data=csv_data,
            file_name=f"retiradas_{date.today()}.csv",
            mime="text/csv",
            type="primary",
        )

# ══════════════════════════════════════════════
# TAB — MOVIMENTAÇÕES DE ESTOQUE
# ══════════════════════════════════════════════
with tab_mov:
    df_mov = movimentacoes_completas()

    if df_mov.empty:
        st.info("Nenhuma movimentação registrada ainda.")
    else:
        # Filtros rápidos
        fmv1, fmv2 = st.columns(2)
        tipo_opts = ["Todos"] + sorted(df_mov['tipo'].unique().tolist())
        fil_tipo  = fmv1.selectbox("Tipo", tipo_opts, key="hmov_tipo")
        mat_opts2 = ["Todos"] + sorted(df_mov['material'].unique().tolist())
        fil_mat2  = fmv2.selectbox("Material", mat_opts2, key="hmov_mat")

        df_mov_view = df_mov.copy()
        if fil_tipo != "Todos":
            df_mov_view = df_mov_view[df_mov_view['tipo'] == fil_tipo]
        if fil_mat2 != "Todos":
            df_mov_view = df_mov_view[df_mov_view['material'] == fil_mat2]

        st.subheader(f"📦 Movimentações ({len(df_mov_view)} registros)")
        st.dataframe(
            df_mov_view.rename(columns={
                'data': 'Data', 'tipo': 'Tipo', 'material': 'Material',
                'quantidade': 'Qtd.', 'responsavel': 'Responsável', 'observacao': 'Obs.'
            }),
            use_container_width=True,
            hide_index=True,
        )

        csv_mov = df_mov_view.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Exportar CSV",
            data=csv_mov,
            file_name=f"movimentacoes_{date.today()}.csv",
            mime="text/csv",
            type="primary",
        )
