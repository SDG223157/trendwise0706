# src/analysis/analysis_service.py

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

class AnalysisService:
    @staticmethod
    def calculate_price_appreciation_pct(current_price, highest_price, lowest_price):
        """Calculate price appreciation percentage relative to range"""
        total_range = highest_price - lowest_price
        if total_range > 0:
            current_from_low = current_price - lowest_price
            return (current_from_low / total_range) * 100
        return 0

    @staticmethod
    def find_crossover_points(dates, series1, series2, prices):
        """Find points where two series cross each other"""
        crossover_points = []
        crossover_values = []
        crossover_directions = []
        crossover_prices = []
        
        s1 = np.array(series1)
        s2 = np.array(series2)
        
        diff = s1 - s2
        for i in range(1, len(diff)):
            if diff[i-1] <= 0 and diff[i] > 0:
                cross_value = (s1[i-1] + s2[i-1]) / 2
                crossover_points.append(dates[i])
                crossover_values.append(cross_value)
                crossover_directions.append('down')
                crossover_prices.append(prices[i])
            elif diff[i-1] >= 0 and diff[i] < 0:
                cross_value = (s1[i-1] + s2[i-1]) / 2
                crossover_points.append(dates[i])
                crossover_values.append(cross_value)
                crossover_directions.append('up')
                crossover_prices.append(prices[i])
        
        return crossover_points, crossover_values, crossover_directions, crossover_prices

    @staticmethod
    def format_regression_equation(coefficients, intercept, max_x):
        """Format regression equation string"""
        terms = []
        if coefficients[2] != 0:
            terms.append(f"{coefficients[2]:.4f}(x/{max_x})²")
        if coefficients[1] != 0:
            sign = "+" if coefficients[1] > 0 else ""
            terms.append(f"{sign}{coefficients[1]:.4f}(x/{max_x})")
        if intercept != 0:
            sign = "+" if intercept > 0 else ""
            terms.append(f"{sign}{intercept:.4f}")
        equation = "ln(y) = " + " ".join(terms)
        return equation

    @staticmethod
    def perform_polynomial_regression(data, future_days=180):
        """Perform polynomial regression analysis"""
        # Transform to log scale
        data['Log_Close'] = np.log(data['Close'])
        
        # Prepare data
        scale = 1
        X = (data.index - data.index[0]).days.values.reshape(-1, 1)
        y = data['Log_Close'].values
        X_scaled = X / (np.max(X) * scale)
        
        # Polynomial regression
        poly_features = PolynomialFeatures(degree=2)
        X_poly = poly_features.fit_transform(X_scaled)
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # Generate predictions
        X_future = np.arange(len(data) + future_days).reshape(-1, 1)
        X_future_scaled = X_future / np.max(X) * scale
        X_future_poly = poly_features.transform(X_future_scaled)
        y_pred_log = model.predict(X_future_poly)
        
        # Transform predictions back
        y_pred = np.exp(y_pred_log)
        
        # Calculate confidence bands
        residuals = y - model.predict(X_poly)
        std_dev = np.std(residuals)
        y_pred_upper = np.exp(y_pred_log + 2 * std_dev)
        y_pred_lower = np.exp(y_pred_log - 2 * std_dev)
        
        # Calculate metrics
        r2 = r2_score(y, model.predict(X_poly))
        coef = model.coef_
        intercept = model.intercept_
        max_x = np.max(X)
        
        # Format equation
        equation = AnalysisService.format_regression_equation(coef, intercept, max_x)
        
        return {
            'predictions': y_pred,
            'upper_band': y_pred_upper,
            'lower_band': y_pred_lower,
            'r2': r2,
            'coefficients': coef,
            'intercept': intercept,
            'std_dev': std_dev,
            'equation': equation,
            'max_x': max_x
        }

    @staticmethod
    def calculate_growth_rates(df):
        """Calculate period-over-period growth rates for financial metrics"""
        growth_rates = {}
        
        for metric in df.index:
            values = df.loc[metric][:-1]  # Exclude CAGR column
            if len(values) > 1:
                growth_rates[metric] = []
                for i in range(1, len(values)):
                    prev_val = float(values.iloc[i-1])
                    curr_val = float(values.iloc[i])
                    if prev_val and prev_val != 0:  # Avoid division by zero
                        growth = ((curr_val / prev_val) - 1) * 100
                        growth_rates[metric].append(growth)
                    else:
                        growth_rates[metric].append(None)
        
        return growth_rates

    @staticmethod
    def analyze_stock_data(data, lookback_days=180):
        """Perform comprehensive stock analysis"""
        analysis_dates = []
        ratios = []
        prices = []
        highest_prices = []
        lowest_prices = []
        appreciation_pcts = []
        
        for current_date in data.index:
            year_start = current_date - timedelta(days=lookback_days)
            mask = (data.index > year_start) & (data.index <= current_date)
            period_data = data.loc[mask]
            
            if len(period_data) < 20:
                continue
                
            current_price = period_data['Close'].iloc[-1]
            highest_price = period_data['Close'].max()
            lowest_price = period_data['Close'].min()
            
            # Calculate ratio
            total_move = highest_price - lowest_price
            if total_move > 0:
                current_retracement = highest_price - current_price
                ratio = (current_retracement / total_move) * 100
            else:
                ratio = 0
                
            # Calculate appreciation percentage
            appreciation_pct = AnalysisService.calculate_price_appreciation_pct(
                current_price, highest_price, lowest_price)
            
            analysis_dates.append(current_date)
            ratios.append(ratio)
            prices.append(current_price)
            highest_prices.append(highest_price)
            lowest_prices.append(lowest_price)
            appreciation_pcts.append(appreciation_pct)
            
        return pd.DataFrame({
            'Date': analysis_dates,
            'Price': prices,
            'High': highest_prices,
            'Low': lowest_prices,
            'Retracement_Ratio_Pct': ratios,
            'Price_Position_Pct': appreciation_pcts
        })