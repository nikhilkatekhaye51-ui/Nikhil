"""Tests for the JSON API endpoints."""
import database
from app import COURSES


def add(db_path, course, rating, name="Student", message="ok"):
    """Insert a row directly so API tests do not depend on the web form."""
    database.add_feedback(db_path, name, course, rating, message)


def test_feedback_api_returns_valid_json(client, db_path):
    add(db_path, COURSES[0], 4, name="Ravi", message="Nice")
    response = client.get("/api/feedback")
    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["count"] == 1
    assert body["data"][0]["student_name"] == "Ravi"
    assert body["data"][0]["rating"] == 4


def test_feedback_api_empty_database(client):
    body = client.get("/api/feedback").get_json()
    assert body == {"status": "ok", "count": 0, "data": []}


def test_feedback_api_filters_by_course(client, db_path):
    add(db_path, COURSES[0], 5)
    add(db_path, COURSES[1], 3)
    body = client.get("/api/feedback", query_string={"course": COURSES[1]}).get_json()
    assert body["count"] == 1
    assert body["data"][0]["course"] == COURSES[1]


def test_feedback_api_rejects_unknown_course(client):
    response = client.get("/api/feedback", query_string={"course": "Nope"})
    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


def test_stats_api_with_no_data(client):
    data = client.get("/api/stats").get_json()["data"]
    assert data["total_feedback"] == 0
    assert data["average_rating"] == 0.0
    assert data["courses_with_feedback"] == 0
    assert data["courses"] == []


def test_stats_api_calculates_correct_values(client, db_path):
    add(db_path, COURSES[0], 5)
    add(db_path, COURSES[0], 4)
    add(db_path, COURSES[1], 3)
    response = client.get("/api/stats")
    data = response.get_json()["data"]

    assert response.status_code == 200
    assert data["total_feedback"] == 3
    assert data["average_rating"] == 4.0
    assert data["courses_with_feedback"] == 2
    assert data["rating_distribution"] == {"1": 0, "2": 0, "3": 1, "4": 1, "5": 1}

    by_course = {row["course"]: row for row in data["courses"]}
    assert by_course[COURSES[0]]["count"] == 2
    assert by_course[COURSES[0]]["average_rating"] == 4.5
    assert by_course[COURSES[1]]["average_rating"] == 3.0


def test_stats_average_is_rounded_to_two_decimals(client, db_path):
    for rating in (5, 5, 4):
        add(db_path, COURSES[0], rating)
    data = client.get("/api/stats").get_json()["data"]
    assert data["average_rating"] == 4.67
