# Notes API

A session-authenticated Flask REST API for private notes. Users can create, list, read, update, and delete their own notes. The API uses bcrypt password hashes, Flask sessions, SQLAlchemy, and Flask-Migrate.

## Requirements

- Python 3.8.13
- Pipenv
- Node.js and npm, if you want to run the supplied sessions client

## Installation

From the `server` directory, create the virtual environment and install dependencies:

```bash
pipenv install --python 3.8.13
```

The project pins Flask and Werkzeug versions that are compatible with Python 3.8.13. Copy the example environment file and set a strong secret key:

```bash
cp .env.example .env
```

Edit `.env`, then load its values into your current Bash session:

```bash
set -a
source .env
set +a
```

For local development, `SESSION_COOKIE_SECURE=false` is appropriate. Set it to `true` when serving the API over HTTPS. If a frontend runs on a separate origin, set `FRONTEND_ORIGIN` to that exact origin.

## Database setup

The project includes its initial migration. Apply it to create the database tables:

```bash
pipenv run flask --app app db upgrade
```

To generate and apply a migration after changing a model:

```bash
pipenv run flask --app app db migrate -m "describe the schema change"
pipenv run flask --app app db upgrade
```

## Seed data

Seed two demo accounts and three sample notes:

```bash
pipenv run python seed.py
```

Demo login details:

- `brian` / `password123`
- `yobby` / `password123`

**The seed script deletes existing users and notes before reseeding. Use it only with a development database.**

## Run the API

Start the API from the `server` directory:

```bash
pipenv run flask --app app run --host 0.0.0.0 --port 5555
```

The API listens on `http://localhost:5555`. Use the Flask CLI command above; running `python app.py` directly can trigger a circular import.

Check that the service is responding:

```bash
curl -i http://localhost:5555/api/health
```

## Run the supplied sessions client

Leave the API running. In a second terminal, start the client:

```bash
cd ../client-with-sessions
npm install
npm start
```

The sessions client uses cookie-based authentication. Browser requests must include credentials. If the frontend calls the API from a separate origin, configure `FRONTEND_ORIGIN` and allow credentialed requests.

## API endpoints

All request and response bodies use JSON unless the response is empty.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Check that the API is running. |
| `POST` | `/signup` | Create an account and sign in. Requires `username`, `password`, and `password_confirmation`. |
| `POST` | `/login` | Sign in with `username` and `password`. |
| `GET` | `/check_session` | Return the signed-in user's `id` and `username`; return `{}` when signed out. |
| `DELETE` | `/logout` | Clear the current session and return `{}`. |
| `GET` | `/notes?page=1&per_page=10` | List the signed-in user's notes with pagination metadata. `per_page` is capped at 100. |
| `POST` | `/notes` | Create a note. Requires `title` and `content`. |
| `GET` | `/notes/<id>` | Read one of the signed-in user's notes. |
| `PATCH` | `/notes/<id>` | Update an owned note's `title` and/or `content`. |
| `DELETE` | `/notes/<id>` | Delete an owned note. |
| `GET` | `/api/auth/me` | Additional session check; returns 401 when signed out. |

The auth routes also have `/api/auth/register`, `/api/auth/login`, and `/api/auth/logout` aliases. The Notes routes also have `/api/notes` aliases.

## Access control and responses

All Notes endpoints require a signed-in user and only return or modify notes owned by that user. Requests for another user's note return `404 Not Found`. Unauthenticated Notes requests return `401 Unauthorized`.

Successful account creation and note creation return `201 Created`. Invalid input returns `400 Bad Request`; a duplicate username returns `409 Conflict`. Deleting a note returns `204 No Content`.
