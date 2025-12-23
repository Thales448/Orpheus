package com.optiontoolsapi.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * ENTITY/MODEL LAYER - Database Table Mapping
 * 
 * This class represents a database table. Each instance = one row in the table.
 * 
 * @Entity: Tells JPA this class is a database entity
 * @Table(name = "options"): Maps to "options" table in database
 * 
 * JPA Annotations:
 * - @Id: Primary key field
 * - @GeneratedValue: Auto-increment ID (database generates it)
 * - @Column: Maps field to database column
 * - @PrePersist: Runs before saving new record
 * - @PreUpdate: Runs before updating existing record
 * 
 * JPA automatically:
 * - Creates the table if it doesn't exist (when ddl-auto=update)
 * - Converts Java objects to database rows
 * - Converts database rows to Java objects
 */
@Entity
@Table(name = "options")
public class Option {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false)
    private String symbol;
    
    @Column(nullable = false)
    private String optionType; // "CALL" or "PUT"
    
    @Column(nullable = false)
    private Double strikePrice;
    
    @Column(nullable = false)
    private Double currentPrice;
    
    @Column(nullable = false)
    private LocalDateTime expirationDate;
    
    private Double premium;
    private Double delta;
    private Double gamma;
    private Double theta;
    private Double vega;
    
    @Column(name = "created_at")
    private LocalDateTime createdAt;
    
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
    
    // Constructors
    public Option() {
    }
    
    public Option(String symbol, String optionType, Double strikePrice, Double currentPrice, LocalDateTime expirationDate) {
        this.symbol = symbol;
        this.optionType = optionType;
        this.strikePrice = strikePrice;
        this.currentPrice = currentPrice;
        this.expirationDate = expirationDate;
    }
    
    // Pre-persist and pre-update hooks
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }
    
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
    
    // Getters and Setters
    public Long getId() {
        return id;
    }
    
    public void setId(Long id) {
        this.id = id;
    }
    
    public String getSymbol() {
        return symbol;
    }
    
    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }
    
    public String getOptionType() {
        return optionType;
    }
    
    public void setOptionType(String optionType) {
        this.optionType = optionType;
    }
    
    public Double getStrikePrice() {
        return strikePrice;
    }
    
    public void setStrikePrice(Double strikePrice) {
        this.strikePrice = strikePrice;
    }
    
    public Double getCurrentPrice() {
        return currentPrice;
    }
    
    public void setCurrentPrice(Double currentPrice) {
        this.currentPrice = currentPrice;
    }
    
    public LocalDateTime getExpirationDate() {
        return expirationDate;
    }
    
    public void setExpirationDate(LocalDateTime expirationDate) {
        this.expirationDate = expirationDate;
    }
    
    public Double getPremium() {
        return premium;
    }
    
    public void setPremium(Double premium) {
        this.premium = premium;
    }
    
    public Double getDelta() {
        return delta;
    }
    
    public void setDelta(Double delta) {
        this.delta = delta;
    }
    
    public Double getGamma() {
        return gamma;
    }
    
    public void setGamma(Double gamma) {
        this.gamma = gamma;
    }
    
    public Double getTheta() {
        return theta;
    }
    
    public void setTheta(Double theta) {
        this.theta = theta;
    }
    
    public Double getVega() {
        return vega;
    }
    
    public void setVega(Double vega) {
        this.vega = vega;
    }
    
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
    
    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
    
    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
    
    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}



