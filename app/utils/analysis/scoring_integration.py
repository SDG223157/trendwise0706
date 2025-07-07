"""
Integration module for using the Optimized Scoring System
Provides compatibility layer with existing TrendWise infrastructure
"""

import logging
from typing import Dict, Optional
import pandas as pd
from .optimized_scoring_system import OptimizedScoringSystem
from .analysis_service import AnalysisService

logger = logging.getLogger(__name__)

class ScoringIntegration:
    """
    Integration class that allows using both the original and optimized scoring systems
    """
    
    @staticmethod
    def compare_scoring_methods(
        data: pd.DataFrame,
        symbol: str,
        sp500_data: Optional[pd.DataFrame] = None,
        use_optimized: bool = True
    ) -> Dict:
        """
        Compare results from both scoring systems
        
        Args:
            data: Stock price data
            symbol: Stock symbol
            sp500_data: S&P 500 benchmark data
            use_optimized: Whether to include optimized scoring
            
        Returns:
            Comparison results with both scores
        """
        try:
            results = {}
            
            # 1. Get original scoring
            logger.info(f"Calculating original score for {symbol}")
            original_analysis = AnalysisService.perform_polynomial_regression(
                data=data,
                symbol=symbol,
                calculate_sp500_baseline=True
            )
            
            if 'total_score' in original_analysis:
                results['original'] = {
                    'final_score': original_analysis['total_score']['score'],
                    'rating': original_analysis['total_score']['rating'],
                    'components': original_analysis['total_score']['components'],
                    'r_squared': original_analysis['r2'],
                    'weights': original_analysis['total_score']['weights']
                }
            
            # 2. Get optimized scoring if requested
            if use_optimized:
                logger.info(f"Calculating optimized score for {symbol}")
                
                # Extract S&P 500 parameters from original analysis
                sp500_params = None
                if 'total_score' in original_analysis and 'benchmark' in original_analysis['total_score']:
                    sp500_params = {
                        'annual_return': original_analysis['total_score']['benchmark']['sp500_return'] / 100,
                        'annual_volatility': original_analysis['total_score']['benchmark']['sp500_volatility'] / 100
                    }
                
                optimized_results = OptimizedScoringSystem.calculate_enhanced_score(
                    data=data,
                    symbol=symbol,
                    sp500_data=sp500_data,
                    sp500_params=sp500_params
                )
                
                results['optimized'] = optimized_results
            
            # 3. Calculate differences and improvements
            if 'original' in results and 'optimized' in results:
                results['comparison'] = ScoringIntegration._calculate_comparison(
                    results['original'], results['optimized']
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in scoring comparison: {str(e)}")
            raise
    
    @staticmethod
    def get_enhanced_stock_analysis(
        data: pd.DataFrame,
        symbol: str,
        sp500_data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Get enhanced analysis using the optimized scoring system
        with backward compatibility
        
        Returns results in a format compatible with existing TrendWise UI
        """
        try:
            # Get original analysis for compatibility
            original_analysis = AnalysisService.perform_polynomial_regression(
                data=data,
                symbol=symbol,
                calculate_sp500_baseline=True
            )
            
            # Extract S&P 500 parameters
            sp500_params = None
            if 'total_score' in original_analysis and 'benchmark' in original_analysis['total_score']:
                sp500_params = {
                    'annual_return': original_analysis['total_score']['benchmark']['sp500_return'] / 100,
                    'annual_volatility': original_analysis['total_score']['benchmark']['sp500_volatility'] / 100
                }
            
            # Get optimized scoring
            optimized_results = OptimizedScoringSystem.calculate_enhanced_score(
                data=data,
                symbol=symbol,
                sp500_data=sp500_data,
                sp500_params=sp500_params
            )
            
            # Merge results for backward compatibility
            enhanced_analysis = original_analysis.copy()
            
            # Update the total_score section with optimized results
            if 'total_score' in enhanced_analysis:
                # Keep original structure but update with optimized values
                enhanced_analysis['total_score']['score'] = optimized_results['final_score']
                enhanced_analysis['total_score']['rating'] = ScoringIntegration._convert_rating(
                    optimized_results['rating']
                )
                
                # Add enhanced metrics
                enhanced_analysis['total_score']['enhanced_metrics'] = {
                    'risk_metrics': optimized_results['metrics']['risk'],
                    'momentum': optimized_results['metrics']['momentum'],
                    'trend_quality': optimized_results['metrics']['trend']['trend_quality'],
                    'market_regime': optimized_results['market_regime'],
                    'confidence_level': optimized_results['confidence_level']
                }
                
                # Update component scores with optimized values
                components = enhanced_analysis['total_score']['components']
                opt_components = optimized_results['components']
                
                # Map optimized scores to original format
                if 'trend' in components:
                    components['trend']['score'] = opt_components['trend']
                    components['trend']['enhanced_quality'] = (
                        optimized_results['metrics']['trend']['trend_quality']
                    )
                
                if 'return' in components:
                    components['return']['score'] = opt_components['return']
                    components['return']['risk_adjusted'] = opt_components['risk_adjusted']
                
                if 'volatility' in components:
                    components['volatility']['score'] = opt_components['volatility']
                    components['volatility']['stability'] = (
                        optimized_results['metrics']['basic']['volatility_stability']
                    )
                
                # Add momentum as a new component
                components['momentum'] = {
                    'score': opt_components['momentum'],
                    'strength': optimized_results['metrics']['momentum']['strength'],
                    'factors': optimized_results['metrics']['momentum']['factors']
                }
            
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis: {str(e)}")
            # Fall back to original analysis
            return original_analysis
    
    @staticmethod
    def _calculate_comparison(original: Dict, optimized: Dict) -> Dict:
        """Calculate differences between original and optimized scoring"""
        comparison = {
            'score_difference': optimized['final_score'] - original['final_score'],
            'improvements': []
        }
        
        # Check for improvements
        if optimized['final_score'] > original['final_score']:
            comparison['improvements'].append(
                f"Score improved by {comparison['score_difference']:.2f} points"
            )
        
        # Compare confidence levels
        if 'confidence_level' in optimized:
            comparison['confidence'] = {
                'original': 'Based on R² only',
                'optimized': optimized['confidence_level']
            }
        
        # Compare risk metrics
        if 'risk' in optimized['metrics']:
            risk_metrics = optimized['metrics']['risk']
            comparison['risk_analysis'] = {
                'sharpe_ratio': risk_metrics['sharpe_ratio'],
                'sortino_ratio': risk_metrics['sortino_ratio'],
                'max_drawdown': risk_metrics['max_drawdown'],
                'risk_adjusted_score': risk_metrics['risk_adjusted_score']
            }
            comparison['improvements'].append("Added comprehensive risk analysis")
        
        # Compare trend analysis
        if 'trend' in optimized['metrics']:
            trend_metrics = optimized['metrics']['trend']
            comparison['trend_analysis'] = {
                'quality': trend_metrics['trend_quality'],
                'persistence': trend_metrics['persistence'],
                'efficiency': trend_metrics['efficiency']
            }
            comparison['improvements'].append("Enhanced trend analysis with multiple indicators")
        
        # Momentum addition
        if 'momentum' in optimized['components']:
            comparison['momentum_added'] = {
                'score': optimized['components']['momentum'],
                'strength': optimized['metrics']['momentum']['strength']
            }
            comparison['improvements'].append("Added momentum analysis component")
        
        return comparison
    
    @staticmethod
    def _convert_rating(optimized_rating: str) -> str:
        """Convert optimized rating to original rating format"""
        rating_map = {
            'legendary': 'Excellent ★★★★★★★',
            'exceptional': 'Excellent ★★★★★★',
            'excellent': 'Excellent ★★★★★',
            'very_good': 'Very Good ★★★★',
            'good': 'Good ★★★',
            'above_average': 'Good ★★★',
            'average': 'Fair ★★',
            'below_average': 'Fair ★★',
            'poor': 'Poor ★',
            'very_poor': 'Poor ★'
        }
        
        return rating_map.get(optimized_rating, optimized_rating)


# Example usage function
def demonstrate_optimized_scoring():
    """
    Demonstration of how to use the optimized scoring system
    """
    # This would be called from your existing routes or analysis functions
    
    # Example 1: Direct comparison
    # results = ScoringIntegration.compare_scoring_methods(
    #     data=stock_data,
    #     symbol='AAPL',
    #     sp500_data=sp500_data,
    #     use_optimized=True
    # )
    
    # Example 2: Enhanced analysis with backward compatibility
    # enhanced = ScoringIntegration.get_enhanced_stock_analysis(
    #     data=stock_data,
    #     symbol='AAPL',
    #     sp500_data=sp500_data
    # )
    
    pass