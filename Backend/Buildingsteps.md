# DXB Events Backend Infrastructure - Development Prompt

## Project Overview
Build a robust backend infrastructure for the Dubai Events Intelligence Platform (DXB Events) - a family-focused event discovery and recommendation platform serving Dubai's affluent expat community. This backend will initially support a web application with future mobile expansion planned.

## Core Business Context
- **Target Market**: Affluent families in Dubai/Abu Dhabi with disposable income (AED 30K-50K/month)
- **Pain Points**: Busy parents need curated, family-appropriate event discovery that respects their time and budget
- **Value Proposition**: AI-powered event aggregation with family-centric filtering and personalized recommendations

## Technical Architecture Requirements

### 1. Microservices Foundation
Build using a microservices architecture with the following core services:

#### **User Service**
- User registration/authentication (email, social login prep)
- Family profile management (parents + children with ages)
- User preferences storage (event types, price ranges, locations)
- Subscription management (free/premium tiers)

#### **Event Service** 
- Event CRUD operations with comprehensive metadata
- Venue information management
- Pricing and booking details
- Event categorization and tagging
- Media/image management

#### **Search Service**
- Full-text search across events
- Geospatial search (distance-based filtering)
- Faceted search (price, category, age group, date)
- Search suggestions and autocomplete

#### **Notification Service**
- Email notifications for saved events
- Event reminders
- New event alerts based on preferences
- System notifications

### 2. Database Schema Design

#### **Core Tables Structure:**

**Users Table:**
```sql
- id (UUID, primary key)
- email (unique, not null)
- password_hash 
- created_at, updated_at
- subscription_tier (free/premium)
- is_verified
```

**Profiles Table:**
```sql
- id (UUID, primary key)
- user_id (foreign key)
- first_name, last_name
- location_preference (Dubai area)
- budget_range (low/medium/high)
- preferences (JSON: event types, interests)
```

**Family_Members Table:**
```sql
- id (UUID, primary key)
- profile_id (foreign key)
- name
- age
- relationship (parent/child/other)
- interests (JSON array)
```

**Events Table:**
```sql
- id (UUID, primary key)
- title, description
- start_date, end_date
- venue_id (foreign key)
- price_min, price_max
- currency (AED default)
- age_min, age_max
- category_tags (JSON array)
- source_url
- is_family_friendly (boolean)
- created_at, updated_at
```

**Venues Table:**
```sql
- id (UUID, primary key)
- name, address
- latitude, longitude
- amenities (JSON: parking, metro_access, stroller_friendly)
- contact_info
- area (Dubai Marina, JBR, etc.)
```

**User_Events Table:**
```sql
- user_id, event_id (composite key)
- status (saved/interested/attended)
- created_at
```

### 3. API Design

