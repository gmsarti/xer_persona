import logging
import logging.handlers
import sys
from pathlib import Path

from xer_persona.settings import settings


class LogConfig:
    """Configuração centralizada do sistema de logging."""

    def __init__(self):
        self.log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
        self.log_file = getattr(settings, 'LOG_FILE', 'xerazadi.log')
        self.log_format = getattr(
            settings,
            'LOG_FORMAT',
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
        self.log_date_format = getattr(
            settings, 'LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S'
        )

        # Cria diretório de logs se não existir
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)
        self.log_file_path = self.log_dir / self.log_file

    def setup_logging(self):
        """Configura o sistema de logging."""
        # Configura o logger raiz
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Remove handlers existentes para evitar duplicação
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Handler para arquivo (todos os níveis)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            self.log_format, datefmt=self.log_date_format
        )
        file_handler.setFormatter(file_formatter)

        # Handler para console (INFO e superior)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S',
        )
        console_handler.setFormatter(console_formatter)

        # Adiciona handlers ao logger raiz
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Configura loggers específicos
        self._setup_fastapi_logging()
        self._setup_sqlalchemy_logging()
        self._setup_uvicorn_logging()

        logging.info('Sistema de logging configurado com sucesso')
        logging.info(f'Logs sendo salvos em: {self.log_file_path.absolute()}')
        logging.info(f'Nível de log: {self.log_level}')

    @staticmethod
    def _setup_fastapi_logging():
        """Configura logging específico para FastAPI."""
        # Reduz verbosidade do FastAPI
        logging.getLogger('fastapi').setLevel(logging.INFO)
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)

    @staticmethod
    def _setup_sqlalchemy_logging():
        """Configura logging específico para SQLAlchemy."""
        # Log de queries SQL (apenas em desenvolvimento)
        if getattr(settings, 'ENVIRONMENT', 'production') == 'development':
            logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        else:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    @staticmethod
    def _setup_uvicorn_logging():
        """Configura logging específico para Uvicorn."""
        logging.getLogger('uvicorn').setLevel(logging.INFO)
        logging.getLogger('uvicorn.error').setLevel(logging.INFO)


# Instância global da configuração
log_config = LogConfig()


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado para o módulo especificado."""
    return logging.getLogger(name)


def setup_logging():
    """Função para configurar o logging."""
    log_config.setup_logging()