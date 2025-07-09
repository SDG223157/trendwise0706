/**
 * Enhanced News Search Experience with AI-Powered Suggestions
 * 
 * Features:
 * - AI-powered intelligent search suggestions
 * - Real-time keyword suggestions from database
 * - Auto-complete functionality with semantic matching
 * - Search history and user behavior tracking
 * - Progressive loading and result streaming
 * - Trending topics and popular searches
 * - Keyboard navigation and shortcuts
 */

class EnhancedNewsSearch {
    constructor() {
        this.searchInput = document.getElementById('q');
        this.searchForm = document.getElementById('searchForm');
        this.resultsContainer = document.getElementById('articlesContainer');
        this.resultsCount = document.getElementById('resultsCount');
        this.loadingIndicator = null;
        this.suggestionsContainer = null;
        this.currentSuggestionIndex = -1;
        
        // Search state
        this.searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
        this.currentQuery = '';
        this.searchMetrics = {
            totalSearches: 0,
            avgResponseTime: 0,
            successRate: 0,
            suggestionsUsed: 0
        };
        
        // AI suggestion settings
        this.suggestionSettings = {
            minQueryLength: 2,
            debounceTime: 300,
            maxSuggestions: 8,
            cacheTimeout: 5 * 60 * 1000, // 5 minutes
            enableTrending: true,
            enablePersonalization: true
        };
        
        // Suggestion cache
        this.suggestionCache = new Map();
        
        this.init();
    }
    
    init() {
        this.createUI();
        this.setupEventListeners();
        this.loadSearchMetrics();
        this.loadTrendingKeywords();
        
        // Show initial suggestions on focus
        if (this.searchInput) {
            this.searchInput.addEventListener('focus', () => {
                const query = this.searchInput.value.trim();
                if (query) {
                    this.fetchSuggestions(query);
                } else {
                    this.showPopularSuggestions();
                }
            });
        }
    }
    
    createUI() {
        this.createLoadingIndicator();
        this.createSuggestionsContainer();
        this.createSearchEnhancements();
    }
    
    createLoadingIndicator() {
        this.loadingIndicator = document.createElement('div');
        this.loadingIndicator.id = 'aiSearchLoading';
        this.loadingIndicator.className = 'ai-search-loading';
        this.loadingIndicator.innerHTML = `
            <div class="loading-content">
                <div class="ai-spinner"></div>
                <span class="loading-text">AI is searching...</span>
            </div>
        `;
        this.loadingIndicator.style.display = 'none';
        
        if (this.searchInput) {
            this.searchInput.parentNode.insertBefore(this.loadingIndicator, this.searchInput.nextSibling);
        }
    }
    
    createSuggestionsContainer() {
        if (!this.searchInput) return;
        
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.id = 'aiSearchSuggestions';
        this.suggestionsContainer.className = 'ai-search-suggestions';
        this.suggestionsContainer.style.display = 'none';
        
        this.searchInput.parentNode.insertBefore(this.suggestionsContainer, this.searchInput.nextSibling);
    }
    
    createSearchEnhancements() {
        // Add search help text
        const helpText = document.createElement('div');
        helpText.className = 'search-help';
        helpText.innerHTML = `
            <div class="search-tips">
                <span class="tip">💡 Try: "AI earnings", "Tesla news", "crypto analysis"</span>
                <span class="shortcut">⌘K to focus search</span>
            </div>
        `;
        
        if (this.searchInput) {
            this.searchInput.parentNode.insertBefore(helpText, this.searchInput.nextSibling);
        }
    }
    
    setupEventListeners() {
        this.setupSearchSuggestions();
        this.setupSearchForm();
        this.setupKeyboardShortcuts();
        this.setupClickHandlers();
    }
    
