# app/analyzer/stock_analyzer.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

from app.utils.data.data_service import DataService
from app.utils.analysis.analysis_service import AnalysisService
from app.utils.visualization.visualization_service import VisualizationService
from app.utils.analysis.stock_news_service import StockNewsService
from app.utils.config.metrics_config import METRICS_TO_FETCH, ANALYSIS_DEFAULTS
from app.utils.config.layout_config import LAYOUT_CONFIG
from app.utils.symbol_utils import normalize_ticker

class StockAnalyzer:
    """Class to handle stock analysis operations"""
    
    def __init__(self):
        self.data_service = DataService()

def create_stock_visualization(
    ticker: str, 
    end_date: Optional[str] = None, 
    lookback_days: int = ANALYSIS_DEFAULTS['lookback_days'],
    crossover_days: int = ANALYSIS_DEFAULTS['crossover_days']
) -> 'plotly.graph_objects.Figure':
    """
    Create a complete stock analysis visualization

    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    end_date : str, optional
        End date in YYYY-MM-DD format. If None, uses current date
    lookback_days : int, optional
        Number of days to look back for display
    crossover_days : int, optional
        Number of days for crossover analysis

    Returns
    -------
    plotly.graph_objects.Figure
        Complete analysis visualization figure
    """
    logger = logging.getLogger(__name__)
    analysis_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    print(f"Starting analysis {analysis_id} for {ticker}")
    try:
        # Initialize services
        data_service = DataService()
        
        # Set up dates
        if end_date is None or not end_date.strip():
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Calculate extended start date for ratio calculations
        # Fetch additional historical data (lookback + crossover days) to ensure accurate ratio calculations
        extended_lookback = max(lookback_days, crossover_days) + lookback_days
        extended_start_date = data_service.get_analysis_dates(end_date, 'days', extended_lookback)
        display_start_date = data_service.get_analysis_dates(end_date, 'days', lookback_days)
        
        logger.info(f"Fetching extended historical data for {ticker} from {extended_start_date} to {end_date}")
        historical_data_extended = data_service.get_historical_data(ticker, extended_start_date, end_date)
        
        if historical_data_extended.empty:
            raise ValueError(f"No historical data found for {ticker}")
        
        print("Performing technical analysis...")
        # Perform technical analysis on extended data
        analysis_df = AnalysisService.analyze_stock_data(historical_data_extended, crossover_days)
        
         # Log analysis results
        logger.debug(f"Analysis DataFrame columns: {analysis_df.columns.tolist()}")
        if 'R2_Pct' in analysis_df.columns:
            logger.debug(f"R2_Pct sample: {analysis_df['R2_Pct'].head()}")
        
        
        # Filter data for display period
        display_start = pd.to_datetime(display_start_date)
        historical_data = historical_data_extended[historical_data_extended.index >= display_start]
        analysis_df = analysis_df[analysis_df.index >= display_start]
        
        # Perform regression analysis on display period data
        regression_results = AnalysisService.perform_polynomial_regression(
            historical_data, 
            future_days=int(lookback_days*LAYOUT_CONFIG['lookback_days_ratio']),
            symbol=ticker
        )
        
        # Find crossover points within display period
        crossover_data = AnalysisService.find_crossover_points(
            analysis_df.index.tolist(),
            analysis_df['Retracement_Ratio_Pct'].tolist(),
            analysis_df['Price_Position_Pct'].tolist(),
            analysis_df['Close'].tolist()
        )
        
        print("Fetching financial metrics...")
        # Get financial metrics
        current_year = datetime.now().year
        start_year = str(current_year - 10)
        end_year = str(current_year)
        
        metrics_df = data_service.create_metrics_table(
            ticker=ticker,
            metrics=METRICS_TO_FETCH,
            start_year=start_year,
            end_year=end_year
        )
        
        # Prepare signal returns data
        # Inside create_stock_visualization function, replace the signal returns section with:

        # Prepare signal returns data
        print("Analyzing trading signals...")
        signal_returns = []
        if crossover_data[0]:  # If there are crossover points
            dates, values, directions, prices = crossover_data
            current_position = None
            entry_price = None
            
            for date, value, direction, price in zip(dates, values, directions, prices):
                if direction == 'up' and current_position is None:  # Buy signal
                    entry_price = price
                    current_position = 'long'
                    signal_returns.append({
                        'Entry Date': date,
                        'Entry Price': price,
                        'Signal': 'Buy',
                        'Status': 'Open'
                    })
                elif direction == 'down':  # Sell signal
                    exit_price = price
                    if current_position == 'long':  # Regular sell after buy
                        trade_return = ((exit_price / entry_price) - 1) * 100
                        current_position = None
                        
                        if signal_returns:
                            signal_returns[-1]['Status'] = 'Closed'
                        
                        signal_returns.append({
                            'Entry Date': date,
                            'Entry Price': price,
                            'Signal': 'Sell',
                            'Trade Return': trade_return,
                            'Status': 'Closed'
                        })
                    else:  # Exit-only signal (no corresponding buy)
                        signal_returns.append({
                            'Signal': 'Sell',
                            'Exit Date': date,
                            'Exit Price': price,
                            'Status': 'Exit Only'
                        })
            
            # Handle open position
            if current_position == 'long':
                last_price = historical_data['Close'].iloc[-1]
                open_trade_return = ((last_price / entry_price) - 1) * 100
                if signal_returns and signal_returns[-1]['Signal'] == 'Buy':
                    signal_returns[-1]['Trade Return'] = open_trade_return
                    signal_returns[-1]['Current Price'] = last_price
        
        print("Creating visualization...")
        # Create visualization
        fig = VisualizationService.create_stock_analysis_chart(
            symbol=ticker,
            data=analysis_df,  # Use display period data for visualization
            analysis_dates=analysis_df.index.tolist(),
            ratios=analysis_df['Retracement_Ratio_Pct'].tolist(),
            prices=analysis_df['Close'].tolist(),
            appreciation_pcts=analysis_df['Price_Position_Pct'].tolist(),
            regression_results=regression_results,
            crossover_data=crossover_data,
            signal_returns=signal_returns,
            metrics_df=metrics_df
        )
        
        print("Fetching and processing news...")
        # Check for recent news and trigger background fetch if needed
        try:
            news_result = StockNewsService.auto_check_and_fetch_news(ticker)
            logger.info(f"Auto news check for {ticker}: {news_result['status']}")
        except Exception as news_error:
            logger.warning(f"News processing failed for {ticker}: {str(news_error)}")
        
        print("Analysis completed successfully!")
        return fig
    
    except Exception as e:
        print(f"Error in create_stock_visualization: {str(e)}")
        raise

