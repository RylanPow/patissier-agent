from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Patissier"
    SYNC_DATABASE_URL: str
    DATABASE_URL : str #async URL for fastapi gateway later
    GOOGLE_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()