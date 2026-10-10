# CampusPulse - Student Feedback and Course Rating Portal

CampusPulse is a small Flask web app where students rate their courses and
leave feedback. The dashboard shows live statistics calculated from a SQLite
database. The project also demonstrates a full CI/CD pipeline
(GitHub Actions -> Docker build -> Render deploy).

## Problem statement
Colleges collect course feedback on paper or in scattered forms, so results
are slow to read and easy to lose. CampusPulse collects feedback in one place,
validates it, stores it, and shows averages instantly.

## Objectives
- Build a dynamic, server-rendered web app (Flask + Jinja2).
- Validate every input on the server.
- Expose JSON API and health-check endpoints.
- Test automatically (pytest) and lint automatically (flake8).
- Use Git/GitHub, GitHub Actions CI/CD, Docker and Render.
- Show the deployed Git commit in the page footer.

## Features
- Dashboard: total feedback, overall average, courses reviewed, rating
  breakdown (1-5 stars), per-course averages, most recent feedback.
- Feedback form: name, course (dropdown), rating 1-5, message.
- Server-side validation, max lengths, duplicate-submission guard.
- Feedback list, newest first, with star ratings and server-side course filter.
- JSON API: `/api/feedback`, `/api/stats`, `/health`.
- Responsive layout, CSS-variable design system, accessible labels.
- Footer shows the first 7 characters of `RENDER_GIT_COMMIT` (or `local`).

## Technology stack
Python 3.12, Flask, Jinja2, SQLite, HTML/CSS, a little vanilla JavaScript,
pytest, flake8, Gunicorn, Docker, GitHub Actions, Render.

## Architecture overview
```
Browser --HTTP--> Flask routes (app.py) --SQL--> SQLite file (database.py)
                       |
                       +--> Jinja2 templates -> HTML
```
- `app.py` holds routes, validation and the `create_app()` factory.
- `database.py` holds all SQL (parameterized queries only).
- Tests build their own app pointing at a temporary database file.

## Folder structure
```
campuspulse/
├── app.py                  routes, validation, app factory
├── database.py             SQLite helpers and statistics
├── requirements.txt        runtime dependencies (Flask, Gunicorn)
├── requirements-dev.txt    adds pytest and flake8 (used by CI)
├── pytest.ini              tells pytest where code and tests are
├── .flake8                 lint settings
├── Dockerfile, .dockerignore, render.yaml
├── templates/              base, index (dashboard), feedback (list),
│                           submit (form), error, _macros
├── static/css/style.css, static/js/main.js
├── tests/                  conftest.py, test_health.py,
│                           test_feedback.py, test_api.py
└── .github/workflows/ci-cd.yml
```
Changes from the suggested layout: added `submit.html` (the form page),
`error.html` and `_macros.html` (shared star/card markup), and
`requirements-dev.txt` (so Docker images do not contain test tools).

## Prerequisites (Windows)
Python 3.12, Git, a GitHub account, a Render account, and Docker Desktop
(optional, for local container runs).

## Local setup (Windows PowerShell)
```powershell
cd campuspulse
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```
If activation is blocked, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**Database initialization:** automatic. `create_app()` creates
`campuspulse.db` and the `feedback` table on first start.

**Run locally**
```powershell
python app.py
```
Open http://127.0.0.1:5000

**Tests and lint**
```powershell
pytest -v
flake8 .
```

## Docker
```powershell
docker build -t campuspulse .
docker run -d --name campuspulse -p 8000:8000 campuspulse
# open http://localhost:8000
curl http://localhost:8000/health
```
Use a volume to keep data between container runs:
`docker run -d -p 8000:8000 -v campuspulse-data:/data campuspulse`

## GitHub setup
```powershell
git init -b main
git add .
git commit -m "Initial CampusPulse project"
git remote add origin https://github.com/<your-username>/campuspulse.git
git push -u origin main
```
Create the empty repository on github.com first. Make several smaller commits
as you customize the project.

## CI/CD workflow (`.github/workflows/ci-cd.yml`)
| Job | Runs when | What it does |
|-----|-----------|--------------|
| lint | every push and pull request | checkout, Python 3.12, install, `flake8 .` |
| test | after lint passes | `pytest -v` |
| build | after test passes | `docker build`, then starts the container and calls `/health` |
| deploy | after build passes AND only on a push to `main` | POSTs to the Render deploy hook |

