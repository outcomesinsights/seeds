"""Pytest fixtures for seeds tests."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from seeds.db import Database
from seeds.models import (
    Relationship,
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def db(temp_dir):
    """Create an initialized test database."""
    db_path = temp_dir / ".seeds" / "seeds.db"
    database = Database(path=db_path)
    database.init()
    yield database
    database.close()


@pytest.fixture
def sample_seed():
    """Create a sample seed for testing."""
    return Seed(
        id="seed-test",
        title="Test Seed",
        content="This is test content",
        status=SeedStatus.CAPTURED,
        seed_type=SeedType.IDEA,
        tags=["test", "sample"],
    )


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def cli_env(temp_dir):
    """Create environment for CLI testing with isolated .seeds directory."""
    seeds_dir = temp_dir / ".seeds"
    seeds_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
