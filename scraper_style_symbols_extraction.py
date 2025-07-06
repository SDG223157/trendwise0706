#!/usr/bin/env python3
"""
Scraper-Style Symbol Extraction for TrendWise
Mimics the symbol format that TradingView/Investing.com scrapers would have provided
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsArticle, NewsSearchIndex
import json
import re
from typing import List, Dict, Set
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperStyleSymbolExtractor:
    def __init__(self):
        """Initialize with comprehensive symbol patterns matching scraper formats"""
        
        # US Market symbols (most common in TradingView)
        self.us_patterns = [
            # Direct mentions with exchange
            r'\b(NASDAQ|NYSE|AMEX):([A-Z]{1,5})\b',
            r'\b(NASDAQ|NYSE|AMEX)\s+([A-Z]{1,5})\b',
            
            # Ticker symbols in various contexts
            r'\$([A-Z]{1,5})\b',  # $AAPL format
            r'\b([A-Z]{2,5})\s+(?:stock|shares|equity|ticker)\b',
            r'\b(?:ticker|symbol)\s+([A-Z]{2,5})\b',
            r'\b([A-Z]{2,5})\s+(?:Inc|Corp|Company|Ltd)\b',
            r'\b([A-Z]{2,5})(?:\s+)?(?:reported|announced|said)\b',
        ]
        
        # Hong Kong Exchange
        self.hk_patterns = [
            r'\b(HKEX):(\d{1,5})\b',
            r'\b(\d{4})\.HK\b',  # 0700.HK format
            r'\bHong Kong.*?(\d{4})\b',
        ]
        
        # Chinese Exchanges
        self.china_patterns = [
            r'\b(SSE|SZSE):(\d{6})\b',
            r'\b(\d{6})\.S[SZ]\b',  # 600519.SS format
            r'\bShanghai.*?(\d{6})\b',
            r'\bShenzhen.*?(\d{6})\b',
        ]
        
        # Other major exchanges
        self.other_patterns = [
            r'\b(TSE):([A-Z0-9]{1,5})\b',  # Tokyo
            r'\b(LSE):([A-Z]{2,5})\b',     # London
            r'\b(ASX):([A-Z]{2,5})\b',     # Australia
        ]
        
        # Common false positives to exclude
        self.exclude_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR',
            'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE',
            'TWO', 'WHO', 'BOY', 'DID', 'HAS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE', 'WAY', 'WIN',
            'CEO', 'CFO', 'CTO', 'COO', 'USA', 'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'HKD', 'GDP', 'IPO',
            'ETF', 'ESG', 'SEC', 'FDA', 'FTC', 'DOJ', 'EPA', 'FBI', 'CIA', 'NSA', 'IRS', 'FED', 'ECB',
            'IMF', 'WTO', 'WHO', 'API', 'AI', 'ML', 'AR', 'VR', 'IoT', 'IT', 'HR', 'PR', 'QA', 'UI',
            'UX', 'SEO', 'SEM', 'CRM', 'ERP', 'SaaS', 'PaaS', 'IaaS', 'AWS', 'IBM', 'HP', 'GM', 'GE',
            'YEAR', 'YEARS', 'WEEK', 'WEEKS', 'MONTH', 'MONTHS', 'TODAY', 'DAYS', 'TIME', 'TIMES',
            'QUARTER', 'HALF', 'FULL', 'PART', 'MOST', 'SOME', 'MANY', 'MUCH', 'MORE', 'LESS', 'BEST',
            'CHINA', 'JAPAN', 'KOREA', 'INDIA', 'FRANCE', 'GERMANY', 'ITALY', 'SPAIN', 'CANADA',
            'MARKET', 'MARKETS', 'TRADE', 'TRADING', 'BUSINESS', 'COMPANY', 'COMPANIES', 'FIRM', 'FIRMS',
            'STOCK', 'STOCKS', 'SHARE', 'SHARES', 'PRICE', 'PRICES', 'VALUE', 'VALUES', 'PROFIT', 'LOSS',
            'SALES', 'REVENUE', 'INCOME', 'EARNINGS', 'GROWTH', 'REPORT', 'REPORTS', 'NEWS', 'UPDATE',
            'PERCENT', 'BILLION', 'MILLION', 'THOUSAND', 'DOLLAR', 'DOLLARS', 'RISE', 'FALL', 'UP', 'DOWN',
            'HIGH', 'LOW', 'OPEN', 'CLOSE', 'BUY', 'SELL', 'HOLD', 'STRONG', 'WEAK', 'GOOD', 'BAD',
            'FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'LAST', 'NEXT', 'PREVIOUS', 'CURRENT', 'PAST',
            'FUTURE', 'EARLY', 'LATE', 'SOON', 'LONG', 'SHORT', 'BIG', 'SMALL', 'LARGE', 'HUGE', 'TINY'
        }
        
        # Well-known company mappings to proper symbols
        self.company_mappings = {
            'Apple': 'NASDAQ:AAPL',
            'Microsoft': 'NASDAQ:MSFT', 
            'Amazon': 'NASDAQ:AMZN',
            'Tesla': 'NASDAQ:TSLA',
            'Google': 'NASDAQ:GOOGL',
            'Alphabet': 'NASDAQ:GOOGL',
            'Meta': 'NASDAQ:META',
            'Facebook': 'NASDAQ:META',
            'Netflix': 'NASDAQ:NFLX',
            'NVIDIA': 'NASDAQ:NVDA',
            'Berkshire': 'NYSE:BRK.A',
            'JPMorgan': 'NYSE:JPM',
            'Johnson & Johnson': 'NYSE:JNJ',
            'Procter & Gamble': 'NYSE:PG',
            'Visa': 'NYSE:V',
            'Mastercard': 'NYSE:MA',
            'Coca-Cola': 'NYSE:KO',
            'McDonald': 'NYSE:MCD',
            'Disney': 'NYSE:DIS',
            'Boeing': 'NYSE:BA',
            'Intel': 'NASDAQ:INTC',
            'AMD': 'NASDAQ:AMD',
            'Qualcomm': 'NASDAQ:QCOM',
            'Cisco': 'NASDAQ:CSCO',
            'Oracle': 'NYSE:ORCL',
            'Salesforce': 'NYSE:CRM',
            'PayPal': 'NASDAQ:PYPL',
            'Adobe': 'NASDAQ:ADBE',
            'Shopify': 'NYSE:SHOP',
            'Zoom': 'NASDAQ:ZM',
            'Slack': 'NYSE:WORK',
            'Twitter': 'NYSE:TWTR',
            'Snapchat': 'NYSE:SNAP',
            'Uber': 'NYSE:UBER',
            'Lyft': 'NASDAQ:LYFT',
            'Airbnb': 'NASDAQ:ABNB',
            'DoorDash': 'NYSE:DASH',
            'Peloton': 'NASDAQ:PTON',
            'Robinhood': 'NASDAQ:HOOD',
            'Coinbase': 'NASDAQ:COIN',
            'Palantir': 'NYSE:PLTR',
            'Snowflake': 'NYSE:SNOW',
            'Alibaba': 'NYSE:BABA',
            'Tencent': 'HKEX:0700',
            'TSMC': 'NYSE:TSM',
            'Samsung': 'KRX:005930',
            'Sony': 'NYSE:SONY',
            'Toyota': 'NYSE:TM',
            'Volkswagen': 'OTCMKTS:VWAGY',
            'ASML': 'NASDAQ:ASML',
            'Shopee': 'NYSE:SE',
            'Grab': 'NASDAQ:GRAB',
            'Baidu': 'NASDAQ:BIDU',
            'JD.com': 'NASDAQ:JD',
            'Pinduoduo': 'NASDAQ:PDD',
            'NIO': 'NYSE:NIO',
            'XPeng': 'NYSE:XPEV',
            'Li Auto': 'NASDAQ:LI',
            'BYD': 'HKEX:1211',
            'Geely': 'HKEX:0175',
            'Xiaomi': 'HKEX:1810',
            'Meituan': 'HKEX:3690',
            'Kuaishou': 'HKEX:1024',
            'Bilibili': 'NASDAQ:BILI',
            'NetEase': 'NASDAQ:NTES',
            'Weibo': 'NASDAQ:WB',
            'Sina': 'NASDAQ:SINA',
            'Sohu': 'NASDAQ:SOHU',
            'Vipshop': 'NYSE:VIPS',
            'Yum China': 'NYSE:YUMC',
            'Starbucks': 'NASDAQ:SBUX',
            'KFC': 'NYSE:YUM',
            'McDonald': 'NYSE:MCD',
            'Domino': 'NYSE:DPZ',
            'Chipotle': 'NYSE:CMG',
            'Walmart': 'NYSE:WMT',
            'Target': 'NYSE:TGT',
            'Home Depot': 'NYSE:HD',
            'Lowe': 'NYSE:LOW',
            'Costco': 'NASDAQ:COST',
            'CVS': 'NYSE:CVS',
            'Walgreens': 'NASDAQ:WBA',
            'Pfizer': 'NYSE:PFE',
            'Moderna': 'NASDAQ:MRNA',
            'Johnson': 'NYSE:JNJ',
            'AbbVie': 'NYSE:ABBV',
            'Merck': 'NYSE:MRK',
            'Bristol': 'NYSE:BMY',
            'Gilead': 'NASDAQ:GILD',
            'Biogen': 'NASDAQ:BIIB',
            'Regeneron': 'NASDAQ:REGN',
            'Illumina': 'NASDAQ:ILMN',
            'Amgen': 'NASDAQ:AMGN',
            'Celgene': 'NASDAQ:CELG',
            'Genentech': 'NYSE:DNA',
            'Roche': 'OTCMKTS:RHHBY',
            'Novartis': 'NYSE:NVS',
            'Sanofi': 'NASDAQ:SNY',
            'GlaxoSmithKline': 'NYSE:GSK',
            'AstraZeneca': 'NASDAQ:AZN',
            'Bayer': 'OTCMKTS:BAYRY',
            'BASF': 'OTCMKTS:BASFY',
            'Siemens': 'OTCMKTS:SIEGY',
            'SAP': 'NYSE:SAP',
            'Adidas': 'OTCMKTS:ADDYY',
            'Nike': 'NYSE:NKE',
            'Lululemon': 'NASDAQ:LULU',
            'Under Armour': 'NYSE:UAA',
            'VF Corp': 'NYSE:VFC',
            'Ralph Lauren': 'NYSE:RL',
            'Coach': 'NYSE:TPG',
            'Louis Vuitton': 'OTCMKTS:LVMUY',
            'Hermès': 'OTCMKTS:HESAY',
            'Gucci': 'OTCMKTS:GUCCY',
            'Prada': 'HKEX:1913',
            'Burberry': 'OTCMKTS:BURBY',
            'L'Oréal': 'OTCMKTS:LRLCY',
            'Unilever': 'NYSE:UL',
            'Procter': 'NYSE:PG',
            'Colgate': 'NYSE:CL',
            'Kimberly': 'NYSE:KMB',
            'Estée Lauder': 'NYSE:EL',
            'Coty': 'NYSE:COTY',
            'Revlon': 'NYSE:REV',
            'Avon': 'NYSE:AVP',
            'Mary Kay': 'OTCMKTS:MKAY',
            'Sephora': 'OTCMKTS:SEPRY',
            'Ulta': 'NASDAQ:ULTA',
            'Sally Beauty': 'NYSE:SBH',
            'GameStop': 'NYSE:GME',
            'AMC': 'NYSE:AMC',
            'BlackBerry': 'NYSE:BB',
            'Nokia': 'NYSE:NOK',
            'Bed Bath': 'NASDAQ:BBBY',
            'Blockbuster': 'OTCMKTS:BLIAQ',
            'Sears': 'OTCMKTS:SHLDQ',
            'JCPenney': 'OTCMKTS:JCPNQ',
            'Macy': 'NYSE:M',
            'Nordstrom': 'NYSE:JWN',
            'Kohl': 'NYSE:KSS',
            'TJX': 'NYSE:TJX',
            'Ross': 'NASDAQ:ROST',
            'Burlington': 'NYSE:BURL',
            'Gap': 'NYSE:GPS',
            'American Eagle': 'NYSE:AEO',
            'Abercrombie': 'NYSE:ANF',
            'Urban Outfitters': 'NASDAQ:URBN',
            'Anthropologie': 'NASDAQ:URBN',
            'Free People': 'NASDAQ:URBN',
            'Zara': 'OTCMKTS:IDEXY',
            'H&M': 'OTCMKTS:HNNMY',
            'Uniqlo': 'OTCMKTS:FRCOY',
            'Forever 21': 'OTCMKTS:FVRT',
            'Hot Topic': 'NASDAQ:HOTT',
            'Spencer': 'NASDAQ:SPNC',
            'Torrid': 'NYSE:CURV',
            'Lane Bryant': 'NYSE:ASCENA',
            'Victoria Secret': 'NYSE:BBWI',
            'Bath & Body Works': 'NYSE:BBWI',
            'Bed Bath & Beyond': 'NASDAQ:BBBY',
            'Williams Sonoma': 'NYSE:WSM',
            'Pottery Barn': 'NYSE:WSM',
            'West Elm': 'NYSE:WSM',
            'Restoration Hardware': 'NYSE:RH',
            'Crate & Barrel': 'OTCMKTS:CRATB',
            'Wayfair': 'NYSE:W',
            'Overstock': 'NASDAQ:OSTK',
            'Chewy': 'NYSE:CHWY',
            'Petco': 'NASDAQ:WOOF',
            'PetSmart': 'OTCMKTS:PTSMQ'
        }

    def extract_symbols_from_text(self, text: str) -> List[str]:
        """Extract symbols from text using patterns that match scraper behavior"""
        if not text:
            return []
            
        symbols = set()
        text_upper = text.upper()
        
        # 1. Extract exchange-prefixed symbols (highest priority)
        for pattern in (self.us_patterns + self.hk_patterns + 
                       self.china_patterns + self.other_patterns):
            matches = re.findall(pattern, text_upper)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2:
                        exchange, symbol = match
                        full_symbol = f"{exchange}:{symbol}"
                        symbols.add(full_symbol)
                    elif len(match) == 1:
                        symbol = match[0]
                        if symbol not in self.exclude_words:
                            # Default to NASDAQ for unspecified US symbols
                            symbols.add(f"NASDAQ:{symbol}")
                else:
                    if match not in self.exclude_words:
                        symbols.add(f"NASDAQ:{match}")
        
        # 2. Extract from company name mentions
        for company, symbol in self.company_mappings.items():
            if company.upper() in text_upper:
                symbols.add(symbol)
        
        # 3. Clean up and validate
        valid_symbols = []
        for symbol in symbols:
            # Basic validation
            if ':' in symbol:
                exchange, ticker = symbol.split(':', 1)
                if len(ticker) >= 1 and len(ticker) <= 6:
                    valid_symbols.append(symbol)
            elif len(symbol) >= 1 and len(symbol) <= 5:
                valid_symbols.append(f"NASDAQ:{symbol}")
        
        return list(set(valid_symbols))  # Remove duplicates

    def populate_symbols_json(self, dry_run: bool = False) -> Dict:
        """Populate symbols_json field with scraper-style symbols"""
        try:
            # Get articles from search index that need symbols
            articles = NewsSearchIndex.query.filter(
                NewsSearchIndex.symbols_json.is_(None)
            ).all()
            
            logger.info(f"Found {len(articles)} articles with missing symbols_json")
            
            results = {
                'processed': 0,
                'symbols_found': 0,
                'symbols_added': 0,
                'failed': 0,
                'sample_extractions': []
            }
            
            for article in articles:
                try:
                    # Extract symbols from title and AI content
                    text_to_analyze = ""
                    if article.title:
                        text_to_analyze += article.title + " "
                    if article.ai_summary:
                        text_to_analyze += article.ai_summary + " "
                    if article.ai_insights:
                        text_to_analyze += article.ai_insights
                    
                    # Extract symbols
                    symbols = self.extract_symbols_from_text(text_to_analyze)
                    
                    # Store sample for verification
                    if len(results['sample_extractions']) < 10:
                        results['sample_extractions'].append({
                            'article_id': article.id,
                            'title': article.title[:100] + "..." if len(article.title) > 100 else article.title,
                            'symbols_found': symbols,
                            'symbol_count': len(symbols)
                        })
                    
                    results['processed'] += 1
                    results['symbols_found'] += len(symbols)
                    
                    if symbols and not dry_run:
                        # Store as JSON
                        article.symbols_json = json.dumps(symbols)
                        results['symbols_added'] += len(symbols)
                        logger.debug(f"Article {article.id}: Added {len(symbols)} symbols")
                    
                except Exception as e:
                    logger.error(f"Error processing article {article.id}: {str(e)}")
                    results['failed'] += 1
                    continue
            
            if not dry_run:
                db.session.commit()
                logger.info(f"✅ Committed changes to database")
            else:
                logger.info(f"🔍 DRY RUN - No changes made to database")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in populate_symbols_json: {str(e)}")
            if not dry_run:
                db.session.rollback()
            return {'error': str(e)}

def main():
    """Main execution function"""
    print("🔍 Scraper-Style Symbol Extraction for TrendWise")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        extractor = ScraperStyleSymbolExtractor()
        
        # Run dry run first
        print("\n📊 Running DRY RUN to preview results...")
        dry_results = extractor.populate_symbols_json(dry_run=True)
        
        if 'error' in dry_results:
            print(f"❌ Error: {dry_results['error']}")
            return
        
        print(f"\n📈 DRY RUN Results:")
        print(f"   Articles processed: {dry_results['processed']}")
        print(f"   Total symbols found: {dry_results['symbols_found']}")
        print(f"   Average symbols per article: {dry_results['symbols_found'] / dry_results['processed']:.1f}")
        print(f"   Failed articles: {dry_results['failed']}")
        
        print(f"\n🎯 Sample Extractions:")
        for sample in dry_results['sample_extractions']:
            print(f"   • Article {sample['article_id']}: {sample['symbol_count']} symbols")
            print(f"     Title: {sample['title']}")
            print(f"     Symbols: {sample['symbols_found']}")
            print()
        
        # Ask for confirmation
        if dry_results['processed'] > 0:
            response = input(f"\n✅ Apply changes to {dry_results['processed']} articles? (y/N): ")
            if response.lower() == 'y':
                print("\n🚀 Applying changes...")
                final_results = extractor.populate_symbols_json(dry_run=False)
                
                if 'error' in final_results:
                    print(f"❌ Error: {final_results['error']}")
                else:
                    print(f"\n✅ SUCCESS!")
                    print(f"   Articles processed: {final_results['processed']}")
                    print(f"   Symbols added: {final_results['symbols_added']}")
                    print(f"   Failed articles: {final_results['failed']}")
            else:
                print("\n❌ Operation cancelled")
        else:
            print("\n⚠️  No articles found that need symbol extraction")

if __name__ == "__main__":
    main() 