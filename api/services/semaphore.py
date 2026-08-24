import logging
from contextlib import contextmanager
from typing import Any

from django.core.cache import caches

logger = logging.getLogger(__name__)


class DistributedSemaphore:
    """
    A distributed concurrency limiter backed by Redis BLPOP messaging queue.
    Provides blocking queue mechanism to throttle task execution across Celery workers.
    """

    def __init__(self, key_prefix: str, max_concurrency: int = 5):
        self.key_prefix = key_prefix
        self.max_concurrency = max_concurrency
        self.queue_key = f"concurrency_limit:semaphore:{key_prefix}"
        self.redis_client = get_raw_redis_client("default")
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Populates initial token bucket if the key does not exist."""
        if not self.redis_client.exists(self.queue_key):
            tokens = [f"slot_{i}" for i in range(self.max_concurrency)]
            self.redis_client.rpush(self.queue_key, *tokens)
            # 24-hour expiration prevents unused keys from lingering indefinitely
            self.redis_client.expire(self.queue_key, 86400)

    @contextmanager
    def acquire(self, timeout: int = 30):
        """
        Acquire a slot in a blocking manner.

        Tasks wait in the Redis queue until a slot becomes available or times out,
        eliminating unnecessary Celery task re-queueing and retries.

        :param timeout: Maximum wait time in seconds before raising TimeoutError.
        """
        logger.debug(
            "Waiting for execution slot [%s] (max concurrency: %d)",
            self.key_prefix,
            self.max_concurrency,
        )

        # BLPOP blocks worker thread until a token is available
        result = self.redis_client.blpop(self.queue_key, timeout=timeout)

        if not result:
            logger.error(
                "Slot acquisition timed out after %d seconds [%s]",
                timeout,
                self.key_prefix,
            )
            raise TimeoutError(
                f"Execution slot acquisition timed out for '{self.key_prefix}' after {timeout} seconds."
            )

        token = result[1]
        token_str = token.decode("utf-8") if isinstance(token, bytes) else token
        logger.debug("Slot acquired [%s]: %s", self.key_prefix, token_str)

        try:
            yield
        finally:
            # Return token back to the queue upon completion or error
            self.redis_client.rpush(self.queue_key, token)
            logger.debug("Slot released back to queue [%s]", self.key_prefix)


@contextmanager
def acquire_concurrency_slot(key_prefix: str, max_concurrency: int = 5, timeout: int = 30):
    """
    Context manager helper for concurrency control.

    :param key_prefix: Identifier prefix (e.g., provider name, API category).
    :param max_concurrency: Maximum permitted parallel executions.
    :param timeout: Maximum wait time in seconds before timing out.
    """
    limiter = DistributedSemaphore(key_prefix=key_prefix, max_concurrency=max_concurrency)
    with limiter.acquire(timeout=timeout):
        yield

def get_raw_redis_client(cache_alias: str = "default") -> Any:
    """
    Safely extracts the raw redis-py client from the configured Django cache backend.

    Supports both Django 4.0+ native PyRedisCache and the django-redis package
    while resolving Pylance static type checker warnings (reportAttributeAccessIssue).
    """
    redis_cache = caches[cache_alias]

    # 1. Django 4.0+ native PyRedisCache and modern django-redis
    if hasattr(redis_cache, "client"):
        client_wrapper = getattr(redis_cache, "client")
        if hasattr(client_wrapper, "get_client"):
            return client_wrapper.get_client()

    # 2. Legacy django-redis fallback
    if hasattr(redis_cache, "_cache"):
        internal_cache = getattr(redis_cache, "_cache")
        if hasattr(internal_cache, "get_client"):
            return internal_cache.get_client()

    raise AttributeError(
        f"Cache backend '{cache_alias}' does not support direct Redis client extraction."
    )
