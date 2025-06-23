# DXB Events Backend Setup Guide

## Prerequisites Installation

### 1. Install Docker Desktop (Required)

**For macOS:**
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop/
2. Install the downloaded `.dmg` file
3. Launch Docker Desktop from Applications
4. Wait for Docker to start (whale icon in menu bar should be active)

**Verify Docker Installation:**
```bash
docker --version
docker compose version
```

### 2. Install Python 3.11+ (Optional for local development)

**Using Homebrew (Recommended):**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
```

**Verify Python Installation:**
```bash
python3 --version
pip3 --version
```

## Quick Start Options

### Option 1: Docker Compose (Recommended)

This starts all services (PostgreSQL, MongoDB, Redis, Elasticsearch, and the API):

```bash
# Navigate to Backend directory
cd Backend

# Start all services
docker compose up -d

# Check logs
docker compose logs -f backend

# Stop all services
docker compose down
```

**Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- MongoDB: localhost:27017
- Redis: localhost:6379
- Elasticsearch: localhost:9200

### Option 2: Local Development

For development with hot-reload:

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Start only databases with Docker
docker compose up -d postgres mongo redis elasticsearch

# Set environment variables
export DATABASE_URL="postgresql://postgres:password@localhost:5432/dxb_events"
export MONGODB_URL="mongodb://localhost:27017"
export REDIS_URL="redis://localhost:6379"
export ELASTICSEARCH_URL="http://localhost:9200"

# Run database migrations
alembic upgrade head

# Start the API server with hot-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Testing the Installation

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "environment": "development",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy",
    "search": "healthy"
  }
}
```

### 2. Register a Test User
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 3. Login Test
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

## Troubleshooting

### Docker Issues

**Docker not found:**
- Ensure Docker Desktop is installed and running
- Restart your terminal after installation

**Permission denied:**
```bash
sudo chmod 666 /var/run/docker.sock
```

**Port conflicts:**
```bash
# Check what's using ports
lsof -i :8000
lsof -i :5432

# Kill processes if needed
sudo kill -9 <PID>
```

### Database Issues

**PostgreSQL connection failed:**
- Ensure Docker containers are running: `docker compose ps`
- Check PostgreSQL logs: `docker compose logs postgres`

**MongoDB connection failed:**
- Check MongoDB logs: `docker compose logs mongo`
- Verify MongoDB is accessible: `docker exec -it backend-mongo-1 mongosh`

### Python Issues

**Import errors:**
- Ensure you're in the Backend directory
- Install requirements: `pip3 install -r requirements.txt`
- Check Python path: `echo $PYTHONPATH`

**Alembic errors:**
- Ensure PostgreSQL is running
- Check database URL in `.env` file
- Reset migrations: `alembic downgrade base && alembic upgrade head`

## Development Workflow

### 1. Daily Development
```bash
# Start services
docker compose up -d

# Activate virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Start development server
uvicorn main:app --reload
```

### 2. Database Changes
```bash
# After modifying models
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

### 3. Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=./ --cov-report=html
```

### 4. Code Quality
```bash
# Format code
black .
isort .

# Lint
flake8 .
```

## Production Deployment

### Environment Variables
Create `.env.production`:
```bash
DEBUG=False
SECRET_KEY=<generate-strong-secret>
DATABASE_URL=<production-postgres-url>
MONGODB_URL=<production-mongodb-url>
REDIS_URL=<production-redis-url>
ELASTICSEARCH_URL=<production-elasticsearch-url>
CORS_ORIGINS=["https://yourdomain.com"]
```

### Docker Production Build
```bash
# Build production image
docker build -t dxb-events-api:latest .

# Run production container
docker run -d \
  --name dxb-events-api \
  -p 8000:8000 \
  --env-file .env.production \
  dxb-events-api:latest
```

## Next Steps

After successful setup:

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Test Authentication**: Register and login via the API docs
3. **Review the Code**: Check out the project structure in `README.md`
4. **Start Development**: Begin with Phase 2 features (Search & Discovery)

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs: `docker compose logs`
3. Check GitHub issues
4. Contact the development team

---

**Happy coding! 🚀** 