from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    playwright_headless: bool = True

    class Config:
        env_file = ".env"


config = Settings()
