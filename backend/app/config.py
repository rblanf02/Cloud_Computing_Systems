from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a .env file."""

    # Load configuration from the .env file and ignore extra variables.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL connection URL used by SQLAlchemy.
    database_url: str = "postgresql+psycopg2://appuser:apppass@db:5432/appdb"

    # Environment name. Defaults to development.
    environment: str = "development"

    # Secret key used to sign and verify JWT access tokens.
    # Replace the default value with a secure secret in production.
    jwt_secret: str = "dev-only-change-me"

    # Cryptographic algorithm used to sign JWT tokens.
    jwt_algorithm: str = "HS256"

    # Access token lifetime, expressed in minutes.
    access_token_expire_minutes: int = 60

    # Allowed frontend origins for Cross-Origin Resource Sharing (CORS).
    # Multiple origins can be provided as a comma-separated string.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8443"
    )

    # Enable or disable the creation of an initial administrator account.
    seed_admin: bool = True
    seed_admin_username: str = "admin"
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "admin123"

    # Azure Blob Storage / Azurite connection settings.
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "files"

    # Maximum size allowed for an uploaded file.
    max_upload_size_mb: int = 10

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