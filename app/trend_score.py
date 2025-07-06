import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from typing import Dict, Union, Tuple
import warnings
warnings.filterwarnings('ignore')

class CompleteTrendAnalyzer:
    """
    Complete trend analysis system with integrated bullish/bearish scoring
    """
    def __init__(self, symbol: str, period_years: float = 2):
        self.symbol = symbol
        self.period_years = period_years
        self.trading_days = int(252 * period_years)
        
    def fetch_data(self) -> pd.DataFrame:
        """Fetch market data"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=int(self.period_years * 365 * 1.1))
            
            data = yf.download(self.symbol, start=start_date, end=end_date)
            if len(data) < self.trading_days:
                raise ValueError(f"Insufficient data: got {len(data)} days, need {self.trading_days}")
            
            self.data = data
            self.price_data = data['Close'].values
            self.dates = data.index
            return data
            
        except Exception as e:
            raise Exception(f"Error fetching data for {self.symbol}: {str(e)}")
    
    def perform_regression(self) -> Dict[str, float]:
        """Perform polynomial regression"""
        try:
            log_prices = np.log(self.price_data)
            X = np.arange(len(self.price_data)).reshape(-1, 1)
            X_scaled = X / len(X)
            
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X_scaled)
            
            model = LinearRegression()
            model.fit(X_poly, log_prices)
            
            y_pred = model.predict(X_poly)
            
            self.regression_results = {
                'quad_coef': model.coef_[2],
                'linear_coef': model.coef_[1],
                'constant': model.intercept_,
                'r_squared': r2_score(log_prices, y_pred),
                'fitted_values': np.exp(y_pred)
            }
            
            return self.regression_results
            
        except Exception as e:
            raise Exception(f"Error in regression analysis: {str(e)}")
    
    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate market metrics"""
        returns = np.diff(self.price_data) / self.price_data[:-1]
        log_returns = np.diff(np.log(self.price_data))
        
        total_return = (self.price_data[-1] - self.price_data[0]) / self.price_data[0]
        
        self.metrics = {
            'total_return': total_return,
            'daily_volatility': np.std(log_returns),
            'annual_volatility': np.std(log_returns) * np.sqrt(252),
            'annualized_return': (1 + total_return)**(1/self.period_years) - 1,
            'skewness': pd.Series(returns).skew(),
            'kurtosis': pd.Series(returns).kurtosis(),
            'daily_returns': returns,
            'log_returns': log_returns
        }
        
        return self.metrics
    
    def calculate_benchmarks(self) -> Dict[str, float]:
        """Calculate robust benchmarks"""
        vol_linear = self.metrics['annual_volatility'] * np.sqrt(self.period_years)
        vol_quad = self.metrics['annual_volatility'] / np.sqrt(self.trading_days)
        
        return_linear = abs(self.metrics['total_return'] / self.period_years)
        return_quad = self.metrics['daily_volatility'] / np.sqrt(self.trading_days)
        
        vol_weight = 0.6 if self.metrics['annual_volatility'] <= 0.25 else 0.8
        return_weight = 1 - vol_weight
        
        self.benchmarks = {
            'linear': vol_linear * vol_weight + return_linear * return_weight,
            'quadratic': vol_quad * 0.7 + return_quad * 0.3
        }
        
        return self.benchmarks
    
    def calculate_bullish_bearish_score(self) -> Dict[str, float]:
        """
        Calculate final score from 100 (most bullish) to 0 (most bearish)
        """
        # 1. Extract key components
        quad_coef = self.regression_results['quad_coef']
        linear_coef = self.regression_results['linear_coef']
        r_squared = self.regression_results['r_squared']
        
        # 2. Calculate trend components
        trend_score = 50  # Neutral base
        
        # Linear component (max ±25 points)
        linear_impact = linear_coef / self.benchmarks['linear']
        trend_score += 25 * min(1, max(-1, linear_impact))
        
        # Quadratic component (max ±15 points)
        quad_impact = quad_coef / self.benchmarks['quadratic']
        if (quad_coef > 0 and linear_coef > 0) or (quad_coef < 0 and linear_coef < 0):
            # Reinforcing trend
            trend_score += 15 * min(1, max(-1, quad_impact))
        else:
            # Counteracting trend
            trend_score -= 15 * min(1, max(-1, abs(quad_impact)))
        
        # 3. Momentum component (max ±10 points)
        recent_returns = self.metrics['log_returns'][-20:]  # Last month
        momentum = np.mean(recent_returns) * np.sqrt(252)
        momentum_score = 10 * min(1, max(-1, momentum / self.metrics['annual_volatility']))
        
        # 4. Apply strength multiplier
        strength_multiplier = 0.5 + (0.5 * r_squared)  # Range: 0.5-1.0
        
        # 5. Calculate final score
        raw_score = trend_score + momentum_score
        final_score = raw_score * strength_multiplier
        
        # 6. Normalize to 0-100 range
        final_score = min(100, max(0, final_score))
        
        return {
            'final_score': final_score,
            'components': {
                'trend_score': trend_score,
                'momentum_score': momentum_score,
                'strength_multiplier': strength_multiplier,
                'linear_impact': linear_impact,
                'quad_impact': quad_impact
            },
            'interpretation': self._interpret_bullish_bearish_score(final_score)
        }
    
    def _interpret_bullish_bearish_score(self, score: float) -> str:
        """Interpret the bullish/bearish score"""
        if score >= 90: return "Extremely Bullish"
        elif score >= 80: return "Very Bullish"
        elif score >= 65: return "Bullish"
        elif score >= 55: return "Slightly Bullish"
        elif score > 45: return "Neutral"
        elif score > 35: return "Slightly Bearish"
        elif score > 20: return "Bearish"
        elif score > 10: return "Very Bearish"
        else: return "Extremely Bearish"
    
    def run_analysis(self) -> Dict[str, Union[float, str, Dict]]:
        """Run complete analysis pipeline"""
        try:
            # Fetch and analyze data
            self.fetch_data()
            self.perform_regression()
            self.calculate_metrics()
            self.calculate_benchmarks()
            
            # Calculate bullish/bearish score
            score_results = self.calculate_bullish_bearish_score()
            
            return {
                'symbol': self.symbol,
                'period_years': self.period_years,
                'bull_bear_score': score_results,
                'regression': self.regression_results,
                'metrics': self.metrics,
                'benchmarks': self.benchmarks
            }
            
        except Exception as e:
            raise Exception(f"Error in analysis pipeline: {str(e)}")

