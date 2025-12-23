package com.optiontoolsapi.api.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

/**
 * CORS CONFIGURATION
 * 
 * CORS (Cross-Origin Resource Sharing) allows your frontend (running on a different
 * origin/port) to make requests to this API.
 * 
 * Development: Allow localhost:3000 (typical React/Vue dev server)
 * Production: Update to your actual frontend domain
 * 
 * @Configuration: Tells Spring this class contains configuration beans
 */
@Configuration
public class CorsConfig {
    
    @Bean
    public CorsFilter corsFilter() {
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        CorsConfiguration config = new CorsConfiguration();
        
        // Allow credentials (cookies, auth headers) - needed for authentication later
        config.setAllowCredentials(true);
        
        // Development: Allow React/Vue dev server (typically port 3000)
        // Add more origins as needed: config.addAllowedOrigin("http://localhost:3001")
        config.addAllowedOrigin("http://localhost:3000");
        config.addAllowedOrigin("http://localhost:5173"); // Vite default port
        config.addAllowedOrigin("http://localhost:4200"); // Angular default port
        
        // Production: Replace with your actual frontend domain
        // config.addAllowedOrigin("https://yourdomain.com");
        // config.addAllowedOrigin("https://www.yourdomain.com");
        
        // For development, you can use pattern matching (less secure):
        // config.addAllowedOriginPattern("http://localhost:*");
        
        // Allow all headers (Authorization, Content-Type, etc.)
        config.addAllowedHeader("*");
        
        // Allow all HTTP methods
        config.addAllowedMethod("GET");
        config.addAllowedMethod("POST");
        config.addAllowedMethod("PUT");
        config.addAllowedMethod("DELETE");
        config.addAllowedMethod("OPTIONS");
        config.addAllowedMethod("PATCH");
        
        // Apply CORS to all endpoints
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}



