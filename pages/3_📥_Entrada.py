import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
from datetime import date
from db.database import (
    init_db,
    listar_materiais, listar_itens_retirada,
    registrar_devolucao, registrar_entrada_estoque,
)

st.set_page_config(page_title="Entrada | MKT", page_icon="📥", layout="wide")
init_db()

st.title("📥 Entrada de Materiais")
st.markdown("Registre **devoluções** de itens retirados ou **entradas de novos produtos** no estoque.")
st.divider()

tab_dev, tab_ent = st.tabs(["🔄 Devolução de Retirada", "📦 Entrada de Novos Produtos"])

# ══════════════════════════════════════════════
# TAB — DEVOLUÇÕES
# ══════════════════════════════════════════════
with tab_dev:
    st.subheader("🔄 Registrar Devolução")
    st.markdown("Selecione os itens que estão sendo devolvidos e informe a quantidade.")

    # Carrega itens abertos ou parciais
    df_itens = listar_itens_retirada(status=None)
    df_itens_abertos = df_itens[df_itens['status'].isin(['aberto', 'parcial'])]

    if df_itens_abertos.empty:
        st.success("✅ Nenhum item pendente de devolução no momento.")
    else:
        # Filtros
        col_f1, col_f2 = st.columns(2)
        responsaveis_unicos = ["Todos"] + sorted(df_itens_abertos['responsavel'].dropna().unique().tolist())
        fil_resp = col_f1.selectbox("Filtrar por responsável", responsaveis_unicos, key="fil_resp_dev")
        materiais_unicos = ["Todos"] + sorted(df_itens_abertos['material'].unique().tolist())
        fil_mat  = col_f2.selectbox("Filtrar por material", materiais_unicos, key="fil_mat_dev")

        df_view = df_itens_abertos.copy()
        if fil_resp != "Todos":
            df_view = df_view[df_view['responsavel'] == fil_resp]
        if fil_mat != "Todos":
            df_view = df_view[df_view['material'] == fil_mat]

        st.dataframe(
            df_view[['id', 'retirada_id', 'responsavel', 'setor', 'material',
                     'quantidade', 'quantidade_devolvida', 'pendente',
                     'data_retirada', 'previsao_devolucao', 'status']].rename(columns={
                'id': 'ID Item', 'retirada_id': 'Ret. #', 'responsavel': 'Responsável',
                'setor': 'Setor', 'material': 'Material', 'quantidade': 'Qtd. Retirada',
                'quantidade_devolvida': 'Já Devolvido', 'pendente': 'Pendente',
                'data_retirada': 'Data Retirada', 'previsao_devolucao': 'Prev. Dev.',
                'status': 'Status',
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("📝 Registrar Devolução")

        opcoes_item = {
            f"Item #{r['id']} — {r['material']} (pendente: {r['pendente']} {r['unidade']}) | Resp.: {r['responsavel']}": r['id']
            for _, r in df_view.iterrows()
        }

        if not opcoes_item:
            st.info("Nenhum item encontrado com os filtros selecionados.")
        else:
            with st.form("form_devolucao", clear_on_submit=True):
                item_sel   = st.selectbox("Item a devolver *", list(opcoes_item.keys()))
                item_id    = opcoes_item[item_sel]
                item_row   = df_view[df_view['id'] == item_id].iloc[0]
                pendente   = int(item_row['pendente'])

                col_d1, col_d2 = st.columns(2)
                qtd_dev  = col_d1.number_input(
                    f"Quantidade devolvida (máx: {pendente})",
                    min_value=1, max_value=pendente, value=pendente, step=1
                )
                data_dev = col_d2.date_input("Data da devolução", value=date.today())
                obs_dev  = st.text_area("Observação", height=70)
                salvar_dev = st.form_submit_button("✅ Registrar Devolução", type="primary", use_container_width=True)

            if salvar_dev:
                ok = registrar_devolucao(item_id, qtd_dev, data_dev, obs_dev)
                if ok:
                    st.success(f"✅ Devolução de **{qtd_dev}** unidade(s) registrada com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao registrar devolução.")

# ══════════════════════════════════════════════
# TAB — ENTRADA DE NOVOS PRODUTOS
# ══════════════════════════════════════════════
with tab_ent:
    st.subheader("📦 Entrada de Novos Produtos")
    st.markdown("Use este formulário para registrar a chegada de novos materiais no estoque.")

    df_mat = listar_materiais(apenas_ativos=True)

    if df_mat.empty:
        st.warning("Nenhum material cadastrado. Acesse **Cadastro** primeiro.")
    else:
        opcoes_mat = {
            f"{r['nome']} ({r['unidade']}) — estoque atual: {r['quantidade_estoque']}": r['id']
            for _, r in df_mat.iterrows()
        }

        with st.form("form_entrada_estoque", clear_on_submit=True):
            mat_ent  = st.selectbox("Material *", list(opcoes_mat.keys()))
            col_e1, col_e2 = st.columns(2)
            qtd_ent  = col_e1.number_input("Quantidade recebida *", min_value=1, value=1, step=1)
            data_ent = col_e2.date_input("Data de entrada", value=date.today())
            resp_ent = st.text_input("Responsável pelo recebimento", placeholder="Nome de quem recebeu")
            obs_ent  = st.text_area("Observação / NF / Fornecedor", height=80)
            salvar_ent = st.form_submit_button("✅ Registrar Entrada", type="primary", use_container_width=True)

        if salvar_ent:
            material_id = opcoes_mat[mat_ent]
            registrar_entrada_estoque(material_id, qtd_ent, data_ent, resp_ent, obs_ent)
            st.success(f"✅ Entrada de **{qtd_ent}** unidade(s) registrada no estoque!")
            st.rerun()
