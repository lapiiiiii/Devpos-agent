from typing import Dict, List, Any, Optional, Callable
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AsyncRequestQueue:
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._queue: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False

    async def add_task(
        self,
        task_func: Callable,
        *args,
        priority: int = 0,
        **kwargs
    ) -> Any:
        event = asyncio.Event()
        task_item = {
            "func": task_func,
            "args": args,
            "kwargs": kwargs,
            "priority": priority,
            "event": event,
            "result": None,
            "exception": None,
        }

        await self._queue.put((priority, task_item))
        await event.wait()

        if task_item["exception"]:
            raise task_item["exception"]
        return task_item["result"]

    async def _worker(self):
        while self._running:
            try:
                priority, task_item = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )

                async with self._semaphore:
                    try:
                        result = await task_item["func"](
                            *task_item["args"], **task_item["kwargs"]
                        )
                        task_item["result"] = result
                    except Exception as e:
                        task_item["exception"] = e
                        logger.error(f"Task execution error: {e}")

                task_item["event"].set()
                self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    async def start(self):
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker())
            for _ in range(min(self.max_concurrent, 5))
        ]

    async def stop(self):
        self._running = False
        await asyncio.gather(*self._workers, return_exceptions=True)


class CacheManager:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, prefix: str, **kwargs) -> str:
        key_parts = [prefix]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return "|".join(key_parts)

    def get(self, prefix: str, **kwargs) -> Optional[Any]:
        key = self._generate_key(prefix, **kwargs)

        if key not in self._cache:
            return None

        entry = self._cache[key]
        if datetime.utcnow().timestamp() - entry["timestamp"] > self.ttl_seconds:
            del self._cache[key]
            return None

        entry["last_accessed"] = datetime.utcnow().timestamp()
        entry["access_count"] += 1
        return entry["value"]

    def set(self, prefix: str, value: Any, **kwargs):
        key = self._generate_key(prefix, **kwargs)

        self._cache[key] = {
            "value": value,
            "timestamp": datetime.utcnow().timestamp(),
            "last_accessed": datetime.utcnow().timestamp(),
            "access_count": 0,
        }

    def invalidate(self, prefix: str, **kwargs):
        key = self._generate_key(prefix, **kwargs)
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        total_entries = len(self._cache)
        total_accesses = sum(e["access_count"] for e in self._cache.values())

        return {
            "total_entries": total_entries,
            "total_accesses": total_accesses,
            "cache_size_mb": sum(len(str(v)) for v in self._cache.values()) / (1024 * 1024),
        }


class AsyncBatcher:
    def __init__(self, batch_size: int = 10, timeout_seconds: float = 1.0):
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self._pending: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def add(
        self, item: Any, callback: Callable
    ) -> List[Any]:
        event = asyncio.Event()

        async with self._lock:
            self._pending.append({
                "item": item,
                "callback": callback,
                "event": event,
                "result": None,
            })

            should_process = len(self._pending) >= self.batch_size

        if should_process:
            return await self._process_batch()

        asyncio.create_task(self._delayed_process())

        await event.wait()
        return [self._pending[-1]["result"]]

    async def _delayed_process(self):
        await asyncio.sleep(self.timeout_seconds)

        async with self._lock:
            if self._pending:
                await self._process_batch()

    async def _process_batch(self) -> List[Any]:
        async with self._lock:
            batch = self._pending[:self.batch_size]
            self._pending = self._pending[self.batch_size:]

        if not batch:
            return []

        results = []
        for item in batch:
            try:
                result = await item["callback"](item["item"])
                item["result"] = result
                results.append(result)
            except Exception as e:
                item["result"] = e
                results.append(e)
            finally:
                item["event"].set()

        return results


class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0

    async def __aenter__(self):
        await self._semaphore.acquire()
        self._active_count += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._semaphore.release()
        self._active_count -= 1

    @property
    def active_count(self) -> int:
        return self._active_count


class AsyncOptimizer:
    def __init__(self):
        self.cache_manager = CacheManager(ttl_seconds=300)
        self.request_queue = AsyncRequestQueue(max_concurrent=10)
        self.batcher = AsyncBatcher(batch_size=10, timeout_seconds=1.0)
        self.concurrency_limiter = ConcurrencyLimiter(max_concurrent=5)

    async def cached_call(
        self, cache_key: str, func: Callable, *args, **kwargs
    ) -> Any:
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached_result

        result = await func(*args, **kwargs)
        self.cache_manager.set(cache_key, result)
        return result

    async def optimized_call(
        self,
        func: Callable,
        *args,
        use_cache: bool = True,
        cache_key: Optional[str] = None,
        **kwargs
    ) -> Any:
        if use_cache and cache_key:
            return await self.cached_call(cache_key, func, *args, **kwargs)

        async with self.concurrency_limiter:
            return await func(*args, **kwargs)
