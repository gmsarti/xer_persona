from pathlib import Path
from urllib.parse import urljoin

# Configurações da Raspagem
BASE_URL = 'https://sites.pitt.edu/~dash/'
START_URL = urljoin(BASE_URL, 'folktexts.html')

# Define o caminho para o diretório de dados na raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)  # Cria o diretório 'data' se não existir

DB_NAME = str(DATA_DIR / 'contos.sqlite')
TABLE_NAME = 'tales'

# Adiciona um cabeçalho User-Agent para simular um navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
