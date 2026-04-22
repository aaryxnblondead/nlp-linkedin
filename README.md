# QualifyAI - Intelligent Resume Screening & Candidate Matching System

An advanced NLP-powered platform for resume screening, candidate evaluation, and intelligent matching using state-of-the-art machine learning and large language models.

## 🚀 Features

### Core Capabilities
- **Resume Parsing & NER**: Extract structured information from PDF and DOCX resumes using spaCy and custom NER models
- **Semantic Search**: ChromaDB-powered vector search for finding similar candidates
- **LLM-Enhanced Processing**: Google Gemini integration for:
  - Intelligent name extraction
  - Skills enrichment and expansion
  - Advanced candidate scoring
- **LinkedIn Integration**: Automated profile scraping and data enrichment
- **Interactive Chat**: RAG-based conversational interface for querying candidate information
- **Batch Processing**: Celery-powered asynchronous resume ingestion
- **RESTful API**: FastAPI backend with comprehensive endpoints

### Technical Highlights
- Named Entity Recognition for education, skills, experience, and contact information
- Embedding-based semantic similarity scoring
- Multi-model support (transformers fallback when LLM unavailable)
- PostgreSQL database with SQLAlchemy ORM
- React-based modern frontend with data visualization
- Docker containerization for easy deployment

## 📋 Prerequisites

### Development Environment
- **Python**: 3.11+
- **Node.js**: 16+ (for frontend)
- **PostgreSQL**: 14+ (or Docker)
- **Redis**: 6+ (for Celery, optional)

### Production Environment
- **Docker**: 20.10+
- **Docker Compose**: v2+

### API Keys (Optional but Recommended)
- `GOOGLE_API_KEY`: For enhanced LLM features (name extraction, skills enrichment, scoring)

## 🛠️ Installation & Setup

### Option 1: Local Development (Windows)

#### 1. Clone Repository
```powershell
git clone https://github.com/aaryxnblondead/nlp-linkedin.git
cd nlp-linkedin
```

#### 2. Backend Setup
```powershell
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Set up environment variables (create .env file)
cp .env.example .env  # Edit with your database credentials and API keys

# Run database migrations
alembic upgrade head
```

#### 3. Frontend Setup
```powershell
cd frontend

# Install Node dependencies
npm install

# Create environment file
echo REACT_APP_API_URL=http://localhost:8000/api/v1 > .env.development.local
```

#### 4. Quick Start (Both Services)
```powershell
# From project root
.\start_all.ps1
```

This will:
- Start the FastAPI backend on `http://localhost:8000`
- Start the React frontend on `http://localhost:3000`
- Configure API proxying automatically

#### 5. Individual Service Startup

**Backend Only:**
```powershell
.\start_backend.ps1
```

**Frontend Only:**
```powershell
cd frontend
npm start
```

### Option 2: Docker Deployment (Production)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete Docker deployment instructions.

**Quick Docker Start:**
```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# Check logs
docker compose logs -f backend
```

Services:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: Port 5432
- **Redis**: Port 6379

## 📁 Project Structure

