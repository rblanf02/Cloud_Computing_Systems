from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a .env file."""

    # Load configuration from the .env file and ignore extra variables.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL connection URL used by SQLAlchemy.
    database_url: str = "postgresql+psycopg2://appuser:apppass@db:5432/appdb"

    # Secret key used to sign and verify JWT access tokens.
    # Replace the default value with a secure secret in production.
    jwt_secret: str = "change-me-in-production"

    # Cryptographic algorithm used to sign JWT tokens.
    jwt_algorithm: str = "HS256"

    # Access token lifetime, expressed in minutes.
    access_token_expire_minutes: int = 60

    # Allowed frontend origins for Cross-Origin Resource Sharing (CORS).
    # Multiple origins can be provided as a comma-separated string.
    cors_origins: str = "*"

    # Enable or disable the creation of an initial administrator account.
    seed_admin: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        """Return the configured CORS origins as a cleaned list of strings."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


# Create a settings instance accessible throughout the application.
settings = Settings()