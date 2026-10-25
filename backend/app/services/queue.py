"""ARQ job enqueue helpers."""

from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.settings import Settings

_pool: ArqRedis | None = None


def redis_settings_from_url(url: str) -> RedisSettings:
    return RedisSettings.from_dsn(url)


async def get_arq_pool(settings: Settings) -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings_from_url(settings.redis_url))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close(close_connection_pool=True)
        _pool = None


async def enqueue_analyze(settings: Settings, run_id: str) -> str:
    """Enqueue analyze_sheet_job; returns ARQ job id (may differ from run_id)."""
    pool = await get_arq_pool(settings)
    job = await pool.enqueue_job("analyze_sheet_job", run_id, _job_id=run_id)
    return job.job_id if job else run_id
