package com.optiontoolsapi.api.service;

import com.optiontoolsapi.api.model.Option;
import com.optiontoolsapi.api.repository.OptionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

/**
 * SERVICE LAYER - Business Logic
 * 
 * This layer contains your business rules and logic.
 * Controllers should be thin - they just receive requests and delegate to services.
 * 
 * @Service: Tells Spring this is a service component
 * - Spring manages the lifecycle (creates, destroys instances)
 * - Can be injected into controllers via @Autowired
 * 
 * Why separate Service from Controller?
 * - Reusability: Business logic can be used by multiple controllers
 * - Testability: Easier to unit test business logic
 * - Separation of Concerns: Controllers handle HTTP, Services handle business rules
 */
@Service
public class OptionService {
    
    private final OptionRepository optionRepository;
    
    @Autowired
    public OptionService(OptionRepository optionRepository) {
        this.optionRepository = optionRepository;
    }
    
    // Get all options
    public List<Option> getAllOptions() {
        return optionRepository.findAll();
    }
    
    // Get option by ID
    public Optional<Option> getOptionById(Long id) {
        return optionRepository.findById(id);
    }
    
    // Get options by symbol
    public List<Option> getOptionsBySymbol(String symbol) {
        return optionRepository.findBySymbol(symbol);
    }
    
    // Get options by type
    public List<Option> getOptionsByType(String optionType) {
        return optionRepository.findByOptionType(optionType);
    }
    
    // Create a new option
    public Option createOption(Option option) {
        return optionRepository.save(option);
    }
    
    // Update an existing option
    public Option updateOption(Long id, Option optionDetails) {
        Optional<Option> optionalOption = optionRepository.findById(id);
        if (optionalOption.isPresent()) {
            Option option = optionalOption.get();
            option.setSymbol(optionDetails.getSymbol());
            option.setOptionType(optionDetails.getOptionType());
            option.setStrikePrice(optionDetails.getStrikePrice());
            option.setCurrentPrice(optionDetails.getCurrentPrice());
            option.setExpirationDate(optionDetails.getExpirationDate());
            option.setPremium(optionDetails.getPremium());
            option.setDelta(optionDetails.getDelta());
            option.setGamma(optionDetails.getGamma());
            option.setTheta(optionDetails.getTheta());
            option.setVega(optionDetails.getVega());
            return optionRepository.save(option);
        }
        return null;
    }
    
    // Delete an option
    public boolean deleteOption(Long id) {
        if (optionRepository.existsById(id)) {
            optionRepository.deleteById(id);
            return true;
        }
        return false;
    }
}



