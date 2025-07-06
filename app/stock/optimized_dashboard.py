# app/stock/optimized_dashboard.py

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import datetime
import time
import logging
from typing import Dict, Tuple, Optional

from app.utils.cache.enhanced_stock_cache import enhanced_stock_cache

logger = logging.getLogger(__name__)

def analyze_stock_multi_period_cached(ticker_symbol: str, period: str = "2y") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Analyzes a stock with comprehensive caching for performance optimization
    
    Parameters:
    ticker_symbol (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
    period (str): Time period for data retrieval (default: '2y' for 2 years)
    
    Returns:
    tuple: Tuple containing daily, weekly, and monthly DataFrames with price and volatility data
    """
    start_time = time.time()
    cache_hit = False
    
    try:
        # Check for cached multi-period analysis first
        cached_result = enhanced_stock_cache.get_multi_period_analysis(ticker_symbol, period)
        if cached_result:
            daily_data, weekly_data, monthly_data = cached_result
            cache_hit = True
            duration = time.time() - start_time
            enhanced_stock_cache.track_analysis_performance(ticker_symbol, "multi_period_analysis", duration, cache_hit=True)
            logger.info(f"🎯 Multi-period cache hit for {ticker_symbol} {period} ({duration*1000:.1f}ms)")
            return daily_data, weekly_data, monthly_data
        
        # Check for individual cached yfinance data
        daily_data = enhanced_stock_cache.get_yfinance_data(ticker_symbol, period, "1d")
        weekly_data = enhanced_stock_cache.get_yfinance_data(ticker_symbol, period, "1wk")
        monthly_data = enhanced_stock_cache.get_yfinance_data(ticker_symbol, period, "1mo")
        
        data_cache_hits = sum([daily_data is not None, weekly_data is not None, monthly_data is not None])
        
        # Fetch missing data from yfinance
        stock = yf.Ticker(ticker_symbol)
        
        if daily_data is None:
            logger.info(f"🔄 Fetching daily data for {ticker_symbol} {period}")
            daily_data = stock.history(period=period)
            if len(daily_data) > 0:
                enhanced_stock_cache.set_yfinance_data(ticker_symbol, period, "1d", daily_data)
        
        if weekly_data is None:
            logger.info(f"🔄 Fetching weekly data for {ticker_symbol} {period}")
            weekly_data = stock.history(period=period, interval="1wk")
            if len(weekly_data) > 0:
                enhanced_stock_cache.set_yfinance_data(ticker_symbol, period, "1wk", weekly_data)
        
        if monthly_data is None:
            logger.info(f"🔄 Fetching monthly data for {ticker_symbol} {period}")
            monthly_data = stock.history(period=period, interval="1mo")
            if len(monthly_data) > 0:
                enhanced_stock_cache.set_yfinance_data(ticker_symbol, period, "1mo", monthly_data)
        
        # Check if we have valid data
        if daily_data is None or len(daily_data) == 0:
            logger.error(f"No data found for {ticker_symbol}")
            return None, None, None
        
        # Process the data with technical indicators
        daily_data = _add_technical_indicators(daily_data)
        weekly_data = _add_technical_indicators(weekly_data) if weekly_data is not None and len(weekly_data) > 0 else pd.DataFrame()
        monthly_data = _add_technical_indicators(monthly_data) if monthly_data is not None and len(monthly_data) > 0 else pd.DataFrame()
        
        # Cache the complete multi-period analysis
        enhanced_stock_cache.set_multi_period_analysis(ticker_symbol, period, daily_data, weekly_data, monthly_data)
        
        duration = time.time() - start_time
        cache_hit = data_cache_hits > 0
        enhanced_stock_cache.track_analysis_performance(ticker_symbol, "multi_period_analysis", duration, cache_hit=cache_hit)
        
        logger.info(f"✅ Multi-period analysis for {ticker_symbol} {period} completed ({duration*1000:.1f}ms, {data_cache_hits}/3 cache hits)")
        return daily_data, weekly_data, monthly_data
        
    except Exception as e:
        duration = time.time() - start_time
        enhanced_stock_cache.track_analysis_performance(ticker_symbol, "multi_period_analysis", duration, cache_hit=False)
        logger.error(f"❌ Error analyzing {ticker_symbol}: {str(e)}")
        return None, None, None

def _add_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to the data"""
    if data is None or len(data) == 0:
        return data
    
    # Calculate returns and volatility
    data['Return'] = data['Close'].pct_change()
    
    # Calculate volatility based on data frequency
    if len(data) > 252:  # Likely daily data
        data['Volatility'] = data['Return'].rolling(window=21).std() * np.sqrt(252)
        # Add moving averages for daily data
        data['MA_100'] = data['Close'].rolling(window=100).mean()
        data['MA_200'] = data['Close'].rolling(window=200).mean()
        
        if len(data) >= 500:
            data['MA_500'] = data['Close'].rolling(window=500).mean()
        else:
            data['MA_500'] = np.nan
            
        if len(data) >= 1000:
            data['MA_1000'] = data['Close'].rolling(window=1000).mean()
        else:
            data['MA_1000'] = np.nan
            
    elif len(data) > 52:  # Likely weekly data
        data['Volatility'] = data['Return'].rolling(window=4).std() * np.sqrt(52)
    else:  # Likely monthly data
        data['Volatility'] = data['Return'].rolling(window=3).std() * np.sqrt(12)
    
    return data

def create_plotly_dashboard_cached(ticker_symbol: str, period: str = "2y", chart_type: str = "dashboard") -> Dict:
    """
    Creates an interactive Plotly dashboard with comprehensive caching
    
    Parameters:
    ticker_symbol (str): Stock ticker symbol for the title
    period (str): Time period for analysis
    chart_type (str): Type of chart to create
    
    Returns:
    dict: Plotly figure as JSON-serializable dictionary
    """
    start_time = time.time()
    
    # Create cache parameters
    params = {
        'ticker': ticker_symbol,
        'period': period,
        'chart_type': chart_type,
        'version': '1.0'  # Increment when chart structure changes
    }
    
    # Check for cached figure first
    cached_figure = enhanced_stock_cache.get_plotly_figure(ticker_symbol, period, chart_type, params)
    if cached_figure:
        duration = time.time() - start_time
        enhanced_stock_cache.track_analysis_performance(ticker_symbol, "plotly_dashboard", duration, cache_hit=True)
        logger.info(f"🎯 Plotly dashboard cache hit for {ticker_symbol} {period} ({duration*1000:.1f}ms)")
        return cached_figure['figure']
    
    # Get data (this will use caching internally)
    daily_data, weekly_data, monthly_data = analyze_stock_multi_period_cached(ticker_symbol, period)
    
    if daily_data is None or len(daily_data) == 0:
        logger.error(f"No data available for dashboard creation: {ticker_symbol}")
        return None
    
    # Create the dashboard
    fig = _create_dashboard_figure(daily_data, weekly_data, monthly_data, ticker_symbol)
    
    # Convert to JSON-serializable format
    figure_dict = fig.to_dict()
    
    # Cache the figure
    enhanced_stock_cache.set_plotly_figure(ticker_symbol, period, chart_type, params, figure_dict)
    
    duration = time.time() - start_time
    enhanced_stock_cache.track_analysis_performance(ticker_symbol, "plotly_dashboard", duration, cache_hit=False)
    
    logger.info(f"✅ Plotly dashboard created for {ticker_symbol} {period} ({duration*1000:.1f}ms)")
    return figure_dict

def _create_dashboard_figure(daily_data: pd.DataFrame, weekly_data: pd.DataFrame, monthly_data: pd.DataFrame, ticker_symbol: str):
    """Create the actual Plotly dashboard figure"""
    
    # Create figure with subplots
    fig = make_subplots(
        rows=3, 
        cols=2,
        shared_xaxes=False,
        vertical_spacing=0.08,
        horizontal_spacing=0.05,
        subplot_titles=(
            f"{ticker_symbol} - Daily Price & Moving Averages", f"{ticker_symbol} - Weekly & Monthly Price",
            "Daily Volatility", "Weekly & Monthly Volatility",
            "Current Metrics", "Historical Volatility Comparison"
        ),
        row_heights=[0.5, 0.25, 0.25],
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "table"}, {"type": "table"}]
        ]
    )
    
    # 1. Daily price chart with MAs
    fig.add_trace(
        go.Scatter(
            x=daily_data.index, 
            y=daily_data['Close'],
            mode='lines',
            name='Daily Close',
            line=dict(color='black', width=1)
        ),
        row=1, col=1
    )
    
    # Add moving averages
    ma_names = ['MA_100', 'MA_200', 'MA_500', 'MA_1000']
    ma_colors = ['blue', 'green', 'red', 'purple']
    
    for ma, color in zip(ma_names, ma_colors):
        if ma in daily_data.columns and not daily_data[ma].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=daily_data.index,
                    y=daily_data[ma],
                    mode='lines',
                    name=f'{ma.replace("MA_", "")}-day MA',
                    line=dict(color=color, width=1.5)
                ),
                row=1, col=1
            )
    
    # 2. Weekly and Monthly price charts (if data available)
    if weekly_data is not None and len(weekly_data) > 0:
        fig.add_trace(
            go.Scatter(
                x=weekly_data.index, 
                y=weekly_data['Close'],
                mode='lines',
                name='Weekly Close',
                line=dict(color='darkblue', width=1.5)
            ),
            row=1, col=2
        )
    
    if monthly_data is not None and len(monthly_data) > 0:
        fig.add_trace(
            go.Scatter(
                x=monthly_data.index, 
                y=monthly_data['Close'],
                mode='lines',
                name='Monthly Close',
                line=dict(color='darkred', width=2)
            ),
            row=1, col=2
        )
    
    # 3. Volatility charts
    if 'Volatility' in daily_data.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_data.index,
                y=daily_data['Volatility'],
                mode='lines',
                name='Daily Vol',
                line=dict(color='blue')
            ),
            row=2, col=1
        )
    
    if weekly_data is not None and len(weekly_data) > 0 and 'Volatility' in weekly_data.columns:
        fig.add_trace(
            go.Scatter(
                x=weekly_data.index,
                y=weekly_data['Volatility'],
                mode='lines',
                name='Weekly Vol',
                line=dict(color='blue')
            ),
            row=2, col=2
        )
    
    if monthly_data is not None and len(monthly_data) > 0 and 'Volatility' in monthly_data.columns:
        fig.add_trace(
            go.Scatter(
                x=monthly_data.index,
                y=monthly_data['Volatility'],
                mode='lines',
                name='Monthly Vol',
                line=dict(color='red')
            ),
            row=2, col=2
        )
    
    # 4. Add tables
    _add_metrics_tables(fig, daily_data, weekly_data, monthly_data)
    
    # 5. Update layout
    fig.update_layout(
        height=1000,
        title_text=f"{ticker_symbol} Multi-Timeframe Analysis Dashboard",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            itemsizing="constant",
            itemwidth=30,
            font=dict(size=10),
            tracegroupgap=5
        ),
        hovermode="closest"
    )
    
    # Update axes labels
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=2)
    fig.update_yaxes(title_text="Volatility (Annualized)", row=2, col=1)
    fig.update_yaxes(title_text="Volatility (Annualized)", row=2, col=2)
    
    # Add date range selectors
    fig.update_xaxes(
        rangeslider_visible=False,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ),
        row=1, col=1
    )
    
    return fig

