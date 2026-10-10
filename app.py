"""CampusPulse - Student Feedback and Course Rating Portal (Flask app)."""
import os
import sqlite3

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

import database

# The only courses students can choose from.
COURSES = [
    "Cloud Computing and DevOps",
    "Data Structures and Algorithms",
    "Database Management Systems",
    "Operating Systems",
    "Computer Networks",
    "Software Engineering",
    "Machine Learning",
]

MAX_NAME_LENGTH = 60
MAX_MESSAGE_LENGTH = 1000


def get_commit_id():
    """Short Git commit shown in the footer.

    Render sets RENDER_GIT_COMMIT for deployed services. When it is missing
    (for example on your own laptop) we show 'local'.
    """
    commit = os.environ.get("RENDER_GIT_COMMIT", "").strip()
    return commit[:7] if commit else "local"


def validate_feedback(form):
    """Check the submitted form on the server.

    Returns (clean_data, errors). If errors is not empty, the data is invalid.
    """
    name = form.get("student_name", "").strip()
    course = form.get("course", "").strip()
    rating_text = form.get("rating", "").strip()
    message = form.get("message", "").strip()
    errors = {}

    if not name:
        errors["student_name"] = "Student name is required."
    elif len(name) > MAX_NAME_LENGTH:
        errors["student_name"] = (
            f"Name must be at most {MAX_NAME_LENGTH} characters."
        )

    if course not in COURSES:
        errors["course"] = "Please choose a course from the list."

    rating = None
    # isdigit() rejects values such as "3.5", "-1", "abc" and "".
    if rating_text.isascii() and rating_text.isdigit():
        rating = int(rating_text)
    if rating is None or not 1 <= rating <= 5:
        errors["rating"] = "Rating must be a whole number from 1 to 5."

    if not message:
        errors["message"] = "Feedback message is required."
    elif len(message) > MAX_MESSAGE_LENGTH:
        errors["message"] = (
            f"Message must be at most {MAX_MESSAGE_LENGTH} characters."
        )

    clean = {
        "student_name": name,
        "course": course,
        "rating": rating,
        "message": message,
    }
    return clean, errors


def create_app(test_config=None):
    """Application factory: builds and returns a configured Flask app."""
    app = Flask(__name__)
    # SECRET_KEY signs the session cookie used for flash messages.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(24).hex()
    app.config["DATABASE"] = os.environ.get(
        "DATABASE_PATH", database.DEFAULT_DB_PATH
    )
    if test_config:
        app.config.update(test_config)

    database.init_db(app.config["DATABASE"])

    @app.context_processor
    def inject_globals():
        return {"commit_id": get_commit_id(), "courses": COURSES}

    @app.template_filter("stars")
    def stars_filter(rating):
        """Turn 4 into the text '★★★★☆'."""
        rating = int(round(rating or 0))
        return "★" * rating + "☆" * (5 - rating)

    # ---------- Web pages ----------

    @app.route("/")
    def index():
        db = app.config["DATABASE"]
        stats = database.get_stats(db)
        latest = database.list_feedback(db, limit=3)
        return render_template("index.html", stats=stats, latest=latest)

    @app.route("/feedback")
    def feedback_list():
        db = app.config["DATABASE"]
        selected = request.args.get("course", "").strip()
        if selected and selected not in COURSES:
            flash("Unknown course filter, showing all feedback.", "error")
            selected = ""
        items = database.list_feedback(db, course=selected or None)
        return render_template(
            "feedback.html", items=items, selected=selected
        )

    @app.route("/submit", methods=["GET", "POST"])
    def submit():
        if request.method == "GET":
            return render_template("submit.html", values={}, errors={})

        db = app.config["DATABASE"]
        clean, errors = validate_feedback(request.form)
        if not errors and database.is_duplicate(
            db, clean["student_name"], clean["course"], clean["message"]
        ):
            errors["form"] = (
                "This feedback was just submitted. Please do not send it twice."
            )
        if errors:
            return (
                render_template("submit.html", values=clean, errors=errors),
                400,
            )

        database.add_feedback(
            db,
            clean["student_name"],
            clean["course"],
            clean["rating"],
            clean["message"],
        )
        flash("Thank you! Your feedback was submitted.", "success")
        return redirect(url_for("index"))

    # ---------- JSON API ----------

    @app.route("/api/feedback")
    def api_feedback():
        course = request.args.get("course", "").strip()
        if course and course not in COURSES:
            return jsonify(status="error", message="Unknown course."), 400
        items = database.list_feedback(
            app.config["DATABASE"], course=course or None
        )
        return jsonify(status="ok", count=len(items), data=items)

    @app.route("/api/stats")
    def api_stats():
        stats = database.get_stats(app.config["DATABASE"])
        return jsonify(status="ok", data=stats)

    @app.route("/health")
    def health():
        """Health check: also confirms the database can be opened."""
        try:
            with database.connect(app.config["DATABASE"]) as conn:
                conn.execute("SELECT 1")
        except sqlite3.Error:
            return jsonify(status="error"), 503
        return jsonify(status="ok"), 200

    # ---------- Error pages ----------

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify(status="error", message="Not found."), 404
        return render_template("error.html", code=404, text="Page not found."), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith("/api/"):
            return jsonify(status="error", message="Method not allowed."), 405
        return (
            render_template("error.html", code=405, text="Method not allowed."),
            405,
        )

    return app


if __name__ == "__main__":
    # Local development only. In production Gunicorn runs create_app().
    port = int(os.environ.get("PORT", 5000))
    create_app().run(host="127.0.0.1", port=port, debug=True)
