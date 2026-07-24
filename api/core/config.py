from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_key: str = ""
    anthropic_api_key: str = ""
    voyage_api_key: str = ""
    tesseract_cmd: str = ""
    deepgram_api_key: str = ""
    # comma-separated allowed browser origins for CORS; default covers local dev
    cors_origins: str = "http://localhost:3000"


settings = Settings()
