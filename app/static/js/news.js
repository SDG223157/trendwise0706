document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
      window.newsApp = new NewsApp();
    }
   });
   
   class NewsApp {
    constructor() {
      this.initializeElements();
      this.initializeEventListeners();
      this.pagination = new PaginationManager(this);
    }
   
    initializeElements() {
      this.elements = {
        searchForm: document.getElementById('searchForm'),
        searchResults: document.getElementById('searchResults'),
        searchButton: document.getElementById('searchButton'),
        resetButton: document.getElementById('resetButton'),
        fetchButton: document.getElementById('fetchNews'),
        loadingIndicator: document.getElementById('loadingIndicator'),
        resultsCount: document.getElementById('resultsCount')
      };
    }
   
    initializeEventListeners() {
      if (this.elements.searchForm) {
        this.elements.searchForm.addEventListener('submit', async (e) => {
          e.preventDefault();
          const formData = new FormData(this.elements.searchForm);
          await this.performSearch(formData);
        });
      }
   
      if (this.elements.fetchButton) {
        this.elements.fetchButton.addEventListener('click', () => this.handleFetch());
      }
   
      if (this.elements.resetButton) {
        this.elements.resetButton.addEventListener('click', () => this.handleReset());
      }
   
      this.setupArticleFeatures();
    }
   
    async performSearch(formData) {
      try {
        this.setLoading(true);
        const searchParams = new URLSearchParams(formData);
        const response = await fetch(`/news/search?${searchParams.toString()}`, {
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          }
        });
   
        const data = await response.json();
        if (this.elements.resultsCount) {
          this.elements.resultsCount.textContent = `${data.total} articles found`;
        }
   
        if (this.elements.searchResults) {
          if (data.articles?.length) {
            this.elements.searchResults.innerHTML = data.articles
              .map((article, index) => this.renderArticle(article, index))
              .join('');
            this.setupArticleFeatures();
          } else {
            this.elements.searchResults.innerHTML = this.renderEmptyState();
          }
        }
   
        UrlManager.updateUrl(formData);
   
      } catch (error) {
        console.error('Search error:', error);
        if (this.elements.searchResults) {
          this.elements.searchResults.innerHTML = this.renderError(error);
        }
      } finally {
        this.setLoading(false);
      }
    }
   
    async handleFetch() {
      try {
        const symbol = document.getElementById('symbol')?.value?.trim();
        console.log('Fetching news for symbol:', symbol);
        
        if (!symbol) {
          NotificationSystem.show('Please enter a stock symbol', 'error');
          return;
        }
   
        this.setLoading(true);
        NotificationSystem.show('Fetching latest news...', 'info');
   
        console.log('Sending fetch request...');
        const response = await fetch('/news/api/fetch', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({
            symbols: [symbol],
            limit: 10
          })
        });
   
        console.log('Response:', response);
        
        if (!response.ok) {
          throw new Error('Failed to fetch news');
        }
   
        const data = await response.json();
        console.log('Fetch response data:', data);
        
        if (this.elements.searchForm) {
          const formData = new FormData(this.elements.searchForm);
          formData.set('symbol', symbol);
          await this.performSearch(formData);
        }
   
        NotificationSystem.show(
          `Successfully fetched ${data.articles?.length || 0} articles for ${symbol}`,
          'success'
        );
   
      } catch (error) {
        console.error('Fetch error:', error);
        NotificationSystem.show('Failed to fetch news: ' + error.message, 'error');
      } finally {
        this.setLoading(false);
      }
    }
   
    handleReset() {
      if (this.elements.searchForm) {
        this.elements.searchForm.reset();
        const formData = new FormData(this.elements.searchForm);
        this.performSearch(formData);
      }
    }
   
    setLoading(isLoading) {
      if (this.elements.loadingIndicator) {
        if (isLoading) {
          this.elements.loadingIndicator.classList.remove('hidden');
        } else {
          this.elements.loadingIndicator.classList.add('hidden');
        }
      }
   
      const buttons = [
        this.elements.searchButton,
        this.elements.resetButton,
        this.elements.fetchButton
      ];
   
      buttons.forEach(button => {
        if (button) button.disabled = isLoading;
      });
    }
   
    setupArticleFeatures() {
      document.querySelectorAll('.expand-button').forEach(button => {
        button.addEventListener('click', () => {
          const content = button.previousElementSibling;
          const isExpanded = content.classList.contains('max-h-96');
          
          if (isExpanded) {
            content.classList.remove('max-h-96', 'opacity-100');
            content.classList.add('max-h-0', 'opacity-0');
            button.textContent = 'Show More';
            button.setAttribute('aria-expanded', 'false');
          } else {
            content.classList.remove('max-h-0', 'opacity-0');
            content.classList.add('max-h-96', 'opacity-100');
            button.textContent = 'Show Less';
            button.setAttribute('aria-expanded', 'true');
          }
        });
      });
   
      this.addCopyFeature();
      this.addShareFeature();
    }
   
    addCopyFeature() {
      document.querySelectorAll('.copy-button').forEach(button => {
        button.addEventListener('click', async (e) => {
          e.stopPropagation();
          const article = button.closest('.article-card');
          const title = article.querySelector('h3 a').textContent.trim();
          const content = article.querySelector('p').textContent.trim();
          const url = article.querySelector('a').href;
          
          try {
            await navigator.clipboard.writeText(`${title}\n\n${content}\n\nRead more: ${url}`);
            NotificationSystem.show('Article copied to clipboard', 'success');
          } catch (err) {
            NotificationSystem.show('Failed to copy article', 'error');
          }
        });
      });
    }
   
    addShareFeature() {
      document.querySelectorAll('.share-button').forEach(button => {
        button.addEventListener('click', async (e) => {
          e.stopPropagation();
          const article = button.closest('.article-card');
          const title = article.querySelector('h3 a').textContent.trim();
          const url = article.querySelector('a').href;
   
          if (navigator.share) {
            try {
              await navigator.share({
                title: title,
                url: url
              });
              NotificationSystem.show('Article shared successfully', 'success');
            } catch (err) {
              if (err.name !== 'AbortError') {
                NotificationSystem.show('Failed to share article', 'error');
              }
            }
          } else {
            try {
              await navigator.clipboard.writeText(url);
              NotificationSystem.show('Article URL copied to clipboard', 'success');
            } catch (err) {
              NotificationSystem.show('Failed to copy URL', 'error');
            }
          }
        });
      });
    }
   
    renderArticle(article, index) {
      return `
        <div class="article-card border-b border-gray-200 pb-6 last:border-b-0 mb-4">
          <div class="flex justify-between items-start mb-2">
            <h3 class="text-lg font-medium text-gray-900">
              <a href="${article.url}" target="_blank" class="text-blue-600 hover:text-blue-800">
                ${article.title}
              </a>
            </h3>
            <span class="text-sm text-gray-500">${article.published_at}</span>
          </div>
   
          <p class="text-gray-600">
            ${article.brief_summary || article.content || ''}
          </p>
   
          <div class="article-content max-h-0 opacity-0 overflow-hidden transition-all duration-500">
            ${article.market_impact_summary ? `
              <div class="mb-3">
                <h4 class="text-sm font-semibold text-gray-700">Market Impact:</h4>
                <p class="text-sm text-gray-600">${article.market_impact_summary}</p>
              </div>
            ` : ''}
   
            <div class="flex flex-wrap gap-2 mt-3">
              ${article.symbols?.map(symbol => `
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  ${symbol}
                </span>
              `).join('') || ''}
   
              ${article.sentiment_label ? `
                <span class="sentiment-tag inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
                  ${article.sentiment_label === 'POSITIVE' ? 'bg-green-100 text-green-800' :
                    article.sentiment_label === 'NEGATIVE' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'}">
                  ${article.sentiment_label}
                  ${article.sentiment_score ? 
                    `(${(article.sentiment_score * 100).toFixed(1)}%)` : 
                    ''}
                </span>
              ` : ''}
            </div>
          </div>
   
          <button class="expand-button mt-2 text-sm text-blue-600 hover:text-blue-800 focus:outline-none"
                  aria-expanded="false">
            Show More
          </button>
        </div>
      `;
    }
   
    renderEmptyState() {
      return `
        <div class="text-center py-8">
          <h3 class="text-sm font-medium text-gray-900">No articles found</h3>
          <p class="mt-1 text-sm text-gray-500">Try adjusting your search parameters</p>
        </div>
      `;
    }
   
    renderError(error) {
      return `
        <div class="bg-red-50 border-l-4 border-red-400 p-4">
          <div class="flex">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800">Error loading articles</h3>
              <p class="mt-2 text-sm text-red-700">${error.message}</p>
            </div>
          </div>
        </div>
      `;
    }
   }
   
   class PaginationManager {
    constructor(newsApp) {
      this.newsApp = newsApp;
      this.initialize();
    }
   
    initialize() {
      document.querySelectorAll('[data-page]').forEach(button => {
        button.addEventListener('click', async () => {
          const page = button.dataset.page;
          if (this.newsApp.elements.searchForm) {
            const formData = new FormData(this.newsApp.elements.searchForm);
            formData.set('page', page);
            await this.newsApp.performSearch(formData);
          }
        });
      });
    }
   }
   
   class UrlManager {
    static updateUrl(formData) {
      const url = new URL(window.location);
      formData.forEach((value, key) => {
        if (value) {
          url.searchParams.set(key, value);
        } else {
          url.searchParams.delete(key);
        }
      });
      window.history.pushState({}, '', url);
    }
   }
   
   class NotificationSystem {
    static show(message, type = 'info', duration = 5000) {
      const notification = document.createElement('div');
      notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 
        ${type === 'error' ? 'bg-red-500' : 
          type === 'success' ? 'bg-green-500' : 
          'bg-blue-500'} text-white`;
   
      notification.innerHTML = `
        <div class="flex items-center justify-between">
          <span>${message}</span>
          <button class="ml-4 text-white hover:text-gray-200 focus:outline-none">×</button>
        </div>
      `;
   
      document.body.appendChild(notification);
   
      const close = () => {
        notification.remove();
      };
   
      notification.querySelector('button').addEventListener('click', close);
      if (duration) setTimeout(close, duration);
   
      return notification;
    }
   }