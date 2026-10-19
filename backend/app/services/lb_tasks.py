"""产线平衡寻优 / SOP 批量等长任务的内存任务管理（MVP，对应计划书 §4.3）。

寻优 DFS 是 CPU 密集且有 60~150s 超时上限，故走「提交→后台线程跑→前端轮询」模式，
不阻塞事件循环。MVP 用进程内字典存任务态；规模上来再换 Redis/Celery（计划书 §5.1）。
"""
from __future__ import annotations
import asyncio
import uuid
import time
from typing import Any, Callable


class Task:
    __slots__ = ("id", "status", "progress", "result", "error", "created_at", "updated_at")

    def __init__(self, task_id: str):
        self.id = task_id
        self.status = "pending"  # pending|running|done|error
        self.progress = ""
        self.result: Any = None
        self.error: str | None = None
        self.created_at = time.time()
        self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "taskId": self.id,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
        }


class TaskManager:
    def __init__(self, ttl_seconds: int = 1800):
        self._tasks: dict[str, Task] = {}
        self._ttl = ttl_seconds

    def _gc(self) -> None:
        now = time.time()
        stale = [tid for tid, t in self._tasks.items()
                 if t.status in ("done", "error") and now - t.updated_at > self._ttl]
        for tid in stale:
            self._tasks.pop(tid, None)

    def create(self) -> Task:
        self._gc()
        task = Task(uuid.uuid4().hex)
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def submit(self, task: Task, fn: Callable[[Callable[[str], None]], Any]) -> None:
        """在后台线程跑 fn(progress_cb)，把结果/异常写回 task。"""
        loop = asyncio.get_running_loop()

        def _progress(msg: str) -> None:
            task.progress = msg
            task.updated_at = time.time()

        async def _runner():
            task.status = "running"
            task.updated_at = time.time()
            try:
                result = await asyncio.to_thread(fn, _progress)
                task.result = result
                task.status = "done"
            except Exception as e:  # noqa: BLE001 — 任务态需捕获全部异常回传前端
                task.error = str(e)
                task.status = "error"
            finally:
                task.updated_at = time.time()

        loop.create_task(_runner())


task_manager = TaskManager()
