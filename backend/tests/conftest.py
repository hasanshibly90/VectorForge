import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.models import *  # noqa: F401, F403 — register all models with Base.metadata

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session, db_engine):
    from app.main import app
    import app.database as database_module
    import app.workers.conversion_worker as worker_module

    # Override get_db to use test session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Override the async_session factory used by background workers
    test_session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    original_session = database_module.async_session
    database_module.async_session = test_session_factory
    worker_module.async_session = test_session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    database_module.async_session = original_session