def create_stock_visualization_old(
    ticker: str, 
    end_date: Optional[str] = None, 
    lookback_days: int = ANALYSIS_DEFAULTS['lookback_days'],
    crossover_days: int = ANALYSIS_DEFAULTS['crossover_days']
) -> 'plotly.graph_objects.Figure':
    """
    Create a complete stock analysis visualization

    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    end_date : str, optional
        End date in YYYY-MM-DD format. If None, uses current date
    lookback_days : int, optional
        Number of days to look back for display
    crossover_days : int, optional
        Number of days for crossover analysis

    Returns
    -------
    plotly.graph_objects.Figure
        Complete analysis visualization figure
    """
    analysis_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    logger = logging.getLogger(__name__)
    logger.info(f"Starting analysis {analysis_id} for {ticker}")
    
    try:
        # Initialize services
        data_service = DataService()
        
        # Set up dates
        if end_date is None or not end_date.strip():
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Calculate extended start date for ratio calculations
        # Fetch additional historical data (lookback + crossover days) to ensure accurate ratio calculations
        extended_lookback = lookback_days + crossover_days
        extended_start_date = data_service.get_analysis_dates(end_date, 'days', extended_lookback)
        display_start_date = data_service.get_analysis_dates(end_date, 'days', lookback_days)
        
        logger.info(f"Fetching extended historical data for {ticker} from {extended_start_date} to {end_date}")
        
        # Get extended historical data for calculations
        yahoo_ticker = normalize_ticker(ticker, purpose='analyze')
        try:
            historical_data_extended = data_service.get_historical_data(
                yahoo_ticker, extended_start_date, end_date)
        except ValueError as e:
            logger.error(f"Failed to get historical data for {ticker}: {str(e)}")
            raise ValueError(f"No historical data found for {ticker}")
        
        if historical_data_extended.empty:
            logger.error(f"Empty historical data returned for {ticker}")
            raise ValueError(f"No historical data found for {ticker}")
        
        # Verify we have enough data points (account for weekends/holidays)
        # Rule of thumb: ~252 trading days per year, so minimum should be about 65% of requested days
        min_required_days = max(50, int(lookback_days * 0.65))  # At least 50 days or 65% of requested
        if len(historical_data_extended) < min_required_days:
            logger.error(f"Insufficient data points for {ticker}: got {len(historical_data_extended)}, need at least {min_required_days} (requested {lookback_days} calendar days)")
            raise ValueError(f"Insufficient historical data for {ticker}. Got {len(historical_data_extended)} trading days, need at least {min_required_days}.")
        
        logger.info("Performing technical analysis...")
        # Perform technical analysis on extended data
        analysis_df = AnalysisService.analyze_stock_data(historical_data_extended, crossover_days)
        
        # Filter data for display period
        historical_data = historical_data_extended[historical_data_extended.index >= display_start_date]
        analysis_df = analysis_df[analysis_df['Date'] >= pd.to_datetime(display_start_date)]
        
        # Verify filtered data
        if historical_data.empty or analysis_df.empty:
            logger.error(f"No data available for display period for {ticker}")
            raise ValueError(f"No data available for analysis period for {ticker}")
        
        # Perform regression analysis on display period data
        regression_results = AnalysisService.perform_polynomial_regression(
            historical_data, 
            future_days=int(lookback_days*LAYOUT_CONFIG['lookback_days_ratio']),
            symbol=ticker
        )
        
        # Find crossover points within display period
        crossover_data = AnalysisService.find_crossover_points(
            analysis_df['Date'].tolist(),
            analysis_df['Retracement_Ratio_Pct'].tolist(),
            analysis_df['Price_Position_Pct'].tolist(),
            analysis_df['Price'].tolist()
        )
        
        logger.info("Fetching financial metrics...")
        # Get financial metrics
        current_year = datetime.now().year
        start_year = str(current_year - 10)
        end_year = str(current_year)
        
        metrics_df = data_service.create_metrics_table(
            ticker=ticker,
            metrics=METRICS_TO_FETCH,
            start_year=start_year,
            end_year=end_year
        )
        
        # Prepare signal returns data
        logger.info("Analyzing trading signals...")
        signal_returns = []
        if crossover_data[0]:  # If there are crossover points
            dates, values, directions, prices = crossover_data
            current_position = None
            entry_price = None
            
            for date, value, direction, price in zip(dates, values, directions, prices):
                if direction == 'up' and current_position is None:  # Buy signal
                    entry_price = price
                    current_position = 'long'
                    signal_returns.append({
                        'Entry Date': date,
                        'Entry Price': price,
                        'Signal': 'Buy',
                        'Status': 'Open'
                    })
                elif direction == 'down':  # Sell signal
                    exit_price = price
                    if current_position == 'long':  # Regular sell after buy
                        trade_return = ((exit_price / entry_price) - 1) * 100
                        current_position = None
                        
                        if signal_returns:
                            signal_returns[-1]['Status'] = 'Closed'
                        
                        signal_returns.append({
                            'Entry Date': date,
                            'Entry Price': price,
                            'Signal': 'Sell',
                            'Trade Return': trade_return,
                            'Status': 'Closed'
                        })
                    else:  # Exit-only signal (no corresponding buy)
                        signal_returns.append({
                            'Signal': 'Sell',
                            'Exit Date': date,
                            'Exit Price': price,
                            'Status': 'Exit Only'
                        })
            
            # Handle open position
            if current_position == 'long':
                last_price = historical_data['Close'].iloc[-1]
                open_trade_return = ((last_price / entry_price) - 1) * 100
                if signal_returns and signal_returns[-1]['Signal'] == 'Buy':
                    signal_returns[-1]['Trade Return'] = open_trade_return
                    signal_returns[-1]['Current Price'] = last_price
        
        logger.info("Creating visualization...")
        # Create visualization
        fig = VisualizationService.create_stock_analysis_chart(
            symbol=ticker,
            data=historical_data,  # Use display period data for visualization
            analysis_dates=analysis_df['Date'].tolist(),
            ratios=analysis_df['Retracement_Ratio_Pct'].tolist(),
            prices=analysis_df['Price'].tolist(),
            appreciation_pcts=analysis_df['Price_Position_Pct'].tolist(),
            regression_results=regression_results,
            crossover_data=crossover_data,
            signal_returns=signal_returns,
            metrics_df=metrics_df
        )
        
        logger.info("Analysis completed successfully!")
        return fig
    
    except Exception as e:
        logger.error(f"Error in create_stock_visualization: {str(e)}")
        raise