Why broken code is not deployed: each job has `needs:` on the previous one,
so a failure stops everything after it. The deploy job also has
`if: github.event_name == 'push' && github.ref == 'refs/heads/main'`, so pull
requests and feature branches never deploy.

## Environment variables and secrets
| Name | Where | Purpose |
|------|-------|---------|
| `RENDER_GIT_COMMIT` | set by Render automatically | commit shown in footer |
| `SECRET_KEY` | Render environment (use "Generate") | signs flash-message cookie |
| `DATABASE_PATH` | optional; Docker image defaults to `/data/campuspulse.db` | SQLite file location |
| `PORT` | set by Render | port Gunicorn listens on |
| `RENDER_DEPLOY_HOOK` | **GitHub Actions secret** | deploy-hook URL |

Never put the deploy-hook URL in code, the README, or a commit. Anyone with
that URL can trigger deploys.

## Render deployment (you do these steps with your own accounts)
Files I generated: `Dockerfile`, `render.yaml`, the workflow. Everything below
needs your accounts.
1. Create an account at render.com and sign in with GitHub.
2. Push this project to your own GitHub repository.
3. Dashboard -> **New** -> **Web Service** -> connect your repository.
4. Choose language/runtime **Docker** (it uses the Dockerfile; no build or
   start command is needed).
5. Pick an instance type. Check Render's current pricing page for what is free.
6. Add environment variable `SECRET_KEY` (any long random text).
7. Under Advanced, set **Health Check Path** to `/health` and **Auto-Deploy**
   to **Off**, so only the pipeline deploys.
8. Create the service and wait for the first deploy.
9. Service **Settings** -> **Deploy Hook** -> copy the URL.
10. GitHub repo -> **Settings** -> **Secrets and variables** -> **Actions** ->
    **New repository secret**: name `RENDER_DEPLOY_HOOK`, value = the URL.
11. Push a commit to `main`; watch the **Actions** tab, then open your Render
    URL (shown at the top of the service page).
12. Visit `<your-url>/health` - expect `{"status":"ok"}`.
13. Compare the footer commit with `git rev-parse --short=7 HEAD`.

**Persistence warning:** SQLite is a file. On a hosting instance with an
ephemeral filesystem, the file is deleted on redeploy or restart. To keep
data you need a persistent disk (a paid Render feature - the commented `disk`
block in `render.yaml` mounts one at `/data`, matching `DATABASE_PATH`) or an
external database. For a demo, losing data is acceptable; just say so in
your viva.

### Troubleshooting
| Problem | Fix |
|---------|-----|
| `RENDER_DEPLOY_HOOK secret is missing` | Add the secret (step 10). |
| curl error 404/410 in deploy job | The hook URL is wrong or was regenerated; copy it again. |
| Render shows "Port scan timeout" | Do not change the Dockerfile CMD; it binds to `$PORT`. |
| Footer shows `local` | You are running locally, or the deploy did not happen. |
| Data disappeared | Ephemeral disk; see persistence warning. |
| `flake8` fails on CI only | Run `flake8 .` locally and fix the lines it prints. |
| PowerShell cannot activate venv | Change execution policy (see setup). |
| `ModuleNotFoundError: app` when running pytest | Run it from the project root (where `pytest.ini` is). |

## Verifying a deployment
1. Actions tab: all four jobs are green.
2. Render dashboard shows the new deploy as **Live**.
3. `<your-url>/health` returns 200 with `{"status":"ok"}`.
4. The footer commit matches the first 7 characters of your latest commit.

## CI/CD demonstration for the assessment
**Success demo**
1. Make a small change (e.g. edit a heading in `templates/index.html`).
2. `git add . && git commit -m "Update dashboard heading" && git push`
3. Open Actions: lint, test, build pass; deploy runs and finishes.
4. Open the live site and show the footer commit equals your new commit.

**Failure demo (never break `main`)**
1. `git checkout -b demo/failing-test`
2. In `tests/test_health.py` change `== 200` to `== 500` in
   `test_health_returns_ok_json`.
