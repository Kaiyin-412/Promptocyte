from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./promptsentinel.db"
    ml_model_path: str = "../ml/model"
    allow_threshold: int = 49
    warn_threshold: int = 79

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
