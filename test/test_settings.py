from app.core.settings import get_settings


def test_settings_loaded():
    settings = get_settings()
    assert settings.app_name
    assert settings.mysql_url.startswith("mysql")
    assert settings.openai_base_url.startswith("http")