```
nlp-linkedin/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/v1/endpoints/  # API routes (applicants, chat, auth)
│   │   ├── core/              # Configuration and security
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── services/          # Business logic (NER, embeddings, LLM)
│   │   ├── worker/            # Celery tasks
│   │   └── main.py            # FastAPI application entry point
│   ├── scripts/               # Utility scripts (ingestion, testing)
│   ├── migrations/            # Alembic database migrations
│   ├── requirements.txt       # Python dependencies
│   └── alembic.ini            # Database migration config
│
├── frontend/                  # React frontend application
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page-level components
│   │   └── services/          # API client services
│   └── package.json           # Node dependencies
│
├── chroma_db/                 # ChromaDB vector database storage
├── real resumes/              # Resume dataset for ingestion
├── uploaded_resumes/          # User-uploaded resume files
│
├── start_all.ps1              # Development startup script
├── start_backend.ps1          # Backend-only startup script
├── docker-compose.yml         # Docker orchestration
└── DEPLOYMENT.md              # Production deployment guide
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nlp_linkedin

# Redis (optional, for Celery)
REDIS_URL=redis://localhost:6379/0

# LLM Features (optional)
GOOGLE_API_KEY=your_google_api_key_here
USE_LLM_NAME=true
USE_LLM_SKILLS_ENRICH=true
USE_LLM_SCORING=true

# Frontend
FRONTEND_ORIGIN=http://localhost:3000

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### spaCy Model Selection

Default: `en_core_web_sm` (fast, lightweight)

For better accuracy:
```bash
python -m spacy download en_core_web_lg
```

Update in Docker:
```bash
docker compose build --build-arg SPACY_MODEL=en_core_web_lg backend
```

## 📊 Usage

### Resume Ingestion

#### Using VS Code Task (Recommended)
1. Open VS Code Command Palette (`Ctrl+Shift+P`)
2. Run: `Tasks: Run Task`
3. Select: **Ingest real resumes**

#### Using PowerShell Script
```powershell
cd backend
python -m scripts.ingest_real_resumes --root "../real resumes" --skip-existing
```

#### Using API Endpoint
```bash
POST http://localhost:8000/api/v1/applicants/
Content-Type: multipart/form-data

file: resume.pdf
```

### Check RAG System Status
```powershell
# Via task
Tasks: Run Task > Check RAG status

# Via curl/PowerShell
Invoke-WebRequest http://localhost:8000/api/v1/rag/status
```

### Interactive Chat
```bash
POST http://localhost:8000/api/v1/chat
{
  "message": "Find candidates with Python and machine learning experience"
}
```

## 🧪 Testing

### NER Smoke Test
```powershell
Tasks: Run Task > Smoke test NER on IIT
```

### Run Backend Tests
```powershell
cd backend
pytest tests/
```

## 📡 API Endpoints

### Applicants
- `POST /api/v1/applicants/` - Upload resume
- `GET /api/v1/applicants/` - List all applicants (with filters)
- `GET /api/v1/applicants/{id}` - Get applicant details
- `GET /api/v1/applicants/{id}/similar` - Find similar candidates
- `POST /api/v1/applicants/{id}/reprocess` - Reprocess resume
- `GET /api/v1/applicants/{id}/scoring_breakdown` - Get detailed scores

### LinkedIn Integration
- `POST /api/v1/applicants/{id}/linkedin/import` - Import LinkedIn data
- `POST /api/v1/applicants/{id}/linkedin/scrape_test` - Test LinkedIn scraping

### Chat & RAG
- `POST /api/v1/chat` - General chat query
- `POST /api/v1/chat/{applicant_id}` - Applicant-specific chat
- `GET /api/v1/rag/status` - Check RAG system status

### Authentication
- `POST /api/v1/auth/token` - Login
- `GET /api/v1/me/applicant` - Current user profile

## 🔍 Key Technologies

### Backend
- **FastAPI**: High-performance async web framework
- **SQLAlchemy**: SQL ORM and database toolkit
- **spaCy**: Industrial-strength NLP
- **LangChain**: LLM orchestration framework
- **ChromaDB**: Vector database for embeddings
- **Sentence Transformers**: Semantic embeddings
- **Google Gemini**: Advanced LLM capabilities
- **Celery**: Distributed task queue
- **Alembic**: Database migrations

### Frontend
- **React**: UI framework
- **React Router**: Navigation
- **Chart.js**: Data visualization
- **Axios**: HTTP client

### DevOps
- **Docker**: Containerization
- **PostgreSQL**: Relational database
- **Redis**: Caching and message broker
- **Nginx**: Production web server

## 🎯 LLM Features

When `GOOGLE_API_KEY` is set, the system enables:

1. **Smart Name Extraction**: Uses Gemini to extract and normalize candidate names from unstructured text
2. **Skills Enrichment**: Expands detected skills with related technologies and synonyms
3. **Advanced Scoring**: LLM-based candidate evaluation considering context and nuance

Graceful fallback to transformer-based models when API key is unavailable.

## 🚢 Deployment

### Production Checklist
- [ ] Set strong `SECRET_KEY` in environment
- [ ] Configure production database credentials
- [ ] Restrict CORS origins in `backend/app/main.py`
- [ ] Set up HTTPS via reverse proxy
- [ ] Configure backup strategy for PostgreSQL and ChromaDB
- [ ] Set up monitoring and logging
- [ ] Review security settings in Docker Compose

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed production deployment guide.
For AWS hosting on ECS/Fargate, follow [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md).

### AWS Deployment Deep Dive (Extreme Detail)

This section documents the full cloud architecture and delivery story for QualifyAI, including design decisions, implementation phases, production issues, and how they were resolved.

#### 1. Architecture Overview

QualifyAI runs on a serverless container architecture on AWS. "Serverless" here means AWS manages the underlying compute hosts while we manage the containers and application lifecycle.

| Component | AWS Service | Purpose |
| --- | --- | --- |
| Compute | AWS Fargate (Amazon ECS) | Runs Backend (FastAPI/Python), Frontend (Nginx/React), and optional Celery worker without managing EC2 servers |
| Persistent Shared Storage | Amazon EFS | Stores uploaded resumes and ChromaDB files so data survives container restarts and can be shared across tasks |
| Relational Database | Amazon RDS for PostgreSQL | Stores users, applicants, scoring metadata, and other transactional data |
| Secrets and Config | AWS Systems Manager Parameter Store | Stores sensitive runtime configuration such as `DATABASE_URL`, `GOOGLE_API_KEY`, and model tokens |
| External Traffic Entry | Application Load Balancer (ALB) | Receives traffic on port 80/443 and routes requests to ECS services using path rules |

Request flow in production:
1. Browser sends traffic to ALB DNS (for example, `http://qualifyai-alb-...elb.amazonaws.com`).
2. ALB listener evaluates path rules and forwards traffic to target groups.
3. `/*` is routed to the web target group (frontend Nginx container on port 80).
4. `/api/*` is routed to backend target group (FastAPI container on port 8000).
5. Backend reads/writes structured data in RDS and shared files/vectors on EFS.
6. Celery (if deployed) handles async jobs using Redis as broker and can also use EFS-backed assets.

