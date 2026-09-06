from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Patissier"
    SYNC_DATABASE_URL: set
    DATABASE_URL : str #async URL for fastapi gateway later

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()