def format_analysis_report(results: Dict) -> str:
    """Format analysis results into a readable report"""
    report = []
    
    report.append(f"\n=== ANALYSIS REPORT FOR {results['symbol']} ===")
    report.append(f"Period: {results['period_years']:.1f} years")
    
    score = results['bull_bear_score']
    report.append(f"\nBULLISH/BEARISH SCORE: {score['final_score']:.2f}")
    report.append(f"Interpretation: {score['interpretation']}")
    
    report.append("\nSCORE COMPONENTS:")
    components = score['components']
    report.append(f"Base Trend Score: {components['trend_score']:.2f}")
    report.append(f"Momentum Impact: {components['momentum_score']:.2f}")
    report.append(f"Strength Multiplier: {components['strength_multiplier']:.2f}")
    
    report.append("\nKEY METRICS:")
    report.append(f"Annual Return: {results['metrics']['annualized_return']*100:.1f}%")
    report.append(f"Annual Volatility: {results['metrics']['annual_volatility']*100:.1f}%")
    report.append(f"R-squared: {results['regression']['r_squared']:.4f}")
    
    return "\n".join(report)

# Example usage
if __name__ == "__main__":
    # Analyze a stock/index
    symbol = "BA"  # Example: China ETF
    analyzer = CompleteTrendAnalyzer(symbol, period_years=2)
    results = analyzer.run_analysis()
    
    # Print formatted report
    print(format_analysis_report(results))