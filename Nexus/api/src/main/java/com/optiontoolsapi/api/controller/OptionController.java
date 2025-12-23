package com.optiontoolsapi.api.controller;

import com.optiontoolsapi.api.model.Option;
import com.optiontoolsapi.api.service.OptionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

/**
 * REST CONTROLLER - The API Layer
 * 
 * This is where HTTP requests come in and responses go out.
 * 
 * Key Spring Boot Annotations:
 * - @RestController: Combines @Controller + @ResponseBody
 *   * Tells Spring this class handles HTTP requests
 *   * Automatically converts return values to JSON
 * 
 * - @RequestMapping("/api/options"): Base URL path for all methods in this controller
 *   * All endpoints will start with /api/options
 * 
 * - @CrossOrigin: Allows frontend (different origin) to call this API
 *   * CORS = Cross-Origin Resource Sharing
 *   * In production, specify exact frontend URL instead of "*"
 * 
 * - @Autowired: Dependency Injection
 *   * Spring automatically provides the OptionService instance
 *   * No need to manually create: new OptionService()
 * 
 * Request Flow:
 * 1. HTTP Request → Controller (this class)
 * 2. Controller → Service (business logic)
 * 3. Service → Repository (database access)
 * 4. Repository → Database
 * 5. Response flows back up the chain
 */
@RestController
@RequestMapping("/api/options")
@CrossOrigin(origins = "*") // Allow all origins - adjust for production
public class OptionController {
    
    /**
     * DEPENDENCY INJECTION
     * Spring automatically provides this service instance.
     * We use constructor injection (best practice) instead of field injection.
     */
    private final OptionService optionService;
    
    @Autowired
    public OptionController(OptionService optionService) {
        this.optionService = optionService;
    }
    
    /**
     * HTTP GET /api/options
     * 
     * @GetMapping: Maps HTTP GET requests to this method
     * ResponseEntity: Wraps the response with HTTP status code
     * 
     * Returns: List of all options (200 OK)
     */
    @GetMapping
    public ResponseEntity<List<Option>> getAllOptions() {
        List<Option> options = optionService.getAllOptions();
        return ResponseEntity.ok(options); // HTTP 200
    }
    
    /**
     * HTTP GET /api/options/{id}
     * 
     * @PathVariable: Extracts {id} from URL path
     * Optional<Option>: Handles case where option doesn't exist
     * 
     * Returns: Option if found (200 OK), or 404 Not Found
     */
    @GetMapping("/{id}")
    public ResponseEntity<Option> getOptionById(@PathVariable Long id) {
        Optional<Option> option = optionService.getOptionById(id);
        return option.map(ResponseEntity::ok)  // If found, return 200
                    .orElse(ResponseEntity.notFound().build()); // If not, return 404
    }
    
    /**
     * HTTP GET /api/options/symbol/{symbol}
     * 
     * Example: GET /api/options/symbol/AAPL
     * Returns all options for Apple stock
     */
    @GetMapping("/symbol/{symbol}")
    public ResponseEntity<List<Option>> getOptionsBySymbol(@PathVariable String symbol) {
        List<Option> options = optionService.getOptionsBySymbol(symbol);
        return ResponseEntity.ok(options);
    }
    
    /**
     * HTTP GET /api/options/type/{type}
     * 
     * Example: GET /api/options/type/CALL
     * Returns all CALL options
     */
    @GetMapping("/type/{type}")
    public ResponseEntity<List<Option>> getOptionsByType(@PathVariable String type) {
        List<Option> options = optionService.getOptionsByType(type);
        return ResponseEntity.ok(options);
    }
    
    /**
     * HTTP POST /api/options
     * 
     * @PostMapping: Maps HTTP POST requests
     * @RequestBody: Converts JSON request body to Option object
     * 
     * Returns: Created option with 201 Created status
     */
    @PostMapping
    public ResponseEntity<Option> createOption(@RequestBody Option option) {
        Option createdOption = optionService.createOption(option);
        return ResponseEntity.status(HttpStatus.CREATED).body(createdOption); // HTTP 201
    }
    
    /**
     * HTTP PUT /api/options/{id}
     * 
     * Updates an existing option by ID
     * 
     * Returns: Updated option (200 OK) or 404 Not Found
     */
    @PutMapping("/{id}")
    public ResponseEntity<Option> updateOption(@PathVariable Long id, @RequestBody Option option) {
        Option updatedOption = optionService.updateOption(id, option);
        if (updatedOption != null) {
            return ResponseEntity.ok(updatedOption);
        }
        return ResponseEntity.notFound().build(); // HTTP 404
    }
    
    /**
     * HTTP DELETE /api/options/{id}
     * 
     * Deletes an option by ID
     * 
     * Returns: 204 No Content if deleted, 404 if not found
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteOption(@PathVariable Long id) {
        boolean deleted = optionService.deleteOption(id);
        if (deleted) {
            return ResponseEntity.noContent().build(); // HTTP 204
        }
        return ResponseEntity.notFound().build(); // HTTP 404
    }
}