    setupSearchSuggestions() {
        if (!this.searchInput) return;
        
        let suggestionTimeout;
        
        // Input event for real-time suggestions
        this.searchInput.addEventListener('input', (e) => {
            clearTimeout(suggestionTimeout);
            const query = e.target.value.trim();
            this.currentQuery = query;
            
            if (query.length >= this.suggestionSettings.minQueryLength) {
                suggestionTimeout = setTimeout(() => {
                    this.fetchSuggestions(query);
                }, this.suggestionSettings.debounceTime);
            } else if (query.length === 0) {
                this.showPopularSuggestions();
            } else {
                this.hideSuggestions();
            }
        });
        
        // Keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleSuggestionKeyboard(e);
        });
        
        // Hide suggestions on outside click
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && 
                !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
    }
    
    async fetchSuggestions(query) {
        if (!query) return;
        
        // Check cache first
        const cacheKey = query.toLowerCase();
        if (this.suggestionCache.has(cacheKey)) {
            const cached = this.suggestionCache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.suggestionSettings.cacheTimeout) {
                this.displaySuggestions(cached.suggestions, query);
                return;
            }
        }
        
        try {
            const userId = this.getCurrentUserId();
            const sessionId = this.getSessionId();
            
            const params = new URLSearchParams({
                q: query,
                limit: this.suggestionSettings.maxSuggestions.toString(),
                context: 'true'
            });
            
            if (userId) params.set('user_id', userId);
            if (sessionId) params.set('session_id', sessionId);
            
            const response = await fetch(`/news/api/suggestions?${params.toString()}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                const suggestions = data.data.suggestions;
                
                // Cache the suggestions
                this.suggestionCache.set(cacheKey, {
                    suggestions: suggestions,
                    timestamp: Date.now()
                });
                
                this.displaySuggestions(suggestions, query);
            } else {
                this.hideSuggestions();
            }
        } catch (error) {
            console.error('Error fetching AI suggestions:', error);
            this.hideSuggestions();
        }
    }
    
    async showPopularSuggestions() {
        try {
            const response = await fetch('/news/api/suggestions?q=&limit=8');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.displaySuggestions(data.data.suggestions, '', 'Popular Searches');
            }
        } catch (error) {
            console.error('Error fetching popular suggestions:', error);
        }
    }
    
    displaySuggestions(suggestions, query, headerText = 'AI Suggestions') {
        if (!suggestions || suggestions.length === 0) {
            this.hideSuggestions();
            return;
        }
        
        let html = `<div class="suggestions-header">
            <span class="header-text">${headerText}</span>
            <span class="ai-badge">✨ AI-Powered</span>
        </div>`;
        
        suggestions.forEach((suggestion, index) => {
            const icon = this.getSuggestionIcon(suggestion);
            const typeClass = `suggestion-${suggestion.type}`;
            const categoryClass = `category-${suggestion.category}`;
            
            html += `
                <div class="suggestion-item ${typeClass} ${categoryClass}" 
                     data-index="${index}" 
                     data-suggestion="${suggestion.text}"
                     data-category="${suggestion.category}"
                     data-type="${suggestion.type}">
                    <div class="suggestion-content">
                        <div class="suggestion-main">
                            <span class="suggestion-icon">${icon}</span>
                            <span class="suggestion-text">${this.highlightQuery(suggestion.text, query)}</span>
                            ${this.getSuggestionBadge(suggestion)}
                        </div>
                        <div class="suggestion-meta">
                            <span class="suggestion-category">${this.formatCategory(suggestion.category)}</span>
                            ${suggestion.article_count ? `<span class="suggestion-count">${suggestion.article_count} articles</span>` : ''}
                            ${suggestion.recent_activity > 0 ? `<span class="suggestion-recent">${suggestion.recent_activity} recent</span>` : ''}
                            <span class="suggestion-score">${Math.round(suggestion.relevance_score * 100)}% relevant</span>
                        </div>
                    </div>
                </div>
            `;
        });
        
        // Add trending keywords section if enabled
        if (this.suggestionSettings.enableTrending && !query) {
            html += await this.getTrendingSection();
        }
        
        this.suggestionsContainer.innerHTML = html;
        this.suggestionsContainer.style.display = 'block';
        this.currentSuggestionIndex = -1;
        
        // Add click handlers
        this.attachSuggestionHandlers();
    }
    
    getSuggestionIcon(suggestion) {
        const icons = {
            'company': '🏢',
            'technology': '💻',
            'financial': '💰',
            'industry': '🏭',
            'concept': '💡',
            'person': '👤',
            'location': '📍'
        };
        
        // Special icons for suggestion types
        if (suggestion.type === 'trending') return '📈';
        if (suggestion.type === 'personalized') return '👤';
        if (suggestion.type === 'symbol') return '📊';
        
        return icons[suggestion.category] || '🔍';
    }
    
    getSuggestionBadge(suggestion) {
        if (suggestion.type === 'trending') return '<span class="trend-badge">Trending</span>';
        if (suggestion.type === 'personalized') return '<span class="personal-badge">For You</span>';
        if (suggestion.frequency > 50) return '<span class="popular-badge">Popular</span>';
        return '';
    }
    
    formatCategory(category) {
        return category.charAt(0).toUpperCase() + category.slice(1);
    }
    
    async getTrendingSection() {
        try {
            const response = await fetch('/news/api/keywords/trending?days=7&limit=5');
            const data = await response.json();
            
            if (data.status === 'success' && data.data.trending_keywords.length > 0) {
                let html = '<div class="trending-section"><div class="trending-header">🔥 Trending Now</div>';
                
                data.data.trending_keywords.forEach(keyword => {
                    html += `
                        <div class="trending-item" data-suggestion="${keyword.keyword}">
                            <span class="trending-text">${keyword.keyword}</span>
                            <span class="trending-count">${keyword.recent_count} articles</span>
                        </div>
                    `;
                });
                
                html += '</div>';
                return html;
            }
        } catch (error) {
            console.error('Error fetching trending keywords:', error);
        }
        
        return '';
    }
    
    attachSuggestionHandlers() {
        // Regular suggestions
        this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const suggestion = e.currentTarget.dataset.suggestion;
                const category = e.currentTarget.dataset.category;
                const type = e.currentTarget.dataset.type;
                
                this.selectSuggestion(suggestion, { category, type });
            });
        });
        
        // Trending items
        this.suggestionsContainer.querySelectorAll('.trending-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const suggestion = e.currentTarget.dataset.suggestion;
                this.selectSuggestion(suggestion, { type: 'trending' });
            });
        });
    }
    
    selectSuggestion(suggestion, metadata = {}) {
        const originalQuery = this.currentQuery;
        
        this.searchInput.value = suggestion;
        this.currentQuery = suggestion;
        this.hideSuggestions();
        
        // Track suggestion usage
        this.trackSuggestionClick(originalQuery, suggestion, metadata);
        this.updateSuggestionMetrics();
        
        // Perform search
        this.performSearch();
    }
    
    async trackSuggestionClick(originalQuery, selectedSuggestion, metadata = {}) {
        try {
            await fetch('/news/api/suggestions/click', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: originalQuery,
                    selected_suggestion: selectedSuggestion,
                    session_id: this.getSessionId(),
                    user_id: this.getCurrentUserId(),
                    metadata: metadata
                })
            });
        } catch (error) {
            console.error('Error tracking suggestion click:', error);
        }
    }
    
    updateSuggestionMetrics() {
        this.searchMetrics.suggestionsUsed++;
        localStorage.setItem('searchMetrics', JSON.stringify(this.searchMetrics));
    }
    
    highlightQuery(text, query) {
        if (!query) return text;
        
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
    
    handleSuggestionKeyboard(e) {
        const suggestions = this.suggestionsContainer.querySelectorAll('.suggestion-item, .trending-item');
        if (suggestions.length === 0) return;
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.currentSuggestionIndex = (this.currentSuggestionIndex + 1) % suggestions.length;
            this.highlightSuggestion(suggestions);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.currentSuggestionIndex = this.currentSuggestionIndex <= 0 ? 
                suggestions.length - 1 : this.currentSuggestionIndex - 1;
            this.highlightSuggestion(suggestions);
        } else if (e.key === 'Enter' && this.currentSuggestionIndex >= 0) {
            e.preventDefault();
            const selectedItem = suggestions[this.currentSuggestionIndex];
            const suggestion = selectedItem.dataset.suggestion;
            
            const metadata = {
                category: selectedItem.dataset.category,
                type: selectedItem.dataset.type
            };
            
            this.selectSuggestion(suggestion, metadata);
        } else if (e.key === 'Escape') {
            this.hideSuggestions();
        }
    }
    
    highlightSuggestion(suggestions) {
        suggestions.forEach((item, index) => {
            item.classList.toggle('highlighted', index === this.currentSuggestionIndex);
        });
    }
    
    hideSuggestions() {
        this.suggestionsContainer.style.display = 'none';
        this.currentSuggestionIndex = -1;
    }
    
    setupSearchForm() {
        if (!this.searchForm) return;
        
        this.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.performSearch();
        });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+K or Cmd+K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                if (this.searchInput) {
                    this.searchInput.focus();
                    this.searchInput.select();
                }
            }
            
            // Escape to clear search
            if (e.key === 'Escape' && document.activeElement === this.searchInput) {
                this.searchInput.value = '';
                this.hideSuggestions();
            }
        });
    }
    
    setupClickHandlers() {
        // Click outside to hide suggestions
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && 
                !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
    }
    
    async performSearch() {
        const query = this.searchInput.value.trim();
        if (!query) return;
        
        this.currentQuery = query;
        this.showLoading();
        this.addToSearchHistory(query);
        this.hideSuggestions();
        
        const startTime = Date.now();
        
        try {
            // Update URL
            const params = new URLSearchParams(window.location.search);
            params.set('q', query);
            window.history.pushState({}, '', `${window.location.pathname}?${params.toString()}`);
            
            // Perform search
            const response = await fetch(`/news/api/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            const responseTime = Date.now() - startTime;
            this.updateSearchMetrics(responseTime, data.status === 'success');
            
            if (data.status === 'success') {
                this.displayResults(data.data.articles);
                this.updateResultsCount(data.data.pagination.total);
            } else {
                this.displayError(data.message || 'Search failed');
            }
            
        } catch (error) {
            console.error('Search error:', error);
            this.displayError('Search failed. Please try again.');
            this.updateSearchMetrics(Date.now() - startTime, false);
        } finally {
            this.hideLoading();
        }
    }
    
    showLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'block';
        }
    }
    
    hideLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'none';
        }
    }
    
    displayResults(articles) {
        if (!this.resultsContainer) return;
        
        if (articles.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <h3>No results found</h3>
                    <p>Try different keywords or check our trending topics below.</p>
                    <div class="search-suggestions-help">
                        <button onclick="this.closest('.no-results').nextSibling.style.display='block'">
                            Show Search Suggestions
                        </button>
                    </div>
                </div>
            `;
            return;
        }
        
        const resultsHtml = articles.map(article => this.formatArticle(article)).join('');
        this.resultsContainer.innerHTML = resultsHtml;
    }
    
    formatArticle(article) {
        const publishedDate = new Date(article.published_at).toLocaleDateString();
        const sentimentRating = article.summary?.ai_sentiment_rating || 0;
        const sentimentClass = this.getSentimentClass(sentimentRating);
        
        return `
            <div class="article-card enhanced">
                <div class="article-header">
                    <h3><a href="${article.url}" target="_blank">${article.title}</a></h3>
                    <div class="article-meta">
                        <span class="article-source">${article.source}</span>
                        <span class="article-date">${publishedDate}</span>
                        <span class="sentiment-badge ${sentimentClass}">
                            ${this.getSentimentEmoji(sentimentRating)} ${this.getSentimentLabel(sentimentRating)}
                        </span>
                    </div>
                </div>
                <div class="article-content">
                    <div class="ai-summary">
                        ${article.summary?.ai_summary || article.content?.substring(0, 200) + '...'}
                    </div>
                    ${article.summary?.ai_insights ? `
                        <div class="ai-insights">
                            <strong>AI Insights:</strong> ${article.summary.ai_insights}
                        </div>
                    ` : ''}
                </div>
                ${article.symbols?.length > 0 ? `
                    <div class="article-symbols">
                        ${article.symbols.map(s => `<span class="symbol-tag">${s.symbol}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    getSentimentClass(rating) {
        if (rating >= 4) return 'sentiment-positive';
        if (rating <= 2) return 'sentiment-negative';
        return 'sentiment-neutral';
    }
    
    getSentimentEmoji(rating) {
        if (rating >= 4) return '📈';
        if (rating <= 2) return '📉';
        return '➡️';
    }
    
    getSentimentLabel(rating) {
        if (rating >= 4) return 'Positive';
        if (rating <= 2) return 'Negative';
        return 'Neutral';
    }
    
    displayError(message) {
        if (this.resultsContainer) {
            this.resultsContainer.innerHTML = `
                <div class="search-error">
                    <div class="error-icon">⚠️</div>
                    <h3>Search Error</h3>
                    <p>${message}</p>
                    <button onclick="location.reload()">Retry</button>
                </div>
            `;
        }
    }
    
    updateResultsCount(total) {
        if (this.resultsCount) {
            this.resultsCount.innerHTML = `
                <span class="results-number">${total}</span> results found
                <span class="ai-powered">✨ AI-Enhanced</span>
            `;
        }
    }
    
    addToSearchHistory(query) {
        this.searchHistory = this.searchHistory.filter(item => item.query !== query);
        
        this.searchHistory.unshift({
            query: query,
            timestamp: Date.now(),
            results: 0 // Will be updated after search
        });
        
        this.searchHistory = this.searchHistory.slice(0, 50);
        localStorage.setItem('searchHistory', JSON.stringify(this.searchHistory));
    }
    
    updateSearchMetrics(responseTime, success) {
        this.searchMetrics.totalSearches++;
        this.searchMetrics.avgResponseTime = (this.searchMetrics.avgResponseTime + responseTime) / 2;
        
        const successCount = this.searchMetrics.totalSearches * this.searchMetrics.successRate;
        this.searchMetrics.successRate = (successCount + (success ? 1 : 0)) / this.searchMetrics.totalSearches;
        
        localStorage.setItem('searchMetrics', JSON.stringify(this.searchMetrics));
    }
    
    loadSearchMetrics() {
        const saved = localStorage.getItem('searchMetrics');
        if (saved) {
            this.searchMetrics = { ...this.searchMetrics, ...JSON.parse(saved) };
        }
    }
    
    async loadTrendingKeywords() {
        try {
            const response = await fetch('/news/api/keywords/trending?days=7&limit=10');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.trendingKeywords = data.data.trending_keywords;
            }
        } catch (error) {
            console.error('Error loading trending keywords:', error);
        }
    }
    
    getCurrentUserId() {
        // This would typically come from your authentication system
        return localStorage.getItem('userId') || null;
    }
    
    getSessionId() {
        let sessionId = localStorage.getItem('searchSessionId');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('searchSessionId', sessionId);
        }
        return sessionId;
    }
    
    // Public methods for external use
    
    showSearchAnalytics() {
        console.log('Search Analytics:', this.searchMetrics);
        console.log('Search History:', this.searchHistory);
    }
    
    clearSearchHistory() {
        this.searchHistory = [];
        localStorage.removeItem('searchHistory');
        console.log('Search history cleared');
    }
    
    clearSearchCache() {
        this.suggestionCache.clear();
        console.log('Suggestion cache cleared');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.enhancedSearch = new EnhancedNewsSearch();
    
    // Add global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.altKey && e.key === 'h') {
            e.preventDefault();
            window.enhancedSearch.showSearchAnalytics();
        }
    });
}); 