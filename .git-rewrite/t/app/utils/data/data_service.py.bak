# app/data/data_service.py

import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from app.utils.config.metrics_config import METRICS_MAP, CAGR_METRICS

class DataService:
    def __init__(self):
        """Initialize DataService with API configuration and metrics mapping"""
        self.API_KEY = "a365bff224a6419fac064dd52e1f80d9"
        self.BASE_URL = "https://api.roic.ai/v1/rql"
        self.METRICS = METRICS_MAP
        self.CAGR_METRICS = CAGR_METRICS

    def get_historical_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical price data using yfinance

        Parameters:
        -----------
        ticker : str
            Stock ticker symbol
        start_date : str
            Start date in YYYY-MM-DD format
        end_date : str
            End date in YYYY-MM-DD format

        Returns:
        --------
        pd.DataFrame
            DataFrame containing historical price data
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(start=start_date, end=end_date)
            
            if df.empty:
                raise ValueError(f"No data found for {ticker} in the specified date range")
            
            df.index = df.index.tz_localize(None)
            return df
            
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {str(e)}")
            raise

    def get_financial_data(self, ticker: str, metric_description: str, 
                         start_year: str, end_year: str) -> pd.Series:
        """
        Fetch financial metrics data from ROIC API

        Parameters:
        -----------
        ticker : str
            Stock ticker symbol
        metric_description : str
            Description of the metric to fetch
        start_year : str
            Start year in YYYY format
        end_year : str
            End year in YYYY format

        Returns:
        --------
        pd.Series or None
            Series containing financial metric data or None if data not available
        """
        metric_field = self.METRICS.get(metric_description.lower())
        if not metric_field:
            print(f"Warning: Unknown metric '{metric_description}', skipping...")
            return None

        query = f"get({metric_field}(fa_period_reference=range('{start_year}', '{end_year}'))) for('{ticker}')"
        url = f"{self.BASE_URL}?query={query}&apikey={self.API_KEY}"

        try:
            response = requests.get(url)
            response.raise_for_status()

            df = pd.DataFrame(response.json())
            if df.empty:
                print(f"No data available for {metric_description}")
                return None

            df.columns = df.iloc[0]
            df = df.drop(0).reset_index(drop=True)

            years = df['fiscal_year'].astype(int)
            values = df[metric_field].astype(float)

            return pd.Series(values.values, index=years, name=metric_description)
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed for {metric_description}: {str(e)}")
            return None
        except Exception as e:
            print(f"Error processing data for {metric_description}: {str(e)}")
            return None

    def get_analysis_dates(self, end_date: str, lookback_type: str, 
                         lookback_value: int) -> str:
        """
        Calculate start date based on lookback period

        Parameters:
        -----------
        end_date : str
            End date in YYYY-MM-DD format
        lookback_type : str
            Type of lookback period ('quarters' or 'days')
        lookback_value : int
            Number of quarters or days to look back

        Returns:
        --------
        str
            Start date in YYYY-MM-DD format
        """
        try:
            # Handle None or empty end_date
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
                
            # Validate date format
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                print(f"Invalid date format: {end_date}, using current date")
                end_dt = datetime.now()
                
            if lookback_type == 'quarters':
                start_dt = end_dt - relativedelta(months=3*lookback_value)
            else:  # days
                start_dt = end_dt - relativedelta(days=lookback_value)
                
            return start_dt.strftime("%Y-%m-%d")
            
        except Exception as e:
            print(f"Error calculating analysis dates: {str(e)}")
            raise

    def create_metrics_table(self, ticker: str, metrics: list, 
                           start_year: str, end_year: str) -> pd.DataFrame:
        """
        Creates a combined table of all metrics with selective growth rates

        Parameters:
        -----------
        ticker : str
            Stock ticker symbol
        metrics : list
            List of metrics to fetch
        start_year : str
            Start year in YYYY format
        end_year : str
            End year in YYYY format

        Returns:
        --------
        pd.DataFrame or None
            DataFrame containing metrics and growth rates or None if no data available
        """
        data = {}
        growth_rates = {}

        for metric in metrics:
            metric = metric.lower()
            series = self.get_financial_data(ticker.upper(), metric, start_year, end_year)
            
            if series is not None:
                data[metric] = series

                # Calculate CAGR only for specified metrics
                if metric in self.CAGR_METRICS:
                    try:
                        first_value = series.iloc[0]
                        last_value = series.iloc[-1]
                        num_years = len(series) - 1
                        if num_years > 0 and first_value > 0 and last_value > 0:
                            growth_rate = ((last_value / first_value) ** (1 / num_years) - 1) * 100
                            growth_rates[metric] = growth_rate
                    except Exception as e:
                        print(f"Error calculating CAGR for {metric}: {str(e)}")
                        growth_rates[metric] = None

        if data:
            try:
                # Create main DataFrame with metrics
                df = pd.DataFrame(data).T

                # Add growth rates column only for specified metrics
                df['CAGR %'] = None  # Initialize with None
                for metric in self.CAGR_METRICS:
                    if metric in growth_rates and metric in df.index:
                        df.at[metric, 'CAGR %'] = growth_rates[metric]

                return df
            except Exception as e:
                print(f"Error creating metrics table: {str(e)}")
                return None
        
        return None

    def calculate_returns(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate daily returns for a price series

        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame containing price data

        Returns:
        --------
        pd.Series
            Series containing daily returns
        """
        try:
            if 'Close' not in df.columns:
                raise ValueError("Price data must contain 'Close' column")
                
            returns = df['Close'].pct_change()
            returns.fillna(0, inplace=True)
            return returns
            
        except Exception as e:
            print(f"Error calculating returns: {str(e)}")
            raise