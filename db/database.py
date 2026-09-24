import sqlite3
import os
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'materiais.db')


def get_connection():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria todas as tabelas se não existirem."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS responsaveis (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nome    TEXT    NOT NULL,
            setor   TEXT,
            ativo   INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS materiais (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            nome               TEXT    NOT NULL,
            categoria          TEXT,
            quantidade_estoque INTEGER DEFAULT 0,
            unidade            TEXT    DEFAULT 'unid',
            ativo              INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS retiradas (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            responsavel_id      INTEGER,
            setor               TEXT,
            data_retirada       TEXT,
            previsao_devolucao  TEXT,
            observacao          TEXT,
            status              TEXT DEFAULT 'aberto',
            FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id)
        );

        CREATE TABLE IF NOT EXISTS retirada_itens (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            retirada_id          INTEGER NOT NULL,
            material_id          INTEGER NOT NULL,
            quantidade           INTEGER NOT NULL,
            quantidade_devolvida INTEGER DEFAULT 0,
            status               TEXT    DEFAULT 'aberto',
            FOREIGN KEY (retirada_id) REFERENCES retiradas(id),
            FOREIGN KEY (material_id) REFERENCES materiais(id)
        );

        CREATE TABLE IF NOT EXISTS movimentacoes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            quantidade  INTEGER NOT NULL,
            tipo        TEXT    NOT NULL,   -- 'entrada' | 'devolucao'
            data        TEXT    NOT NULL,
            responsavel TEXT,
            observacao  TEXT,
            retirada_item_id INTEGER,
            FOREIGN KEY (material_id) REFERENCES materiais(id)
        );
    """)
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# RESPONSÁVEIS
# ──────────────────────────────────────────────

def listar_responsaveis(apenas_ativos=True):
    conn = get_connection()
    q = "SELECT * FROM responsaveis"
    q += " WHERE ativo = 1" if apenas_ativos else ""
    q += " ORDER BY nome"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def inserir_responsavel(nome, setor):
    conn = get_connection()
    conn.execute("INSERT INTO responsaveis (nome, setor) VALUES (?, ?)", (nome, setor))
    conn.commit()
    conn.close()


def atualizar_responsavel(id_, nome, setor, ativo):
    conn = get_connection()
    conn.execute(
        "UPDATE responsaveis SET nome=?, setor=?, ativo=? WHERE id=?",
        (nome, setor, int(ativo), id_)
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# MATERIAIS
# ──────────────────────────────────────────────

def listar_materiais(apenas_ativos=True):
    conn = get_connection()
    q = "SELECT * FROM materiais"
    q += " WHERE ativo = 1" if apenas_ativos else ""
    q += " ORDER BY nome"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def inserir_material(nome, categoria, quantidade, unidade):
    conn = get_connection()
    conn.execute(
        "INSERT INTO materiais (nome, categoria, quantidade_estoque, unidade) VALUES (?,?,?,?)",
        (nome, categoria, quantidade, unidade)
    )
    conn.commit()
    conn.close()


def atualizar_material(id_, nome, categoria, quantidade, unidade, ativo):
    conn = get_connection()
    conn.execute(
        "UPDATE materiais SET nome=?, categoria=?, quantidade_estoque=?, unidade=?, ativo=? WHERE id=?",
        (nome, categoria, quantidade, unidade, int(ativo), id_)
    )
    conn.commit()
    conn.close()


def ajustar_estoque(material_id, delta):
    """Incrementa (delta>0) ou decrementa (delta<0) o estoque."""
    conn = get_connection()
    conn.execute(
        "UPDATE materiais SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?",
        (delta, material_id)
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# RETIRADAS
# ──────────────────────────────────────────────

def registrar_retirada(responsavel_id, setor, data_retirada, previsao_devolucao, observacao, itens):
    """
    itens: lista de dicts {material_id, quantidade}
    Decrementa o estoque de cada material retirado.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO retiradas (responsavel_id, setor, data_retirada, previsao_devolucao, observacao, status)
           VALUES (?,?,?,?,?,'aberto')""",
        (responsavel_id, setor, str(data_retirada), str(previsao_devolucao) if previsao_devolucao else None, observacao)
    )
    retirada_id = cur.lastrowid
    for item in itens:
        cur.execute(
            "INSERT INTO retirada_itens (retirada_id, material_id, quantidade) VALUES (?,?,?)",
            (retirada_id, item['material_id'], item['quantidade'])
        )
        cur.execute(
            "UPDATE materiais SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?",
            (item['quantidade'], item['material_id'])
        )
    conn.commit()
    conn.close()
    return retirada_id


def listar_retiradas(status=None):
    conn = get_connection()
    q = """
        SELECT r.id, resp.nome AS responsavel, r.setor, r.data_retirada,
               r.previsao_devolucao, r.observacao, r.status
        FROM retiradas r
        LEFT JOIN responsaveis resp ON resp.id = r.responsavel_id
    """
    if status:
        q += f" WHERE r.status = '{status}'"
    q += " ORDER BY r.data_retirada DESC"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def listar_itens_retirada(retirada_id=None, status=None):
    conn = get_connection()
    q = """
        SELECT ri.id, ri.retirada_id, m.nome AS material, m.unidade,
               ri.quantidade, ri.quantidade_devolvida,
               ri.quantidade - ri.quantidade_devolvida AS pendente,
               ri.status,
               r.data_retirada, r.previsao_devolucao,
               resp.nome AS responsavel, r.setor
        FROM retirada_itens ri
        JOIN materiais m    ON m.id = ri.material_id
        JOIN retiradas r    ON r.id = ri.retirada_id
        LEFT JOIN responsaveis resp ON resp.id = r.responsavel_id
        WHERE 1=1
    """
    params = []
    if retirada_id:
        q += " AND ri.retirada_id = ?"
        params.append(retirada_id)
    if status:
        q += " AND ri.status = ?"
        params.append(status)
    q += " ORDER BY r.data_retirada DESC"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def registrar_devolucao(item_id, quantidade_devolvida, data_devolucao, observacao):
    """Registra devolução parcial ou total de um item de retirada."""
    conn = get_connection()
    cur = conn.cursor()

    # Busca o item
    row = cur.execute(
        "SELECT material_id, quantidade, quantidade_devolvida FROM retirada_itens WHERE id=?",
        (item_id,)
    ).fetchone()
    if not row:
        conn.close()
        return False

    material_id = row['material_id']
    qtd_total   = row['quantidade']
    qtd_dev_ant = row['quantidade_devolvida']
    nova_qtd_dev = qtd_dev_ant + quantidade_devolvida

    novo_status = 'devolvido' if nova_qtd_dev >= qtd_total else 'parcial'

    cur.execute(
        "UPDATE retirada_itens SET quantidade_devolvida=?, status=? WHERE id=?",
        (nova_qtd_dev, novo_status, item_id)
    )

    # Atualiza estoque
    cur.execute(
        "UPDATE materiais SET quantidade_estoque = quantidade_estoque + ? WHERE id=?",
        (quantidade_devolvida, material_id)
    )

    # Registra movimentação
    cur.execute(
        """INSERT INTO movimentacoes (material_id, quantidade, tipo, data, observacao, retirada_item_id)
           VALUES (?,?,'devolucao',?,?,?)""",
        (material_id, quantidade_devolvida, str(data_devolucao), observacao, item_id)
    )

    # Atualiza status da retirada pai
    retirada_id = cur.execute(
        "SELECT retirada_id FROM retirada_itens WHERE id=?", (item_id,)
    ).fetchone()['retirada_id']
    todos_status = cur.execute(
        "SELECT status FROM retirada_itens WHERE retirada_id=?", (retirada_id,)
    ).fetchall()
    status_list = [s['status'] for s in todos_status]
    if all(s == 'devolvido' for s in status_list):
        cur.execute("UPDATE retiradas SET status='devolvido' WHERE id=?", (retirada_id,))
    elif any(s in ('devolvido', 'parcial') for s in status_list):
        cur.execute("UPDATE retiradas SET status='parcial' WHERE id=?", (retirada_id,))

    conn.commit()
    conn.close()
    return True


def registrar_entrada_estoque(material_id, quantidade, data, responsavel, observacao):
    """Entrada direta de novos produtos no estoque."""
    conn = get_connection()
    conn.execute(
        "UPDATE materiais SET quantidade_estoque = quantidade_estoque + ? WHERE id=?",
        (quantidade, material_id)
    )
    conn.execute(
        """INSERT INTO movimentacoes (material_id, quantidade, tipo, data, responsavel, observacao)
           VALUES (?,?,'entrada',?,?,?)""",
        (material_id, quantidade, str(data), responsavel, observacao)
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# DASHBOARD / RELATÓRIOS
# ──────────────────────────────────────────────

def stats_gerais():
    conn = get_connection()
    stats = {}
    stats['total_materiais'] = conn.execute(
        "SELECT COUNT(*) FROM materiais WHERE ativo=1"
    ).fetchone()[0]
    stats['retiradas_abertas'] = conn.execute(
        "SELECT COUNT(*) FROM retiradas WHERE status='aberto'"
    ).fetchone()[0]
    stats['itens_pendentes'] = conn.execute(
        "SELECT COALESCE(SUM(quantidade - quantidade_devolvida),0) FROM retirada_itens WHERE status!='devolvido'"
    ).fetchone()[0]
    stats['total_responsaveis'] = conn.execute(
        "SELECT COUNT(*) FROM responsaveis WHERE ativo=1"
    ).fetchone()[0]
    conn.close()
    return stats


def top_materiais_retirados(limit=10):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT m.nome, SUM(ri.quantidade) AS total_retirado
        FROM retirada_itens ri
        JOIN materiais m ON m.id = ri.material_id
        GROUP BY m.id
        ORDER BY total_retirado DESC
        LIMIT ?
    """, conn, params=(limit,))
    conn.close()
    return df


