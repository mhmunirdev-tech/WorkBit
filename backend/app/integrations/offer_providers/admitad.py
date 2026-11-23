from app.core.config import settings

ADMITAD_API_ORIGIN = "https://api.admitad.com"
ADMITAD_SLUG = "admitad"


class AdmitadConfigurationError(RuntimeError):
    pass


def admitad_credentials() -> tuple[str, str, str]:
    if not settings.admitad_enabled:
        raise AdmitadConfigurationError("Admitad integration is disabled.")

    client_id = (settings.admitad_client_id or "").strip()
    client_secret = settings.admitad_client_secret or ""
    website_id = (settings.admitad_website_id or "").strip()
    if not client_id or not client_secret or not website_id:
        raise AdmitadConfigurationError(
            "Admitad client credentials and approved website ID are required."
        )
    if not website_id.isdigit() or int(website_id) <= 0:
        raise AdmitadConfigurationError("Admitad website ID must be a positive integer.")
    return client_id, client_secret, website_id