#### 2. Phase-by-Phase Breakdown

##### Phase 1: Infrastructure Foundations

Goal: build a highly available network and storage base before deploying application code.

What was provisioned:
1. Custom VPC for isolation.
2. Subnets across three Availability Zones in `us-east-1` (`a`, `b`, `c`) for high availability.
3. Security groups for ALB, ECS services, RDS, and EFS.
4. EFS file system with mount targets in each AZ used by ECS tasks.
5. RDS PostgreSQL instance in private networking context.

Why this matters:
1. Multi-AZ subnet design keeps the app online even if one AZ is impaired.
2. EFS solves the stateless-container problem by externalizing durable file/vector data.
3. Isolated network boundaries reduce blast radius and tighten security posture.

Implementation details to capture in infrastructure-as-code or console setup:
1. VPC DNS Hostnames and DNS Resolution must be enabled.
2. EFS mount targets must exist in each subnet used by Fargate tasks.
3. Security groups must allow NFS (`2049`) from ECS task security group to EFS security group.
4. RDS security group must allow PostgreSQL (`5432`) from ECS task security group.
5. ALB security group allows inbound `80/443` from internet and outbound to ECS service ports.

##### Phase 2: Containerization and Amazon ECR Pipeline

Goal: package frontend/backend into reproducible images and publish to a managed registry.

What was implemented:
1. Backend image built from `backend/Dockerfile` with runtime entrypoint in `backend/docker-entrypoint.sh`.
2. Frontend image built from `frontend/Dockerfile` serving static React build via Nginx.
3. Images pushed to ECR repositories using AWS CLI from PowerShell/local terminal.

Representative pipeline:
1. Authenticate Docker to ECR.
2. Build backend and frontend images.
3. Tag each image with ECR URI.
4. Push both images to ECR.

