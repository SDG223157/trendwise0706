#!/usr/bin/env python3
"""
News Fetch Scheduler

This service automatically runs the "Fetch Top 100" news functionality every 6 hours.
It replicates the same logic as the manual "Fetch Top 100" button but runs automatically.

Features:
- Runs every 6 hours automatically
- Fetches news for top 100 symbols
- Processes symbols in chunks to avoid overwhelming APIs
- Includes retry logic and error handling
- Integrates with existing news infrastructure
- Can be started/stopped via web interface
"""

import os
import threading
import time
import schedule
import logging
import requests
import random
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Dict, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import NewsArticle
from app.utils.analysis.news_service import NewsAnalysisService

# Set up logging
logger = logging.getLogger(__name__)

class NewsFetchScheduler:
    """Automated scheduler for fetching top 100 news articles every 6 hours"""
    
    def __init__(self):
        """Initialize the news fetch scheduler"""
        self.running = False
        self.thread = None
        self.news_service = NewsAnalysisService()
        self.chunk_size = 15  # Process 15 symbols at a time (as per spec)
        self.retry_attempts = 2  # Retry failed symbols up to 2 times
        
        # Market-specific configuration
        self.market_config = {
            "CHINA_HK": {
                "articles_per_symbol": 2,
                "markets": ["CN", "HK", "GLOBAL"],
                "max_symbols_per_run": 347,  # China/Hong Kong + Global symbols
                "schedule_times": ["01:00", "04:30", "08:30"]
            },
            "US": {
                "articles_per_symbol": 5,  # US symbols get 5 articles
                "global_articles_per_symbol": 2,  # Global symbols get 2 articles
                "markets": ["US", "GLOBAL"],
                "max_symbols_per_run": 1004,  # US + Global symbols (updated to match actual implementation)
                "schedule_times": ["14:00", "17:30", "21:30"]
            }
        }
        
        # Progress tracking
        self.current_progress = {
            'is_active': False,
            'start_time': None,
            'total_symbols': 0,
            'symbols_processed': 0,
            'articles_fetched': 0,
            'symbols_failed': 0,
            'current_symbol': None,
            'current_operation': 'Idle',
            'failed_symbols': [],
            'duration_seconds': 0
        }
        
        # Last completed operation tracking (persists even when scheduler is stopped)
        self.last_completed_operation = {
            'completed_at': None,
            'total_symbols': 0,
            'symbols_processed': 0,
            'articles_fetched': 0,
            'symbols_failed': 0,
            'duration_seconds': 0,
            'failed_symbols': [],
            'status': 'never_run'  # 'never_run', 'success', 'error'
        }
        
        # Complete list of 1,102 symbols - organized by market categories
        # Market-specific scheduling: China/Hong Kong sessions vs US sessions
        self.DEFAULT_SYMBOLS = {
            # US Markets (755 symbols)
            "US": [
                # S&P 500 Technology (120 symbols)
                "NASDAQ:AAPL", "NASDAQ:MSFT", "NASDAQ:GOOGL", "NASDAQ:NVDA", "NASDAQ:META", "NASDAQ:TSLA", 
                "NASDAQ:ORCL", "NASDAQ:CRM", "NASDAQ:ADBE", "NASDAQ:INTC", "NASDAQ:QCOM", "NASDAQ:AMD", 
                "NASDAQ:AVGO", "NASDAQ:TXN", "NASDAQ:AMAT", "NASDAQ:ADI", "NASDAQ:LRCX", "NASDAQ:KLAC", 
                "NASDAQ:MRVL", "NASDAQ:MU", "NASDAQ:NXPI", "NASDAQ:MCHP", "NASDAQ:CSCO", "NASDAQ:ANET", 
                "NASDAQ:PANW", "NASDAQ:CRWD", "NASDAQ:ZS", "NASDAQ:OKTA", "NASDAQ:SNOW", "NASDAQ:DDOG", 
                "NYSE:ACN", "NYSE:IBM", "NASDAQ:CDW", "NYSE:CTSH", "NYSE:EPAM", "NASDAQ:INTU", "NASDAQ:ADSK", 
                "NASDAQ:SNPS", "NASDAQ:CDNS", "NASDAQ:ANSS", "NASDAQ:FTNT", "NASDAQ:TEAM", "NASDAQ:WDAY", 
                "NASDAQ:SPLK", "NASDAQ:VEEV", "NASDAQ:DOCU", "NASDAQ:ZM", "NASDAQ:WORK", "NASDAQ:PLTR", 
                "NASDAQ:RBLX", "NASDAQ:U", "NASDAQ:DKNG", "NASDAQ:COIN", "NASDAQ:HOOD", "NASDAQ:RIVN", 
                "NASDAQ:LCID", "NASDAQ:NKLA", "NASDAQ:SPCE", "NASDAQ:BYND", "NASDAQ:PTON", "NASDAQ:TDOC", 
                "NASDAQ:ROKU", "NASDAQ:NFLX", "NASDAQ:DIS", "NASDAQ:CMCSA", "NASDAQ:CHTR", "NASDAQ:DISH", 
                "NASDAQ:SIRI", "NASDAQ:FOXA", "NASDAQ:FOX", "NASDAQ:PARA", "NASDAQ:WBD", "NASDAQ:NWSA", 
                "NASDAQ:NEWS", "NASDAQ:MTCH", "NASDAQ:PINS", "NASDAQ:SNAP", "NASDAQ:TWTR", "NASDAQ:UBER", 
                "NASDAQ:LYFT", "NASDAQ:ABNB", "NASDAQ:DASH", "NASDAQ:GRUB", "NASDAQ:ETSY", "NASDAQ:EBAY", 
                "NASDAQ:PYPL", "NASDAQ:SQ", "NASDAQ:AFRM", "NASDAQ:UPST", "NASDAQ:SOFI", "NASDAQ:OPEN", 
                "NASDAQ:ROKU", "NASDAQ:SPOT", "NASDAQ:TWLO", "NASDAQ:OKTA", "NASDAQ:DDOG", "NASDAQ:CRWD", 
                "NASDAQ:ZS", "NASDAQ:NET", "NASDAQ:FSLY", "NASDAQ:AKAM", "NASDAQ:VRSN", "NASDAQ:TTWO", 
                "NASDAQ:EA", "NASDAQ:ATVI", "NASDAQ:RBLX", "NASDAQ:ZNGA", "NASDAQ:SEAS", "NASDAQ:NTES", 
                "NASDAQ:BILI", "NASDAQ:HUYA", "NASDAQ:DOYU", "NASDAQ:MOMO", "NASDAQ:YY", "NASDAQ:BIDU", 
                "NASDAQ:SINA", "NASDAQ:SOHU", "NASDAQ:VIPS", "NASDAQ:JD", "NASDAQ:PDD", 
                "NASDAQ:TCOM", "NASDAQ:MELI", "NASDAQ:SE", "NASDAQ:GRAB", "NASDAQ:GOJEK", "NASDAQ:DIDI",
                
                # S&P 500 Financial (80 symbols)
                "NYSE:JPM", "NYSE:BAC", "NYSE:WFC", "NYSE:C", "NYSE:GS", "NYSE:MS", "NYSE:BLK", "NYSE:V", 
                "NYSE:MA", "NYSE:AXP", "NYSE:BRK.B", "NYSE:SCHW", "NYSE:USB", "NYSE:PNC", "NYSE:TFC", 
                "NYSE:COF", "NYSE:AMT", "NYSE:CCI", "NYSE:EQIX", "NYSE:DLR", "NYSE:SPG", "NYSE:O", 
                "NYSE:PSA", "NYSE:SPGI", "NYSE:MCO", "NYSE:ICE", "NYSE:CME", "NYSE:CBOE", "NYSE:NDAQ", 
                "NYSE:IEX", "NYSE:MKTX", "NYSE:VRSK", "NYSE:MMC", "NYSE:AON", "NYSE:MSCI", "NYSE:TRV", 
                "NYSE:PGR", "NYSE:ALL", "NYSE:AIG", "NYSE:MET", "NYSE:PRU", "NYSE:AFL", "NYSE:AJG", 
                "NYSE:BRO", "NYSE:CB", "NYSE:CINF", "NYSE:EG", "NYSE:GL", "NYSE:HIG", "NYSE:L", 
                "NYSE:LNC", "NYSE:MKL", "NYSE:PFG", "NYSE:RGA", "NYSE:TMK", "NYSE:UNM", "NYSE:WRB", 
                "NYSE:ZION", "NYSE:PBCT", "NYSE:HBAN", "NYSE:RF", "NYSE:CFG", "NYSE:FITB", "NYSE:KEY", 
                "NYSE:CMA", "NYSE:NTRS", "NYSE:STT", "NYSE:BK", "NYSE:TROW", "NYSE:BEN", "NYSE:IVZ", 
                "NYSE:AMG", "NYSE:CBSH", "NYSE:WTFC", "NYSE:SIVB", "NYSE:SBNY", "NYSE:PACW", "NYSE:WAL", 
                "NYSE:EWBC", "NYSE:COLB", "NYSE:FBIZ", "NYSE:TCBI", "NYSE:BANF", "NYSE:FFIN", "NYSE:CATY",
                
                # S&P 500 Healthcare (81 symbols)
                "NYSE:JNJ", "NYSE:PFE", "NYSE:UNH", "NYSE:ABT", "NYSE:MRK", "NYSE:LLY", "NYSE:TMO", 
                "NYSE:DHR", "NYSE:BMY", "NYSE:ABBV", "NYSE:AMGN", "NASDAQ:VRTX", "NASDAQ:REGN", 
                "NASDAQ:BIIB", "NYSE:BSX", "NYSE:MDT", "NYSE:SYK", "NYSE:BDX", "NYSE:ISRG", "NYSE:CVS", 
                "NYSE:CI", "NYSE:HUM", "NYSE:HCA", "NYSE:MCK", "NYSE:CAH", "NYSE:ABC", "NYSE:COR", 
                "NYSE:DXCM", "NYSE:EW", "NYSE:HOLX", "NYSE:IDXX", "NYSE:IQV", "NYSE:MRNA", "NYSE:REGN", 
                "NYSE:RMD", "NYSE:TDOC", "NYSE:VEEV", "NYSE:WAT", "NYSE:WST", "NYSE:XRAY", "NYSE:ZBH", 
                "NYSE:ZTS", "NASDAQ:ALGN", "NASDAQ:ALXN", "NASDAQ:AMZN", "NASDAQ:BMRN", "NASDAQ:CELG", 
                "NASDAQ:CERN", "NASDAQ:CHKP", "NASDAQ:CTAS", "NASDAQ:CTLT", "NASDAQ:DLTR", "NASDAQ:ESRX", 
                "NASDAQ:EXAS", "NASDAQ:FAST", "NASDAQ:FISV", "NASDAQ:GENZ", "NASDAQ:HSIC", "NASDAQ:ILMN", 
                "NASDAQ:INCY", "NASDAQ:ISRG", "NASDAQ:KLAC", "NASDAQ:LBTYA", "NASDAQ:LILA", "NASDAQ:MXIM", 
                "NASDAQ:NTAP", "NASDAQ:NVTA", "NASDAQ:PAYX", "NASDAQ:PCAR", "NASDAQ:QRVO", "NASDAQ:SBAC", 
                "NASDAQ:SGEN", "NASDAQ:SHPG", "NASDAQ:SIRI", "NASDAQ:SWKS", "NASDAQ:TECH", "NASDAQ:TMUS", 
                "NASDAQ:ULTA", "NASDAQ:VRSK", "NASDAQ:VRTX", "NASDAQ:WDC", "NASDAQ:XLNX", "NASDAQ:XRAY",
                
                # S&P 500 Consumer Discretionary (94 symbols)
                "NYSE:HD", "NYSE:LOW", "NYSE:MCD", "NYSE:SBUX", "NYSE:NKE", "NASDAQ:TSLA", "NASDAQ:AMZN", 
                "NYSE:TGT", "NYSE:COST", "NYSE:WMT", "NYSE:DIS", "NYSE:CCL", "NYSE:RCL", "NYSE:MAR", 
                "NYSE:HLT", "NYSE:F", "NYSE:GM", "NYSE:LULU", "NASDAQ:ABNB", "NASDAQ:UBER", "NASDAQ:LYFT", 
                "NASDAQ:DASH", "NASDAQ:GRUB", "NASDAQ:ETSY", "NASDAQ:EBAY", "NASDAQ:NFLX", "NASDAQ:ROKU", 
                "NASDAQ:SPOT", "NASDAQ:TWTR", "NASDAQ:SNAP", "NASDAQ:PINS", "NASDAQ:MTCH", "NASDAQ:BMBL", 
                "NASDAQ:RBLX", "NASDAQ:TTWO", "NASDAQ:EA", "NASDAQ:ATVI", "NASDAQ:ZNGA", "NASDAQ:SEAS", 
                "NYSE:YUM", "NYSE:QSR", "NYSE:CMG", "NYSE:DNKN", "NYSE:DPZ", "NYSE:BLMN", "NYSE:CAKE", 
                "NYSE:EAT", "NYSE:FRGI", "NYSE:JACK", "NYSE:PZZA", "NYSE:RRGB", "NYSE:SHAK", "NYSE:SONO", 
                "NYSE:TXRH", "NYSE:WING", "NYSE:ZUMZ", "NYSE:AAP", "NYSE:AZO", "NYSE:ORLY", "NYSE:ADBE", 
                "NYSE:AN", "NYSE:ANF", "NYSE:AEO", "NYSE:BURL", "NYSE:CHWY", "NYSE:COTY", "NYSE:GPS", 
                "NYSE:GES", "NYSE:HBI", "NYSE:JWN", "NYSE:KSS", "NYSE:LB", "NYSE:M", "NYSE:NCLH", 
                "NYSE:NWL", "NYSE:PENN", "NYSE:PVH", "NYSE:RL", "NYSE:ROST", "NYSE:SWBI", "NYSE:TJX", 
                "NYSE:TPG", "NYSE:TSCO", "NYSE:UA", "NYSE:UAA", "NYSE:ULTA", "NYSE:VFC", "NYSE:WYNN", 
                "NYSE:XYL", "NYSE:YUMC", "NYSE:ZUMZ", "NYSE:AAP", "NYSE:AZO", "NYSE:ORLY", "NYSE:ADBE", 
                "NYSE:AN", "NYSE:ANF", "NYSE:AEO", "NYSE:BURL", "NYSE:CHWY", "NYSE:COTY", "NYSE:GPS",
                
                # S&P 500 Industrial (96 symbols)
                "NYSE:BA", "NYSE:CAT", "NYSE:GE", "NYSE:MMM", "NYSE:HON", "NYSE:UPS", "NYSE:FDX", 
                "NYSE:RTX", "NYSE:LMT", "NYSE:NOC", "NYSE:GD", "NYSE:DE", "NYSE:CMI", "NYSE:ETN", 
                "NYSE:EMR", "NYSE:ITW", "NYSE:CSX", "NYSE:UNP", "NYSE:NSC", "NASDAQ:CHRW", "NYSE:JBHT", 
                "NYSE:KNX", "NYSE:LSTR", "NYSE:ODFL", "NYSE:SAIA", "NYSE:WERN", "NYSE:XPO", "NYSE:ARCB", 
                "NYSE:CVTI", "NYSE:ECHO", "NYSE:EXPD", "NYSE:FWRD", "NYSE:HUBG", "NYSE:LOGI", "NYSE:MATX", 
                "NYSE:MRTN", "NYSE:PTSI", "NYSE:RADX", "NYSE:RLGT", "NYSE:SNDR", "NYSE:TFII", "NYSE:UHAL", 
                "NYSE:WERN", "NYSE:YELL", "NYSE:ARCB", "NYSE:CVTI", "NYSE:ECHO", "NYSE:EXPD", "NYSE:FWRD", 
                "NYSE:HUBG", "NYSE:LOGI", "NYSE:MATX", "NYSE:MRTN", "NYSE:PTSI", "NYSE:RADX", "NYSE:RLGT", 
                "NYSE:SNDR", "NYSE:TFII", "NYSE:UHAL", "NYSE:WERN", "NYSE:YELL", "NYSE:ARCB", "NYSE:CVTI", 
                "NYSE:ECHO", "NYSE:EXPD", "NYSE:FWRD", "NYSE:HUBG", "NYSE:LOGI", "NYSE:MATX", "NYSE:MRTN", 
                "NYSE:PTSI", "NYSE:RADX", "NYSE:RLGT", "NYSE:SNDR", "NYSE:TFII", "NYSE:UHAL", "NYSE:WERN", 
                "NYSE:YELL", "NYSE:ARCB", "NYSE:CVTI", "NYSE:ECHO", "NYSE:EXPD", "NYSE:FWRD", "NYSE:HUBG", 
                "NYSE:LOGI", "NYSE:MATX", "NYSE:MRTN", "NYSE:PTSI", "NYSE:RADX", "NYSE:RLGT", "NYSE:SNDR", 
                "NYSE:TFII", "NYSE:UHAL", "NYSE:WERN", "NYSE:YELL", "NYSE:ARCB", "NYSE:CVTI", "NYSE:ECHO", 
                "NYSE:EXPD", "NYSE:FWRD", "NYSE:HUBG", "NYSE:LOGI", "NYSE:MATX", "NYSE:MRTN", "NYSE:PTSI",
                
                # S&P 500 Energy (59 symbols)
                "NYSE:XOM", "NYSE:CVX", "NYSE:COP", "NYSE:EOG", "NYSE:SLB", "NYSE:HAL", "NYSE:PSX", 
                "NYSE:VLO", "NYSE:MPC", "NYSE:HES", "NYSE:OXY", "NYSE:DVN", "NYSE:FANG", "NYSE:EPD", 
                "NYSE:ET", "NYSE:WMB", "NYSE:OKE", "NYSE:KMI", "NYSE:NEE", "NASDAQ:FSLR", "NYSE:ENPH", 
                "NYSE:SEDG", "NYSE:PLUG", "NYSE:BE", "NYSE:BLDP", "NYSE:SPWR", "NYSE:RUN", "NYSE:NOVA", 
                "NYSE:CSIQ", "NYSE:JKS", "NYSE:DQ", "NYSE:TSL", "NYSE:MAXN", "NYSE:ARRY", "NYSE:VSLR", 
                "NYSE:PEGI", "NYSE:BEP", "NYSE:NEP", "NYSE:CWEN", "NYSE:AES", "NYSE:CNP", "NYSE:CMS", 
                "NYSE:D", "NYSE:DTE", "NYSE:DUK", "NYSE:ED", "NYSE:EIX", "NYSE:ETR", "NYSE:EXC", 
                "NYSE:FE", "NYSE:NI", "NYSE:NRG", "NYSE:PCG", "NYSE:PEG", "NYSE:PNW", "NYSE:PPL", 
                "NYSE:SO", "NYSE:SRE", "NYSE:VST", "NYSE:WEC", "NYSE:XEL",
                
                # S&P 500 Consumer Staples (54 symbols)
                "NYSE:PG", "NYSE:KO", "NYSE:PEP", "NYSE:WMT", "NYSE:COST", "NYSE:KR", "NYSE:CL", 
                "NYSE:CLX", "NYSE:EL", "NYSE:KMB", "NYSE:TSN", "NYSE:GIS", "NYSE:K", "NYSE:CPB", 
                "NYSE:HSY", "NYSE:MDLZ", "NYSE:PM", "NYSE:MO", "NYSE:STZ", "NYSE:BF.B", "NYSE:DEO", 
                "NYSE:TAP", "NYSE:SAM", "NYSE:MNST", "NYSE:KDP", "NYSE:COCA", "NYSE:CCEP", "NYSE:COKE", 
                "NYSE:FMX", "NYSE:ABEV", "NYSE:BREW", "NYSE:CELH", "NYSE:FIZZ", "NYSE:KOFK", "NYSE:REYN", 
                "NYSE:UNFI", "NYSE:SJM", "NYSE:HRL", "NYSE:CAG", "NYSE:MKC", "NYSE:SEIC", "NYSE:LW", 
                "NYSE:POST", "NYSE:LANC", "NYSE:JJSF", "NYSE:CALM", "NYSE:SAFM", "NYSE:PPC", "NYSE:SENEA", 
                "NYSE:SENEB", "NYSE:USFD", "NYSE:PFGC", "NYSE:CHEF",
                
                # S&P 500 Utilities (48 symbols)
                "NYSE:NEE", "NYSE:DUK", "NYSE:SO", "NYSE:D", "NYSE:EXC", "NYSE:XEL", "NYSE:SRE", 
                "NYSE:PEG", "NYSE:EIX", "NYSE:ED", "NYSE:ETR", "NYSE:FE", "NYSE:AEE", "NYSE:CMS", 
                "NYSE:DTE", "NYSE:AWK", "NYSE:ATO", "NYSE:CNP", "NYSE:ES", "NYSE:EVRG", "NYSE:LNT", 
                "NYSE:NI", "NYSE:NRG", "NYSE:OGE", "NYSE:PCG", "NYSE:PNW", "NYSE:PPL", "NYSE:WEC", 
                "NYSE:AES", "NYSE:CEG", "NYSE:VST", "NYSE:WTRG", "NYSE:UGI", "NYSE:SR", "NYSE:SWX", 
                "NYSE:NWE", "NYSE:AVA", "NYSE:BKH", "NYSE:IDA", "NYSE:MDU", "NYSE:NJR", "NYSE:NWN", 
                "NYSE:ORA", "NYSE:POR", "NYSE:SJI", "NYSE:UTL", "NYSE:WGL",
                
                # S&P 500 Materials (60 symbols)
                "NYSE:APD", "NYSE:LIN", "NYSE:DD", "NYSE:DOW", "NYSE:LYB", "NYSE:ECL", "NYSE:SHW", 
                "NYSE:PPG", "NYSE:NEM", "NYSE:FCX", "NYSE:NUE", "NYSE:STLD", "NYSE:VMC", "NYSE:MLM", 
                "NYSE:PKG", "NYSE:IP", "NYSE:BALL", "NYSE:CCK", "NYSE:AVY", "NYSE:BLL", "NYSE:SEE", 
                "NYSE:SON", "NYSE:WRK", "NYSE:CF", "NYSE:FMC", "NYSE:MOS", "NYSE:IFF", "NYSE:ALB", 
                "NYSE:FUL", "NYSE:RPM", "NYSE:VVV", "NYSE:ASH", "NYSE:AXTA", "NYSE:CE", "NYSE:CRH", 
                "NYSE:EMN", "NYSE:ESI", "NYSE:HUN", "NYSE:KRA", "NYSE:LYFT", "NYSE:OLN", "NYSE:PX", 
                "NYSE:SXT", "NYSE:TROX", "NYSE:WLK", "NYSE:AA", "NYSE:ACH", "NYSE:ARNC", "NYSE:ATI", 
                "NYSE:BTU", "NYSE:CENX", "NYSE:CX", "NYSE:HCC", "NYSE:KALU", "NYSE:MTC", "NYSE:RGLD", 
                "NYSE:SCCO", "NYSE:TECK", "NYSE:UEC", "NYSE:WPM", "NYSE:X",
                
                # S&P 500 Communication (47 symbols)
                "NYSE:VZ", "NYSE:T", "NYSE:DIS", "NASDAQ:NFLX", "NYSE:CMCSA", "NYSE:CHTR", "NASDAQ:GOOGL", 
                "NASDAQ:GOOG", "NASDAQ:META", "NYSE:LYV", "NYSE:OMC", "NYSE:IPG", "NASDAQ:SNAP", "NASDAQ:PINS", 
                "NASDAQ:TWTR", "NASDAQ:MTCH", "NASDAQ:BMBL", "NASDAQ:LBRDA", "NASDAQ:LBRDK", "NASDAQ:LSXMA", 
                "NASDAQ:LSXMB", "NASDAQ:LSXMK", "NASDAQ:SIRI", "NASDAQ:FOXA", "NASDAQ:FOX", "NASDAQ:PARA", 
                "NASDAQ:WBD", "NASDAQ:NWSA", "NASDAQ:NEWS", "NYSE:TMUS", "NYSE:DISH", "NYSE:LILAK", 
                "NYSE:LILA", "NYSE:LBRDA", "NYSE:LBRDK", "NYSE:LSXMA", "NYSE:LSXMB", "NYSE:LSXMK", 
                "NYSE:SIRI", "NYSE:FOXA", "NYSE:FOX", "NYSE:PARA", "NYSE:WBD", "NYSE:NWSA", "NYSE:NEWS", 
                "NYSE:TMUS", "NYSE:DISH", "NYSE:LILAK",
                
                # Major ETFs & Indices (71 symbols)
                "TVC:SPX", "TVC:DJI", "TVC:NDX", "TVC:RUT", "TVC:VIX", "NYSE:SPY", "NASDAQ:QQQ", 
                "NYSE:VTI", "NYSE:VOO", "NYSE:IVV", "NYSE:VEA", "NYSE:VWO", "NYSE:XLE", "NYSE:XLF", 
                "NYSE:XLK", "NYSE:XLV", "NYSE:XLI", "NYSE:XLU", "NYSE:XLP", "NYSE:XLY", "NYSE:XLB", 
                "NYSE:XLRE", "NYSE:XLC", "NYSE:TLT", "NYSE:AGG", "NYSE:BND", "NYSE:LQD", "NYSE:HYG", 
                "NYSE:JNK", "NYSE:EMB", "NYSE:TIP", "NYSE:GLD", "NYSE:SLV", "NYSE:USO", "NYSE:UNG", 
                "NYSE:DBA", "NYSE:DBC", "NYSE:ARKK", "NYSE:ARKQ", "NYSE:ARKW", "NYSE:ARKG", "NYSE:ARKF", 
                "NYSE:ICLN", "NYSE:CLEAN", "NYSE:KWEB", "NYSE:FXI", "NYSE:MCHI", "NYSE:EWJ", "NYSE:EWZ", 
                "NYSE:EWY", "NYSE:INDA", "NYSE:EWT", "NYSE:EWG", "NYSE:EWU", "NYSE:VGK", "NYSE:VPL", 
                "NYSE:VGE", "NYSE:VNQ", "NYSE:VTEB", "NYSE:VMOT", "NYSE:VGIT", "NYSE:VGSH", "NYSE:VCSH", 
                "NYSE:VCIT", "NYSE:VXUS", "NYSE:VTIAX", "NYSE:VBTLX", "NYSE:VTSAX", "NYSE:VFWAX", 
                "NYSE:VTWAX", "NYSE:VTIAX", "NYSE:VBTLX", "NYSE:VTSAX", "NYSE:VFWAX", "NYSE:VTWAX",
            ],
            
            # Hong Kong Markets (71 symbols)
            "HK": [
                # Tech Giants (20 symbols)
                "HKEX:700", "HKEX:9988", "HKEX:9618", "HKEX:3690", "HKEX:1024", "HKEX:9999", 
                "HKEX:1833", "HKEX:2382", "HKEX:1347", "HKEX:285", "HKEX:3888", "HKEX:9626", 
                "HKEX:1109", "HKEX:3958", "HKEX:2013", "HKEX:3333", "HKEX:1458", "HKEX:2518", 
                "HKEX:2020", "HKEX:1193",
                
                # Financial Services (20 symbols)
                "HKEX:5", "HKEX:939", "HKEX:1398", "HKEX:3988", "HKEX:1288", "HKEX:3968", 
                "HKEX:1988", "HKEX:2388", "HKEX:1359", "HKEX:6030", "HKEX:1658", "HKEX:1618", 
                "HKEX:1336", "HKEX:2628", "HKEX:2318", "HKEX:1113", "HKEX:1928", "HKEX:1818", 
                "HKEX:1299", "HKEX:1448",
                
                # Consumer & Retail (19 symbols)
                "HKEX:1", "HKEX:6", "HKEX:83", "HKEX:1038", "HKEX:2319", "HKEX:2269", 
                "HKEX:1876", "HKEX:1972", "HKEX:2282", "HKEX:1478", "HKEX:1128", "HKEX:1368", 
                "HKEX:1766", "HKEX:1234", "HKEX:1177", "HKEX:1919", "HKEX:2888", "HKEX:1093", 
                "HKEX:3319",
                
                # Infrastructure & Utilities (12 symbols)
                "HKEX:2", "HKEX:3", "HKEX:1072", "HKEX:1177", "HKEX:1548", "HKEX:1800", 
                "HKEX:1768", "HKEX:1816", "HKEX:1052", "HKEX:1186", "HKEX:1208", "HKEX:1299",
            ],
            
            # China Markets (118 symbols)
            "CN": [
                # Shanghai Stock Exchange (58 symbols)
                "SSE:600519", "SSE:600036", "SSE:601398", "SSE:600276", "SSE:600585", "SSE:600809", 
                "SSE:600588", "SSE:600887", "SSE:600745", "SSE:600196", "SSE:601012", "SSE:600918", 
                "SSE:600570", "SSE:601318", "SSE:600563", "SSE:600297", "SSE:600406", "SSE:600438", 
                "SSE:600048", "SSE:600871", "SSE:601939", "SSE:601988", "SSE:600000", "SSE:600015", 
                "SSE:600016", "SSE:601166", "SSE:601009", "SSE:600926", "SSE:601169", "SSE:601128", 
                "SSE:600919", "SSE:601998", "SSE:601916", "SSE:600837", "SSE:601818", "SSE:600958", 
                "SSE:600340", "SSE:601328", "SSE:601857", "SSE:600028", "SSE:601668", "SSE:600019", 
                "SSE:601088", "SSE:600362", "SSE:600348", "SSE:600150", "SSE:600188", "SSE:600583", 
                "SSE:600782", "SSE:600795", "SSE:600489", "SSE:600026", "SSE:600157", "SSE:600121", 
                "SSE:600058", "SSE:600111", "SSE:600219", "SSE:600395",
                
                # Shenzhen Stock Exchange (60 symbols)
                "SZSE:000858", "SZSE:002415", "SZSE:000002", "SZSE:002594", "SZSE:000001", "SZSE:002230", 
                "SZSE:002241", "SZSE:000660", "SZSE:002202", "SZSE:000063", "SZSE:000725", "SZSE:002714", 
                "SZSE:000776", "SZSE:002352", "SZSE:000100", "SZSE:000568", "SZSE:002508", "SZSE:000938", 
                "SZSE:002129", "SZSE:000069", "SZSE:000333", "SZSE:000651", "SZSE:000895", "SZSE:000876", 
                "SZSE:000157", "SZSE:002304", "SZSE:000596", "SZSE:000766", "SZSE:000027", "SZSE:000623", 
                "SZSE:000338", "SZSE:000402", "SZSE:000869", "SZSE:000537", "SZSE:000617", "SZSE:000709", 
                "SZSE:000951", "SZSE:000729", "SZSE:000792", "SZSE:000912", "SZSE:000661", "SZSE:002007", 
                "SZSE:000999", "SZSE:002252", "SZSE:000513", "SZSE:002022", "SZSE:002038", "SZSE:000739", 
                "SZSE:002821", "SZSE:000788", "SZSE:002317", "SZSE:000423", "SZSE:002727", "SZSE:002332", 
                "SZSE:000078", "SZSE:002294", "SZSE:002399", "SZSE:002001", "SZSE:002393", "SZSE:002030",
            ],
            
            # Global Markets (158 symbols)
            "GLOBAL": [
                # Commodities & Futures (34 symbols)
                "COMEX:GC1!", "COMEX:SI1!", "COMEX:PA1!", "NYMEX:PL1!", "NYMEX:CL1!", "NYMEX:NG1!", 
                "NYMEX:RB1!", "NYMEX:HO1!", "ICE:B1!", "CBOT:ZC1!", "CBOT:ZS1!", "CBOT:ZW1!", 
                "CBOT:ZM1!", "CBOT:ZL1!", "ICE:KC1!", "ICE:SB1!", "ICE:CT1!", "ICE:CC1!", 
                "ICE:OJ1!", "COMEX:HG1!", "LME:AH1!", "LME:CA1!", "LME:PB1!", "LME:SN1!", 
                "LME:ZS1!", "LME:NI1!", "SHFE:AL1!", "SHFE:ZN1!", "SHFE:CU1!", "CME:LE1!", 
                "CME:GF1!", "CME:HE1!", "CME:FC1!", "CME:DA1!",
                
                # Cryptocurrency (32 symbols)
                "BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:BNBUSDT", "BINANCE:ADAUSDT", "BINANCE:SOLUSDT", 
                "BINANCE:XRPUSDT", "BINANCE:DOTUSDT", "BINANCE:DOGENUSDT", "BINANCE:AVAXUSDT", "BINANCE:MATICUSDT", 
                "BINANCE:LINKUSDT", "BINANCE:LTCUSDT", "BINANCE:UNIUSDT", "BINANCE:ATOMUSDT", "BINANCE:XLMUSDT", 
                "BINANCE:VETUSDT", "BINANCE:FILUSDT", "BINANCE:TRXUSDT", "BINANCE:ETCUSDT", "BINANCE:THETAUSDT", 
                "BINANCE:ALGOUSDT", "BINANCE:ICPUSDT", "BINANCE:NEARUSDT", "BINANCE:FLOWUSDT", "BINANCE:SANDUSDT", 
                "BINANCE:MANAUSDT", "BINANCE:GALAUSDT", "BINANCE:AXSUSDT", "BINANCE:AAVEUSDT", "BINANCE:COMPUSDT", 
                "BINANCE:MKRUSDT", "BINANCE:SUSHIUSDT",
                
                # Forex Markets (45 symbols)
                "FX:EURUSD", "FX:GBPUSD", "FX:USDJPY", "FX:USDCHF", "FX:USDCAD", "FX:AUDUSD", 
                "FX:NZDUSD", "FX:EURGBP", "FX:EURJPY", "FX:EURCHF", "FX:EURNZD", "FX:EURAUD", 
                "FX:GBPJPY", "FX:GBPCHF", "FX:GBPCAD", "FX:CHFJPY", "FX:CADJPY", "FX:AUDJPY", 
                "FX:NZDJPY", "FX:AUDNZD", "FX:USDCNY", "FX:USDHKD", "FX:USDSGD", "FX:USDKRW", 
                "FX:USDINR", "FX:USDBRL", "FX:USDMXN", "FX:USDZAR", "FX:USDTRY", "FX:USDRUB", 
                "FX:USDTHB", "FX:USDPHP", "FX:USDIDR", "FX:USDMYR", "FX:USDVND", "FX:USDNOK", 
                "FX:USDSEK", "FX:USDDKK", "FX:USDPLN", "FX:USDCZK", "FX:USDHUF", "FX:USDRON", 
                "FX:USDBGN", "FX:USDHRK", "FX:USDARGS",
                
                # Global Indices (47 symbols)
                "TVC:UKX", "TVC:DAX", "TVC:CAC", "TVC:SX5E", "TVC:IBEX", "TVC:MIB", "TVC:AEX", 
                "TVC:OMX", "TVC:WIG", "TVC:PX1", "TVC:BUX", "TVC:BELEX15", "TVC:NI225", "TVC:HSI", 
                "TVC:SHCOMP", "TVC:SENSEX", "TVC:KOSPI", "TVC:TWII", "TVC:ASX", "TVC:NZX50", 
                "TVC:SET", "TVC:KLSE", "TVC:IDX", "TVC:PSI", "TVC:JCI", "TVC:STI", "TVC:VNINDEX", 
                "TVC:RTS", "TVC:BVSP", "TVC:MERV", "TVC:IPC", "TVC:COLCAP", "TVC:IPSA", "TVC:IGPA", 
                "TVC:BOVESPA", "TVC:MEXBOL", "TVC:CHILE65", "TVC:TA125", "TVC:EGX30", "TVC:CASE30", 
                "TVC:NGSE30", "TVC:DSMD", "TVC:ADSMI", "TVC:QE20", "TVC:BSE", "TVC:MSX30", "TVC:TUNINDEX",
            ]
        }
        
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        
    def start(self):
        """Start the automated news fetch scheduler"""
        if self.running:
            logger.warning("News fetch scheduler is already running")
            return False
            
        try:
            # Clear any existing jobs
            schedule.clear()
            
            # Schedule market-based timing (6 times daily)
            self._schedule_market_times()
            
            # Start the scheduler thread
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=False, name="NewsFetchScheduler")
            self.thread.start()
            
            logger.info("🚀 News fetch scheduler started - will run at market opening/closing times")
            
            # Run immediately when scheduler starts
            logger.info("⚡ Running initial fetch job immediately...")
            initial_thread = threading.Thread(
                target=self._run_initial_job, 
                daemon=False, 
                name="NewsSchedulerInitial"
            )
            initial_thread.start()
            logger.info("⚡ Initial fetch job started in background")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start news fetch scheduler: {str(e)}")
            self.running = False
            return False
    
    def stop(self):
        """Stop the automated news fetch scheduler"""
        if not self.running:
            logger.warning("News fetch scheduler is not running")
            return False
            
        try:
            self.running = False
            schedule.clear()
            
            if self.thread and self.thread.is_alive():
                # Give the thread time to finish current iteration
                self.thread.join(timeout=5)
            
            logger.info("🛑 News fetch scheduler stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping news fetch scheduler: {str(e)}")
            return False
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("📅 News fetch scheduler thread started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)
        
        logger.info("📅 News fetch scheduler thread stopped")
    
    def _schedule_market_times(self):
        """Schedule market-specific news fetch at optimal times"""
        # Clear any existing schedules
        schedule.clear()
        
        # China/Hong Kong + Global Markets Sessions
        # These sessions process CN, HK, and GLOBAL symbols (347 total)
        schedule.every().day.at("01:00").do(self._run_scheduled_job, market_session="CHINA_HK", session_name="China/Hong Kong Market Open")
        schedule.every().day.at("04:30").do(self._run_scheduled_job, market_session="CHINA_HK", session_name="China/Hong Kong Mid-Session")
        schedule.every().day.at("08:30").do(self._run_scheduled_job, market_session="CHINA_HK", session_name="China/Hong Kong Market Close")
        
        # US + Global Markets Sessions
        # These sessions process US and GLOBAL symbols (913 total)
        schedule.every().day.at("14:00").do(self._run_scheduled_job, market_session="US", session_name="US Pre-Market")
        schedule.every().day.at("17:30").do(self._run_scheduled_job, market_session="US", session_name="US Mid-Session")
        schedule.every().day.at("21:30").do(self._run_scheduled_job, market_session="US", session_name="US After-Hours")
        
        logger.info("📅 Market-specific scheduling configured:")
        logger.info("  🇨🇳 China/Hong Kong Sessions (347 symbols):")
        logger.info("    • 01:00 UTC - China/Hong Kong Market Open")
        logger.info("    • 04:30 UTC - China/Hong Kong Mid-Session")
        logger.info("    • 08:30 UTC - China/Hong Kong Market Close")
        logger.info("  🇺🇸 US Sessions (1004 symbols):")  # Updated to reflect actual count
        logger.info("    • 14:00 UTC - US Pre-Market")
        logger.info("    • 17:30 UTC - US Mid-Session")
        logger.info("    • 21:30 UTC - US After-Hours")
        logger.info("  🌍 Global symbols included in all sessions")
        logger.info("  📊 Maximum 15,114 articles per day")  # Updated calculation

    def _run_scheduled_job(self, market_session="Unknown", session_name="Unknown"):
        """Run the scheduled fetch job with proper Flask app context"""
        try:
            logger.info(f"⏰ Scheduled news fetch job triggered - {session_name}")
            
            # Ensure we have proper Flask app context
            if hasattr(self, 'app') and self.app:
                with self.app.app_context():
                    result = self.run_fetch_job(market_session=market_session)
                    logger.info(f"⏰ {session_name} job completed: {result}")
            else:
                # Fallback: try to get or create app context
                try:
                    from flask import current_app
                    result = self.run_fetch_job(market_session=market_session)
                    logger.info(f"⏰ {session_name} job completed: {result}")
                except RuntimeError:
                    # No app context available, create one
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        result = self.run_fetch_job(market_session=market_session)
                        logger.info(f"⏰ {session_name} job completed: {result}")
                        
        except Exception as e:
            logger.error(f"❌ Error in {session_name} fetch job: {str(e)}", exc_info=True)
    
    def _determine_current_market_session(self) -> str:
        """Intelligently determine which market session to run based on nearest scheduled time"""
        current_time = datetime.now()
        current_time_str = current_time.strftime('%H:%M UTC')
        
        # Define all scheduled times with their session types
        scheduled_times = [
            (1, 0, "CHINA_HK", "China/HK Market Open"),
            (4, 30, "CHINA_HK", "China/HK Mid-Session"),
            (8, 30, "CHINA_HK", "China/HK Market Close"),
            (14, 0, "US", "US Pre-Market"),
            (17, 30, "US", "US Mid-Session"),
            (21, 30, "US", "US After-Hours"),
        ]
        
        # Define market session windows (30 minutes before and after each scheduled time)
        china_hk_windows = [
            (0, 30, 2, 0),    # 00:30-02:00 for 01:00 session
            (4, 0, 5, 30),    # 04:00-05:30 for 04:30 session  
            (8, 0, 9, 30),    # 08:00-09:30 for 08:30 session
        ]
        
        us_windows = [
            (13, 30, 15, 0),  # 13:30-15:00 for 14:00 session
            (17, 0, 18, 30),  # 17:00-18:30 for 17:30 session
            (21, 0, 22, 30),  # 21:00-22:30 for 21:30 session
        ]
        
        # Check if current time falls within any China/HK window
        for start_hour, start_min, end_hour, end_min in china_hk_windows:
            if (current_time.hour > start_hour or (current_time.hour == start_hour and current_time.minute >= start_min)) and \
               (current_time.hour < end_hour or (current_time.hour == end_hour and current_time.minute <= end_min)):
                logger.info(f"🇨🇳 {current_time_str} falls within China/HK session window")
                return "CHINA_HK"
        
        # Check if current time falls within any US window
        for start_hour, start_min, end_hour, end_min in us_windows:
            if (current_time.hour > start_hour or (current_time.hour == start_hour and current_time.minute >= start_min)) and \
               (current_time.hour < end_hour or (current_time.hour == end_hour and current_time.minute <= end_min)):
                logger.info(f"🇺🇸 {current_time_str} falls within US session window")
                return "US"
        
        # If not in any active window, find the nearest scheduled time
        min_diff = float('inf')
        nearest_session = None
        nearest_session_name = None
        
        for hour, minute, session_type, session_name in scheduled_times:
            # Create datetime for this scheduled time today
            scheduled_today = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Calculate time difference (can be positive or negative)
            diff = (scheduled_today - current_time).total_seconds()
            
            # If the scheduled time is in the past today, also consider tomorrow
            if diff < 0:
                scheduled_tomorrow = scheduled_today + timedelta(days=1)
                diff_tomorrow = (scheduled_tomorrow - current_time).total_seconds()
                
                # Choose the smaller absolute difference
                if abs(diff_tomorrow) < abs(diff):
                    diff = diff_tomorrow
                    scheduled_time = scheduled_tomorrow
                else:
                    scheduled_time = scheduled_today
            else:
                scheduled_time = scheduled_today
            
            # Check if this is the nearest time
            if abs(diff) < min_diff:
                min_diff = abs(diff)
                nearest_session = session_type
                nearest_session_name = session_name
                nearest_time = scheduled_time
        
        # Format the time difference for logging
        hours = int(min_diff // 3600)
        minutes = int((min_diff % 3600) // 60)
        
        if nearest_time < current_time:
            time_desc = f"{hours}h {minutes}m ago"
            logger.info(f"🕐 {current_time_str} - Nearest session: {nearest_session_name} ({time_desc})")
        else:
            time_desc = f"{hours}h {minutes}m ahead"
            logger.info(f"🕐 {current_time_str} - Nearest session: {nearest_session_name} ({time_desc})")
        
        return nearest_session

    def _run_initial_job(self):
        """Run the initial fetch job when scheduler starts with intelligent market session selection"""
        try:
            # Intelligent market session selection based on current UTC time
            current_market_session = self._determine_current_market_session()
            
            logger.info(f"⚡ Initial news fetch job triggered (scheduler start)")
            logger.info(f"🎯 Current time: {datetime.now().strftime('%H:%M UTC')} - Selected market session: {current_market_session}")
            
            # Ensure we have proper Flask app context
            if hasattr(self, 'app') and self.app:
                with self.app.app_context():
                    result = self.run_fetch_job(market_session=current_market_session)
                    logger.info(f"⚡ Initial {current_market_session} job completed: {result}")
            else:
                # Fallback: try to get or create app context
                try:
                    from flask import current_app
                    result = self.run_fetch_job(market_session=current_market_session)
                    logger.info(f"⚡ Initial {current_market_session} job completed: {result}")
                except RuntimeError:
                    # No app context available, create one
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        result = self.run_fetch_job(market_session=current_market_session)
                        logger.info(f"⚡ Initial {current_market_session} job completed: {result}")
                        
        except Exception as e:
            logger.error(f"❌ Error in initial fetch job: {str(e)}", exc_info=True)
    
    @contextmanager
    def get_db_session(self):
        """Get database session with proper Flask app context"""
        try:
            # Import here to avoid circular imports
            from flask import current_app
            from app import create_app, db
            
            # Get the current app or create one if needed
            try:
                app = current_app._get_current_object()
            except RuntimeError:
                # No app context available, create one
                app = create_app()
            
            # Run with proper application context
            with app.app_context():
                yield db.session
                
        except Exception as e:
            logger.error(f"Error getting database session: {str(e)}")
            raise
    
    def run_fetch_job(self, market_session="Unknown"):
        """Run the automated news fetch job with market-specific processing"""
        try:
            logger.info(f"🤖 Starting automated news fetch job for {market_session} session...")
            
            # Safety check: ensure news service is available
            if not hasattr(self, 'news_service') or self.news_service is None:
                logger.error("❌ News service not initialized!")
                return {
                    'status': 'error',
                    'message': 'News service not initialized'
                }
            
            # Get market-specific configuration
            if market_session not in self.market_config:
                logger.error(f"❌ Unknown market session: {market_session}")
                return {
                    'status': 'error',
                    'message': f'Unknown market session: {market_session}'
                }
            
            config = self.market_config[market_session]
            start_time = datetime.now()
            
            # Get symbols for this market session
            selected_symbols = self._get_market_symbols(market_session)
            
            if not selected_symbols:
                logger.error(f"❌ No symbols found for market session: {market_session}")
                return {
                    'status': 'error',
                    'message': f'No symbols found for market session: {market_session}'
                }
            
            # Initialize progress tracking
            self.current_progress.update({
                'is_active': True,
                'start_time': start_time,
                'total_symbols': len(selected_symbols),
                'symbols_processed': 0,
                'articles_fetched': 0,
                'symbols_failed': 0,
                'current_symbol': None,
                'current_operation': f'Initializing {market_session} session',
                'failed_symbols': [],
                'duration_seconds': 0,
                'market_session': market_session
            })
            
            # Clean up articles with no content first
            self.current_progress['current_operation'] = 'Cleaning up empty articles'
            self._cleanup_empty_articles()
            
            # Shuffle symbols for variety
            self.current_progress['current_operation'] = 'Preparing symbols list'
            shuffled_symbols = self._shuffle_symbols(selected_symbols)
            
            logger.info(f"📋 {market_session} session: {len(shuffled_symbols)} symbols selected")
            logger.info(f"🎲 First 10 symbols: {shuffled_symbols[:10]}")
            
            # Process symbols in chunks
            all_articles = []
            failed_symbols = []
            processed_count = 0
            
            # Process in chunks
            chunk_size = self.chunk_size
            chunks = [shuffled_symbols[i:i + chunk_size] for i in range(0, len(shuffled_symbols), chunk_size)]
            
            logger.info(f"🔄 Processing {len(chunks)} chunks of {chunk_size} symbols each")
            self.current_progress['current_operation'] = f'Processing {len(chunks)} chunks for {market_session}'
            
            for chunk_idx, chunk in enumerate(chunks):
                chunk_start_time = datetime.now()
                logger.info(f"🔄 Processing chunk {chunk_idx + 1}/{len(chunks)}: {chunk}")
                
                # Update progress for chunk
                self.current_progress['current_operation'] = f'Processing chunk {chunk_idx + 1}/{len(chunks)} ({market_session})'
                
                chunk_processed = 0
                chunk_failed = 0
                
                for symbol_idx, symbol_info in enumerate(chunk):
                    try:
                        symbol = symbol_info['symbol']
                        articles_limit = symbol_info['articles_limit']
                        
                        # Update current symbol being processed
                        self.current_progress['current_symbol'] = symbol
                        self.current_progress['current_operation'] = f'Processing {symbol} ({market_session})'
                        
                        # Update duration
                        elapsed = (datetime.now() - start_time).total_seconds()
                        self.current_progress['duration_seconds'] = elapsed
                        
                        logger.info(f"🎯 Processing symbol {symbol_idx + 1}/{len(chunk)} in chunk {chunk_idx + 1}: {symbol} (limit: {articles_limit})")
                        
                        # Fetch articles for this symbol
                        articles = self._fetch_symbol_with_retry(symbol, articles_limit)
                        if articles:
                            all_articles.extend(articles)
                            chunk_processed += 1
                            processed_count += 1
                            
                            # Update progress counters
                            self.current_progress['symbols_processed'] = processed_count
                            self.current_progress['articles_fetched'] = len(all_articles)
                            
                            logger.info(f"✅ Symbol {symbol} added {len(articles)} articles (total: {len(all_articles)})")
                        else:
                            failed_symbols.append(symbol)
                            chunk_failed += 1
                            
                            # Update failed counters
                            self.current_progress['symbols_failed'] = len(failed_symbols)
                            self.current_progress['failed_symbols'] = failed_symbols[-10:]  # Keep last 10 for display
                            
                            logger.warning(f"⚠️ Symbol {symbol} yielded no articles")
                            
                    except Exception as e:
                        symbol = symbol_info.get('symbol', 'unknown')
                        failed_symbols.append(symbol)
                        chunk_failed += 1
                        
                        # Update failed counters
                        self.current_progress['symbols_failed'] = len(failed_symbols)
                        self.current_progress['failed_symbols'] = failed_symbols[-10:]  # Keep last 10 for display
                        
                        logger.error(f"❌ Error processing symbol {symbol}: {str(e)}")
                
                chunk_end_time = datetime.now()
                chunk_duration = (chunk_end_time - chunk_start_time).total_seconds()
                logger.info(f"📊 Chunk {chunk_idx + 1} completed: {chunk_processed} success, {chunk_failed} failed, {chunk_duration:.1f}s")
                
                # Add a small delay between chunks to avoid overwhelming the system
                if chunk_idx < len(chunks) - 1:  # Don't sleep after the last chunk
                    self.current_progress['current_operation'] = 'Brief pause between chunks'
                    logger.info("⏳ Brief pause between chunks...")
                    time.sleep(1)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Mark completion
            self.current_progress.update({
                'is_active': False,
                'current_operation': f'Completed {market_session} session',
                'current_symbol': None,
                'duration_seconds': duration.total_seconds()
            })
            
            # Store completed operation results for historical tracking
            self.last_completed_operation.update({
                'completed_at': end_time,
                'total_symbols': len(selected_symbols),
                'symbols_processed': processed_count,
                'articles_fetched': len(all_articles),
                'symbols_failed': len(failed_symbols),
                'duration_seconds': duration.total_seconds(),
                'failed_symbols': failed_symbols[:10],  # Keep last 10 for display
                'status': 'success',
                'market_session': market_session
            })
            
            logger.info(f"🏁 {market_session} session completed in {duration.total_seconds():.1f} seconds")
            logger.info(f"📊 Final stats: {len(all_articles)} articles, {processed_count} symbols processed, {len(failed_symbols)} failed")
            
            if failed_symbols:
                logger.warning(f"❌ Failed symbols: {failed_symbols[:10]}{'...' if len(failed_symbols) > 10 else ''}")
            
            return {
                'status': 'success',
                'articles_fetched': len(all_articles),
                'symbols_processed': processed_count,
                'symbols_failed': len(failed_symbols),
                'duration_seconds': duration.total_seconds(),
                'failed_symbols': failed_symbols[:20],  # Limit for response size
                'market_session': market_session
            }
            
        except Exception as e:
            # Mark error in progress
            self.current_progress.update({
                'is_active': False,
                'current_operation': f'Error in {market_session}: {str(e)}',
                'current_symbol': None
            })
            
            # Store error status in last completed operation
            self.last_completed_operation.update({
                'completed_at': datetime.now(),
                'status': 'error',
                'error_message': str(e),
                'market_session': market_session
            })
            
            logger.error(f"❌ Critical error in {market_session} fetch job: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'market_session': market_session
            }
    
    def _get_market_symbols(self, market_session: str) -> List[Dict]:
        """Get symbols for a specific market session with proper articles per symbol configuration"""
        try:
            if market_session not in self.market_config:
                logger.error(f"Unknown market session: {market_session}")
                return []
            
            config = self.market_config[market_session]
            symbol_list = []
            
            # Iterate through the markets for this session
            for market_code in config['markets']:
                if market_code not in self.DEFAULT_SYMBOLS:
                    logger.warning(f"Market code {market_code} not found in DEFAULT_SYMBOLS")
                    continue
                
                market_symbols = self.DEFAULT_SYMBOLS[market_code]
                
                # Determine articles per symbol based on market type
                if market_session == "US":
                    if market_code == "US":
                        articles_per_symbol = config['articles_per_symbol']  # 5 for US symbols
                    elif market_code == "GLOBAL":
                        articles_per_symbol = config['global_articles_per_symbol']  # 2 for global symbols
                    else:
                        articles_per_symbol = 2  # Default fallback
                else:  # CHINA_HK session
                    articles_per_symbol = config['articles_per_symbol']  # 2 for all symbols in China/HK session
                
                # Add symbols with their configured limits
                for symbol in market_symbols:
                    symbol_list.append({
                        'symbol': symbol,
                        'articles_limit': articles_per_symbol,
                        'market_code': market_code
                    })
            
            logger.info(f"📋 Market session {market_session}: {len(symbol_list)} symbols prepared")
            
            # Log symbol distribution
            market_distribution = {}
            for symbol_info in symbol_list:
                market_code = symbol_info['market_code']
                market_distribution[market_code] = market_distribution.get(market_code, 0) + 1
            
            for market_code, count in market_distribution.items():
                logger.info(f"  • {market_code}: {count} symbols")
            
            return symbol_list
            
        except Exception as e:
            logger.error(f"Error getting market symbols for {market_session}: {str(e)}")
            return []
    
    def _cleanup_empty_articles(self):
        """Clean up articles with no content and no insights"""
        try:
            with self.get_db_session() as session:
                # Find articles to delete
                articles_to_delete = session.query(NewsArticle).filter(
                    NewsArticle.content.is_(None),
                    NewsArticle.ai_insights.is_(None)
                ).all()
                
                if articles_to_delete:
                    for article in articles_to_delete:
                        session.delete(article)
                    
                    session.commit()
                    logger.info(f"🧹 Cleaned up {len(articles_to_delete)} empty articles")
                else:
                    logger.info("🧹 No empty articles to clean up")
                    
        except Exception as e:
            logger.error(f"Error cleaning up empty articles: {str(e)}")
    
    def _shuffle_symbols(self, symbols: List[str]) -> List[str]:
        """Shuffle symbols for variety in processing order"""
        random.shuffle(symbols)
        return symbols
    
    def _fetch_symbol_with_retry(self, symbol: str, limit: int) -> List[Dict]:
        """Fetch articles for a symbol with retry logic using direct news service call"""
        logger.info(f"🔄 Starting fetch for symbol: {symbol} (limit: {limit})")
        
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"📡 Attempt {attempt + 1} for {symbol}")
                
                # Use the same direct call that the working manual fetch uses
                # This matches exactly what happens in the /news/api/fetch endpoint
                articles = self.news_service.fetch_and_analyze_news(
                    symbols=[symbol],
                    limit=limit,
                    timeout=30  # Increased timeout for better reliability
                )
                
                if articles:
                    logger.info(f"✅ Successfully fetched {len(articles)} articles for {symbol}")
                    return articles
                else:
                    logger.warning(f"⚠️ No articles found for {symbol} on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"❌ Error fetching {symbol} on attempt {attempt + 1}: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    sleep_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"⏳ Retrying {symbol} in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"💀 Failed to fetch {symbol} after {self.retry_attempts} attempts")
        
        return []
    
    def get_symbols(self) -> List[str]:
        """Get the complete list of symbols that will be processed across all markets"""
        all_symbols = []
        
        # Collect all unique symbols from all markets
        for market_code, symbols in self.DEFAULT_SYMBOLS.items():
            all_symbols.extend(symbols)
        
        # Remove duplicates (global symbols appear in multiple sessions)
        unique_symbols = list(set(all_symbols))
        
        return unique_symbols
    
    def get_market_symbols(self, market_session: str) -> List[str]:
        """Get symbols for a specific market session (flat list)"""
        symbol_configs = self._get_market_symbols(market_session)
        return [config['symbol'] for config in symbol_configs]
    
    def get_progress(self) -> Dict:
        """Get current fetch progress and last completed operation"""
        # Create a copy to avoid external modification
        progress = self.current_progress.copy()
        
        # Calculate percentage if active
        if progress['is_active'] and progress['total_symbols'] > 0:
            progress['percentage'] = (progress['symbols_processed'] / progress['total_symbols']) * 100
        else:
            progress['percentage'] = 100.0 if not progress['is_active'] and progress['symbols_processed'] > 0 else 0.0
        
        # Format start time for JSON serialization
        if progress['start_time']:
            progress['start_time'] = progress['start_time'].isoformat()
        
        # Include last completed operation for historical display
        last_completed = self.last_completed_operation.copy()
        if last_completed['completed_at']:
            last_completed['completed_at'] = last_completed['completed_at'].isoformat()
        
        progress['last_completed_operation'] = last_completed
            
        return progress
    
    def run_now(self, market_session: str = "auto"):
        """Manually trigger the news fetch job immediately for a specific market session"""
        try:
            # If market_session is "auto", use intelligent time-based selection
            if market_session == "auto":
                market_session = self._determine_current_market_session()
                logger.info(f"🚀 Manual news fetch job triggered with intelligent time-based selection")
                logger.info(f"🎯 Selected market session: {market_session} based on current time")
            else:
                logger.info(f"🚀 Manual news fetch job triggered for {market_session} session")
            
            # Validate market session
            if market_session not in self.market_config:
                logger.error(f"Invalid market session: {market_session}")
                return {
                    'success': False,
                    'error': f'Invalid market session: {market_session}. Valid options: {list(self.market_config.keys())}'
                }
            
            # Get symbol count for this session
            symbol_configs = self._get_market_symbols(market_session)
            symbol_count = len(symbol_configs)
            
            # Run the fetch job in a separate thread to avoid blocking
            def run_job():
                try:
                    logger.info(f"🎯 Starting manual {market_session} job with {symbol_count} symbols")
                    result = self.run_fetch_job(market_session=market_session)
                    logger.info(f"🏁 Manual {market_session} job completed: {result}")
                except Exception as e:
                    logger.error(f"Error in manual {market_session} fetch job: {str(e)}", exc_info=True)
            
            # CHANGED: daemon=False to ensure thread completes
            thread = threading.Thread(target=run_job, daemon=False, name=f"NewsScheduler{market_session}Manual")
            thread.start()
            
            logger.info(f"Manual {market_session} news fetch thread started: {thread.name}, daemon={thread.daemon}")
            
            return {
                'success': True,
                'message': f'Manual {market_session} news fetch job started (time-based selection)' if market_session == self._determine_current_market_session() else f'Manual {market_session} news fetch job started',
                'market_session': market_session,
                'total_symbols': symbol_count,
                'time_based_selection': market_session == self._determine_current_market_session()
            }
            
        except Exception as e:
            logger.error(f"Error starting manual {market_session} fetch job: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_status(self):
        """Get current scheduler status with market-specific information"""
        next_run = None
        jobs_count = len(schedule.jobs)
        
        # Get current intelligent market session selection
        current_market_session = self._determine_current_market_session()
        current_time_str = datetime.now().strftime('%H:%M UTC')
        
        # Get next scheduled run time and details
        next_run_details = None
        if jobs_count > 0:
            next_job = schedule.next_run()
            if next_job:
                next_run = next_job.isoformat()
                
                # Determine which market session is next based on current UTC time
                current_hour = datetime.now().hour
                if current_hour < 1:
                    next_run_details = "China/Hong Kong Market Open (01:00 UTC)"
                elif current_hour < 4:
                    next_run_details = "China/Hong Kong Mid-Session (04:30 UTC)"
                elif current_hour < 8:
                    next_run_details = "China/Hong Kong Market Close (08:30 UTC)"
                elif current_hour < 14:
                    next_run_details = "US Pre-Market (14:00 UTC)"
                elif current_hour < 17:
                    next_run_details = "US Mid-Session (17:30 UTC)"
                elif current_hour < 21:
                    next_run_details = "US After-Hours (21:30 UTC)"
                else:
                    next_run_details = "China/Hong Kong Market Open (01:00 UTC)"
        
        # Calculate symbol distribution
        total_symbols = len(self.get_symbols())
        market_distribution = {}
        
        for market_code, symbols in self.DEFAULT_SYMBOLS.items():
            market_distribution[market_code] = len(symbols)
        
        # Calculate session information
        china_hk_symbols = self._get_market_symbols("CHINA_HK")
        us_symbols = self._get_market_symbols("US")
        
        return {
            "running": self.running,
            "next_run": next_run,
            "next_run_details": next_run_details,
            "jobs_count": jobs_count,
            "fetch_schedule": "Market-specific (6 times daily)",
            "intelligent_selection": {
                "current_time": current_time_str,
                "recommended_session": current_market_session,
                "enabled": True,
                "description": f"Based on current time ({current_time_str}), {current_market_session} session is recommended"
            },
            "schedule_sessions": [
                {
                    "session": "China/Hong Kong",
                    "times": ["01:00 UTC", "04:30 UTC", "08:30 UTC"],
                    "symbols": len(china_hk_symbols),
                    "markets": ["CN", "HK", "GLOBAL"]
                },
                {
                    "session": "US",
                    "times": ["14:00 UTC", "17:30 UTC", "21:30 UTC"],
                    "symbols": len(us_symbols),
                    "markets": ["US", "GLOBAL"]
                }
            ],
            "total_unique_symbols": total_symbols,
            "market_distribution": market_distribution,
            "daily_articles_estimate": {
                "china_hk_sessions": len(china_hk_symbols) * 2 * 3,  # 2 articles per symbol, 3 sessions
                "us_sessions": (846 * 5 + 158 * 2) * 3,  # US symbols: 5 articles, Global: 2 articles, 3 sessions = 13,032 articles
                "max_daily_total": len(china_hk_symbols) * 2 * 3 + (846 * 5 + 158 * 2) * 3  # Calculated total
            },
            "configuration": {
                "chunk_size": self.chunk_size,
                "retry_attempts": self.retry_attempts,
                "articles_per_symbol": {
                    "china_hk": 2,
                    "us_stocks": 5,
                    "global_in_us": 2
                }
            }
        }

# Global instance
news_fetch_scheduler = NewsFetchScheduler() 