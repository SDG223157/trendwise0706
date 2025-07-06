import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import datetime

def analyze_stock_multi_period(ticker_symbol, period="2y"):
    """
    Analyzes a stock by calculating volatility based on actual daily, weekly, and monthly returns
    
    Parameters:
    ticker_symbol (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
    period (str): Time period for data retrieval (default: '2y' for 2 years)
    
    Returns:
    tuple: Tuple containing daily, weekly, and monthly DataFrames with price and volatility data
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Get daily data
        daily_data = stock.history(period=period)
        if len(daily_data) == 0:
            return None, None, None
        
        # Calculate daily returns and volatility
        daily_data['Return'] = daily_data['Close'].pct_change()
        daily_data['Volatility'] = daily_data['Return'].rolling(window=21).std() * np.sqrt(252)
        daily_data['MA_100'] = daily_data['Close'].rolling(window=100).mean()
        daily_data['MA_200'] = daily_data['Close'].rolling(window=200).mean()
        
        # Only calculate MA_500 and MA_1000 if we have enough data
        if len(daily_data) >= 500:
            daily_data['MA_500'] = daily_data['Close'].rolling(window=500).mean()
        else:
            daily_data['MA_500'] = np.nan
            
        if len(daily_data) >= 1000:
            daily_data['MA_1000'] = daily_data['Close'].rolling(window=1000).mean()
        else:
            daily_data['MA_1000'] = np.nan
        
        # Get weekly data (actual weekly returns, not rolling)
        weekly_data = stock.history(period=period, interval="1wk")
        weekly_data['Return'] = weekly_data['Close'].pct_change()
        weekly_data['Volatility'] = weekly_data['Return'].rolling(window=4).std() * np.sqrt(52)
        
        # Get monthly data (actual monthly returns, not rolling)
        monthly_data = stock.history(period=period, interval="1mo")
        monthly_data['Return'] = monthly_data['Close'].pct_change()
        monthly_data['Volatility'] = monthly_data['Return'].rolling(window=3).std() * np.sqrt(12)
        
        return daily_data, weekly_data, monthly_data
    
    except Exception as e:
        print(f"Error analyzing {ticker_symbol}: {str(e)}")
        return None, None, None

def create_plotly_dashboard(daily_data, weekly_data, monthly_data, ticker_symbol):
    """
    Creates an interactive Plotly dashboard with price and volatility across timeframes
    
    Parameters:
    daily_data, weekly_data, monthly_data: DataFrames with price and calculated metrics
    ticker_symbol (str): Stock ticker symbol for the title
    
    Returns:
    dict: Plotly figure as JSON-serializable dictionary
    """
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
        # Check if we have data for this MA
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
    
    # 2. Weekly and Monthly price charts
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
    
    # 3. Daily volatility
    fig.add_trace(
        go.Scatter(
            x=daily_data.index,
            y=daily_data['Volatility'],
            mode='lines',
            name='Daily Vol',  # Shortened name
            line=dict(color='blue')
        ),
        row=2, col=1
    )
    
    # 4. Weekly and Monthly volatility
    fig.add_trace(
        go.Scatter(
            x=weekly_data.index,
            y=weekly_data['Volatility'],
            mode='lines',
            name='Weekly Vol',  # Shortened name
            line=dict(color='blue')
        ),
        row=2, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=monthly_data.index,
            y=monthly_data['Volatility'],
            mode='lines',
            name='Monthly Vol',  # Shortened name
            line=dict(color='red')
        ),
        row=2, col=2
    )
    
    # 5. Current metrics table
    latest_daily = daily_data.iloc[-1]
    latest_weekly = weekly_data.iloc[-1]
    latest_monthly = monthly_data.iloc[-1]
    
    # Format values and handle NaN
    def format_value(value, is_price=True):
        if pd.isna(value):
            return "N/A"
        if is_price:
            return f"${value:.2f}"
        return f"{value:.4f}"
    
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
                    f"{latest_daily['Return']*100:.2f}%" if not pd.isna(latest_daily['Return']) else "N/A",
                    format_value(latest_daily['Volatility'], False) if 'Volatility' in latest_daily else "N/A",
                    format_value(latest_daily['MA_100']) if 'MA_100' in latest_daily else "N/A",
                    format_value(latest_daily['MA_200']) if 'MA_200' in latest_daily else "N/A",
                    format_value(latest_daily['MA_500']) if 'MA_500' in latest_daily else "N/A",
                    format_value(latest_daily['MA_1000']) if 'MA_1000' in latest_daily else "N/A"
                ],
                [
                    format_value(latest_weekly['Close']),
                    f"{latest_weekly['Return']*100:.2f}%" if not pd.isna(latest_weekly['Return']) else "N/A",
                    format_value(latest_weekly['Volatility'], False) if 'Volatility' in latest_weekly else "N/A",
                    "N/A", "N/A", "N/A", "N/A"
                ],
                [
                    format_value(latest_monthly['Close']),
                    f"{latest_monthly['Return']*100:.2f}%" if not pd.isna(latest_monthly['Return']) else "N/A",
                    format_value(latest_monthly['Volatility'], False) if 'Volatility' in latest_monthly else "N/A",
                    "N/A", "N/A", "N/A", "N/A"
                ]
            ],
            fill_color=[['lavender', 'white']*2],
            align='left',
            font=dict(size=11)
        )
    )
    
    fig.add_trace(current_metrics, row=3, col=1)
    
    # 6. Historical volatility comparison
    # Calculate average volatility over different time periods
    periods = ['30 days', '90 days', '180 days', '1 year', 'All time']
    
    # Function to safely get mean for a slice
    def safe_mean(data, window, column='Volatility'):
        if column not in data.columns:
            return np.nan
        if len(data) >= window and not data[column].isna().all():
            return data[column].iloc[-window:].mean()
        return np.nan
    
    # For daily data
    daily_vol_30d = safe_mean(daily_data, 30)
    daily_vol_90d = safe_mean(daily_data, 90)
    daily_vol_180d = safe_mean(daily_data, 180)
    daily_vol_1y = safe_mean(daily_data, 252)
    daily_vol_all = daily_data['Volatility'].mean() if 'Volatility' in daily_data.columns and not daily_data['Volatility'].isna().all() else np.nan
    
    # For weekly data (4 weeks = ~1 month, 13 weeks = ~3 months, 26 weeks = ~6 months, 52 weeks = 1 year)
    weekly_vol_30d = safe_mean(weekly_data, 4)
    weekly_vol_90d = safe_mean(weekly_data, 13)
    weekly_vol_180d = safe_mean(weekly_data, 26)
    weekly_vol_1y = safe_mean(weekly_data, 52)
    weekly_vol_all = weekly_data['Volatility'].mean() if 'Volatility' in weekly_data.columns and not weekly_data['Volatility'].isna().all() else np.nan
    
    # For monthly data (1 month, 3 months, 6 months, 12 months)
    monthly_vol_30d = safe_mean(monthly_data, 1)
    monthly_vol_90d = safe_mean(monthly_data, 3)
    monthly_vol_180d = safe_mean(monthly_data, 6)
    monthly_vol_1y = safe_mean(monthly_data, 12)
    monthly_vol_all = monthly_data['Volatility'].mean() if 'Volatility' in monthly_data.columns and not monthly_data['Volatility'].isna().all() else np.nan
    
    # Format values for table
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
                [format_vol(daily_vol_30d), format_vol(daily_vol_90d), format_vol(daily_vol_180d), 
                 format_vol(daily_vol_1y), format_vol(daily_vol_all)],
                [format_vol(weekly_vol_30d), format_vol(weekly_vol_90d), format_vol(weekly_vol_180d), 
                 format_vol(weekly_vol_1y), format_vol(weekly_vol_all)],
                [format_vol(monthly_vol_30d), format_vol(monthly_vol_90d), format_vol(monthly_vol_180d), 
                 format_vol(monthly_vol_1y), format_vol(monthly_vol_all)]
            ],
            fill_color='lavender',
            align='left',
            font=dict(size=11)
        )
    )
    
    fig.add_trace(vol_table, row=3, col=2)
    
    # Update layout - Fix the legend overlap issue
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
            itemsizing="constant",  # Make legend items same size
            itemwidth=30,  # Set a fixed width for items
            font=dict(size=10),  # Smaller font
            tracegroupgap=5  # Smaller gap between legend groups
        ),
        hovermode="closest"
    )
    
    # Add more space between the chart title and the plot area
    fig.update_annotations(y=0.95, selector=dict(text=f"{ticker_symbol} - Daily Price & Moving Averages"))
    fig.update_annotations(y=0.95, selector=dict(text=f"{ticker_symbol} - Weekly & Monthly Price"))
    
    # Update axes labels
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=2)
    fig.update_yaxes(title_text="Volatility (Annualized)", row=2, col=1)
    fig.update_yaxes(title_text="Volatility (Annualized)", row=2, col=2)
    
    # Add date range selectors to first plot
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
    
    # Return the figure directly as a dict - we'll jsonify in the route
    return fig

def get_stock_analysis(ticker, period):
    """
    Generate stock analysis for the given ticker and period
    
    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Time period for analysis
    
    Returns:
    tuple: (figure_dict, info_dict) or (None, error_message)
    """
    # Get data for the ticker and period
    daily_data, weekly_data, monthly_data = analyze_stock_multi_period(ticker, period)
    
    if daily_data is None or len(daily_data) == 0:
        return None, f"No data found for {ticker}"
    
    # Create dashboard figure
    fig = create_plotly_dashboard(daily_data, weekly_data, monthly_data, ticker)
    
    # Generate info text
    info = {
        "ticker": ticker,
        "period": period,
        "daily_points": len(daily_data),
        "weekly_points": len(weekly_data),
        "monthly_points": len(monthly_data),
        "start_date": daily_data.index[0].strftime('%Y-%m-%d'),
        "end_date": daily_data.index[-1].strftime('%Y-%m-%d')
    }
    
    return fig, info