#### **Authentication Endpoints:**
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
GET  /api/auth/me
```

#### **User Management:**
```
GET    /api/users/profile
PUT    /api/users/profile
POST   /api/users/family-members
PUT    /api/users/family-members/:id
DELETE /api/users/family-members/:id
GET    /api/users/preferences
PUT    /api/users/preferences
```

#### **Events API:**
```
GET    /api/events?category=&location=&date=&price_max=&age_group=
GET    /api/events/:id
POST   /api/events/:id/save
DELETE /api/events/:id/save
GET    /api/events/saved
GET    /api/events/trending
```

#### **Search API:**
```
GET    /api/search?q=&filters[category]=&filters[location]=
GET    /api/search/suggestions?q=
GET    /api/search/filters (return available filter options)
```

### 4. Technology Stack

#### **Backend Framework:**
- **Primary:** Python with FastAPI (if team prefers Python)

#### **Database:**
- **Primary:** : Mongodb
- **Cache:** Redis for sessions and frequent queries
- **secondary**: PostgreSQL (with PostGIS for geospatial)

#### **Authentication:**
- JWT with refresh tokens
- Passport.js for social login preparation
- bcrypt for password hashing

#### **Search Engine:**
- Elasticsearch for advanced search capabilities
- Real-time indexing of events

#### **File Storage:**
- AWS S3 for event images and media
- CloudFront CDN for fast delivery

#### **API Documentation:**
- OpenAPI 3.0 specification
- Swagger UI for testing

### 5. Data Collection Integration Points

#### **Webhook Endpoints for External Data:**
```
POST /api/webhooks/events/timeout-dubai
POST /api/webhooks/events/platinumlist
POST /api/webhooks/events/generic
```

#### **Data Validation & Processing:**
- Event deduplication logic
- Price normalization (ensure AED currency)
- Date/time standardization
- Image optimization and storage

### 6. Business Logic Requirements

#### **Family Suitability Scoring:**
Start with rule-based logic:
- Age appropriateness based on event metadata
- Price range matching family budget
- Location preference matching
- Time/duration suitability for families

#### **Basic Recommendation Engine:**
Initial algorithm without ML:
- Events similar to previously saved events
- Popular events in user's area/price range
- Events matching family member ages
- Trending events among similar families

#### **Premium Features Logic:**
- Free tier: 10 saved events, basic search
- Premium tier: Unlimited saves, advanced filters, early access to popular events

### 7. Infrastructure Setup

#### **Development Environment:**
- Docker containers for all services
- Docker Compose for local development
- Environment-based configuration

#### **Production Considerations:**
- Horizontal scaling preparation
- Database connection pooling
- Rate limiting middleware
- CORS configuration for web client
- Health check endpoints for monitoring

### 8. Initial API Response Formats

#### **Event List Response:**
```json
{
  "events": [
    {
      "id": "uuid",
      "title": "Family Fun Day at JBR Beach",
      "description": "Beach activities for all ages...",
      "start_date": "2025-06-15T10:00:00Z",
      "venue": {
        "name": "JBR Beach",
        "area": "Dubai Marina",
        "distance_km": 5.2
      },
      "price": {
        "min": 0,
        "max": 100,
        "currency": "AED"
      },
      "family_score": 85,
      "age_range": "0-99",
      "tags": ["outdoor", "beach", "family"],
      "is_saved": false
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 156
  },
  "filters": {
    "categories": ["outdoor", "indoor", "educational"],
    "areas": ["Dubai Marina", "JBR", "DIFC"]
  }
}
```

### 9. Performance Requirements

#### **Response Times:**
- API responses: < 200ms for simple queries
- Search results: < 500ms
- Event details: < 100ms

#### **Caching Strategy:**
- Redis for frequent event queries
- Cache popular search results for 15 minutes
- Cache user preferences and family data

#### **Database Optimization:**
- Indexes on frequently queried fields (location, date, category)
- Query optimization for geospatial searches
- Connection pooling for concurrent users

### 10. Security Implementation

#### **Data Protection:**
- Encrypt sensitive user data at rest
- HTTPS only for all endpoints
- Input validation and sanitization
- SQL injection prevention

#### **Access Control:**
- JWT token expiration (15 minutes access, 7 days refresh)
- Role-based permissions (user/admin)
- Rate limiting per user/IP

### 11. Monitoring & Logging

#### **Essential Metrics:**
- API response times and error rates
- Database query performance
- User registration and engagement metrics
- Search query analytics

#### **Logging Requirements:**
- Structured logging (JSON format)
- User action logging for analytics
- Error tracking and alerting
- Performance monitoring

### 12. Development Phases

#### **Phase 1: Core Backend (Weeks 1-2)**
- User authentication system
- Basic event CRUD operations
- Database schema implementation
- Core API endpoints

#### **Phase 2: Search & Discovery (Weeks 3-4)**
- Elasticsearch integration
- Advanced search functionality
- Basic recommendation logic
- Event filtering and sorting

#### **Phase 3: Family Features (Weeks 5-6)**
- Family profile management
- Age-based event filtering
- Saved events functionality
- Basic notification system

#### **Phase 4: Data Integration (Weeks 7-8)**
- Webhook endpoints for external data
- Data processing and validation
- Event deduplication
- Image handling and optimization

### 13. Testing Requirements

#### **Unit Testing:**
- Test coverage > 80%
- API endpoint testing
- Database operations testing
- Business logic validation

#### **Integration Testing:**
- End-to-end API workflows
- Database integration tests
- External service integration tests

### 14. Documentation Deliverables

- API documentation with Swagger
- Database schema documentation
- Setup and deployment guides
- Architecture decision records

### 15. Future Considerations

#### **Mobile API Preparation:**
- Versioned APIs for mobile compatibility
- Optimized payload sizes
- Offline data synchronization endpoints

#### **Scalability Preparation:**
- Stateless service design
- Database sharding strategy planning
- Microservice communication patterns

## Success Criteria

The backend should successfully:
1. Handle 1000+ concurrent users
2. Support family-centric event discovery
3. Provide sub-500ms search responses
4. Maintain 99.9% uptime
5. Support easy integration of external event data
6. Enable seamless future mobile app development

## Budget Constraints

Keep monthly operational costs under $500 USD for initial deployment, scaling with user growth.

## Next Steps

After backend completion, the system should be ready for:
1. Frontend web application development
2. External data source integration
3. Basic AI/ML feature enhancement
4. Mobile application development

This backend infrastructure will serve as the foundation for the DXB Events platform, focusing on delivering value to Dubai's family market through intelligent event discovery and personalized recommendations.