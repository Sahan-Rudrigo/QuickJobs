# QuickJobs

A WhatsApp-first AI-powered job matching platform for blue-collar and semi-skilled workers in Sri Lanka.

Candidates register, upload CVs, and receive personalised job alerts entirely through WhatsApp — no app download or website required. Employers post jobs through a web dashboard, and an AI matching engine automatically finds the best-fit candidates using vector embeddings.

---

## Architecture Overview

```
Candidate (WhatsApp)          Employer (Browser)         Admin (Browser)
        |                             |                         |
        v                             v                         v
  Meta Cloud API            Employer Dashboard           Admin Panel
  graph.facebook.com         Next.js + Cognito          Next.js + Cognito
        |                             |                         |
        | Webhook                     +──────────┬──────────────+
        v                                        v
 WhatsApp Gateway :8000              Company Service :8003
  State machine                      Job posting · Company approval
  Redis sessions                     Admin endpoints
        |                                        |
        |── POST /users ──► User Service :8001   |── POST /match/job ──►  Matching Service :8004
        |                   Candidate profiles   |                        Pinecone vectors
        |                                        |                        Sentence-BERT
        |── POST /cv ──────► File Service :8002  |
                             S3 upload            |── SQS: job-matched ──► Notification Service :8005
                             SQS: cv-uploaded ────┘                        WhatsApp alerts
                                     |
                                     └──► Matching Service (reverse match)
```

---

## Services

| Service | Port | Responsibility |
|---|---|---|
| WhatsApp Gateway | 8000 | Receives Meta webhooks, runs conversation state machine, routes CV uploads |
| User Service | 8001 | Manages candidate profiles (name, skills, experience, location, salary) |
| File Service | 8002 | Extracts CV text (PDF/DOCX), uploads to S3, publishes SQS event |
| Company Service | 8003 | Company registration, job posting, admin approval, AI matching trigger |
| Matching Service | 8004 | Sentence-BERT embeddings + Pinecone vector search for job-candidate matching |
| Notification Service | 8005 | Polls SQS job-matched queue, sends WhatsApp alerts via Meta Graph API |

### Frontend

| App | Description |
|---|---|
| `frontend/employer-dashboard` | Next.js dashboard for employers — post jobs, view matched candidates |
| `frontend/admin-panel` | Next.js admin panel — approve companies, monitor platform KPIs |

---

## Technology Stack

- **Backend:** FastAPI (Python 3.11)
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Auth:** AWS Cognito (employers + admins)
- **Database:** PostgreSQL 15
- **Cache / Sessions:** Redis 7
- **File Storage:** AWS S3
- **Message Queue:** AWS SQS
- **Vector Database:** Pinecone
- **AI / Embeddings:** Sentence-Transformers (`all-MiniLM-L6-v2`)
- **WhatsApp API:** Meta Graph API v18.0
- **Infrastructure:** Docker, Docker Compose

---

## Candidate Conversation Flow

```
Send "Hi"          → Registration begins
Name               → Enter full name
Skills             → e.g. Python, React, SQL
Experience         → 1=Junior  2=Mid  3=Senior  4=Lead
Location           → City or region
Salary             → e.g. 80000-150000 (LKR)
Upload CV (PDF)    → Profile complete, AI matching activated
```

Once registered, candidates receive WhatsApp alerts when a matching job is posted. They can update their profile at any time by replying with the menu number, or type `STOP` to unsubscribe and `DELETE MY DATA` for full PDPA erasure.

---

## Job Posting Flow

1. Employer posts a job on the Dashboard
2. Company Service saves the job and calls Matching Service
3. Matching Service embeds the job description and queries Pinecone for matching CV vectors
4. Matched candidate phone numbers are returned
5. Company Service publishes a `job-matched` SQS event
6. Notification Service picks it up and sends each matched candidate a WhatsApp alert

---

## Quick Start (Docker Compose)

```bash
# 1. Clone the repository
git clone https://github.com/Sahan-Rudrigo/QuickJobs.git
cd QuickJobs

# 2. Add .env files for each service (see .env.example in each service directory)

# 3. Start infrastructure + all services
docker-compose -f infra/docker-compose.yml up --build
```

Services start automatically in dependency order. All database tables are created on first run.

### Manual startup order (without Docker)

```bash
# 1. Infrastructure
docker run -d -p 5433:5432 -e POSTGRES_DB=quickjobs -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=password123 postgres:15
docker run -d -p 6379:6379 redis:7

# 2-7. Each service
cd services/user-service    && uvicorn main:app --port 8001
cd services/file-service    && uvicorn main:app --port 8002
cd services/company-service && uvicorn main:app --port 8003
cd services/matching-service && uvicorn main:app --port 8004
cd services/notification-service && uvicorn main:app --port 8005
cd services/whatsapp-gateway && uvicorn main:app --host 0.0.0.0 --port 8000

# 8. Expose gateway to Meta
ngrok http 8000
# Set webhook in Meta Developer Console: https://<ngrok-url>/webhook
# Verify token: quickjobs_verify_123
```

---

## Environment Variables

Each service has a `.env.example` file listing required variables. The key ones:

| Variable | Used By | Description |
|---|---|---|
| `WHATSAPP_TOKEN` | Gateway, Notification | Meta API bearer token |
| `WHATSAPP_PHONE_ID` | Gateway, Notification | Meta phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | Gateway | Webhook verification secret |
| `DATABASE_URL` | All backend services | PostgreSQL connection string |
| `REDIS_URL` | Gateway, User, Notification | Redis connection string |
| `PINECONE_API_KEY` | Matching Service | Pinecone vector DB key |
| `PINECONE_INDEX` | Matching Service | Pinecone index name |
| `SQS_CV_UPLOADED_URL` | File, Matching | SQS queue URL for CV events |
| `SQS_JOB_MATCHED_URL` | Company, Notification | SQS queue URL for match events |
| `AWS_ACCESS_KEY_ID` | File, Matching, Notification | AWS credentials |
| `COGNITO_USER_POOL_ID` | User, Company | Cognito pool for JWT validation |

---

## API Documentation

Each FastAPI service auto-generates interactive API docs:

| Service | Docs URL |
|---|---|
| WhatsApp Gateway | http://localhost:8000/docs |
| User Service | http://localhost:8001/docs |
| File Service | http://localhost:8002/docs |
| Company Service | http://localhost:8003/docs |
| Matching Service | http://localhost:8004/docs |
| Notification Service | http://localhost:8005/docs |

---

## Project Structure

```
QuickJobs/
├── services/
│   ├── whatsapp-gateway/     # Candidate WhatsApp interface
│   ├── user-service/         # Candidate profile management
│   ├── file-service/         # CV upload, extraction, S3
│   ├── company-service/      # Employer + admin backend
│   ├── matching-service/     # AI vector matching (Pinecone)
│   └── notification-service/ # WhatsApp job alert delivery
├── frontend/
│   ├── employer-dashboard/   # Next.js employer portal
│   └── admin-panel/          # Next.js admin portal
└── infra/
    └── docker-compose.yml    # Full stack orchestration
```

---

## Team

Built as a Distributed Systems mini-project.
