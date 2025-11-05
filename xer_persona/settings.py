from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    OPENAI_API_KEY: str

    # Configuração de logging
    LOG_LEVEL: str = 'INFO'
    LOG_FILE: str = 'xerazadi.log'
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'
    ENVIRONMENT: str = 'production'


settings = Settings()  # type: ignore