3. Commit and `git push -u origin demo/failing-test`.
4. Actions: the **test** job fails; **build** and **deploy** are skipped.
5. Fix the test, commit, push: all checks pass (deploy still skipped, since
   this is not `main`).

Prevention is caused by two conditions in the workflow: `needs: test` on the
build job and `needs: build` on the deploy job (a failed `needs` job means the
dependent job is skipped), and the deploy job's `if:` check for `refs/heads/main`.

## API documentation
| Method | Path | Response |
|--------|------|----------|
| GET | `/health` | `200 {"status":"ok"}` (`503 {"status":"error"}` if DB fails) |
| GET | `/api/feedback` | `{"status":"ok","count":N,"data":[...]}` newest first |
| GET | `/api/feedback?course=<name>` | same, filtered; `400` if course unknown |
| GET | `/api/stats` | `{"status":"ok","data":{total_feedback, average_rating, courses_with_feedback, rating_distribution, courses[]}}` |

Errors use `{"status":"error","message":"..."}`.

## Screenshots
Add your own screenshots after running the app:
- Dashboard: `docs/screenshots/dashboard.png` *(placeholder)*
- Feedback form: `docs/screenshots/form.png` *(placeholder)*
- GitHub Actions run: `docs/screenshots/actions.png` *(placeholder)*
- Live footer commit: `docs/screenshots/footer.png` *(placeholder)*

## Viva questions and answers
1. **What is Flask?** A lightweight Python web framework that maps URLs to Python functions.
2. **What is a dynamic web application?** Pages are generated by the server from live data (here, the database) instead of fixed HTML files.
3. **What is SQLite?** A database stored in a single file, needing no separate server.
4. **What is Git?** A version-control tool that records the history of your code.
5. **What is GitHub?** A website that hosts Git repositories and runs GitHub Actions.
6. **What is a Git branch?** A separate line of development, e.g. `demo/failing-test`, so `main` stays safe.
7. **What is a pull request?** A request to merge one branch into another, where checks and reviews run first.
8. **What is CI?** Continuous Integration: automatically lint and test every change.
9. **What is CD?** Continuous Delivery/Deployment: automatically release changes that passed CI. Here, Render is triggered after checks pass.
10. **What is GitHub Actions?** GitHub's built-in automation service that runs workflows on events such as a push.
11. **What is a workflow YAML file?** A text file in `.github/workflows/` listing triggers, jobs and steps (ours is `ci-cd.yml`).
12. **What is pytest?** A Python testing tool; we use it with Flask's test client in `tests/`.
13. **What is flake8?** A linter that reports style problems and unused code, configured in `.flake8`.
14. **What is Docker?** A tool that packages an app with its dependencies so it runs the same everywhere.
15. **What is a Docker image?** The read-only package/blueprint built from the Dockerfile.
16. **What is a Docker container?** A running instance of an image.
17. **What is Render?** A cloud platform that hosts web services; we deploy the Docker image there.
18. **What is a deployment hook?** A secret URL; sending a POST request to it makes Render start a deploy.
19. **What is an API?** A way for programs to exchange data; ours returns JSON at `/api/feedback` and `/api/stats`.
20. **What is a health-check endpoint?** `/health` returns `{"status":"ok"}` with 200 when the app and database work; platforms use it to check the service.
21. **Why is input validation important?** Users can send bad or malicious data; `validate_feedback()` checks name, course, rating and message on the server, because browser checks can be bypassed.
22. **How does the pipeline prevent broken code from being deployed?** Jobs are chained with `needs:`; deploy only runs after lint, test and build succeed, and only on `main`.
23. **What happens when a test fails?** The test job fails, so build and deploy are skipped and the failure shows in the Actions tab.
24. **How is the average rating calculated?** SQL `AVG(rating)` over all rows, rounded to 2 decimals in `get_stats()`; 0.0 if there is no feedback.
25. **How does the deployed app identify the running commit?** Render sets `RENDER_GIT_COMMIT`; `get_commit_id()` shows its first 7 characters, or `local` if absent.
26. **Why parameterized queries?** SQL uses `?` placeholders so input is treated as data, preventing SQL injection.
27. **Why can data be lost on Render?** SQLite is a file, and without a persistent disk the container filesystem is ephemeral.
