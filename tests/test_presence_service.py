from discordbot.services.presence_service import PresenceService


def test_build_status_text_uses_queue_count_and_speed() -> None:
    service = PresenceService()
    service.set_queue_count(2)
    service.set_tokens_per_second(14.25)

    assert service.build_status_text() == "Queue: 2 | 14.2 tok/s"


def test_build_status_text_uses_placeholder_when_speed_is_unknown() -> None:
    service = PresenceService()
    service.set_queue_count(0)

    assert service.build_status_text() == "Queue: 0 | -- tok/s"
