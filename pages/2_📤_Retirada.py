import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
from datetime import date
from db.database import (
    init_db, listar_responsaveis, listar_materiais, registrar_retirada,
)

st.set_page_config(page_title="Retirada | MKT", page_icon="📤", layout="wide")
init_db()

st.title("📤 Registrar Retirada")
st.markdown("Preencha os dados da retirada. Você pode incluir **múltiplos materiais** em uma única operação.")
st.divider()

# ── Carrega dados ──
df_resp = listar_responsaveis(apenas_ativos=True)
df_mat  = listar_materiais(apenas_ativos=True)

if df_resp.empty:
    st.warning("⚠️ Nenhum responsável cadastrado. Acesse **Cadastro** para adicionar.")
    st.stop()
if df_mat.empty:
    st.warning("⚠️ Nenhum material cadastrado. Acesse **Cadastro** para adicionar.")
    st.stop()

opcoes_resp = {f"{r['nome']} ({r['setor'] or 'sem setor'})": r['id'] for _, r in df_resp.iterrows()}
opcoes_mat  = {f"{r['nome']} [{r['unidade']}] — estoque: {r['quantidade_estoque']}": r for _, r in df_mat.iterrows()}

# ── Estado da sessão para a lista de itens ──
if "itens_retirada" not in st.session_state:
    st.session_state.itens_retirada = []

# ══════════════════════════════════════════════
# FORMULÁRIO — DADOS GERAIS
# ══════════════════════════════════════════════
st.subheader("👤 Dados Gerais da Retirada")

col1, col2 = st.columns(2)
resp_selecionado   = col1.selectbox("Responsável *", list(opcoes_resp.keys()), key="resp_ret")
setor_destino      = col2.text_input("Setor / Evento de destino", placeholder="Ex.: Evento Junho, Filial SP…")

col3, col4 = st.columns(2)
data_retirada      = col3.date_input("Data da retirada *", value=date.today())
previsao_devolucao = col4.date_input("Previsão de devolução (opcional)", value=None)
observacao_geral   = st.text_area("Observação geral", placeholder="Detalhes extras sobre esta retirada…", height=80)

st.divider()

# ══════════════════════════════════════════════
# ADICIONAR ITENS
# ══════════════════════════════════════════════
st.subheader("📦 Itens da Retirada")

with st.container(border=True):
    st.markdown("**Adicionar item:**")
    ci1, ci2, ci3 = st.columns([3, 1, 1])
    mat_key = ci1.selectbox("Material", list(opcoes_mat.keys()), key="mat_add")
    qtd_add = ci2.number_input("Quantidade", min_value=1, value=1, step=1, key="qtd_add")

    mat_info   = opcoes_mat[mat_key]
    estoque_at = int(mat_info['quantidade_estoque'])
    ci3.metric("Estoque disponível", estoque_at)

    btn_add = st.button("➕ Adicionar à lista", type="primary", use_container_width=False)

if btn_add:
    if qtd_add > estoque_at:
        st.error(f"❌ Quantidade solicitada ({qtd_add}) maior que o estoque disponível ({estoque_at}).")
    else:
        # Verifica se já está na lista
        material_id = int(mat_info['id'])
        idx_existente = next(
            (i for i, it in enumerate(st.session_state.itens_retirada) if it['material_id'] == material_id),
            None
        )
        if idx_existente is not None:
            st.session_state.itens_retirada[idx_existente]['quantidade'] += qtd_add
        else:
            st.session_state.itens_retirada.append({
                "material_id": material_id,
                "nome":        mat_info['nome'],
                "unidade":     mat_info['unidade'],
                "quantidade":  qtd_add,
            })
        st.rerun()

# ── Tabela de itens adicionados ──
if st.session_state.itens_retirada:
    st.markdown(f"**{len(st.session_state.itens_retirada)} item(ns) na lista:**")
    df_itens = pd.DataFrame(st.session_state.itens_retirada)[['nome', 'unidade', 'quantidade']]
    df_itens.columns = ['Material', 'Unidade', 'Quantidade']
    st.dataframe(df_itens, use_container_width=True, hide_index=True)

    col_rem, _ = st.columns([2, 4])
    rem_opcoes  = [f"{it['nome']} ({it['quantidade']} {it['unidade']})" for it in st.session_state.itens_retirada]
    item_remover = col_rem.selectbox("Remover item:", rem_opcoes, key="item_rem")
    if st.button("🗑️ Remover item selecionado"):
        idx_rem = rem_opcoes.index(item_remover)
        st.session_state.itens_retirada.pop(idx_rem)
        st.rerun()
else:
    st.info("Nenhum item adicionado ainda. Use o formulário acima para inserir materiais.")

st.divider()

# ══════════════════════════════════════════════
# CONFIRMAR RETIRADA
# ══════════════════════════════════════════════
col_btn1, col_btn2, _ = st.columns([2, 2, 4])

if col_btn1.button("✅ Confirmar Retirada", type="primary", use_container_width=True,
                   disabled=len(st.session_state.itens_retirada) == 0):
    responsavel_id = opcoes_resp[resp_selecionado]
    try:
        retirada_id = registrar_retirada(
            responsavel_id     = responsavel_id,
            setor              = setor_destino,
            data_retirada      = data_retirada,
            previsao_devolucao = previsao_devolucao,
            observacao         = observacao_geral,
            itens              = [{"material_id": it['material_id'], "quantidade": it['quantidade']}
                                  for it in st.session_state.itens_retirada],
        )
        st.session_state.itens_retirada = []
        st.success(f"✅ Retirada **#{retirada_id}** registrada com sucesso!")
        st.balloons()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao registrar retirada: {e}")

if col_btn2.button("🗑️ Limpar formulário", use_container_width=True):
    st.session_state.itens_retirada = []
    st.rerun()
