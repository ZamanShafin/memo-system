import os
os.environ['DATABASE_URL'] = 'sqlite://'

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.seed import seed_database

TEST_ENGINE = create_engine(
    'sqlite://',
    connect_args={'check_same_thread': False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

@pytest.fixture(scope='session', autouse=True)
def init_test_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestingSessionLocal()
    seed_database(seed_demo_memos=True, db_session=db)
    db.close()
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
