package com.optiontoolsapi.api.repository;

import com.optiontoolsapi.api.model.Option;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * REPOSITORY LAYER - Data Access
 * 
 * This interface handles all database operations.
 * Spring Data JPA automatically implements this interface!
 * 
 * @Repository: Marks this as a data access component
 * 
 * JpaRepository<Option, Long> provides:
 * - save(entity) - Create or update
 * - findById(id) - Find by ID
 * - findAll() - Get all records
 * - deleteById(id) - Delete by ID
 * - count() - Count records
 * - And many more...
 * 
 * Custom Query Methods:
 * Spring automatically implements methods based on naming convention:
 * - findBySymbol(String) → SELECT * FROM options WHERE symbol = ?
 * - findByOptionType(String) → SELECT * FROM options WHERE option_type = ?
 * 
 * Naming Pattern: findBy + FieldName + (Optional conditions)
 * Examples:
 * - findBySymbolAndOptionType → WHERE symbol = ? AND option_type = ?
 * - findByStrikePriceGreaterThan → WHERE strike_price > ?
 */
@Repository
public interface OptionRepository extends JpaRepository<Option, Long> {
    
    // Custom query methods
    List<Option> findBySymbol(String symbol);
    
    List<Option> findByOptionType(String optionType);
    
    List<Option> findBySymbolAndOptionType(String symbol, String optionType);
    
    Optional<Option> findById(Long id);
}
