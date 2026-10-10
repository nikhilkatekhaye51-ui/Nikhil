"""Tests for submitting, validating, storing and filtering feedback."""
import pytest

import database
from app import COURSES, create_app


def test_valid_submission_redirects_with_success_message(client, valid_form):
    response = client.post("/submit", data=valid_form, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your feedback was submitted" in response.data
    assert b"Asha Rao" in response.data


def test_feedback_is_saved_in_database(client, valid_form, db_path):
    client.post("/submit", data=valid_form)
    rows = database.list_feedback(db_path)
    assert len(rows) == 1
    assert rows[0]["student_name"] == "Asha Rao"
    assert rows[0]["course"] == COURSES[0]
    assert rows[0]["rating"] == 5


def test_feedback_persists_in_a_new_app_instance(client, valid_form, db_path):
    client.post("/submit", data=valid_form)
    # Simulate an application restart: build a brand new app, same file.
    restarted = create_app({"TESTING": True, "DATABASE": db_path})
    response = restarted.test_client().get("/api/feedback")
    assert response.get_json()["count"] == 1


def test_empty_student_name_is_rejected(client, valid_form, db_path):
    valid_form["student_name"] = "   "
    response = client.post("/submit", data=valid_form)
    assert response.status_code == 400
    assert b"Student name is required" in response.data
    assert database.list_feedback(db_path) == []


@pytest.mark.parametrize("bad_rating", ["abc", "", "3.5", "-1", "0", "6", "100"])
def test_invalid_or_out_of_range_ratings_are_rejected(
    client, valid_form, db_path, bad_rating
):
    valid_form["rating"] = bad_rating
    response = client.post("/submit", data=valid_form)
    assert response.status_code == 400
    assert b"Rating must be a whole number from 1 to 5" in response.data
    assert database.list_feedback(db_path) == []


@pytest.mark.parametrize("rating", ["1", "2", "3", "4", "5"])
def test_every_rating_from_1_to_5_is_accepted(client, valid_form, rating):
    valid_form["rating"] = rating
    assert client.post("/submit", data=valid_form).status_code == 302


def test_invalid_course_is_rejected(client, valid_form, db_path):
    valid_form["course"] = "Underwater Basket Weaving"
    response = client.post("/submit", data=valid_form)
    assert response.status_code == 400
    assert b"Please choose a course" in response.data
    assert database.list_feedback(db_path) == []


def test_empty_message_is_rejected(client, valid_form):
    valid_form["message"] = ""
    response = client.post("/submit", data=valid_form)
    assert response.status_code == 400
    assert b"Feedback message is required" in response.data


def test_too_long_name_and_message_are_rejected(client, valid_form):
    valid_form["student_name"] = "A" * 61
    valid_form["message"] = "B" * 1001
    response = client.post("/submit", data=valid_form)
    assert response.status_code == 400
    assert b"at most 60 characters" in response.data
    assert b"at most 1000 characters" in response.data


def test_html_in_input_is_escaped(client, valid_form):
    valid_form["message"] = "<script>alert(1)</script>"
    client.post("/submit", data=valid_form)
    page = client.get("/feedback").data
    assert b"<script>alert(1)</script>" not in page
    assert b"&lt;script&gt;" in page


def test_duplicate_submission_is_blocked(client, valid_form, db_path):
    assert client.post("/submit", data=valid_form).status_code == 302
    second = client.post("/submit", data=valid_form)
    assert second.status_code == 400
    assert b"do not send it twice" in second.data
    assert len(database.list_feedback(db_path)) == 1


def test_course_filter_shows_only_that_course(client, valid_form):
    client.post("/submit", data=valid_form)
    other = dict(valid_form, course=COURSES[1], message="Different course.")
    client.post("/submit", data=other)

    page = client.get("/feedback", query_string={"course": COURSES[1]}).data
    assert b"Different course." in page
    assert b"Great labs" not in page


def test_unknown_course_filter_shows_error_and_all_items(client, valid_form):
    client.post("/submit", data=valid_form)
    response = client.get("/feedback", query_string={"course": "Nope"})
    assert b"Unknown course filter" in response.data
    assert b"Great labs" in response.data


def test_newest_feedback_is_listed_first(client, valid_form, db_path):
    client.post("/submit", data=valid_form)
    client.post("/submit", data=dict(valid_form, message="Second one."))
    rows = database.list_feedback(db_path)
    assert rows[0]["message"] == "Second one."
