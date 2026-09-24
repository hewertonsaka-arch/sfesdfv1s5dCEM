import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
from db.database import (
    init_db,
    listar_materiais, inserir_material, atualizar_material,
    listar_responsaveis, inserir_responsavel, atualizar_responsavel,
)

st.set_page_config(page_title="Cadastro | MKT", page_icon="📋", layout="wide")
init_db()

st.title("📋 Cadastro")
st.markdown("Gerencie **materiais** e **responsáveis** cadastrados no sistema.")
st.divider()

tab_mat, tab_resp = st.tabs(["📦 Materiais", "👤 Responsáveis"])

# ══════════════════════════════════════════════
# TAB — MATERIAIS
# ══════════════════════════════════════════════
with tab_mat:
    col_form, col_lista = st.columns([1, 2], gap="large")

    with col_form:
        st.subheader("➕ Novo Material")
        with st.form("form_material", clear_on_submit=True):
            nome_mat      = st.text_input("Nome do material *")
            categoria_mat = st.text_input("Categoria", placeholder="Brindes, Banners, Kits…")
            col_q, col_u  = st.columns(2)
            qtd_mat       = col_q.number_input("Estoque inicial", min_value=0, value=0, step=1)
            und_mat       = col_u.selectbox("Unidade", ["unid", "cx", "pct", "kit", "rolo", "m²", "par"])
            submitted_mat = st.form_submit_button("💾 Salvar Material", use_container_width=True, type="primary")

        if submitted_mat:
            if not nome_mat.strip():
                st.error("O nome do material é obrigatório.")
            else:
                inserir_material(nome_mat.strip(), categoria_mat.strip(), qtd_mat, und_mat)
                st.success(f"✅ Material **{nome_mat}** cadastrado!")
                st.rerun()

    with col_lista:
        st.subheader("📦 Materiais Cadastrados")
        mostrar_inativos = st.checkbox("Mostrar inativos", key="mat_inativos")
        df_mat = listar_materiais(apenas_ativos=not mostrar_inativos)

        if df_mat.empty:
            st.info("Nenhum material cadastrado ainda.")
        else:
            # Estoque baixo (highlight)
            def highlight_estoque(row):
                if row.get("quantidade_estoque", 999) <= 0:
                    return ["background-color: #fee2e2"] * len(row)
                elif row.get("quantidade_estoque", 999) <= 5:
                    return ["background-color: #fef9c3"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df_mat.rename(columns={
                    "id": "ID", "nome": "Nome", "categoria": "Categoria",
                    "quantidade_estoque": "Estoque", "unidade": "Unid.", "ativo": "Ativo"
                }).style.apply(highlight_estoque, axis=1),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("🔴 Estoque zerado   🟡 Estoque ≤ 5")

        # Edição
        st.divider()
        st.subheader("✏️ Editar Material")
        if df_mat.empty:
            st.info("Nenhum material para editar.")
        else:
            opcoes = {f"[{r['id']}] {r['nome']}": r for _, r in df_mat.iterrows()}
            sel = st.selectbox("Selecione o material", list(opcoes.keys()), key="sel_mat_edit")
            mat_sel = opcoes[sel]
            with st.form("form_edit_mat"):
                e_nome  = st.text_input("Nome", value=mat_sel['nome'])
                e_cat   = st.text_input("Categoria", value=mat_sel.get('categoria', '') or '')
                c1, c2  = st.columns(2)
                e_qtd   = c1.number_input("Estoque", min_value=0, value=int(mat_sel['quantidade_estoque']))
                unidades = ["unid", "cx", "pct", "kit", "rolo", "m²", "par"]
                idx_und  = unidades.index(mat_sel['unidade']) if mat_sel['unidade'] in unidades else 0
                e_und   = c2.selectbox("Unidade", unidades, index=idx_und)
                e_ativo = st.checkbox("Ativo", value=bool(mat_sel['ativo']))
                salvar_edit = st.form_submit_button("💾 Atualizar", type="primary", use_container_width=True)

            if salvar_edit:
                atualizar_material(mat_sel['id'], e_nome, e_cat, e_qtd, e_und, e_ativo)
                st.success("✅ Material atualizado!")
                st.rerun()

# ══════════════════════════════════════════════
# TAB — RESPONSÁVEIS
# ══════════════════════════════════════════════
with tab_resp:
    col_form_r, col_lista_r = st.columns([1, 2], gap="large")

    with col_form_r:
        st.subheader("➕ Novo Responsável")
        with st.form("form_responsavel", clear_on_submit=True):
            nome_resp  = st.text_input("Nome completo *")
            setor_resp = st.text_input("Setor / Área", placeholder="Marketing, Eventos…")
            submitted_resp = st.form_submit_button("💾 Salvar Responsável", use_container_width=True, type="primary")

        if submitted_resp:
            if not nome_resp.strip():
                st.error("O nome é obrigatório.")
            else:
                inserir_responsavel(nome_resp.strip(), setor_resp.strip())
                st.success(f"✅ Responsável **{nome_resp}** cadastrado!")
                st.rerun()

    with col_lista_r:
        st.subheader("👤 Responsáveis Cadastrados")
        mostrar_inat_resp = st.checkbox("Mostrar inativos", key="resp_inativos")
        df_resp = listar_responsaveis(apenas_ativos=not mostrar_inat_resp)

        if df_resp.empty:
            st.info("Nenhum responsável cadastrado ainda.")
        else:
            st.dataframe(
                df_resp.rename(columns={"id": "ID", "nome": "Nome", "setor": "Setor", "ativo": "Ativo"}),
                use_container_width=True,
                hide_index=True,
            )

        st.divider()
        st.subheader("✏️ Editar Responsável")
        if df_resp.empty:
            st.info("Nenhum responsável para editar.")
        else:
            opcoes_r = {f"[{r['id']}] {r['nome']}": r for _, r in df_resp.iterrows()}
            sel_r    = st.selectbox("Selecione", list(opcoes_r.keys()), key="sel_resp_edit")
            resp_sel = opcoes_r[sel_r]
            with st.form("form_edit_resp"):
                er_nome  = st.text_input("Nome", value=resp_sel['nome'])
                er_setor = st.text_input("Setor", value=resp_sel.get('setor', '') or '')
                er_ativo = st.checkbox("Ativo", value=bool(resp_sel['ativo']))
                salvar_r = st.form_submit_button("💾 Atualizar", type="primary", use_container_width=True)

            if salvar_r:
                atualizar_responsavel(resp_sel['id'], er_nome, er_setor, er_ativo)
                st.success("✅ Responsável atualizado!")
                st.rerun()
