// Main JavaScript for SciSearch engine

document.addEventListener('DOMContentLoaded', function() {
    // Handle search form submission
    const searchForms = document.querySelectorAll('.search-form, .search-form-small');
    
    searchForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const searchInput = this.querySelector('input[name="q"]');
            
            // Prevent empty searches
            if (!searchInput.value.trim()) {
                event.preventDefault();
                searchInput.focus();
            }
        });
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Press / to focus search input
        if (event.key === '/' && document.activeElement.tagName !== 'INPUT') {
            event.preventDefault();
            const searchInput = document.querySelector('.search-input') || 
                               document.querySelector('.search-input-small');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Press Escape to clear search input
        if (event.key === 'Escape') {
            const activeElement = document.activeElement;
            if (activeElement.classList.contains('search-input') || 
                activeElement.classList.contains('search-input-small')) {
                activeElement.value = '';
            }
        }
    });
    
    // Highlight search terms in results
    const highlightSearchTerms = () => {
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');
        
        if (!query) return;
        
        const terms = parseQueryTerms(query);
        const abstracts = document.querySelectorAll('.result-abstract');
        
        abstracts.forEach(abstract => {
            let content = abstract.innerHTML;
            
            terms.forEach(term => {
                if (!term.trim() || ['AND', 'OR', 'NOT'].includes(term.toUpperCase())) return;
                
                // Remove field prefix
                if (term.includes(':')) {
                    term = term.split(':')[1];
                }
                
                // Remove quotes
                term = term.replace(/"/g, '');
                
                const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi');
                content = content.replace(regex, '<mark>$1</mark>');
            });
            
            abstract.innerHTML = content;
        });
    };
    
    // Parse query terms for highlighting
    const parseQueryTerms = (query) => {
        const terms = [];
        const withoutPhrases = query.replace(/"([^"]*)"/g, (match, phrase) => {
            terms.push(phrase);
            return ' ';
        });
        
        const otherTerms = withoutPhrases.split(/\s+/).filter(term => term.trim());
        return [...otherTerms, ...terms].filter(term => term.trim());
    };
    
    // Escape regex special characters
    const escapeRegExp = (string) => {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    };
    
    // Run highlighting on results page
    if (document.querySelector('.results-container')) {
        highlightSearchTerms();
    }
    
    // Add autocomplete
    const addAutocomplete = () => {
        const searchInputs = document.querySelectorAll('.search-input, .search-input-small');
        
        searchInputs.forEach(input => {
            input.addEventListener('input', async function() {
                const query = this.value.trim();
                if (query.length > 2) {
                    await showSuggestions(this, query);
                } else {
                    removeSuggestions();
                }
            });
        });
    };
    
    // Show autocomplete suggestions
    const showSuggestions = async (inputElement, query) => {
        removeSuggestions();
        
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'suggestions-container';
        
        try {
            const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
            const suggestions = await response.json();
            
            if (!Array.isArray(suggestions) || suggestions.length === 0) {
                removeSuggestions();
                return;
            }
            
            suggestions.forEach(suggestion => {
                const suggestionElement = document.createElement('div');
                suggestionElement.className = 'suggestion-item';
                suggestionElement.textContent = suggestion;
                
                suggestionElement.addEventListener('click', () => {
                    inputElement.value = suggestion;
                    inputElement.focus();
                    removeSuggestions();
                });
                
                suggestionsContainer.appendChild(suggestionElement);
            });
            
            const inputRect = inputElement.getBoundingClientRect();
            suggestionsContainer.style.width = `${inputElement.offsetWidth}px`;
            suggestionsContainer.style.top = `${inputRect.bottom + window.scrollY}px`;
            suggestionsContainer.style.left = `${inputRect.left + window.scrollX}px`;
            
            document.body.appendChild(suggestionsContainer);
            
            // Close suggestions when clicking outside
            document.addEventListener('click', function clickOutside(event) {
                if (!suggestionsContainer.contains(event.target) && event.target !== inputElement) {
                    removeSuggestions();
                    document.removeEventListener('click', clickOutside);
                }
            });
        } catch (error) {
            console.error('Error fetching suggestions:', error);
            removeSuggestions();
        }
    };
    
    // Remove autocomplete suggestions
    const removeSuggestions = () => {
        const container = document.querySelector('.suggestions-container');
        if (container) {
            container.remove();
        }
    };
    
    // Initialize autocomplete
    addAutocomplete();
    
    // Add styles for suggestions
    const addSuggestionStyles = () => {
        const style = document.createElement('style');
        style.textContent = `
            .suggestions-container {
                position: absolute;
                background: white;
                border: 1px solid var(--border-color);
                border-top: none;
                border-radius: 0 0 8px 8px;
                box-shadow: 0 4px 6px rgba(32, 33, 36, 0.1);
                z-index: 1100;
                max-height: 250px;
                overflow-y: auto;
            }
            
            .suggestion-item {
                padding: 10px 16px;
                cursor: pointer;
                font-size: 16px;
            }
            
            .suggestion-item:hover {
                background-color: var(--background-color);
            }
            
            mark {
                background-color: rgba(251, 188, 5, 0.3);
                padding: 0 2px;
                border-radius: 2px;
            }
        `;
        document.head.appendChild(style);
    };
    
    addSuggestionStyles();
});