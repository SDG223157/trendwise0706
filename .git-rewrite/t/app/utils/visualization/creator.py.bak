# src/visualization/creator.py
import pandas as pd
from datetime import datetime
from app.utils.config.metrics_config import METRICS_TO_FETCH, ANALYSIS_DEFAULTS
from app.utils.config.api_config import ROIC_API
from app.utils.data.data_service import DataService
from app.utils.analysis.analysis_service import AnalysisService
from app.utils.visualization.visualization_service import VisualizationService

def create_stock_visualization(
    ticker: str, 
    end_date: str = None, 
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
        Number of days to look back for analysis (default from config)
    crossover_days : int, optional
        Number of days for crossover analysis (default from config)

    Returns
    -------
    plotly.graph_objects.Figure
        Complete analysis visualization
    """
    try:
        # Initialize services
        data_service = DataService()
        
        # Set up dates
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = data_service.get_analysis_dates(end_date, 'days', lookback_days)
        
        print(f"Fetching data for {ticker} from {start_date} to {end_date}")
        
        # Get historical data
        historical_data = data_service.get_historical_data(ticker, start_date, end_date)
        
        if historical_data.empty:
            raise ValueError(f"No historical data found for {ticker}")
        
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
        
        # Get financial metrics
        current_year = datetime.now().year
        start_year = str(current_year - 5)
        end_year = str(current_year)
        
        print("Fetching financial metrics...")
        metrics_df = data_service.create_metrics_table(
            ticker=ticker,
            metrics=METRICS_TO_FETCH,
            start_year=start_year,
            end_year=end_year
        )
        
        # Prepare signal returns data
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
        
        # Print signal analysis
        if signal_returns:
            VisualizationService.print_signal_analysis(pd.DataFrame(signal_returns))
        
        return fig
    
    except Exception as e:
        print(f"Error in create_stock_visualization: {str(e)}")
        raise

def save_visualization(fig, ticker: str, output_dir: str = "outputs") -> dict:
    """
    Save visualization in multiple formats

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        The visualization figure to save
    ticker : str
        Stock ticker symbol for filename
    output_dir : str
        Directory to save outputs

    Returns
    -------
    dict
        Dictionary containing paths to saved files
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate base filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"{ticker}_analysis_{timestamp}"
    
    saved_files = {}
    
    try:
        # Save as interactive HTML
        html_path = os.path.join(output_dir, f"{base_filename}.html")
        fig.write_html(
            html_path,
            include_plotlyjs=True,
            full_html=True,
            auto_open=True
        )
        saved_files['html'] = html_path
        print(f"Interactive HTML saved to: {html_path}")
        
        try:
            # Save as static image (PNG)
            png_path = os.path.join(output_dir, f"{base_filename}.png")
            fig.write_image(
                png_path,
                width=1920,
                height=1080,
                scale=2
            )
            saved_files['png'] = png_path
            print(f"Static PNG saved to: {png_path}")
            
            # Save as PDF
            pdf_path = os.path.join(output_dir, f"{base_filename}.pdf")
            fig.write_image(
                pdf_path,
                width=1920,
                height=1080
            )
            saved_files['pdf'] = pdf_path
            print(f"PDF saved to: {pdf_path}")
            
        except Exception as e:
            print(f"Warning: Could not save static images. Error: {str(e)}")
            print("You may need to install additional dependencies:")
            print("pip install -U kaleido")
    
    except Exception as e:
        print(f"Error saving visualization: {str(e)}")
        raise
    
    return saved_files