def _add_metrics_tables(fig, daily_data: pd.DataFrame, weekly_data: pd.DataFrame, monthly_data: pd.DataFrame):
    """Add metrics tables to the figure"""
    
    def format_value(value, is_price=True):
        if pd.isna(value):
            return "N/A"
        if is_price:
            return f"${value:.2f}"
        return f"{value:.4f}"
    
    # Current metrics table
    latest_daily = daily_data.iloc[-1]
    latest_weekly = weekly_data.iloc[-1] if weekly_data is not None and len(weekly_data) > 0 else pd.Series()
    latest_monthly = monthly_data.iloc[-1] if monthly_data is not None and len(monthly_data) > 0 else pd.Series()
    
    current_metrics = go.Table(
        header=dict(
            values=['Metric', 'Daily', 'Weekly', 'Monthly'],
            fill_color='paleturquoise',
            align='left',
            font=dict(size=12)
        ),
        cells=dict(
            values=[
                ['Latest Close', 'Latest Return', 'Current Volatility', 'MA 100', 'MA 200', 'MA 500', 'MA 1000'],
                [
                    format_value(latest_daily['Close']),
                    f"{latest_daily['Return']*100:.2f}%" if not pd.isna(latest_daily.get('Return')) else "N/A",
                    format_value(latest_daily.get('Volatility'), False) if 'Volatility' in latest_daily else "N/A",
                    format_value(latest_daily.get('MA_100')) if 'MA_100' in latest_daily else "N/A",
                    format_value(latest_daily.get('MA_200')) if 'MA_200' in latest_daily else "N/A",
                    format_value(latest_daily.get('MA_500')) if 'MA_500' in latest_daily else "N/A",
                    format_value(latest_daily.get('MA_1000')) if 'MA_1000' in latest_daily else "N/A"
                ],
                [
                    format_value(latest_weekly.get('Close')) if 'Close' in latest_weekly else "N/A",
                    f"{latest_weekly['Return']*100:.2f}%" if not pd.isna(latest_weekly.get('Return')) else "N/A",
                    format_value(latest_weekly.get('Volatility'), False) if 'Volatility' in latest_weekly else "N/A",
                    "N/A", "N/A", "N/A", "N/A"
                ],
                [
                    format_value(latest_monthly.get('Close')) if 'Close' in latest_monthly else "N/A",
                    f"{latest_monthly['Return']*100:.2f}%" if not pd.isna(latest_monthly.get('Return')) else "N/A",
                    format_value(latest_monthly.get('Volatility'), False) if 'Volatility' in latest_monthly else "N/A",
                    "N/A", "N/A", "N/A", "N/A"
                ]
            ],
            fill_color=[['lavender', 'white']*2],
            align='left',
            font=dict(size=11)
        )
    )
    
    fig.add_trace(current_metrics, row=3, col=1)
    
    # Historical volatility comparison table
    periods = ['30 days', '90 days', '180 days', '1 year', 'All time']
    
    def safe_mean(data, window, column='Volatility'):
        if data is None or len(data) == 0 or column not in data.columns:
            return np.nan
        if len(data) >= window and not data[column].isna().all():
            return data[column].iloc[-window:].mean()
        return np.nan
    
    # Calculate volatility stats
    daily_vol_stats = [
        safe_mean(daily_data, 30),
        safe_mean(daily_data, 90),
        safe_mean(daily_data, 180),
        safe_mean(daily_data, 252),
        daily_data['Volatility'].mean() if 'Volatility' in daily_data.columns else np.nan
    ]
    
    weekly_vol_stats = [
        safe_mean(weekly_data, 4),
        safe_mean(weekly_data, 13),
        safe_mean(weekly_data, 26),
        safe_mean(weekly_data, 52),
        weekly_data['Volatility'].mean() if weekly_data is not None and 'Volatility' in weekly_data.columns else np.nan
    ]
    
    monthly_vol_stats = [
        safe_mean(monthly_data, 1),
        safe_mean(monthly_data, 3),
        safe_mean(monthly_data, 6),
        safe_mean(monthly_data, 12),
        monthly_data['Volatility'].mean() if monthly_data is not None and 'Volatility' in monthly_data.columns else np.nan
    ]
    
    def format_vol(vol):
        if pd.isna(vol):
            return "N/A"
        return f"{vol:.4f}"
    
    vol_table = go.Table(
        header=dict(
            values=['Period', 'Daily Volatility', 'Weekly Volatility', 'Monthly Volatility'],
            fill_color='paleturquoise',
            align='left',
            font=dict(size=12)
        ),
        cells=dict(
            values=[
                periods,
                [format_vol(vol) for vol in daily_vol_stats],
                [format_vol(vol) for vol in weekly_vol_stats],
                [format_vol(vol) for vol in monthly_vol_stats]
            ],
            fill_color='lavender',
            align='left',
            font=dict(size=11)
        )
    )
    
    fig.add_trace(vol_table, row=3, col=2)

