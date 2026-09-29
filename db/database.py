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
            estoque_minimo     INTEGER DEFAULT 0,
            ativo              INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS retiradas (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            responsavel_id      INTEGER,
            setor               TEXT,
            data_retirada       TEXT,
            observacao          TEXT,
            status              TEXT DEFAULT 'sucesso',
            FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id)
        );

        CREATE TABLE IF NOT EXISTS retirada_itens (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            retirada_id          INTEGER NOT NULL,
            material_id          INTEGER NOT NULL,
            quantidade           INTEGER NOT NULL,
            FOREIGN KEY (retirada_id) REFERENCES retiradas(id),
            FOREIGN KEY (material_id) REFERENCES materiais(id)
        );

        CREATE TABLE IF NOT EXISTS movimentacoes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            quantidade  INTEGER NOT NULL,
            tipo        TEXT    NOT NULL,   -- 'entrada' | 'retirada'
            data        TEXT    NOT NULL,
            responsavel TEXT,
            observacao  TEXT,
            retirada_id INTEGER,
            FOREIGN KEY (material_id) REFERENCES materiais(id)
        );
    """)
    try:
        conn.execute("ALTER TABLE materiais ADD COLUMN estoque_minimo INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
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


def inserir_material(nome, categoria, quantidade, unidade, estoque_minimo=0):
    conn = get_connection()
    conn.execute(
        "INSERT INTO materiais (nome, categoria, quantidade_estoque, unidade, estoque_minimo) VALUES (?,?,?,?,?)",
        (nome, categoria, quantidade, unidade, estoque_minimo)
    )
    conn.commit()
    conn.close()


def atualizar_material(id_, nome, categoria, quantidade, unidade, estoque_minimo, ativo):
    conn = get_connection()
    conn.execute(
        "UPDATE materiais SET nome=?, categoria=?, quantidade_estoque=?, unidade=?, estoque_minimo=?, ativo=? WHERE id=?",
        (nome, categoria, quantidade, unidade, estoque_minimo, int(ativo), id_)
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


def materiais_estoque_baixo():
    """Retorna materiais onde estoque atual <= estoque_minimo (e estoque_minimo > 0)."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, nome, categoria, quantidade_estoque, estoque_minimo, unidade
        FROM materiais
        WHERE ativo = 1 AND estoque_minimo > 0 AND quantidade_estoque <= estoque_minimo
        ORDER BY quantidade_estoque ASC
    """, conn)
    conn.close()
    return df


# ──────────────────────────────────────────────
# RETIRADAS
# ──────────────────────────────────────────────

def registrar_retirada(responsavel_id, setor, data_retirada, observacao, itens):
    """
    itens: lista de dicts {material_id, quantidade}
    Decrementa o estoque de cada material retirado.
    Status sempre 'sucesso' — material é distribuído ao cliente.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO retiradas (responsavel_id, setor, data_retirada, observacao, status)
           VALUES (?,?,?,?,'sucesso')""",
        (responsavel_id, setor, str(data_retirada), observacao)
    )
    retirada_id = cur.lastrowid
    for item in itens:
        cur.execute(
            "INSERT INTO retirada_itens (retirada_id, material_id, quantidade) VALUES (?,?,?)",
            (retirada_id, item['material_id'], item['quantidade'])
        )
        # Decrementa estoque
        cur.execute(
            "UPDATE materiais SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?",
            (item['quantidade'], item['material_id'])
        )
        # Registra movimentação
        cur.execute(
            """INSERT INTO movimentacoes (material_id, quantidade, tipo, data, observacao, retirada_id)
               VALUES (?,?,'retirada',?,?,?)""",
            (item['material_id'], item['quantidade'], str(data_retirada), observacao, retirada_id)
        )
    conn.commit()
    conn.close()
    return retirada_id


def listar_retiradas(limit=None):
    conn = get_connection()
    q = """
        SELECT r.id, resp.nome AS responsavel, r.setor, r.data_retirada,
               r.observacao, r.status,
               COUNT(ri.id) AS total_itens,
               SUM(ri.quantidade) AS total_unidades
        FROM retiradas r
        LEFT JOIN responsaveis resp ON resp.id = r.responsavel_id
        LEFT JOIN retirada_itens ri ON ri.retirada_id = r.id
        GROUP BY r.id
        ORDER BY r.data_retirada DESC, r.id DESC
    """
    if limit:
        q += f" LIMIT {int(limit)}"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def listar_itens_retirada(retirada_id):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT ri.id, ri.retirada_id, m.nome AS material, m.unidade,
               ri.quantidade,
               r.data_retirada,
               resp.nome AS responsavel, r.setor
        FROM retirada_itens ri
        JOIN materiais m    ON m.id = ri.material_id
        JOIN retiradas r    ON r.id = ri.retirada_id
        LEFT JOIN responsaveis resp ON resp.id = r.responsavel_id
        WHERE ri.retirada_id = ?
        ORDER BY m.nome
    """, conn, params=(retirada_id,))
    conn.close()
    return df


