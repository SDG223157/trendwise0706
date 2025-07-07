"""
Optimized TrendWise Stock Scoring System
Enhanced with advanced metrics and better differentiation
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import logging
from scipy import stats
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

logger = logging.getLogger(__name__)

class OptimizedScoringSystem:
    """
    Enhanced scoring system with improved metrics and better stock differentiation
    """
    
    # Enhanced configuration with more sophisticated parameters
    CONFIG = {
        'weights': {
            # Dynamic base weights that adjust based on market conditions
            'base': {
                'trend': 0.40,      # Reduced from 0.45-0.50 for better balance
                'return': 0.35,     # Maintained
                'volatility': 0.15, # Base volatility weight
                'momentum': 0.10    # NEW: Separate momentum component
            },
            # Market regime adjustments
            'bull_market': {
                'trend': 0.45,
                'return': 0.35,
                'volatility': 0.10,
                'momentum': 0.10
            },
            'bear_market': {
                'trend': 0.30,
                'return': 0.35,
                'volatility': 0.25,
                'momentum': 0.10
            },
            'high_volatility': {
                'trend': 0.35,
                'return': 0.30,
                'volatility': 0.25,
                'momentum': 0.10
            }
        },
        # Enhanced rating thresholds with finer granularity
        'rating_thresholds': {
            'legendary': 110,
            'exceptional': 95,
            'excellent': 85,
            'very_good': 75,
            'good': 65,
            'above_average': 55,
            'average': 45,
            'below_average': 35,
            'poor': 25,
            'very_poor': 0
        },
        # Advanced metrics thresholds
        'advanced_metrics': {
            'sortino_ratio': {
                'exceptional': 3.0,
                'excellent': 2.0,
                'good': 1.5,
                'neutral': 1.0,
                'poor': 0.5
            },
            'calmar_ratio': {
                'exceptional': 2.0,
                'excellent': 1.5,
                'good': 1.0,
                'neutral': 0.5,
                'poor': 0.25
            },
            'omega_ratio': {
                'exceptional': 2.5,
                'excellent': 2.0,
                'good': 1.5,
                'neutral': 1.0,
                'poor': 0.5
            }
        },
        # Trend confidence multipliers
        'confidence_multipliers': {
            'ultra_high': {'min_r2': 0.90, 'multiplier': 1.25},
            'very_high': {'min_r2': 0.80, 'multiplier': 1.15},
            'high': {'min_r2': 0.70, 'multiplier': 1.10},
            'moderate': {'min_r2': 0.60, 'multiplier': 1.05},
            'low': {'min_r2': 0.50, 'multiplier': 1.00},
            'very_low': {'min_r2': 0.0, 'multiplier': 0.85}
        }
    }
    
    @staticmethod
    def calculate_enhanced_score(
        data: pd.DataFrame,
        symbol: str,
        sp500_data: Optional[pd.DataFrame] = None,
        sp500_params: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate enhanced stock score with advanced metrics
        """
        try:
            # 1. Calculate basic metrics
            basic_metrics = OptimizedScoringSystem._calculate_basic_metrics(data)
            
            # 2. Calculate advanced risk metrics
            risk_metrics = OptimizedScoringSystem._calculate_advanced_risk_metrics(
                data, basic_metrics['returns']
            )
            
            # 3. Perform enhanced trend analysis
            trend_analysis = OptimizedScoringSystem._perform_enhanced_trend_analysis(
                data, basic_metrics
            )
            
            # 4. Calculate momentum indicators
            momentum_score = OptimizedScoringSystem._calculate_momentum_score(
                data, basic_metrics['returns']
            )
            
            # 5. Detect market regime
            market_regime = OptimizedScoringSystem._detect_market_regime(
                sp500_data, sp500_params
            )
            
            # 6. Get dynamic weights based on regime
            weights = OptimizedScoringSystem._get_dynamic_weights(
                market_regime, trend_analysis['r_squared']
            )
            
            # 7. Calculate component scores
            component_scores = OptimizedScoringSystem._calculate_component_scores(
                basic_metrics, risk_metrics, trend_analysis, momentum_score,
                sp500_params, weights
            )
            
            # 8. Apply advanced adjustments
            final_score = OptimizedScoringSystem._apply_advanced_adjustments(
                component_scores, risk_metrics, trend_analysis, weights
            )
            
            # 9. Determine rating
            rating = OptimizedScoringSystem._get_enhanced_rating(final_score)
            
            return {
                'final_score': final_score,
                'rating': rating,
                'components': component_scores,
                'metrics': {
                    'basic': basic_metrics,
                    'risk': risk_metrics,
                    'trend': trend_analysis,
                    'momentum': momentum_score
                },
                'market_regime': market_regime,
                'weights': weights,
                'confidence_level': OptimizedScoringSystem._calculate_confidence_level(
                    trend_analysis['r_squared'], risk_metrics
                )
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced scoring calculation: {str(e)}")
            raise
    
    @staticmethod
    def _calculate_basic_metrics(data: pd.DataFrame) -> Dict:
        """Calculate basic performance metrics"""
        returns = data['Close'].pct_change().dropna()
        log_returns = np.log(data['Close'] / data['Close'].shift(1)).dropna()
        
        # Calculate annualized metrics
        trading_days = len(data)
        years = trading_days / 252
        
        total_return = (data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1
        annual_return = (1 + total_return) ** (1 / years) - 1
        annual_volatility = returns.std() * np.sqrt(252)
        
        # Calculate rolling metrics for stability assessment
        rolling_returns = returns.rolling(window=63)  # 3-month rolling
        rolling_vol = rolling_returns.std() * np.sqrt(252)
        vol_stability = 1 - (rolling_vol.std() / rolling_vol.mean() if rolling_vol.mean() > 0 else 0)
        
        return {
            'returns': returns,
            'log_returns': log_returns,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'total_return': total_return,
            'volatility_stability': vol_stability,
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis()
        }
    
    @staticmethod
    def _calculate_advanced_risk_metrics(data: pd.DataFrame, returns: pd.Series) -> Dict:
        """Calculate advanced risk-adjusted performance metrics"""
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        
        # Sharpe Ratio
        excess_returns = returns - risk_free_rate
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / returns.std()
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_deviation = np.sqrt(252) * downside_returns.std()
        sortino_ratio = np.sqrt(252) * excess_returns.mean() / downside_deviation if downside_deviation > 0 else 0
        
        # Maximum Drawdown and Calmar Ratio
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.cummax()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        annual_return = returns.mean() * 252
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Omega Ratio
        threshold = risk_free_rate
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns <= threshold]
        omega_ratio = gains.sum() / losses.sum() if losses.sum() > 0 else 3.0
        
        # Value at Risk (VaR) and Conditional VaR
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean()
        
        # Ulcer Index (measures downside volatility)
        drawdown_squared = drawdowns ** 2
        ulcer_index = np.sqrt(drawdown_squared.mean())
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'omega_ratio': omega_ratio,
            'max_drawdown': max_drawdown,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'ulcer_index': ulcer_index,
            'risk_adjusted_score': OptimizedScoringSystem._calculate_risk_adjusted_score(
                sharpe_ratio, sortino_ratio, calmar_ratio, omega_ratio
            )
        }
    
    @staticmethod
    def _calculate_risk_adjusted_score(sharpe: float, sortino: float, 
                                     calmar: float, omega: float) -> float:
        """Combine multiple risk metrics into a single score"""
        # Normalize each metric to 0-100 scale
        sharpe_score = min(100, max(0, sharpe * 33.33))  # 3.0 Sharpe = 100
        sortino_score = min(100, max(0, sortino * 25))   # 4.0 Sortino = 100
        calmar_score = min(100, max(0, calmar * 50))     # 2.0 Calmar = 100
        omega_score = min(100, max(0, (omega - 1) * 50)) # 3.0 Omega = 100
        
        # Weighted combination favoring Sortino (downside focus)
        weights = {'sharpe': 0.25, 'sortino': 0.35, 'calmar': 0.20, 'omega': 0.20}
        
        combined_score = (
            sharpe_score * weights['sharpe'] +
            sortino_score * weights['sortino'] +
            calmar_score * weights['calmar'] +
            omega_score * weights['omega']
        )
        
        return combined_score
    
    @staticmethod
    def _perform_enhanced_trend_analysis(data: pd.DataFrame, basic_metrics: Dict) -> Dict:
        """Enhanced trend analysis with multiple indicators"""
        prices = data['Close'].values
        log_prices = np.log(prices)
        
        # 1. Polynomial regression (existing approach)
        X = np.arange(len(prices)).reshape(-1, 1)
        X_scaled = X / len(X)
        
        poly = PolynomialFeatures(degree=2)
        X_poly = poly.fit_transform(X_scaled)
        
        model = LinearRegression()
        model.fit(X_poly, log_prices)
        
        predictions = model.predict(X_poly)
        r_squared = r2_score(log_prices, predictions)
        
        coefficients = model.coef_
        quad_coef = coefficients[2]
        linear_coef = coefficients[1]
        
        # 2. Trend strength using multiple methods
        # Moving average analysis
        ma_20 = data['Close'].rolling(20).mean()
        ma_50 = data['Close'].rolling(50).mean()
        ma_200 = data['Close'].rolling(200).mean()
        
        # Count days above each MA
        days_above_ma20 = (data['Close'] > ma_20).sum() / len(data)
        days_above_ma50 = (data['Close'] > ma_50).sum() / len(data[50:]) if len(data) > 50 else 0.5
        days_above_ma200 = (data['Close'] > ma_200).sum() / len(data[200:]) if len(data) > 200 else 0.5
        
        ma_strength = (days_above_ma20 * 0.2 + days_above_ma50 * 0.3 + days_above_ma200 * 0.5)
        
        # 3. Trend persistence (consecutive positive/negative days)
        returns = basic_metrics['returns']
        sign_changes = np.diff(np.sign(returns))
        persistence = 1 - (np.abs(sign_changes) > 0).sum() / len(sign_changes)
        
        # 4. Trend efficiency (price path efficiency)
        total_movement = np.sum(np.abs(np.diff(prices)))
        net_movement = abs(prices[-1] - prices[0])
        efficiency = net_movement / total_movement if total_movement > 0 else 0
        
        # 5. Acceleration analysis
        if len(data) > 60:
            first_half_return = (prices[len(prices)//2] / prices[0]) - 1
            second_half_return = (prices[-1] / prices[len(prices)//2]) - 1
            acceleration_factor = second_half_return / first_half_return if first_half_return > 0 else 1
        else:
            acceleration_factor = 1.0
        
        # Combine trend indicators
        trend_composite_score = (
            r_squared * 0.3 +
            ma_strength * 0.25 +
            persistence * 0.20 +
            efficiency * 0.15 +
            min(2, max(0, acceleration_factor)) * 0.10
        )
        
        return {
            'r_squared': r_squared,
            'quad_coef': quad_coef,
            'linear_coef': linear_coef,
            'ma_strength': ma_strength,
            'persistence': persistence,
            'efficiency': efficiency,
            'acceleration_factor': acceleration_factor,
            'composite_score': trend_composite_score,
            'trend_quality': OptimizedScoringSystem._classify_trend_quality(
                trend_composite_score, r_squared
            )
        }
    
    @staticmethod
    def _calculate_momentum_score(data: pd.DataFrame, returns: pd.Series) -> Dict:
        """Calculate comprehensive momentum indicators"""
        prices = data['Close'].values
        
        # 1. Rate of Change (ROC) - multiple timeframes
        roc_20 = (prices[-1] / prices[-20] - 1) if len(prices) > 20 else 0
        roc_60 = (prices[-1] / prices[-60] - 1) if len(prices) > 60 else 0
        roc_120 = (prices[-1] / prices[-120] - 1) if len(prices) > 120 else 0
        
        # 2. Relative Strength Index (RSI)
        rsi = OptimizedScoringSystem._calculate_rsi(prices)
        
        # 3. MACD indicators
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = macd - signal
        
        # Recent MACD trend
        recent_macd_trend = 1 if macd_histogram.iloc[-1] > macd_histogram.iloc[-5] else -1
        
        # 4. Volume-weighted momentum (if volume available)
        if 'Volume' in data.columns:
            vwap = (data['Close'] * data['Volume']).sum() / data['Volume'].sum()
            price_to_vwap = prices[-1] / vwap
        else:
            price_to_vwap = 1.0
        
        # 5. Momentum consistency
        recent_returns = returns.tail(20)
        positive_days = (recent_returns > 0).sum() / len(recent_returns)
        
        # Calculate composite momentum score
        momentum_factors = {
            'short_term': roc_20,
            'medium_term': roc_60,
            'long_term': roc_120,
            'rsi': (rsi - 50) / 50,  # Normalize around neutral
            'macd_trend': recent_macd_trend,
            'consistency': positive_days - 0.5,  # Center around 0
            'price_to_vwap': price_to_vwap - 1
        }
        
        # Weighted momentum score
        weights = {
            'short_term': 0.25,
            'medium_term': 0.25,
            'long_term': 0.20,
            'rsi': 0.10,
            'macd_trend': 0.10,
            'consistency': 0.10
        }
        
        composite_momentum = sum(
            momentum_factors[key] * weights.get(key, 0)
            for key in momentum_factors if key != 'price_to_vwap'
        )
        
        # Normalize to 0-100 scale
        momentum_score = 50 + (composite_momentum * 50)
        momentum_score = max(0, min(100, momentum_score))
        
        return {
            'score': momentum_score,
            'factors': momentum_factors,
            'strength': OptimizedScoringSystem._classify_momentum_strength(momentum_score)
        }
    
    @staticmethod
    def _detect_market_regime(sp500_data: Optional[pd.DataFrame], 
                            sp500_params: Optional[Dict]) -> str:
        """Detect current market regime"""
        if sp500_data is None or sp500_params is None:
            return 'normal'
        
        # Use S&P 500 data to determine market regime
        sp500_return = sp500_params.get('annual_return', 0.10)
        sp500_volatility = sp500_params.get('annual_volatility', 0.16)
        
        # Recent trend analysis
        if len(sp500_data) > 60:
            recent_return = (sp500_data['Close'].iloc[-1] / sp500_data['Close'].iloc[-60]) ** (252/60) - 1
            recent_vol = sp500_data['Close'].pct_change().tail(60).std() * np.sqrt(252)
        else:
            recent_return = sp500_return
            recent_vol = sp500_volatility
        
        # Classify regime
        if recent_vol > sp500_volatility * 1.5:
            return 'high_volatility'
        elif recent_return > sp500_return * 1.5 and recent_vol < sp500_volatility * 1.2:
            return 'bull_market'
        elif recent_return < 0 and recent_vol > sp500_volatility:
            return 'bear_market'
        else:
            return 'normal'
    
    @staticmethod
    def _get_dynamic_weights(market_regime: str, r_squared: float) -> Dict:
        """Get dynamic weights based on market regime and confidence"""
        # Start with regime-based weights
        regime_weights = {
            'normal': OptimizedScoringSystem.CONFIG['weights']['base'],
            'bull_market': OptimizedScoringSystem.CONFIG['weights']['bull_market'],
            'bear_market': OptimizedScoringSystem.CONFIG['weights']['bear_market'],
            'high_volatility': OptimizedScoringSystem.CONFIG['weights']['high_volatility']
        }
        
        weights = regime_weights.get(market_regime, regime_weights['normal']).copy()
        
        # Adjust based on R² confidence
        if r_squared > 0.85:
            # High confidence - increase trend weight
            weights['trend'] += 0.05
            weights['return'] -= 0.05
        elif r_squared < 0.60:
            # Low confidence - decrease trend weight
            weights['trend'] -= 0.10
            weights['return'] += 0.05
            weights['volatility'] += 0.05
        
        # Normalize weights to sum to 1
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}
        
        return weights
    
    @staticmethod
    def _calculate_component_scores(basic_metrics: Dict, risk_metrics: Dict,
                                  trend_analysis: Dict, momentum_score: Dict,
                                  sp500_params: Optional[Dict], weights: Dict) -> Dict:
        """Calculate individual component scores"""
        # Default S&P 500 parameters if not provided
        if sp500_params is None:
            sp500_params = {
                'annual_return': 0.10,
                'annual_volatility': 0.16
            }
        
        # 1. Return Score (Enhanced)
        return_outperformance = basic_metrics['annual_return'] - sp500_params['annual_return']
        if return_outperformance > 0:
            # Progressive scaling for outperformance
            if return_outperformance > 0.50:  # 50%+ outperformance
                return_score = 85 + min(15, (return_outperformance - 0.50) * 20)
            elif return_outperformance > 0.25:
                return_score = 70 + (return_outperformance - 0.25) * 60
            elif return_outperformance > 0.10:
                return_score = 60 + (return_outperformance - 0.10) * 67
            else:
                return_score = 50 + return_outperformance * 100
        else:
            # Moderate penalties for underperformance
            return_score = 50 + return_outperformance * 80
        
        # Adjust for risk-adjusted performance
        risk_adjustment = risk_metrics['risk_adjusted_score'] / 100
        return_score = return_score * (0.7 + 0.3 * risk_adjustment)
        
        # 2. Volatility Score (Enhanced)
        vol_ratio = basic_metrics['annual_volatility'] / sp500_params['annual_volatility']
        
        # Consider volatility stability
        stability_bonus = basic_metrics['volatility_stability'] * 10
        
        if vol_ratio <= 0.6:
            volatility_score = 90 + stability_bonus
        elif vol_ratio <= 0.8:
            volatility_score = 80 + stability_bonus
        elif vol_ratio <= 1.0:
            volatility_score = 65 + stability_bonus
        elif vol_ratio <= 1.3:
            volatility_score = 50 - (vol_ratio - 1.0) * 50 + stability_bonus
        else:
            volatility_score = max(20, 35 - (vol_ratio - 1.3) * 20) + stability_bonus
        
        # Adjust for downside protection (Sortino ratio consideration)
        if risk_metrics['sortino_ratio'] > risk_metrics['sharpe_ratio'] * 1.2:
            volatility_score += 5  # Bonus for better downside protection
        
        # 3. Trend Score (Enhanced)
        base_trend_score = 50
        
        # Trend quality adjustment
        quality_multiplier = trend_analysis['composite_score']
        
        # Direction and strength
        if trend_analysis['linear_coef'] > 0:
            direction_bonus = min(25, trend_analysis['linear_coef'] * 50)
        else:
            direction_bonus = max(-25, trend_analysis['linear_coef'] * 30)
        
        # Acceleration/deceleration adjustment
        if trend_analysis['quad_coef'] > 0 and trend_analysis['linear_coef'] > 0:
            accel_bonus = min(15, trend_analysis['quad_coef'] * 30)
        elif trend_analysis['quad_coef'] < 0 and trend_analysis['r_squared'] < 0.7:
            accel_bonus = max(-15, trend_analysis['quad_coef'] * 20)
        else:
            accel_bonus = 0
        
        trend_score = base_trend_score + (direction_bonus + accel_bonus) * quality_multiplier
        
        # 4. Momentum Score (already calculated)
        
        return {
            'return': max(0, min(100, return_score)),
            'volatility': max(0, min(100, volatility_score)),
            'trend': max(0, min(100, trend_score)),
            'momentum': momentum_score['score'],
            'risk_adjusted': risk_metrics['risk_adjusted_score']
        }
    
    @staticmethod
    def _apply_advanced_adjustments(component_scores: Dict, risk_metrics: Dict,
                                  trend_analysis: Dict, weights: Dict) -> float:
        """Apply advanced adjustments and calculate final score"""
        # Base weighted score
        weighted_score = sum(
            component_scores[component] * weights.get(component, 0)
            for component in ['return', 'volatility', 'trend', 'momentum']
        )
        
        # Confidence multiplier based on R²
        for tier, config in OptimizedScoringSystem.CONFIG['confidence_multipliers'].items():
            if trend_analysis['r_squared'] >= config['min_r2']:
                confidence_multiplier = config['multiplier']
                break
        
        # Quality bonus for exceptional risk-adjusted performance
        quality_bonus = 0
        if risk_metrics['sharpe_ratio'] > 2.0 and risk_metrics['sortino_ratio'] > 2.5:
            quality_bonus = 10
        elif risk_metrics['sharpe_ratio'] > 1.5 and risk_metrics['sortino_ratio'] > 2.0:
            quality_bonus = 5
        
        # Consistency bonus
        if trend_analysis['persistence'] > 0.65 and trend_analysis['efficiency'] > 0.35:
            consistency_bonus = 5
        else:
            consistency_bonus = 0
        
        # Calculate final score
        final_score = (weighted_score * confidence_multiplier) + quality_bonus + consistency_bonus
        
        # Apply bounds
        final_score = max(0, min(120, final_score))
        
        return round(final_score, 2)
    
    @staticmethod
    def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50  # Neutral RSI
        
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        if down == 0:
            return 100
        
        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def _classify_trend_quality(composite_score: float, r_squared: float) -> str:
        """Classify trend quality based on composite score"""
        if composite_score > 0.80 and r_squared > 0.85:
            return "Exceptional"
        elif composite_score > 0.70 and r_squared > 0.75:
            return "Strong"
        elif composite_score > 0.60 and r_squared > 0.65:
            return "Good"
        elif composite_score > 0.50:
            return "Moderate"
        elif composite_score > 0.40:
            return "Weak"
        else:
            return "Poor"
    
    @staticmethod
    def _classify_momentum_strength(score: float) -> str:
        """Classify momentum strength"""
        if score > 80:
            return "Very Strong"
        elif score > 65:
            return "Strong"
        elif score > 50:
            return "Positive"
        elif score > 35:
            return "Negative"
        elif score > 20:
            return "Weak"
        else:
            return "Very Weak"
    
    @staticmethod
    def _get_enhanced_rating(score: float) -> str:
        """Get enhanced rating with finer granularity"""
        for rating, threshold in OptimizedScoringSystem.CONFIG['rating_thresholds'].items():
            if score >= threshold:
                return rating
        return "very_poor"
    
    @staticmethod
    def _calculate_confidence_level(r_squared: float, risk_metrics: Dict) -> str:
        """Calculate overall confidence level in the analysis"""
        confidence_score = 0
        
        # R² contribution (40%)
        confidence_score += r_squared * 40
        
        # Risk metrics stability (30%)
        if risk_metrics['sharpe_ratio'] > 1.0 and risk_metrics['max_drawdown'] > -0.30:
            confidence_score += 20
        elif risk_metrics['sharpe_ratio'] > 0.5:
            confidence_score += 10
        
        # Consistency metrics (30%)
        if risk_metrics['sortino_ratio'] > risk_metrics['sharpe_ratio']:
            confidence_score += 15
        if risk_metrics['omega_ratio'] > 1.5:
            confidence_score += 15
        
        # Classify confidence
        if confidence_score > 80:
            return "Very High"
        elif confidence_score > 65:
            return "High"
        elif confidence_score > 50:
            return "Moderate"
        elif confidence_score > 35:
            return "Low"
        else:
            return "Very Low"