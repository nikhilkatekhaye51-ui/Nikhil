"""Shared pytest fixtures. Every test gets its own temporary database."""
import pytest

from app import COURSES, create_app


@pytest.fixture
def db_path(tmp_path):
    """A fresh SQLite file in a temporary folder (deleted after the test)."""
    return str(tmp_path / "test_campuspulse.db")


@pytest.fixture
def app(db_path):
    """A CampusPulse app that uses the temporary database."""
    return create_app({"TESTING": True, "DATABASE": db_path})


@pytest.fixture
def client(app):
    """Flask test client: sends fake requests without starting a server."""
    return app.test_client()


@pytest.fixture
def valid_form():
    """A correct form submission that tests can copy and modify."""
    return {
        "student_name": "Asha Rao",
        "course": COURSES[0],
        "rating": "5",
        "message": "Great labs and very clear explanations.",
    }
