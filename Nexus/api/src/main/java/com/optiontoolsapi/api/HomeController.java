package com.optiontoolsapi.api;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * API Health/Info Endpoint
 * 
 * Since we're separating frontend from API, this controller serves
 * API information instead of HTML pages.
 * 
 * The frontend will be a separate application that calls /api/** endpoints.
 */
@RestController
public class HomeController {

    /**
     * GET / - API information endpoint
     * 
     * Returns JSON with API information instead of serving HTML.
     * Useful for API discovery and health checks.
     */
    @GetMapping("/")
    public ResponseEntity<Map<String, Object>> getApiInfo() {
        Map<String, Object> info = new HashMap<>();
        info.put("name", "Options Tool API");
        info.put("version", "1.0.0");
        info.put("status", "running");
        info.put("endpoints", Map.of(
            "options", "/api/options",
            "health", "/api/health"
        ));
        info.put("documentation", "See /api/options for available endpoints");
        return ResponseEntity.ok(info);
    }

    /**
     * GET /api/health - Health check endpoint
     * 
     * Useful for monitoring and load balancers to check if API is running.
     */
    @GetMapping("/api/health")
    public ResponseEntity<Map<String, String>> health() {
        Map<String, String> health = new HashMap<>();
        health.put("status", "UP");
        return ResponseEntity.ok(health);
    }
}

