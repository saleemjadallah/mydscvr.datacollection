# DXB Events Backend API

**Dubai Events Intelligence Platform** - A robust backend infrastructure for family-focused event discovery and recommendation platform serving Dubai's affluent expat community.

## 🏗️ Architecture Overview

This backend implements a microservices architecture with:

- **FastAPI** for high-performance REST APIs
- **PostgreSQL** with PostGIS for user data and geospatial queries
- **MongoDB** for flexible event data storage
- **Redis** for caching and session management
- **Elasticsearch** for advanced search capabilities
- **Docker** for containerization and easy deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Backend
```

### 2. Environment Configuration

Create a `.env` file in the Backend directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/dxb_events
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
ELASTICSEARCH_URL=http://localhost:9200

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Settings
APP_NAME=DXB Events API
APP_VERSION=1.0.0
DEBUG=True
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

### 3. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### 4. Alternative: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start databases (PostgreSQL, MongoDB, Redis, Elasticsearch)
docker-compose up -d postgres mongo redis elasticsearch

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔐 Authentication

The API uses JWT tokens with the following endpoints:

### Register New User
```bash
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Login
```bash
POST /api/auth/login
{
  "email": "user@example.com", 
  "password": "securepassword"
}
```

### Get Current User
```bash
GET /api/auth/me
Authorization: Bearer <access_token>
```

## 🗄️ Database Schema

### PostgreSQL (Primary Database)
- **Users**: User accounts, authentication
- **Profiles**: User profiles and preferences  
- **Family_Members**: Family composition for recommendations
- **Venues**: Event venue information
- **User_Events**: Saved/attended events relationship
- **Refresh_Tokens**: JWT refresh token management

### MongoDB (Event Data)
- **Events**: Event information with flexible schema
- **Event_Analytics**: Event interaction analytics

### Redis (Caching)
- Session storage
- Frequently accessed event data
- Search result caching

### Elasticsearch (Search)
- Full-text event search
- Geospatial search
- Faceted filtering

## 🔧 Development

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=./ --cov-report=html
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint code
flake8 .
```

## 📊 Monitoring & Logging

### Health Checks

- **API Health**: `GET /health`
- **Auth Service**: `GET /api/auth/health`
- **API Status**: `GET /api/status`

### Logging

Structured JSON logging with:
- Request/response logging
- Error tracking
- Performance monitoring
- Security event logging

## 🔒 Security Features

- **JWT Authentication** with access/refresh tokens
- **Password Hashing** using bcrypt
- **Rate Limiting** on authentication endpoints
- **CORS Configuration** for cross-origin requests
- **Input Validation** using Pydantic
- **SQL Injection Prevention** via SQLAlchemy ORM

## 🌍 Deployment

### Docker Production Deployment

```bash
# Build production image
docker build -t dxb-events-api .

# Run with production settings
docker run -d \
  --name dxb-events-api \
  -p 8000:8000 \
  -e DEBUG=False \
  -e SECRET_KEY=your-production-secret \
  dxb-events-api
```

### Environment Variables

Key production environment variables:

```bash
DEBUG=False
SECRET_KEY=<strong-random-secret>
DATABASE_URL=<production-postgres-url>
MONGODB_URL=<production-mongodb-url>
REDIS_URL=<production-redis-url>
ELASTICSEARCH_URL=<production-elasticsearch-url>
CORS_ORIGINS=["https://yourdomain.com"]
```

## 📈 Performance

### Expected Performance Metrics
- API responses: < 200ms for simple queries
- Search results: < 500ms
- Event details: < 100ms
- 1000+ concurrent users supported

### Optimization Features
- Redis caching for frequent queries
- Database connection pooling
- Async/await throughout the application
- Efficient database indexes
- Response compression

## 🏗️ Project Structure

```
Backend/
├── alembic/              # Database migrations
├── models/               # Database models
│   ├── postgres_models.py
│   └── mongodb_models.py
├── routers/              # API route handlers
│   └── auth.py
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── database.py          # Database connections
├── auth.py              # Authentication utilities
├── schemas.py           # Pydantic schemas
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Development environment
├── Dockerfile          # Container configuration
└── README.md           # This file
```

## 🔄 Development Phases

### ✅ Phase 1: Core Backend (Current)
- [x] User authentication system
- [x] Database schema implementation
- [x] Core API endpoints
- [x] Docker environment setup

### 🚧 Phase 2: Search & Discovery (Next)
- [ ] Elasticsearch integration
- [ ] Advanced search functionality
- [ ] Basic recommendation logic
- [ ] Event filtering and sorting

### 📋 Phase 3: Family Features (Planned)
- [ ] Family profile management
- [ ] Age-based event filtering
- [ ] Saved events functionality
- [ ] Basic notification system

### 🔌 Phase 4: Data Integration (Planned)
- [ ] Webhook endpoints for external data
- [ ] Data processing and validation
- [ ] Event deduplication
- [ ] Image handling and optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support, email support@dxb-events.com or create an issue in the repository.

---

**Built with ❤️ for Dubai's families** 