PowerShell-style command sequence:

```powershell
$AWS_REGION = "us-east-1"
$AWS_ACCOUNT_ID = "123456789012"
$BACKEND_REPO = "qualifyai-backend"
$FRONTEND_REPO = "qualifyai-frontend"

aws ecr get-login-password --region $AWS_REGION |
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t $BACKEND_REPO ./backend
docker build -t $FRONTEND_REPO ./frontend

$BACKEND_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$BACKEND_REPO:latest"
$FRONTEND_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$FRONTEND_REPO:latest"

docker tag "$BACKEND_REPO:latest" $BACKEND_URI
docker tag "$FRONTEND_REPO:latest" $FRONTEND_URI

docker push $BACKEND_URI
docker push $FRONTEND_URI
```

##### Phase 3: ECS Task Definitions (Container Blueprints)

Goal: define exactly how each container runs in production.

Task definition design:
1. `qualifyai-backend-task` exposes container port `8000`.
2. `qualifyai-web-task` exposes container port `80`.
3. Optional `qualifyai-celery-task` runs worker process without ALB listener.

Critical task definition fields:
1. `executionRoleArn` for pulling ECR images and writing logs.
2. `taskRoleArn` for runtime AWS API access (for example, reading SSM parameters).
3. `logConfiguration` for CloudWatch logs.
4. `secrets` map for injecting secure values from Parameter Store.
5. EFS volume mappings mounted into `/app/uploaded_resumes` and `/app/chroma_db`.

Example secrets injection pattern:

```json
{
  "name": "backend",
  "secrets": [
    {
      "name": "DATABASE_URL",
      "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/qualifyai/prod/DATABASE_URL"
    },
    {
      "name": "GOOGLE_API_KEY",
      "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/qualifyai/prod/GOOGLE_API_KEY"
    }
  ]
}
```

ALB listener and target group strategy:
1. Backend service target group health check path: `/api/v1/health`.
2. Web service target group health check path: `/`.
3. Listener rule priority: `/api/*` must have higher priority than catch-all `/*`.

##### Phase 4: One-Time Database Migration Task

Goal: apply schema migrations before taking production traffic.

What was done:
1. Ran a standalone ECS task using backend image.
2. Set `RUN_MIGRATIONS=true` for that one-time task.
3. Confirmed Alembic created/upgraded RDS tables.
4. Set regular backend services to `RUN_MIGRATIONS=false` for steady-state operation.

Why this is critical:
1. Prevents race conditions where multiple replicas run migrations concurrently.
2. Reduces startup risk for regular app tasks.
3. Ensures database compatibility before the ALB sends live requests.

#### 3. Engineering Challenges and Solutions

This section demonstrates real-world debugging and operational problem-solving.

##### Challenge A: IAM AccessDenied Errors (Identity and Permissions)

Symptoms:
1. ECS tasks failed to initialize logging or retrieve secure parameters.
2. CloudWatch and SSM operations returned AccessDenied errors.

Root cause:
1. Task execution role lacked required permissions for selected AWS actions.

Resolution:
1. Added targeted inline policies to `ecsTaskExecutionRole` and/or task role.
2. Granted minimum required actions for CloudWatch Logs group/stream creation and writes.
3. Granted SSM Parameter Store reads (`GetParameter`, `GetParameters`, optionally `GetParametersByPath`).
4. Added ECR image pull actions where missing.

Validation:
1. New task launch succeeded.
2. Logs appeared in CloudWatch.
3. Secrets resolved at runtime with no AccessDenied entries.

##### Challenge B: "Host Not Found" Between Frontend and Backend

Symptoms:
1. Frontend container returned upstream resolution errors when trying to reach backend.
2. Browser requests to API paths failed with 502/503-style behavior.

Root cause:
1. Backend hostname used by Nginx was not resolvable in ECS networking context.

Resolution:
1. Implemented AWS Service Connect (or equivalent service discovery) to provide stable internal DNS.
2. Used a private namespace (for example, `qualifyai.local`) so services can communicate by service name instead of ephemeral IPs.

