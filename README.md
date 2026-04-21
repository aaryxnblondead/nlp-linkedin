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
