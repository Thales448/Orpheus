package com.optiontoolsapi.api.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

/**
 * SECURITY CONFIGURATION
 * 
 * Spring Security provides authentication and authorization.
 * 
 * Currently DISABLED for development - all endpoints are open.
 * 
 * When you're ready to add authentication:
 * 1. Uncomment the security rules below
 * 2. Create a User entity and UserRepository
 * 3. Implement authentication (JWT tokens, OAuth2, or session-based)
 * 4. Add @PreAuthorize annotations to controllers for role-based access
 * 
 * Common Authentication Approaches:
 * - JWT (JSON Web Tokens): Stateless, good for APIs
 * - OAuth2: Industry standard, used by Google, GitHub, etc.
 * - Session-based: Traditional, uses cookies
 * 
 * @Configuration: Tells Spring this class contains configuration beans
 * @EnableWebSecurity: Enables Spring Security
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    
    /**
     * SecurityFilterChain: Defines which endpoints require authentication
     * 
     * Currently: All endpoints are public (no authentication required)
     * 
     * To enable authentication later, modify this method to:
     * - Require authentication for /api/** endpoints
     * - Allow public access to /api/auth/** (login/register)
     * - Configure CORS properly
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // Disable CSRF for API (APIs are stateless, CSRF doesn't apply)
            .csrf(csrf -> csrf.disable())
            
            // Allow all requests (no authentication required)
            // TODO: When ready, configure authentication:
            // .authorizeHttpRequests(auth -> auth
            //     .requestMatchers("/api/auth/**").permitAll()
            //     .requestMatchers("/api/**").authenticated()
            //     .anyRequest().permitAll()
            // )
            .authorizeHttpRequests(auth -> auth
                .anyRequest().permitAll()
            );
        
        return http.build();
    }
}


