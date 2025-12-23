# Architecture Decision: Frontend vs API Separation

## ✅ **RECOMMENDED: Separate Frontend and API**

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                        │
│  (React/Vue/Angular/Next.js - Separate Application)     │
│                                                          │
│  - Served from: CDN, Nginx, or separate server          │
│  - Port: 3000 (dev) or 80/443 (prod)                    │
│  - Makes HTTP requests to API                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTP Requests (REST API)
                       │ CORS enabled
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    API LAYER (Spring Boot)               │
│  (Your Current Application)                              │
│                                                          │
│  - Port: 8081                                           │
│  - Endpoints: /api/**                                    │
│  - Returns: JSON only                                   │
│  - No static HTML files                                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ JPA/Hibernate
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    DATABASE                              │
│  (PostgreSQL/H2)                                         │
└─────────────────────────────────────────────────────────┘
```

## Implementation Steps

### 1. Remove Frontend from Spring Boot

**Current Setup (Remove):**
- `HomeController.java` - Remove or convert to API endpoint
- `src/main/resources/static/` - Remove static files
- Keep only API endpoints in controllers

**New Setup:**
- Spring Boot serves **ONLY** JSON API responses
- All controllers return `@RestController` (not `@Controller`)
- No HTML rendering

### 2. Frontend Setup (Separate Application)

**Option A: React/Vue/Angular (Recommended)**
```
frontend/
├── src/
│   ├── components/
│   ├── services/
│   │   └── api.js        # HTTP client for API calls
│   └── App.js
├── package.json
└── .env                  # API_URL=http://localhost:8081
```

**Option B: Next.js (Full-stack React)**
```
frontend/
├── pages/
├── components/
├── lib/
│   └── api.js           # API client
└── package.json
```

### 3. API Configuration

**Keep CORS enabled** (already done):
```java
@CrossOrigin(origins = "http://localhost:3000") // Frontend dev URL
```

**Production CORS:**
```java
@CrossOrigin(origins = "https://yourdomain.com")
```

### 4. Communication Pattern

**Frontend → API:**
```javascript
// Frontend code (React example)
const response = await fetch('http://localhost:8081/api/options', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer <token>', // When auth is added
    'Content-Type': 'application/json'
  }
});
const options = await response.json();
```

**API → Frontend:**
```json
// Always returns JSON
[
  {
    "id": 1,
    "symbol": "AAPL",
    "strikePrice": 150.0,
    ...
  }
]
```

## Development Workflow

### Local Development

1. **Start API:**
   ```bash
   cd Nexus/api
   ./mvnw spring-boot:run
   # API runs on http://localhost:8081
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm start
   # Frontend runs on http://localhost:3000
   ```

3. **Frontend calls API:**
   - Frontend at `localhost:3000`
   - API at `localhost:8081`
   - CORS allows the connection

### Production Deployment

**Option 1: Separate Servers (Recommended)**
- Frontend: Deploy to Vercel, Netlify, AWS S3+CloudFront
- API: Deploy to AWS EC2, Heroku, DigitalOcean, Kubernetes

**Option 2: Same Server, Different Ports**
- Frontend: Nginx on port 80 → serves static files
- API: Spring Boot on port 8081 → serves API
- Nginx can proxy `/api/*` to Spring Boot

**Option 3: Reverse Proxy**
```
Nginx (Port 80)
├── / → Frontend static files
└── /api/* → Proxy to Spring Boot (Port 8081)
```

## Benefits for Your Project

### 1. **Scalability**
- Frontend: Can be cached on CDN globally
- API: Can scale horizontally (multiple instances)

### 2. **Team Collaboration**
- Frontend developer: Works in React/Vue, doesn't need Java
- Backend developer: Focuses on API, doesn't need frontend framework

### 3. **Technology Evolution**
- Can upgrade frontend framework without touching API
- Can add mobile app that uses same API

### 4. **Performance**
- Frontend assets cached by browser/CDN
- API optimized for data processing

## Migration Plan

### Phase 1: Clean Up API (Now)
1. Remove `HomeController.java` or convert to API endpoint
2. Remove static files from `src/main/resources/static/`
3. Ensure all controllers are `@RestController` (return JSON)

### Phase 2: Create Frontend (Later)
1. Create separate frontend project
2. Set up API client to call Spring Boot API
3. Configure CORS for frontend URL

### Phase 3: Deploy Separately
1. Deploy API to production
2. Deploy frontend to CDN/hosting
3. Update CORS to allow production frontend URL

## Example: Frontend API Client

```javascript
// frontend/src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

class ApiService {
  async getOptions() {
    const response = await fetch(`${API_BASE_URL}/api/options`);
    return response.json();
  }

  async getOptionById(id) {
    const response = await fetch(`${API_BASE_URL}/api/options/${id}`);
    return response.json();
  }

  async createOption(option) {
    const response = await fetch(`${API_BASE_URL}/api/options`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(option)
    });
    return response.json();
  }
}

export default new ApiService();
```

## When to Use Monolithic (Spring Boot Serves Both)

**Only if:**
- ✅ Very small internal tool (< 10 users)
- ✅ Simple admin dashboard
- ✅ Prototype/MVP that won't scale
- ✅ Single developer working on everything
- ✅ No plans for mobile app or multiple clients

**For your financial/trading application: Separate is better!**

## Summary

✅ **Separate Frontend and API** - Recommended for your use case
- Better scalability
- Team independence
- Technology flexibility
- Modern best practice

❌ **Monolithic (Spring Boot serves both)** - Not recommended
- Tight coupling
- Harder to scale
- Less flexible


