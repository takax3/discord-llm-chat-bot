from discordbot.version import get_app_version


def test_get_app_version_from_project_metadata() -> None:
    version = get_app_version()

    assert version == "0.1.0"
