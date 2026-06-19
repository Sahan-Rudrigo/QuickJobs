# QuickJobs — User Service

## What is this service?

The User Service manages all job seeker profiles on the QuickJobs platform.
It is the single source of truth for everything related to a job seeker's data.

Every other service that needs user information calls this service.
No other service touches the users database directly.

---

## What can you do with User Service?

| Action | Who calls it | When |
|--------|-------------|------|
| Create a new user profile | WhatsApp Gateway | After onboarding conversation completes |
| Get a user profile | WhatsApp Gateway, Matching Service, Notification Service | Whenever user data is needed |
| Update profile fields | WhatsApp Gateway | When user updates via WhatsApp menu |
| Update CV info | Matching Service | After CV is processed and embedded |
| Opt out of alerts | WhatsApp Gateway | When user sends STOP |
| Opt in to alerts | WhatsApp Gateway | When user sends START |
| Delete user data | WhatsApp Gateway | PDPA compliance — user requests deletion |

---

## How to run locally

### Step 1 — Make sure Docker is running

PostgreSQL and Redis must be running via docker-compose.
Go to the infra folder and run:

```
docker-compose up -d
```

Verify both are running:
```
docker ps
```
You should see quickjobs-postgres and quickjobs-redis listed.

### Step 2 — Create your .env file

Copy the example file:
```
cp .env.example .env
```

The default values already match the docker-compose settings.
No changes needed for local development.

### Step 3 — Create virtual environment and install packages

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4 — Run the service

```
uvicorn main:app --reload --port 8001
```

You should see:
```
Starting User Service...
Database tables created/verified
Redis connection OK
User Service ready on port 8001
API docs available at: http://localhost:8001/docs
```

### Step 5 — Open API docs

Go to your browser:
```
http://localhost:8001/docs
```

You will see the Swagger UI where you can test all endpoints directly.

---

## All API Endpoints

### Health Check
```
GET /health
```
Returns service status, Redis status, and database status.
Use this to verify the service is running correctly.

---

### Create User
```
POST /users
```
Creates a new job seeker profile.

Body example:
```json
{
  "phone": "94771234567",
  "name": "Kasun Perera",
  "skills": ["Python", "React", "SQL"],
  "experience_level": "mid",
  "location": "Colombo",
  "salary_min": 80000,
  "salary_max": 150000,
  "availability": "actively_looking",
  "opt_in_status": true
}
```

Valid values for experience_level: junior, mid, senior, lead
Valid values for availability: actively_looking, open, not_looking

Returns 201 on success.
Returns 400 if phone number already exists.

---

### Get User
```
GET /users/{phone}
```
Returns full profile for a user.

Example:
```
GET /users/94771234567
```

Returns 404 if user not found.

---

### Update User
```
PATCH /users/{phone}
```
Updates one or more fields. Only fields you include get updated.

Example — update only skills:
```json
{
  "skills": ["Python", "Django", "AWS"]
}
```

Example — update CV info (called by Matching Service):
```json
{
  "cv_s3_key": "cvs/94771234567/v2/cv.pdf",
  "cv_version": 2
}
```

Returns 404 if user not found.

---

### Opt Out
```
PATCH /users/{phone}/opt-out
```
Stops job alert notifications for this user.
Called when user sends STOP on WhatsApp.

Sets opt_in_status = false in PostgreSQL AND Redis.

---

### Opt In
```
PATCH /users/{phone}/opt-in
```
Resumes job alert notifications for this user.
Called when user sends START on WhatsApp.

Sets opt_in_status = true in PostgreSQL AND Redis.

---

### Delete User
```
DELETE /users/{phone}
```
Permanently deletes user and all their data.
Required for PDPA compliance.

Also removes opt_in key from Redis.

Note: CV files in S3 are deleted separately by the File Service.

---

### Get All Users
```
GET /users?skip=0&limit=50
```
Returns a paginated list of all users.
Used by Admin Service for monitoring.

---

## How other services use User Service

### WhatsApp Gateway calls:
```
POST   /users              → after onboarding completes
GET    /users/{phone}      → to show current values before update
PATCH  /users/{phone}      → after user confirms update
PATCH  /users/{phone}/opt-out  → when user sends STOP
PATCH  /users/{phone}/opt-in   → when user sends START
DELETE /users/{phone}      → when user requests data deletion
```

### Matching Service calls:
```
GET    /users/{phone}      → to get profile when CV arrives
PATCH  /users/{phone}      → to update cv_s3_key and cv_version
```

### Notification Service calls:
```
GET    /users/{phone}      → to get name for notification message
```
Note: Notification Service checks Redis directly for opt_in status.
It only calls this endpoint for the name field.

---

## How to run tests

```
pip install pytest
pytest test_main.py -v
```

Tests use SQLite so you don't need PostgreSQL running for tests.
Redis calls are mocked automatically.

You should see all tests passing like this:
```
test_health_check PASSED
test_create_user_success PASSED
test_create_user_duplicate_phone PASSED
test_get_user_success PASSED
test_get_user_not_found PASSED
test_update_user_skills PASSED
test_opt_out_success PASSED
test_opt_in_success PASSED
test_delete_user_success PASSED
...
```

---

## File Structure

```
user-service/
├── main.py          → FastAPI app setup, startup logic, health check
├── models.py        → PostgreSQL table definition (User table)
├── schemas.py       → Request and response data shapes (Pydantic)
├── routes.py        → All API endpoints logic
├── database.py      → PostgreSQL connection setup
├── redis_client.py  → Redis connection and opt-in/opt-out helpers
├── test_main.py     → All tests
├── requirements.txt → Python packages needed
├── Dockerfile       → For containerizing the service
├── .env.example     → Environment variable template
└── README.md        → This file
```

---

## Ports used by all services (for reference)

| Service | Port |
|---------|------|
| WhatsApp Gateway | 8000 |
| User Service | 8001 |
| File Service | 8002 |
| Company Service | 8003 |
| Matching Service | 8004 |
| Notification Service | 8005 |
| Admin Service | 8006 |
| Next.js Employer Dashboard | 3000 |
| Next.js Admin Panel | 3001 |
| PostgreSQL | 5432 |
| Redis | 6379 |