def analyze_signals(signal_returns: list) -> Dict[str, Any]:
    """
    Analyze trading signals and calculate performance metrics

    Parameters
    ----------
    signal_returns : list
        List of trading signals and returns

    Returns
    -------
    Dict[str, Any]
        Dictionary containing signal analysis results
    """
    try:
        if not signal_returns:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'average_return': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'total_return': 0
            }

        trades = []
        for signal in signal_returns:
            if 'Trade Return' in signal:
                trades.append(signal['Trade Return'])

        if not trades:
            return {
                'total_trades': len(signal_returns),
                'win_rate': 0,
                'average_return': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'total_return': 0
            }

        winning_trades = len([t for t in trades if t > 0])
        
        return {
            'total_trades': len(trades),
            'win_rate': (winning_trades / len(trades)) * 100 if trades else 0,
            'average_return': np.mean(trades),
            'best_trade': max(trades),
            'worst_trade': min(trades),
            'total_return': sum(trades)
        }
    
    except Exception as e:
        print(f"Error analyzing signals: {str(e)}")
        return None

def format_analysis_summary(ticker: str, historical_data: pd.DataFrame, 
                          signal_analysis: Dict[str, Any]) -> str:
    """
    Format analysis summary for display

    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    historical_data : pd.DataFrame
        Historical price data
    signal_analysis : Dict[str, Any]
        Signal analysis results

    Returns
    -------
    str
        Formatted analysis summary
    """
    try:
        start_date = historical_data.index[0].strftime('%Y-%m-%d')
        end_date = historical_data.index[-1].strftime('%Y-%m-%d')
        start_price = historical_data['Close'].iloc[0]
        end_price = historical_data['Close'].iloc[-1]
        total_return = ((end_price / start_price) - 1) * 100
        
        summary = f"""
Analysis Summary for {ticker}
Period: {start_date} to {end_date}
Starting Price: ${start_price:.2f}
Ending Price: ${end_price:.2f}
Total Return: {total_return:.2f}%

Trading Performance:
Total Trades: {signal_analysis['total_trades']}
Win Rate: {signal_analysis['win_rate']:.1f}%
Average Trade Return: {signal_analysis['average_return']:.2f}%
Best Trade: {signal_analysis['best_trade']:.2f}%
Worst Trade: {signal_analysis['worst_trade']:.2f}%
Total Trading Return: {signal_analysis['total_return']:.2f}%
"""
        return summary
    
    except Exception as e:
        print(f"Error formatting analysis summary: {str(e)}")
        return "Error generating analysis summary"