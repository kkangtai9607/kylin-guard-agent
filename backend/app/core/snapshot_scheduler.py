from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class PeriodicSnapshotService:
    def __init__(
        self,
        interval_seconds: float,
        capture: Callable[[], Awaitable[None]],
    ) -> None:
        if interval_seconds < 0.01:
            raise ValueError("snapshot interval is too small")
        self.interval_seconds = interval_seconds
        self.capture = capture
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            await self.capture()
            await asyncio.sleep(self.interval_seconds)
