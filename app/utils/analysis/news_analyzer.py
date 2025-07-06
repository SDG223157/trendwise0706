# app/utils/analysis/news_analyzer.py

from datetime import datetime
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import re
from typing import Dict, List, Optional
import logging
from apify_client import ApifyClient
import time
import random

class NewsAnalyzer:
    def __init__(self, api_token: str):
        """Initialize NewsAnalyzer with required resources - TradingView only"""
        self.logger = logging.getLogger(__name__)
        
        # Check if API token is valid
        if not api_token or api_token.strip() == "" or api_token == "MISSING_API_TOKEN":
            self.logger.error("❌ Invalid or missing APIFY_API_TOKEN for NewsAnalyzer")
            self.logger.error("News fetching will be disabled")
            self.client = None
        else:
            self.client = ApifyClient(api_token)
            # Only initialize TradingView scraper - no investing scraper
            self.logger.info("✅ NewsAnalyzer initialized with TradingView scraper only")
        
        try:
            # Download required NLTK packages
            nltk_packages = ['punkt', 'averaged_perceptron_tagger', 'vader_lexicon']
            for package in nltk_packages:
                try:
                    nltk.data.find(f'tokenizers/{package}')
                except LookupError:
                    nltk.download(package, quiet=True)
            
            self.vader = SentimentIntensityAnalyzer()
            self.logger.info("Successfully initialized NLTK resources")
            
        except Exception as e:
            self.logger.error(f"Error initializing NLTK resources: {str(e)}")
            raise

    def get_news(self, symbols: List[str], limit: int = 10, retries: int = 3) -> List[Dict]:
        """Fetch news from TradingView only"""
        self.logger.debug(f"Fetching news for symbols: {symbols}")
        
        # Check if properly initialized
        if not self.client:
            self.logger.error("❌ NewsAnalyzer not properly initialized due to missing API token")
            return []
        
        # Fetch from TradingView only
        return self._fetch_tradingview_news(symbols, limit, retries)
    
    def _fetch_tradingview_news(self, symbols: List[str], limit: int = 10, retries: int = 3) -> List[Dict]:
        """Fetch news from TradingView via Apify"""
        if not self.client:
            self.logger.warning("⚠️ TradingView scraper not initialized due to missing API token")
            return []
            
        self.logger.debug(f"Fetching TradingView news for symbols: {symbols}")

        # Determine resultsLimit based on symbol regions
        results_limit = self._get_results_limit_for_symbols(symbols)
        self.logger.debug(f"Using resultsLimit: {results_limit} for symbols: {symbols}")

        run_input = {
            "symbols": symbols,
            "proxy": {"useApifyProxy": True},
            "resultsLimit": results_limit
        }

        for attempt in range(retries):
            try:
                run = self.client.actor("mscraper/tradingview-news-scraper").call(run_input=run_input)
                
                if not run or not run.get("defaultDatasetId"):
                    continue

                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                
                # Add source metadata to TradingView articles
                for item in items:
                    if isinstance(item, dict):
                        item['news_source'] = 'tradingview.com'
                        item['scraper_type'] = 'tradingview'
                
                self.logger.info(f"TradingView: fetched {len(items)} articles")
                return items

            except Exception as e:
                self.logger.error(f"Error fetching TradingView news (attempt {attempt + 1}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

        return []

    def analyze_article(self, article: Dict) -> Optional[Dict]:
        """Analyze a single article from TradingView only"""
        try:
            # Only handle TradingView articles now
            analyzed = self._analyze_tradingview_article(article)
            
            if not analyzed:
                return None
                
            # Add analysis
            content = analyzed.get("content", "")
            analyzed.update({
                "sentiment": self.analyze_sentiment(content),
                "summary": self.generate_summary(content),
                "metrics": self.extract_metrics(content)
            })
            
            return analyzed
            
        except Exception as e:
            self.logger.error(f"Error analyzing article: {str(e)}")
            return None
    
    def _analyze_tradingview_article(self, article: Dict) -> Optional[Dict]:
        """Analyze a TradingView article"""
        try:
            content = article.get("descriptionText", "")
            title = article.get("title", "")
            
            return {
                "external_id": article.get("id", str(hash(title + content))),
                "title": title,
                "content": content,
                "url": article.get("storyPath", ""),
                "published_at": datetime.fromtimestamp(
                    article.get("published", 0) / 1000
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "source": article.get("source", "TradingView"),
                "news_source": "tradingview.com",
                "scraper_type": "tradingview",
                "symbols": [{"symbol": s["symbol"]} for s in article.get("relatedSymbols", [])],
            }
        except Exception as e:
            self.logger.error(f"Error analyzing TradingView article: {str(e)}")
            return None

    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment using VADER"""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            # Map polarity to sentiment labels
            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"
                
            return {
                "label": label,
                "score": polarity,
                "explanation": f"Sentiment analysis indicates {label} sentiment with score {polarity:.2f}"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {str(e)}")
            return {"label": "neutral", "score": 0.0, "explanation": "Sentiment analysis unavailable"}

    def generate_summary(self, text: str) -> Dict:
        """Generate article summaries"""
        try:
            blob = TextBlob(text)
            sentences = blob.sentences
            
            if not sentences:
                return {"brief": text, "key_points": text}
            
            # Brief summary (first sentence)
            brief = str(sentences[0])
            if len(sentences) > 1:
                brief += " " + str(sentences[-1])
                
            # Key points (up to 3 most relevant sentences)
            key_points = [str(s) for s in sentences[:3]]
            
            return {
                "brief": brief,
                "key_points": " ".join(key_points),
                "market_impact": brief  # Simplified market impact
            }
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            return {"brief": "Summary unavailable", "key_points": ""}

    def extract_metrics(self, text: str) -> Dict:
        """Extract financial metrics with context"""
        try:
            return {
                "percentage": {
                    "values": self._extract_percentages(text),
                    "contexts": self._extract_contexts(text, r'\d+%')
                }
            }
        except Exception as e:
            self.logger.error(f"Error extracting metrics: {str(e)}")
            return {}

    def _extract_percentages(self, text: str) -> List[float]:
        """Extract percentage values from text"""
        matches = re.findall(r'(\d+(?:\.\d+)?)%', text)
        return [float(match) for match in matches]

    def _extract_contexts(self, text: str, pattern: str) -> List[str]:
        """Extract context around matches"""
        contexts = []
        for match in re.finditer(pattern, text):
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            contexts.append(text[start:end].strip())
        return contexts
    
    def _get_results_limit_for_symbols(self, symbols: List[str]) -> int:
        """
        Determine resultsLimit based on symbol regions:
        - China and Hong Kong symbols: 2 articles
        - Others: 5 articles
        """
        # Check if any symbol is from China or Hong Kong
        for symbol in symbols:
            if self._is_china_hk_symbol(symbol):
                self.logger.debug(f"China/HK symbol detected: {symbol}, using limit 2")
                return 2
        
        # Default limit for other regions
        self.logger.debug(f"Using default limit 5 for symbols: {symbols}")
        return 5
    
    def _is_china_hk_symbol(self, symbol: str) -> bool:
        """Check if symbol is from China or Hong Kong markets"""
        import re
        
        symbol = symbol.upper().strip()
        
        # China symbols patterns
        china_patterns = [
            r'^SSE:',           # Shanghai Stock Exchange (e.g., SSE:600519)
            r'^SZSE:',          # Shenzhen Stock Exchange (e.g., SZSE:000858)
            r'\.SS$',           # Yahoo Finance Shanghai format (e.g., 600519.SS)
            r'\.SZ$',           # Yahoo Finance Shenzhen format (e.g., 000858.SZ)
            r'^6\d{5}$',        # 6-digit Shanghai stocks starting with 6
            r'^[03]\d{5}$',     # 6-digit Shenzhen stocks starting with 0 or 3
        ]
        
        # Hong Kong symbols patterns
        hk_patterns = [
            r'^HKEX:',          # TradingView Hong Kong format (e.g., HKEX:700)
            r'\d+\.HK$',        # Yahoo Finance Hong Kong format (e.g., 0700.HK)
            r'^\d{3,5}$',       # Bare Hong Kong stock numbers (e.g., 700, 2318)
        ]
        
        # Check China patterns
        for pattern in china_patterns:
            if re.search(pattern, symbol):
                return True
        
        # Check Hong Kong patterns
        for pattern in hk_patterns:
            if re.search(pattern, symbol):
                return True
        
        return False