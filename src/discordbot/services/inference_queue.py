from __future__ import annotations

import asyncio


class InferenceQueue:
    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._next_ticket = 0
        self._serving_ticket = 0
        self._cancelled_tickets: set[int] = set()

    async def reserve(self) -> tuple[int, int]:
        async with self._condition:
            ticket = self._next_ticket
            self._next_ticket += 1
            return ticket, self._queue_ahead(ticket)

    async def wait_for_ahead_change(
        self,
        *,
        ticket: int,
        previous_ahead: int,
    ) -> int:
        async with self._condition:
            await self._condition.wait_for(
                lambda: self._queue_ahead(ticket) != previous_ahead
            )
            return self._queue_ahead(ticket)

    async def finish_turn(self, ticket: int) -> None:
        async with self._condition:
            if ticket != self._serving_ticket:
                return
            self._advance_serving_ticket_locked()
            self._condition.notify_all()

    async def cancel(self, ticket: int) -> None:
        async with self._condition:
            if ticket < self._serving_ticket:
                return
            self._cancelled_tickets.add(ticket)
            while self._serving_ticket in self._cancelled_tickets:
                self._cancelled_tickets.remove(self._serving_ticket)
                self._advance_serving_ticket_locked()
            self._condition.notify_all()

    def _queue_ahead(self, ticket: int) -> int:
        ahead = 0
        for queued_ticket in range(self._serving_ticket, ticket):
            if queued_ticket not in self._cancelled_tickets:
                ahead += 1
        return ahead

    def _advance_serving_ticket_locked(self) -> None:
        self._serving_ticket += 1
        while self._serving_ticket in self._cancelled_tickets:
            self._cancelled_tickets.remove(self._serving_ticket)
            self._serving_ticket += 1
