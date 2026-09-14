from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ORCA P2 Ocean Intelligence"
    argo_enabled: bool = True
    argo_api_base: str = "https://argovis-api.colorado.edu"
    argo_search_days: int = 60
    argo_radius_km: float = 150.0
    ocean_data_path: str = "data/ocean_samples.csv"
    pfz_data_path: str = "data/pfz_samples.csv"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