Validation:
1. Name resolution works from frontend task to backend service endpoint.
2. API requests complete successfully under load balancer path routing.

##### Challenge C: EFS Mount Initialization Errors

Symptoms:
1. ECS task startup failed with `ResourceInitializationError` when mounting EFS.

Root cause:
1. Missing/incomplete EFS mount targets in active subnets or DNS-related VPC misconfiguration.

Resolution:
1. Enabled and verified VPC DNS hostnames/resolution.
2. Created/verified EFS mount targets in each relevant subnet/AZ.
3. Corrected security group rules allowing NFS traffic from ECS tasks to EFS.

Validation:
1. Tasks transition to healthy/running state.
2. Files written by one task are visible to other tasks sharing EFS.

##### Challenge D: 504 Gateway Timeout from ALB

Symptoms:
1. External requests reached ALB but timed out before container response.

Root cause:
1. ALB-to-task network path was blocked by security group rule gaps.

Resolution:
1. Updated security group inbound rules to allow required internal traffic paths.
2. During active debugging, temporarily allowed broader internal VPC traffic to isolate path issues.
3. After verification, tighten rules to least privilege (recommended long-term posture).

Validation:
1. Target group health checks turn healthy.
2. End-user requests stop timing out.
3. ALB `HTTPCode_Target_5XX_Count` and timeout errors drop.

#### 4. Final Result and Production Outcomes

QualifyAI is now a decoupled, production-ready system with strong operational characteristics.

Scalability:
1. Increase ECS desired task count for backend/web services during traffic spikes.
2. Use target tracking autoscaling on CPU/memory/ALB request metrics.

Security:
1. No secrets hardcoded in container images.
2. Runtime secret injection handled via encrypted SSM parameters and IAM roles.

Persistence and Reliability:
1. Uploaded resumes and vector data persist on EFS across task restarts.
2. Structured transactional data persists in RDS PostgreSQL.

Operational control:
1. Centralized logs in CloudWatch for backend/frontend diagnostics.
2. Health checks enforce automated recovery and safer deployments.

#### 5. Recommended Post-Deployment Validation (Runbook)

1. Confirm ALB routing for both path classes.
2. Confirm `GET /` returns the frontend application.
3. Confirm `GET /api/v1/health` returns JSON with `ok: true`.
4. Confirm target group health is green for both backend and web.
5. Confirm backend can read secrets from SSM at startup.
6. Confirm EFS directories contain shared data after resume upload.
7. Confirm RDS connectivity by creating user/applicant records.

For focused command-level deployment steps, continue to use [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md) as the quick execution runbook.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Quality
- Uses **Ruff** for linting (configured in `pyproject.toml`)
- Uses **MyPy** for type checking
- Line length: 100 characters

## 📝 License

This project is part of an academic/research initiative. Please contact the repository owner for licensing information.

## 🙏 Acknowledgments

- spaCy for robust NLP capabilities
- Google for Gemini API
- The open-source community for amazing tools and libraries

## 📧 Contact

**Repository**: [aaryxnblondead/nlp-linkedin](https://github.com/aaryxnblondead/nlp-linkedin)  
**Branch**: optimization/cleanup-2025-10-12

## 🐛 Troubleshooting

### Backend won't start
- Check PostgreSQL is running: `psql -U your_user -d nlp_linkedin`
- Verify `.env` file exists with correct credentials
- Run migrations: `alembic upgrade head`

### Frontend API errors
- Ensure `REACT_APP_API_URL` is set correctly
- Check backend is running on the specified port
- Verify CORS settings in `backend/app/main.py`

### Resume ingestion fails
- Check file format (PDF/DOCX supported)
- Verify spaCy model is installed: `python -m spacy validate`
- Check logs for detailed error messages

### ChromaDB errors
- Ensure `chroma_db/` directory has write permissions
- Clear database if corrupted: delete `chroma_db/` folder and re-ingest

---

**Built with ❤️ using FastAPI, React, and cutting-edge NLP**
