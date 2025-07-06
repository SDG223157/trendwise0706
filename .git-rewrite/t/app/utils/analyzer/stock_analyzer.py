# app/analyzer/stock_analyzer.py

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Any

from app.utils.data.data_service import DataService
from app.utils.analysis.analysis_service import AnalysisService
from app.utils.visualization.visualization_service import VisualizationService
from app.utils.config.metrics_config import METRICS_TO_FETCH, ANALYSIS_DEFAULTS

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
        Number of days to look back for analysis
    crossover_days : int, optional
        Number of days for crossover analysis

    Returns
    -------
    plotly.graph_objects.Figure
        Complete analysis visualization figure
    """
    analysis_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    print(f"Starting analysis {analysis_id} for {ticker}")
    try:
        # Initialize services
        data_service = DataService()
        
        # Set up dates
        if end_date is None or not end_date.strip():
            end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = data_service.get_analysis_dates(end_date, 'days', lookback_days)
        
        print(f"Fetching data for {ticker} from {start_date} to {end_date}")
        
        # Get historical data
        historical_data = data_service.get_historical_data(ticker, start_date, end_date)
        
        if historical_data.empty:
            raise ValueError(f"No historical data found for {ticker}")
        
        print("Performing technical analysis...")
        # Perform technical analysis
        analysis_df = AnalysisService.analyze_stock_data(historical_data, crossover_days)
        
        # Perform regression analysis
        regression_results = AnalysisService.perform_polynomial_regression(historical_data, future_days=lookback_days)
        
        # Find crossover points
        crossover_data = AnalysisService.find_crossover_points(
            analysis_df['Date'].tolist(),
            analysis_df['Retracement_Ratio_Pct'].tolist(),
            analysis_df['Price_Position_Pct'].tolist(),
            analysis_df['Price'].tolist()
        )
        
        print("Fetching financial metrics...")
        # Get financial metrics
        current_year = datetime.now().year
        start_year = str(current_year - 5)
        end_year = str(current_year)
        
        metrics_df = data_service.create_metrics_table(
            ticker=ticker,
            metrics=METRICS_TO_FETCH,
            start_year=start_year,
            end_year=end_year
        )
        
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
                elif direction == 'down' and current_position == 'long':  # Sell signal
                    exit_price = price
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
            data=historical_data,
            analysis_dates=analysis_df['Date'].tolist(),
            ratios=analysis_df['Retracement_Ratio_Pct'].tolist(),
            prices=analysis_df['Price'].tolist(),
            appreciation_pcts=analysis_df['Price_Position_Pct'].tolist(),
            regression_results=regression_results,
            crossover_data=crossover_data,
            signal_returns=signal_returns,
            metrics_df=metrics_df
        )
        
        print("Analysis completed successfully!")
        return fig
    
    except Exception as e:
        print(f"Error in create_stock_visualization: {str(e)}")
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