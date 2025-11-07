import sqlite3

from .config import DB_NAME, TABLE_NAME


def setup_db():
    """Cria a tabela no banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Usando f-string para o nome da tabela, pois ele não pode ser parametrizado.
    # Isso é seguro aqui, pois o nome da tabela vem do nosso arquivo de configuração.
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            origem TEXT,
            url TEXT NOT NULL,
            texto_completo TEXT,
            UNIQUE(url, titulo)
        )
    """)
    conn.commit()
    conn.close()
    print(f"Banco de dados '{DB_NAME}' e tabela '{TABLE_NAME}' configurados.")


def insert_tale(conn, titulo, origem, url, texto_completo):
    """Insere um conto no banco de dados ou atualiza se já existir."""
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO {TABLE_NAME} (titulo, origem, url, texto_completo)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(url, titulo) DO UPDATE SET
        origem=excluded.origem,
        texto_completo=excluded.texto_completo
    """,
        (titulo, origem, url, texto_completo),
    )
    conn.commit()
