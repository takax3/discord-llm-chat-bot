import asyncio

from discordbot.services.inference_queue import InferenceQueue


def test_reserve_returns_ticket_and_zero_when_no_request_is_running() -> None:
    async def scenario() -> tuple[int, int]:
        queue = InferenceQueue()
        return await queue.reserve()

    ticket, queue_ahead = asyncio.run(scenario())

    assert ticket == 0
    assert queue_ahead == 0


def test_reserve_counts_running_and_waiting_requests() -> None:
    async def scenario() -> tuple[int, int, int]:
        queue = InferenceQueue()
        first_ticket, first_ahead = await queue.reserve()
        second_ticket, second_ahead = await queue.reserve()
        third_ticket, third_ahead = await queue.reserve()
        await queue.cancel(second_ticket)
        updated_ahead = await queue.wait_for_ahead_change(
            ticket=third_ticket,
            previous_ahead=third_ahead,
        )
        await queue.finish_turn(first_ticket)
        return first_ahead, second_ahead, updated_ahead

    first_ahead, second_ahead, updated_ahead = asyncio.run(scenario())

    assert first_ahead == 0
    assert second_ahead == 1
    assert updated_ahead == 1


def test_wait_for_ahead_change_reaches_zero_after_previous_turn_finishes() -> None:
    async def scenario() -> int:
        queue = InferenceQueue()
        first_ticket, _ = await queue.reserve()
        second_ticket, second_ahead = await queue.reserve()

        async def release_first() -> None:
            await asyncio.sleep(0)
            await queue.finish_turn(first_ticket)

        release_task = asyncio.create_task(release_first())
        updated_ahead = await queue.wait_for_ahead_change(
            ticket=second_ticket,
            previous_ahead=second_ahead,
        )
        await release_task
        return updated_ahead

    updated_ahead = asyncio.run(scenario())

    assert updated_ahead == 0


def test_get_status_returns_waiting_count() -> None:
    async def scenario() -> tuple[int, int, int]:
        queue = InferenceQueue()
        first_ticket, _ = await queue.reserve()
        await queue.reserve()
        await queue.reserve()
        await queue.finish_turn(first_ticket)
        status = await queue.get_status()
        return status.running_count, status.waiting_count, status.total_count

    running_count, waiting_count, total_count = asyncio.run(scenario())

    assert running_count == 1
    assert waiting_count == 1
    assert total_count == 2
