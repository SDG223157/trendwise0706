
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysis-form');
    const tickerInput = document.getElementById('ticker');
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'suggestions';
    tickerInput.parentNode.appendChild(suggestionsDiv);
    
    let debounceTimeout;

    function formatCompanyName(name) {
        return name.replace(/\\'/g, "'");
    }
    
    // Clear input on double click
    tickerInput.addEventListener('dblclick', function() {
        if (this.value) {
            this.value = '';
            suggestionsDiv.style.display = 'none';
        }
    });
    
    tickerInput.addEventListener('input', function() {
        clearTimeout(debounceTimeout);
        const query = this.value.trim();
        
        if (query.length < 1) {
            suggestionsDiv.style.display = 'none';
            return;
        }
        
        debounceTimeout = setTimeout(() => {
            fetch(`/search_ticker?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    suggestionsDiv.innerHTML = '';
                    
                    if (data.length > 0) {
                        // Filter out results where symbol equals name
                        const filteredData = data.filter(item => 
                            item.symbol.toUpperCase() !== item.name.toUpperCase()
                        );
                        
                        if (filteredData.length > 0) {
                            filteredData.forEach(item => {
                                const div = document.createElement('div');
                                div.className = 'suggestion-item';
                                const formattedName = formatCompanyName(item.name);
                                
                                // Create symbol span
                                const symbolSpan = document.createElement('span');
                                symbolSpan.className = 'symbol';
                                symbolSpan.textContent = item.symbol;
                                
                                // Create name container with inline metadata
                                const nameContainer = document.createElement('div');
                                nameContainer.className = 'name';
                                
                                const companyNameSpan = document.createElement('span');
                                companyNameSpan.className = 'company-name';
                                companyNameSpan.textContent = formattedName;
                                nameContainer.appendChild(companyNameSpan);
                                
                                // Add asset type and exchange info inline after name
                                if (item.type || item.exchange) {
                                    const metaSpan = document.createElement('span');
                                    metaSpan.className = 'meta';
                                    let metaText = [];
                                    if (item.type) metaText.push(item.type);
                                    if (item.exchange && item.exchange !== item.type) metaText.push(item.exchange);
                                    metaSpan.textContent = metaText.join(' • ');
                                    nameContainer.appendChild(metaSpan);
                                }
                                
                                div.appendChild(symbolSpan);
                                div.appendChild(nameContainer);
                                
                                div.addEventListener('click', function() {
                                    // Set input value to both symbol and name
                                    tickerInput.value = `${item.symbol}    ${formattedName}`;
                                    suggestionsDiv.style.display = 'none';
                                });
                                
                                suggestionsDiv.appendChild(div);
                            });
                            suggestionsDiv.style.display = 'block';
                        } else {
                            suggestionsDiv.style.display = 'none';
                        }
                    } else {
                        suggestionsDiv.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Search error:', error);
                    suggestionsDiv.style.display = 'none';
                });
        }, 300);
    });
    
    
    // Close suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!tickerInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
            suggestionsDiv.style.display = 'none';
        }
    });


    // Prevent suggestions from closing when clicking inside the input
    tickerInput.addEventListener('click', function(e) {
        e.stopPropagation();
        if (this.value.trim().length > 0) {
            suggestionsDiv.style.display = 'block';
        }
    });

    // Form submission (if needed)
    const analyzeForm = document.getElementById('analyze-form');
    if (analyzeForm) {
        analyzeForm.addEventListener('submit', function(e) {
            if (!tickerInput.value.trim()) {
                e.preventDefault();
                alert('Please enter a ticker symbol');
            }
        });
    }
});

// Password toggle functionality
function togglePassword(button) {
    const input = button.closest('.input-with-icon').querySelector('input');
    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    
    const icon = button.querySelector('i');
    icon.textContent = type === 'password' ? '👁️' : '👁️‍🗨️';
}

// Make togglePassword globally available
window.togglePassword = togglePassword;




// main.js
document.addEventListener('DOMContentLoaded', function() {
    // Check if elements exist before trying to use them
    const searchForm = document.getElementById('searchForm');
    const searchResults = document.getElementById('searchResults');
    const searchButton = document.getElementById('searchButton');
    const resetButton = document.getElementById('resetButton');
    const fetchButton = document.getElementById('fetchNews');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultsCount = document.getElementById('resultsCount');

    // Only proceed if we're on the news search page
    if (searchForm && fetchButton) {
        // Set default dates if not set
        const endDateInput = document.getElementById('end_date');
        const startDateInput = document.getElementById('start_date');
        
        if (endDateInput && !endDateInput.value) {
            const today = new Date().toISOString().split('T')[0];
            endDateInput.value = today;
        }
        if (startDateInput && !startDateInput.value) {
            const thirtyDaysAgo = new Date();
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
            startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
        }

        // Helper function to show/hide loading state
        function setLoading(isLoading) {
            if (loadingIndicator) {
                loadingIndicator.classList.toggle('hidden', !isLoading);
            }
            // Disable buttons during loading
            [searchButton, resetButton, fetchButton].forEach(button => {
                if (button) {
                    button.disabled = isLoading;
                }
            });
        }

        // Fetch button handler
        fetchButton.addEventListener('click', async function() {
            try {
                const symbol = document.getElementById('symbol')?.value?.trim();
                
                if (!symbol) {
                    alert('Please enter a stock symbol');
                    return;
                }

                setLoading(true);
                console.log('Fetching news for symbol:', symbol);

                const response = await fetch('/news/api/fetch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        symbols: [symbol],
                        limit: 10
                    })
                });

                console.log('Response status:', response.status);
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch news: ${response.status}`);
                }

                const data = await response.json();
                console.log('Fetch response:', data);

                if (data.error) {
                    throw new Error(data.error);
                }

                alert(`Successfully fetched ${data.articles?.length || 0} articles. You can now search for them.`);
                
                // Trigger a search with the current symbol
                if (searchForm) {
                    const formData = new FormData(searchForm);
                    const searchParams = new URLSearchParams(formData);
                    window.location.href = `/news/search?${searchParams.toString()}`;
                }

            } catch (error) {
                console.error('Error fetching news:', error);
                alert('Failed to fetch news: ' + error.message);
            } finally {
                setLoading(false);
            }
        });

        // Form submit handler
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(searchForm);
            const searchParams = new URLSearchParams(formData);
            window.location.href = `/news/search?${searchParams.toString()}`;
        });

        // Reset button handler
        if (resetButton) {
            resetButton.addEventListener('click', function() {
                searchForm.reset();
                if (endDateInput && startDateInput) {
                    const today = new Date();
                    endDateInput.value = today.toISOString().split('T')[0];
                    const thirtyDaysAgo = new Date();
                    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                    startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
                }
                searchForm.dispatchEvent(new Event('submit'));
            });
        }
    }
});