def retiradas_por_status():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT status, COUNT(*) AS qtd
        FROM retiradas
        GROUP BY status
    """, conn)
    conn.close()
    return df


def historico_completo():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            r.id        AS retirada_id,
            r.data_retirada,
            r.previsao_devolucao,
            resp.nome   AS responsavel,
            r.setor,
            m.nome      AS material,
            m.categoria,
            m.unidade,
            ri.quantidade,
            ri.quantidade_devolvida,
            ri.quantidade - ri.quantidade_devolvida AS pendente,
            ri.status   AS status_item,
            r.status    AS status_retirada,
            r.observacao
        FROM retirada_itens ri
        JOIN retiradas r       ON r.id  = ri.retirada_id
        JOIN materiais m       ON m.id  = ri.material_id
        LEFT JOIN responsaveis resp ON resp.id = r.responsavel_id
        ORDER BY r.data_retirada DESC, r.id DESC
    """, conn)
    conn.close()
    return df


def movimentacoes_completas():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT mv.data, mv.tipo, m.nome AS material, mv.quantidade,
               mv.responsavel, mv.observacao
        FROM movimentacoes mv
        JOIN materiais m ON m.id = mv.material_id
        ORDER BY mv.data DESC, mv.id DESC
    """, conn)
    conn.close()
    return df
