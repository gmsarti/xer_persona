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


def create_classification_tables(conn):
    """Cria as tabelas de classificação e relacionamento."""
    cursor = conn.cursor()

    # Tabela de classificações
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            classificacao_id INTEGER PRIMARY KEY AUTOINCREMENT,
            classification_name TEXT NOT NULL,
            framework TEXT NOT NULL,
            UNIQUE(classification_name, framework)
        )
    """)

    # Tabela de relacionamento entre contos e classificações
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tale_classifications (
            conto_id INTEGER NOT NULL,
            classificacao_id INTEGER NOT NULL,
            PRIMARY KEY (conto_id, classificacao_id),
            FOREIGN KEY (conto_id) REFERENCES tales(id) ON DELETE CASCADE,
            FOREIGN KEY (classificacao_id) REFERENCES classifications(classificacao_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    print("Tabelas 'classifications' e 'tale_classifications' criadas com sucesso.")


def insert_classification(conn, classification_name, framework):
    """
    Insere uma classificação ou retorna o ID se já existir.

    Args:
        conn: Conexão com o banco de dados
        classification_name: Nome da classificação (ex: "ATU 333", "Superando o Monstro")
        framework: Framework da classificação (ex: "ATU", "Booker", "Propp_Papel")

    Returns:
        classificacao_id: ID da classificação inserida ou existente
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO classifications (classification_name, framework)
        VALUES (?, ?)
        ON CONFLICT(classification_name, framework) DO NOTHING
    """,
        (classification_name, framework),
    )

    # Busca o ID da classificação
    cursor.execute(
        """
        SELECT classificacao_id FROM classifications
        WHERE classification_name = ? AND framework = ?
    """,
        (classification_name, framework),
    )

    result = cursor.fetchone()
    conn.commit()

    return result[0] if result else None


def link_tale_classification(conn, conto_id, classificacao_id):
    """
    Cria o vínculo entre um conto e uma classificação.

    Args:
        conn: Conexão com o banco de dados
        conto_id: ID do conto
        classificacao_id: ID da classificação
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO tale_classifications (conto_id, classificacao_id)
        VALUES (?, ?)
    """,
        (conto_id, classificacao_id),
    )

    conn.commit()


def add_classification_to_tale(conn, conto_id, classification_name, framework):
    """
    Função auxiliar que insere a classificação e cria o vínculo em uma única chamada.

    Args:
        conn: Conexão com o banco de dados
        conto_id: ID do conto
        classification_name: Nome da classificação
        framework: Framework da classificação
    """
    classificacao_id = insert_classification(conn, classification_name, framework)
    if classificacao_id:
        link_tale_classification(conn, conto_id, classificacao_id)


def get_tale_classifications(conn, conto_id):
    """
    Retorna todas as classificações de um conto.

    Args:
        conn: Conexão com o banco de dados
        conto_id: ID do conto

    Returns:
        Lista de tuplas (classification_name, framework)
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT c.classification_name, c.framework
        FROM classifications c
        JOIN tale_classifications tc ON c.classificacao_id = tc.classificacao_id
        WHERE tc.conto_id = ?
    """,
        (conto_id,),
    )

    return cursor.fetchall()


def get_tales_by_classification(conn, classification_name=None, framework=None):
    """
    Retorna todos os contos que possuem determinada classificação.

    Args:
        conn: Conexão com o banco de dados
        classification_name: Nome da classificação (opcional)
        framework: Framework da classificação (opcional)

    Returns:
        Lista de contos
    """
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT t.*
        FROM tales t
        JOIN tale_classifications tc ON t.id = tc.conto_id
        JOIN classifications c ON tc.classificacao_id = c.classificacao_id
        WHERE 1=1
    """
    params = []

    if classification_name:
        query += ' AND c.classification_name = ?'
        params.append(classification_name)

    if framework:
        query += ' AND c.framework = ?'
        params.append(framework)

    cursor.execute(query, params)
    return cursor.fetchall()
