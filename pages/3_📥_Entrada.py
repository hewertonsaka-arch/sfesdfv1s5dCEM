import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
from datetime import date
from db.database import (
    init_db,
    listar_materiais,
    registrar_entrada_estoque,
)

st.set_page_config(page_title="Entrada | MKT", page_icon="📥", layout="wide")
init_db()

st.title("📥 Entrada de Materiais")
st.markdown("Registre a **entrada de novos produtos** no estoque.")
st.divider()

# ══════════════════════════════════════════════
# ENTRADA DE NOVOS PRODUTOS
# ══════════════════════════════════════════════
st.subheader("📦 Formulário de Entrada")
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