def get_stock_analysis_cached(ticker: str, period: str) -> Tuple[Dict, Dict]:
    """
    Generate stock analysis with comprehensive caching
    
    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Time period for analysis
    
    Returns:
    tuple: (figure_dict, info_dict) or (None, error_message)
    """
    start_time = time.time()
    
    try:
        # Check for complete cached analysis
        params = {'ticker': ticker, 'period': period}
        cached_analysis = enhanced_stock_cache.get_complete_analysis(ticker, period, params)
        
        if cached_analysis:
            duration = time.time() - start_time
            enhanced_stock_cache.track_analysis_performance(ticker, "complete_analysis", duration, cache_hit=True)
            logger.info(f"🎯 Complete analysis cache hit for {ticker} {period} ({duration*1000:.1f}ms)")
            return cached_analysis['figure'], cached_analysis['info']
        
        # Create dashboard figure (this will use caching internally)
        fig = create_plotly_dashboard_cached(ticker, period)
        
        if fig is None:
            return None, f"No data found for {ticker}"
        
        # Get data for info (this will use cached data)
        daily_data, weekly_data, monthly_data = analyze_stock_multi_period_cached(ticker, period)
        
        # Generate info
        info = {
            "ticker": ticker,
            "period": period,
            "daily_points": len(daily_data) if daily_data is not None else 0,
            "weekly_points": len(weekly_data) if weekly_data is not None else 0,
            "monthly_points": len(monthly_data) if monthly_data is not None else 0,
            "start_date": daily_data.index[0].strftime('%Y-%m-%d') if daily_data is not None and len(daily_data) > 0 else None,
            "end_date": daily_data.index[-1].strftime('%Y-%m-%d') if daily_data is not None and len(daily_data) > 0 else None,
            "cache_stats": enhanced_stock_cache.get_cache_stats()
        }
        
        # Cache the complete analysis
        complete_result = {
            'figure': fig,
            'info': info
        }
        enhanced_stock_cache.set_complete_analysis(ticker, period, params, complete_result)
        
        duration = time.time() - start_time
        enhanced_stock_cache.track_analysis_performance(ticker, "complete_analysis", duration, cache_hit=False)
        
        logger.info(f"✅ Complete analysis for {ticker} {period} completed ({duration*1000:.1f}ms)")
        return fig, info
        
    except Exception as e:
        duration = time.time() - start_time
        enhanced_stock_cache.track_analysis_performance(ticker, "complete_analysis", duration, cache_hit=False)
        logger.error(f"❌ Error in complete analysis for {ticker}: {str(e)}")
        return None, f"Error analyzing {ticker}: {str(e)}" 