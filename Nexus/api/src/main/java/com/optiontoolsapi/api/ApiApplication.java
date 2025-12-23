package com.optiontoolsapi.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * MAIN APPLICATION CLASS
 * 
 * @SpringBootApplication is a convenience annotation that combines:
 * - @Configuration: Marks this as a configuration class
 * - @EnableAutoConfiguration: Enables Spring Boot auto-configuration
 * - @ComponentScan: Scans for components (controllers, services, etc.) in this package and sub-packages
 * 
 * This is the entry point of your Spring Boot application.
 * When you run this, Spring Boot will:
 * 1. Start an embedded Tomcat server (default port 8080, yours is 8081)
 * 2. Scan for all @Component, @Service, @Repository, @Controller classes
 * 3. Create instances of them (dependency injection)
 * 4. Configure the database connection
 * 5. Start listening for HTTP requests
 */
@SpringBootApplication
public class ApiApplication {

	public static void main(String[] args) {
		// This starts the entire Spring Boot application
		SpringApplication.run(ApiApplication.class, args);
	}

}
