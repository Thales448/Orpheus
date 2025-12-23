# Spring Boot REST API Learning Guide

## 📚 Table of Contents
1. [Spring Boot Architecture Overview](#spring-boot-architecture-overview)
2. [Key Concepts Explained](#key-concepts-explained)
3. [Request Flow Diagram](#request-flow-diagram)
4. [Essential Annotations](#essential-annotations)
5. [Learning Resources](#learning-resources)
6. [Next Steps for Authentication](#next-steps-for-authentication)

---

## Spring Boot Architecture Overview

### The Layered Architecture

Your API follows a **3-layer architecture** (plus configuration):

```
┌─────────────────────────────────────────┐
│         CONTROLLER LAYER                │  ← HTTP Requests/Responses
│  (OptionController.java)                │     Handles routing
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         SERVICE LAYER                   │  ← Business Logic
│  (OptionService.java)                   │     Validation, calculations
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         REPOSITORY LAYER                │  ← Database Access
│  (OptionRepository.java)                │     SQL queries (auto-generated)
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         DATABASE                         │  ← H2 (dev) or PostgreSQL (prod)
│  (options table)                         │
└─────────────────────────────────────────┘
```

### Why This Structure?

1. **Separation of Concerns**: Each layer has one responsibility
2. **Testability**: Easy to test each layer independently
3. **Maintainability**: Changes in one layer don't break others
4. **Reusability**: Services can be used by multiple controllers

---

## Key Concepts Explained

### 1. Dependency Injection (DI)

**What it is**: Spring automatically creates and provides objects (dependencies) to your classes.

**Example**:
```java
@Autowired
public OptionController(OptionService optionService) {
    this.optionService = optionService;  // Spring provides this!
}
```

**Benefits**:
- No need to write `new OptionService()` everywhere
- Spring manages object lifecycle
- Easy to swap implementations (e.g., for testing)

### 2. Spring Data JPA

**What it is**: Automatically generates database queries from method names.

**Example**:
```java
// You write this:
List<Option> findBySymbol(String symbol);

// Spring generates this SQL:
// SELECT * FROM options WHERE symbol = ?
```

**Magic Methods** (Spring generates these automatically):
- `findAll()` → Get all records
- `findById(id)` → Get by ID
- `save(entity)` → Create or update
- `deleteById(id)` → Delete
- `findBySymbol(String)` → Custom query by symbol
- `findBySymbolAndOptionType(String, String)` → Multiple conditions

### 3. REST API Principles

**REST = Representational State Transfer**

Your API follows REST conventions:

| HTTP Method | Endpoint | Action | Status Code |
|------------|----------|--------|-------------|
| GET | `/api/options` | Get all | 200 OK |
| GET | `/api/options/{id}` | Get one | 200 OK or 404 |
| POST | `/api/options` | Create | 201 Created |
| PUT | `/api/options/{id}` | Update | 200 OK or 404 |
| DELETE | `/api/options/{id}` | Delete | 204 No Content or 404 |

### 4. Annotations Explained

See [Essential Annotations](#essential-annotations) section below.

---

## Request Flow Diagram

### Example: Creating a New Option

```
1. Frontend sends: POST /api/options
   Body: { "symbol": "AAPL", "strikePrice": 150.0, ... }

2. Spring Boot receives request
   ↓
3. OptionController.createOption() is called
   ↓
4. Controller calls: optionService.createOption(option)
   ↓
5. Service calls: optionRepository.save(option)
   ↓
6. JPA converts Option object to SQL:
   INSERT INTO options (symbol, strike_price, ...) VALUES (?, ?, ...)
   ↓
7. Database executes SQL
   ↓
8. Database returns new record with generated ID
   ↓
9. JPA converts database row back to Option object
   ↓
10. Service returns Option to Controller
   ↓
11. Controller wraps in ResponseEntity with 201 Created status
   ↓
12. Spring converts to JSON and sends HTTP response
   ↓
13. Frontend receives: 201 Created
   Body: { "id": 1, "symbol": "AAPL", ... }
```

---

## Essential Annotations

### Application Level
- **`@SpringBootApplication`**: Main application class
- **`@Configuration`**: Configuration class (creates beans)
- **`@ComponentScan`**: Scans for components to auto-discover

### Controller Layer
- **`@RestController`**: Combines `@Controller` + `@ResponseBody` (returns JSON)
- **`@RequestMapping("/path")`**: Base URL for all methods in controller
- **`@GetMapping("/path")`**: Maps HTTP GET requests
- **`@PostMapping("/path")`**: Maps HTTP POST requests
- **`@PutMapping("/path")`**: Maps HTTP PUT requests
- **`@DeleteMapping("/path")`**: Maps HTTP DELETE requests
- **`@PathVariable`**: Extracts variable from URL path (`/api/options/{id}`)
- **`@RequestBody`**: Converts JSON request body to Java object
- **`@CrossOrigin`**: Allows frontend (different origin) to call API

### Service Layer
- **`@Service`**: Marks class as a service component
- **`@Autowired`**: Injects dependencies (Spring provides them)

### Repository Layer
- **`@Repository`**: Marks interface as data access component
- Extends `JpaRepository<Entity, ID>`: Provides CRUD methods

### Entity/Model Layer
- **`@Entity`**: Marks class as database entity
- **`@Table(name = "table_name")`**: Maps to database table
- **`@Id`**: Primary key field
- **`@GeneratedValue`**: Auto-increment ID
- **`@Column`**: Maps field to database column
- **`@PrePersist`**: Runs before saving new record
- **`@PreUpdate`**: Runs before updating existing record

---

## Learning Resources

### Official Documentation (Best Starting Point)
1. **Spring Boot Official Docs**: https://spring.io/projects/spring-boot
   - Start with: "Getting Started" guide
   - Then: "Building RESTful Web Services"

2. **Spring Data JPA Reference**: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/
   - Learn: Query methods, custom queries, relationships

3. **Spring Security**: https://spring.io/projects/spring-security
   - When ready for authentication

### Video Tutorials (Beginner Friendly)
1. **Spring Boot Full Course** (freeCodeCamp)
   - YouTube: Search "Spring Boot Full Course freeCodeCamp"
   - Comprehensive, beginner-friendly

2. **Spring Boot Tutorial** (Java Brains)
   - YouTube: Search "Java Brains Spring Boot"
   - Clear explanations, good examples

3. **Spring Boot REST API Tutorial** (Amigoscode)
   - YouTube: Search "Amigoscode Spring Boot REST API"
   - Practical, project-based

### Interactive Learning
1. **Spring Academy**: https://spring.academy/
   - Free courses, hands-on labs

2. **Baeldung Spring Tutorials**: https://www.baeldung.com/spring-tutorial
   - Excellent written tutorials with examples

### Books
1. **"Spring Boot in Action"** by Craig Walls
   - Comprehensive, beginner-friendly

2. **"Pro Spring Boot 2"** by Felipe Gutierrez
   - Advanced topics, production-ready patterns

### Practice Projects
1. Build a **Todo API** (CRUD operations)
2. Build a **Blog API** (posts, comments, users)
3. Build a **E-commerce API** (products, orders, customers)

---

## Next Steps for Authentication

When you're ready to add user authentication:

### 1. Add User Entity
```java
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue
    private Long id;
    private String username;
    private String email;
    private String password; // Hashed!
    // ... roles, timestamps, etc.
}
```

### 2. Create Authentication Endpoints
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - Authenticate user
- `POST /api/auth/logout` - Logout user

### 3. Choose Authentication Method

**Option A: JWT (JSON Web Tokens)** - Recommended for APIs
- Stateless (no server-side sessions)
- Token sent in Authorization header
- Good for mobile apps and SPAs

**Option B: Session-based**
- Traditional approach
- Uses cookies
- Simpler but requires session storage

### 4. Secure Endpoints
```java
@PreAuthorize("hasRole('USER')")
@GetMapping("/api/options")
public ResponseEntity<List<Option>> getAllOptions() {
    // Only authenticated users can access
}
```

### 5. Resources for Authentication
- **Spring Security + JWT Tutorial**: Search "Spring Boot JWT Authentication"
- **Spring Security Official Docs**: https://docs.spring.io/spring-security/reference/

---

## Common Patterns & Best Practices

### 1. Exception Handling
Create a `@ControllerAdvice` class to handle errors globally:
```java
@ControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<?> handleNotFound(ResourceNotFoundException e) {
        return ResponseEntity.notFound().build();
    }
}
```

### 2. DTOs (Data Transfer Objects)
Create separate classes for API requests/responses:
```java
// Instead of using Option entity directly
public class OptionRequest {
    private String symbol;
    private Double strikePrice;
    // Only fields needed for creation
}
```

### 3. Validation
Add validation annotations:
```java
@NotNull
@Size(min = 1, max = 10)
private String symbol;
```

### 4. Pagination
For large datasets:
```java
Pageable pageable = PageRequest.of(page, size);
Page<Option> options = repository.findAll(pageable);
```

---

## Testing Your API

### Using cURL
```bash
# GET all options
curl http://localhost:8081/api/options

# POST new option
curl -X POST http://localhost:8081/api/options \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","optionType":"CALL","strikePrice":150.0,"currentPrice":155.0}'

# GET by ID
curl http://localhost:8081/api/options/1

# DELETE
curl -X DELETE http://localhost:8081/api/options/1
```

### Using Postman
1. Import collection or create requests manually
2. Test all CRUD operations
3. Check response status codes

### Using Browser
- GET requests work directly in browser
- Visit: `http://localhost:8081/api/options`

---

## Debugging Tips

1. **Check Logs**: Spring Boot logs all SQL queries (when `show-sql=true`)
2. **H2 Console**: Visit `http://localhost:8081/h2-console` to inspect database
3. **Breakpoints**: Use IDE debugger to step through code
4. **Postman Console**: See request/response details

---

## Quick Reference: File Structure

```
src/main/java/com/optiontoolsapi/api/
├── ApiApplication.java          # Main entry point
├── config/
│   ├── CorsConfig.java          # CORS configuration
│   └── SecurityConfig.java      # Security (auth) configuration
├── controller/
│   └── OptionController.java    # REST endpoints
├── service/
│   └── OptionService.java       # Business logic
├── repository/
│   └── OptionRepository.java    # Database access
└── model/
    └── Option.java              # Database entity

src/main/resources/
└── application.properties       # Configuration (database, port, etc.)
```

---

## Summary

You now have a complete REST API with:
- ✅ Database connectivity (H2 for dev, PostgreSQL ready for prod)
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Proper layered architecture
- ✅ CORS enabled for frontend
- ✅ Security framework ready (currently open, easy to add auth later)

**Next**: Start building your frontend! The API is ready to receive requests.

---

*Happy coding! 🚀*


