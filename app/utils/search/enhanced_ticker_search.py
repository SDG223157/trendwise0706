import re
import sqlite3
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

@dataclass
class TickerResult:
    symbol: str
    name: str
    exchange: str
    asset_type: str
    country: str
    score: float
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'exchange': self.exchange,
            'type': self.asset_type,
            'country': self.country,
            'score': self.score,
            'source': 'enhanced'
        }

class EnhancedTickerSearch:
    """Enhanced ticker search with comprehensive database and fuzzy matching"""
    
    def __init__(self):
        self.tickers_db = self._build_comprehensive_ticker_db()
        
    def _build_comprehensive_ticker_db(self) -> List[Dict]:
        """Build a comprehensive ticker database with various asset types"""
        tickers = []
        
        # Major US Stocks (Popular/Large Cap)
        us_stocks = [
            # Technology
            ('AAPL', 'Apple Inc.', 'NASDAQ', 'Equity', 'US'),
            ('MSFT', 'Microsoft Corporation', 'NASDAQ', 'Equity', 'US'),
            ('GOOGL', 'Alphabet Inc. Class A', 'NASDAQ', 'Equity', 'US'),
            ('GOOG', 'Alphabet Inc. Class C', 'NASDAQ', 'Equity', 'US'),
            ('AMZN', 'Amazon.com Inc.', 'NASDAQ', 'Equity', 'US'),
            ('META', 'Meta Platforms Inc.', 'NASDAQ', 'Equity', 'US'),
            ('TSLA', 'Tesla Inc.', 'NASDAQ', 'Equity', 'US'),
            ('NVDA', 'NVIDIA Corporation', 'NASDAQ', 'Equity', 'US'),
            ('NFLX', 'Netflix Inc.', 'NASDAQ', 'Equity', 'US'),
            ('ADBE', 'Adobe Inc.', 'NASDAQ', 'Equity', 'US'),
            ('CRM', 'Salesforce Inc.', 'NYSE', 'Equity', 'US'),
            ('ORCL', 'Oracle Corporation', 'NYSE', 'Equity', 'US'),
            ('INTC', 'Intel Corporation', 'NASDAQ', 'Equity', 'US'),
            ('AMD', 'Advanced Micro Devices', 'NASDAQ', 'Equity', 'US'),
            ('CSCO', 'Cisco Systems Inc.', 'NASDAQ', 'Equity', 'US'),
            ('PYPL', 'PayPal Holdings Inc.', 'NASDAQ', 'Equity', 'US'),
            ('UBER', 'Uber Technologies Inc.', 'NYSE', 'Equity', 'US'),
            ('ABNB', 'Airbnb Inc.', 'NASDAQ', 'Equity', 'US'),
            ('ZOOM', 'Zoom Video Communications', 'NASDAQ', 'Equity', 'US'),
            ('SPOT', 'Spotify Technology S.A.', 'NYSE', 'Equity', 'US'),
            
            # Finance/Banking
            ('JPM', 'JPMorgan Chase & Co.', 'NYSE', 'Equity', 'US'),
            ('BAC', 'Bank of America Corp.', 'NYSE', 'Equity', 'US'),
            ('WFC', 'Wells Fargo & Company', 'NYSE', 'Equity', 'US'),
            ('GS', 'Goldman Sachs Group Inc.', 'NYSE', 'Equity', 'US'),
            ('MS', 'Morgan Stanley', 'NYSE', 'Equity', 'US'),
            ('V', 'Visa Inc.', 'NYSE', 'Equity', 'US'),
            ('MA', 'Mastercard Inc.', 'NYSE', 'Equity', 'US'),
            ('AXP', 'American Express Company', 'NYSE', 'Equity', 'US'),
            ('BRK-A', 'Berkshire Hathaway Class A', 'NYSE', 'Equity', 'US'),
            ('BRK-B', 'Berkshire Hathaway Class B', 'NYSE', 'Equity', 'US'),
            
            # Healthcare/Pharma
            ('JNJ', 'Johnson & Johnson', 'NYSE', 'Equity', 'US'),
            ('PFE', 'Pfizer Inc.', 'NYSE', 'Equity', 'US'),
            ('UNH', 'UnitedHealth Group Inc.', 'NYSE', 'Equity', 'US'),
            ('MRK', 'Merck & Co. Inc.', 'NYSE', 'Equity', 'US'),
            ('ABBV', 'AbbVie Inc.', 'NYSE', 'Equity', 'US'),
            ('LLY', 'Eli Lilly and Company', 'NYSE', 'Equity', 'US'),
            ('BMY', 'Bristol Myers Squibb', 'NYSE', 'Equity', 'US'),
            ('GILD', 'Gilead Sciences Inc.', 'NASDAQ', 'Equity', 'US'),
            ('MRNA', 'Moderna Inc.', 'NASDAQ', 'Equity', 'US'),
            ('BNTX', 'BioNTech SE', 'NASDAQ', 'Equity', 'US'),
            
            # Consumer/Retail
            ('WMT', 'Walmart Inc.', 'NYSE', 'Equity', 'US'),
            ('HD', 'Home Depot Inc.', 'NYSE', 'Equity', 'US'),
            ('PG', 'Procter & Gamble Co.', 'NYSE', 'Equity', 'US'),
            ('KO', 'Coca-Cola Company', 'NYSE', 'Equity', 'US'),
            ('PEP', 'PepsiCo Inc.', 'NASDAQ', 'Equity', 'US'),
            ('NKE', 'Nike Inc.', 'NYSE', 'Equity', 'US'),
            ('SBUX', 'Starbucks Corporation', 'NASDAQ', 'Equity', 'US'),
            ('MCD', 'McDonald\'s Corporation', 'NYSE', 'Equity', 'US'),
            ('DIS', 'Walt Disney Company', 'NYSE', 'Equity', 'US'),
            ('COST', 'Costco Wholesale Corp.', 'NASDAQ', 'Equity', 'US'),
            
            # Energy/Industrial  
            ('XOM', 'Exxon Mobil Corporation', 'NYSE', 'Equity', 'US'),
            ('CVX', 'Chevron Corporation', 'NYSE', 'Equity', 'US'),
            ('GE', 'General Electric Company', 'NYSE', 'Equity', 'US'),
            ('CAT', 'Caterpillar Inc.', 'NYSE', 'Equity', 'US'),
            ('BA', 'Boeing Company', 'NYSE', 'Equity', 'US'),
            ('MMM', '3M Company', 'NYSE', 'Equity', 'US'),
            ('HON', 'Honeywell International', 'NASDAQ', 'Equity', 'US'),
            ('UPS', 'United Parcel Service', 'NYSE', 'Equity', 'US'),
            ('FDX', 'FedEx Corporation', 'NYSE', 'Equity', 'US'),
        ]
        
        # International Stocks
        international_stocks = [
            # European
            ('ASML', 'ASML Holding N.V.', 'NASDAQ', 'Equity', 'NL'),
            ('SAP', 'SAP SE', 'NYSE', 'Equity', 'DE'),
            ('NVO', 'Novo Nordisk A/S', 'NYSE', 'Equity', 'DK'),
            ('UL', 'Unilever PLC', 'NYSE', 'Equity', 'GB'),
            ('NESN.SW', 'Nestle S.A.', 'SWX', 'Equity', 'CH'),
            ('ASML.AS', 'ASML Holding N.V.', 'AMS', 'Equity', 'NL'),
            ('MC.PA', 'LVMH Moet Hennessy', 'EPA', 'Equity', 'FR'),
            ('OR.PA', 'L\'Oreal S.A.', 'EPA', 'Equity', 'FR'),
            ('SIE.DE', 'Siemens AG', 'XETRA', 'Equity', 'DE'),
            ('SAP.DE', 'SAP SE', 'XETRA', 'Equity', 'DE'),
            
            # Asian
            ('TSM', 'Taiwan Semiconductor', 'NYSE', 'Equity', 'TW'),
            ('BABA', 'Alibaba Group Holding', 'NYSE', 'Equity', 'CN'),
            ('JD', 'JD.com Inc.', 'NASDAQ', 'Equity', 'CN'),
            ('NIO', 'NIO Inc.', 'NYSE', 'Equity', 'CN'),
            ('XPEV', 'XPeng Inc.', 'NYSE', 'Equity', 'CN'),
            ('LI', 'Li Auto Inc.', 'NASDAQ', 'Equity', 'CN'),
            ('BIDU', 'Baidu Inc.', 'NASDAQ', 'Equity', 'CN'),
            ('PDD', 'PDD Holdings Inc.', 'NASDAQ', 'Equity', 'CN'),
            ('TME', 'Tencent Music Entertainment', 'NYSE', 'Equity', 'CN'),
            ('SONY', 'Sony Group Corporation', 'NYSE', 'Equity', 'JP'),
            
            # Hong Kong Format
            ('0700.HK', 'Tencent Holdings Ltd.', 'HKEX', 'Equity', 'HK'),
            ('0941.HK', 'China Mobile Limited', 'HKEX', 'Equity', 'HK'),
            ('1299.HK', 'AIA Group Limited', 'HKEX', 'Equity', 'HK'),
            ('2318.HK', 'Ping An Insurance', 'HKEX', 'Equity', 'HK'),
            ('0005.HK', 'HSBC Holdings plc', 'HKEX', 'Equity', 'HK'),
            ('0883.HK', 'CNOOC Limited', 'HKEX', 'Equity', 'HK'),
            ('0388.HK', 'Hong Kong Exchanges', 'HKEX', 'Equity', 'HK'),
            ('1398.HK', 'Industrial Commercial Bank', 'HKEX', 'Equity', 'HK'),
            ('2628.HK', 'China Life Insurance', 'HKEX', 'Equity', 'HK'),
            ('3988.HK', 'Bank of China Limited', 'HKEX', 'Equity', 'HK'),
        ]
        
        # Cryptocurrencies
        cryptocurrencies = [
            ('BTC-USD', 'Bitcoin USD', 'CCC', 'Cryptocurrency', 'US'),
            ('ETH-USD', 'Ethereum USD', 'CCC', 'Cryptocurrency', 'US'),
            ('BNB-USD', 'BNB USD', 'CCC', 'Cryptocurrency', 'US'),
            ('XRP-USD', 'XRP USD', 'CCC', 'Cryptocurrency', 'US'),
            ('ADA-USD', 'Cardano USD', 'CCC', 'Cryptocurrency', 'US'),
            ('SOL-USD', 'Solana USD', 'CCC', 'Cryptocurrency', 'US'),
            ('DOGE-USD', 'Dogecoin USD', 'CCC', 'Cryptocurrency', 'US'),
            ('DOT-USD', 'Polkadot USD', 'CCC', 'Cryptocurrency', 'US'),
            ('MATIC-USD', 'Polygon USD', 'CCC', 'Cryptocurrency', 'US'),
            ('AVAX-USD', 'Avalanche USD', 'CCC', 'Cryptocurrency', 'US'),
            ('SHIB-USD', 'Shiba Inu USD', 'CCC', 'Cryptocurrency', 'US'),
            ('UNI-USD', 'Uniswap USD', 'CCC', 'Cryptocurrency', 'US'),
            ('LINK-USD', 'Chainlink USD', 'CCC', 'Cryptocurrency', 'US'),
            ('LTC-USD', 'Litecoin USD', 'CCC', 'Cryptocurrency', 'US'),
            ('BCH-USD', 'Bitcoin Cash USD', 'CCC', 'Cryptocurrency', 'US'),
            ('ALGO-USD', 'Algorand USD', 'CCC', 'Cryptocurrency', 'US'),
            ('XLM-USD', 'Stellar USD', 'CCC', 'Cryptocurrency', 'US'),
            ('TRX-USD', 'TRON USD', 'CCC', 'Cryptocurrency', 'US'),
        ]
        
        # ETFs
        etfs = [
            ('SPY', 'SPDR S&P 500 ETF Trust', 'NYSE', 'ETF', 'US'),
            ('QQQ', 'Invesco QQQ Trust', 'NASDAQ', 'ETF', 'US'),
            ('VTI', 'Vanguard Total Stock Market', 'NYSE', 'ETF', 'US'),
            ('IWM', 'iShares Russell 2000 ETF', 'NYSE', 'ETF', 'US'),
            ('EFA', 'iShares MSCI EAFE ETF', 'NYSE', 'ETF', 'US'),
            ('EEM', 'iShares MSCI Emerging Markets', 'NYSE', 'ETF', 'US'),
            ('GLD', 'SPDR Gold Shares', 'NYSE', 'ETF', 'US'),
            ('SLV', 'iShares Silver Trust', 'NYSE', 'ETF', 'US'),
            ('TLT', 'iShares 20+ Year Treasury Bond', 'NASDAQ', 'ETF', 'US'),
            ('HYG', 'iShares iBoxx High Yield Corporate', 'NYSE', 'ETF', 'US'),
            ('XLF', 'Financial Select Sector SPDR', 'NYSE', 'ETF', 'US'),
            ('XLK', 'Technology Select Sector SPDR', 'NYSE', 'ETF', 'US'),
            ('XLE', 'Energy Select Sector SPDR', 'NYSE', 'ETF', 'US'),
            ('XLV', 'Health Care Select Sector SPDR', 'NYSE', 'ETF', 'US'),
            ('XLP', 'Consumer Staples Select Sector', 'NYSE', 'ETF', 'US'),
            ('ARKK', 'ARK Innovation ETF', 'NYSE', 'ETF', 'US'),
            ('ARKQ', 'ARK Autonomous Technology & Robotics', 'NYSE', 'ETF', 'US'),
            ('ARKW', 'ARK Next Generation Internet', 'NYSE', 'ETF', 'US'),
            ('ARKG', 'ARK Genomic Revolution ETF', 'NYSE', 'ETF', 'US'),
        ]
        
        # Similar name variations for "Pando" search (like in Yahoo Finance example)
        pando_variations = [
            ('PNDORA.CO', 'Pandora A/S', 'CPH', 'Equity', 'DK'),
            ('PANDO-USD', 'Pando USD', 'CCC', 'Cryptocurrency', 'US'),
            ('POX.F', 'Pandox AB (publ)', 'FRA', 'Equity', 'SE'),
            ('3112.HK', 'Pando CMS Blockchain ETF', 'HKG', 'ETF', 'HK'),
            ('PTX19210-USD', 'Pando Token USD', 'CCC', 'Cryptocurrency', 'US'),
            ('PNDR-USD', 'Pandora Finance USD', 'CCC', 'Cryptocurrency', 'US'),
        ]
        
        # Combine all data
        all_data = us_stocks + international_stocks + cryptocurrencies + etfs + pando_variations
        
        for symbol, name, exchange, asset_type, country in all_data:
            tickers.append({
                'symbol': symbol,
                'name': name,
                'exchange': exchange,
                'asset_type': asset_type,
                'country': country
            })
            
        return tickers
    
    def _calculate_similarity_score(self, query: str, symbol: str, name: str) -> float:
        """Calculate similarity score using multiple matching strategies"""
        query = query.upper()
        symbol = symbol.upper()
        name = name.upper()
        
        # Exact symbol match gets highest score
        if query == symbol:
            return 1.0
        
        # Symbol starts with query gets high score
        if symbol.startswith(query):
            return 0.9 - (len(symbol) - len(query)) * 0.01
        
        # Query is contained in symbol
        if query in symbol:
            position_score = 1.0 - (symbol.index(query) / len(symbol)) * 0.3
            return 0.7 * position_score
        
        # Name starts with query
        if name.startswith(query):
            return 0.8 - (len(name) - len(query)) * 0.005
        
        # Query is contained in name
        if query in name:
            position_score = 1.0 - (name.index(query) / len(name)) * 0.3
            return 0.6 * position_score
        
        # Fuzzy matching using SequenceMatcher for partial matches
        symbol_ratio = SequenceMatcher(None, query, symbol).ratio()
        name_ratio = SequenceMatcher(None, query, name).ratio()
        
        # Use the better of symbol or name fuzzy match
        fuzzy_score = max(symbol_ratio, name_ratio)
        
        # Only return fuzzy matches above a threshold
        if fuzzy_score >= 0.4:
            return 0.4 * fuzzy_score
        
        return 0.0
    
    def search(self, query: str, limit: int = 8) -> List[TickerResult]:
        """Search for tickers using enhanced fuzzy matching"""
        if not query or len(query.strip()) < 1:
            return []
        
        query = query.strip()
        results = []
        
        # Score all tickers
        for ticker_data in self.tickers_db:
            score = self._calculate_similarity_score(
                query, 
                ticker_data['symbol'], 
                ticker_data['name']
            )
            
            if score > 0:
                result = TickerResult(
                    symbol=ticker_data['symbol'],
                    name=ticker_data['name'],
                    exchange=ticker_data['exchange'],
                    asset_type=ticker_data['asset_type'],
                    country=ticker_data['country'],
                    score=score
                )
                results.append(result)
        
        # Sort by score (descending) and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def search_as_dict(self, query: str, limit: int = 8) -> List[Dict]:
        """Search and return results as dictionaries"""
        results = self.search(query, limit)
        return [result.to_dict() for result in results]


# Global instance for use in routes
enhanced_search = EnhancedTickerSearch() 