def cancelar_retirada(retirada_id):
    """
    Cancela uma retirada e reverte o estoque dos itens.
    Status muda para 'cancelado'.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Verifica se a retirada existe e está com status sucesso
    row = cur.execute(
        "SELECT status FROM retiradas WHERE id=?", (retirada_id,)
    ).fetchone()
    if not row or row['status'] == 'cancelado':
        conn.close()
        return False

    # Reverte o estoque de cada item
    itens = cur.execute(
        "SELECT material_id, quantidade FROM retirada_itens WHERE retirada_id=?",
        (retirada_id,)
    ).fetchall()
    for item in itens:
        cur.execute(
            "UPDATE materiais SET quantidade_estoque = quantidade_estoque + ? WHERE id=?",
            (item['quantidade'], item['material_id'])
        )

    # Marca a retirada como cancelada
    cur.execute("UPDATE retiradas SET status='cancelado' WHERE id=?", (retirada_id,))

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
    stats['total_retiradas'] = conn.execute(
        "SELECT COUNT(*) FROM retiradas WHERE status='sucesso'"
    ).fetchone()[0]
    stats['total_responsaveis'] = conn.execute(
        "SELECT COUNT(*) FROM responsaveis WHERE ativo=1"
    ).fetchone()[0]
    stats['total_unidades_retiradas'] = conn.execute(
        """SELECT COALESCE(SUM(ri.quantidade), 0)
           FROM retirada_itens ri
           JOIN retiradas r ON r.id = ri.retirada_id
           WHERE r.status = 'sucesso'"""
    ).fetchone()[0]
    stats['alertas_estoque'] = conn.execute(
        """SELECT COUNT(*) FROM materiais
           WHERE ativo=1 AND estoque_minimo > 0 AND quantidade_estoque <= estoque_minimo"""
    ).fetchone()[0]
    conn.close()
    return stats


def top_materiais_retirados(limit=10):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT m.nome, SUM(ri.quantidade) AS total_retirado
        FROM retirada_itens ri
        JOIN materiais m ON m.id = ri.material_id
        JOIN retiradas r ON r.id = ri.retirada_id
        WHERE r.status = 'sucesso'
        GROUP BY m.id
        ORDER BY total_retirado DESC
        LIMIT ?
    """, conn, params=(limit,))
    conn.close()
    return df


def retiradas_por_mes(meses=12):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT strftime('%Y-%m', data_retirada) AS mes,
               COUNT(*) AS total_retiradas,
               0 AS placeholder
        FROM retiradas
        WHERE status = 'sucesso'
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT ?
    """, conn, params=(meses,))
    conn.close()
    return df


def historico_completo():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            r.id        AS retirada_id,
            r.data_retirada,
            resp.nome   AS responsavel,
            r.setor,
            m.nome      AS material,
            m.categoria,
            m.unidade,
            ri.quantidade,
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
