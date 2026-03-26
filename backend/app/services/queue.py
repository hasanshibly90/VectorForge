from typing import Any, Callable, Coroutine

from fastapi import BackgroundTasks


class JobQueue:
    """Abstraction over background task execution.

    MVP: uses FastAPI BackgroundTasks.
    Future: swap to ARQ/Celery with same interface.
    """

    def __init__(self, background_tasks: BackgroundTasks | None = None):
        self._bg = background_tasks

    def enqueue(self, func: Callable[..., Coroutine], *args: Any, **kwargs: Any) -> None:
        if self._bg:
            self._bg.add_task(func, *args, **kwargs)
        else:
            raise RuntimeError("No background task runner configured")
