"""
Consolidated Refinement System for TrendWise Stock Scoring
Eliminates duplications and ensures single-source adjustments

This module replaces the 16 overlapping refinements with 4 consolidated ones:
- REFINEMENT A: Risk-Adjusted Performance (replaces R2, R3, R8, R9)
- REFINEMENT B: Reliability-Based Adjustments (replaces R4, R5, R7)  
- REFINEMENT C: Deceleration Management (replaces R6, R11, R13)
- REFINEMENT D: Quality Protection System (replaces R14, R15, R16)
"""

import logging
import math

logger = logging.getLogger(__name__)

class ConsolidatedRefinements:
    """Consolidated refinement system eliminating duplications"""
    
    @staticmethod
    def calculate_risk_adjusted_performance(annual_return, annual_volatility, benchmark_return, benchmark_volatility):
        """
        CONSOLIDATED REFINEMENT A: Risk-Adjusted Performance
        Single source for all Sharpe ratio adjustments
        ENHANCED for extreme performers like 9992.HK with ultra-high Sharpe ratios
        Replaces: R2 (Sharpe bonus), R3 (Vol reduction), R8 (Scaled risk), R9 (Quality bonus)
        """
        if not all([annual_return, annual_volatility, benchmark_return, benchmark_volatility]):
            return {'return_bonus': 0, 'volatility_reduction': 0, 'total_adjustment': 0}
        
        # Calculate Sharpe ratios
        risk_free_rate = 0.02  # 2% risk-free rate
        asset_sharpe = (annual_return - risk_free_rate) / annual_volatility
        benchmark_sharpe = (benchmark_return - risk_free_rate) / benchmark_volatility
        sharpe_ratio = asset_sharpe / benchmark_sharpe if benchmark_sharpe > 0 else 1
        
        # ENHANCED: Single-source return bonus calculation with stronger rewards for extreme performers
        return_bonus = 0
        if sharpe_ratio > 15.0:  # NEW: Ultra-extreme Sharpe ratio (targets 9992.HK with 16.31x Sharpe)
            # Ultra-exceptional risk-adjusted performance deserves maximum recognition
            return_bonus = 50 + min(75, (sharpe_ratio - 15.0) * 4)  # Base 50 + up to 75 more = 125 max
            return_bonus = min(return_bonus, 125)  # Cap at 125 points for ultra-performers
        elif sharpe_ratio > 10.0:  # NEW: Extreme Sharpe ratio 
            # Extreme risk-adjusted performance
            return_bonus = 40 + min(35, (sharpe_ratio - 10.0) * 6)  # Base 40 + up to 35 more = 75 max
            return_bonus = min(return_bonus, 75)  # Cap at 75 points for extreme performers
        elif sharpe_ratio > 5.0:  # Enhanced from 2.0 threshold
            # Exceptional Sharpe ratio recognition 
            return_bonus = 30 + min(25, (sharpe_ratio - 5.0) * 5)  # Base 30 + up to 25 more = 55 max
            return_bonus = min(return_bonus, 55)  # Cap at 55 points
        elif sharpe_ratio > 2.0:  # Previous exceptional threshold
            # Very good Sharpe ratio recognition
            return_bonus = 20 * (sharpe_ratio - 1)
            return_bonus = min(return_bonus, 50)  # Cap at 50 points
        elif sharpe_ratio > 1.5:
            # Enhanced Sharpe ratio recognition (was R2)
            return_bonus = 20 * (sharpe_ratio - 1)
            return_bonus = min(return_bonus, 30)  # Cap at 30 points
        elif sharpe_ratio > 1.25:
            # Good Sharpe ratio bonus
            return_bonus = 15 * (sharpe_ratio - 1)
            return_bonus = min(return_bonus, 20)  # Cap at 20 points
        elif sharpe_ratio > 1.0:
            # Moderate Sharpe ratio bonus
            return_bonus = 10 * (sharpe_ratio - 1)
            return_bonus = min(return_bonus, 15)  # Cap at 15 points
        elif sharpe_ratio < 0.8:
            # Poor risk-adjusted performance penalty
            return_bonus = -20 * (0.8 - sharpe_ratio)
            return_bonus = max(return_bonus, -40)  # Floor at -40 points
        
        # ENHANCED: Single-source volatility penalty reduction with stronger protection for extreme performers
        volatility_reduction = 0
        vol_ratio = annual_volatility / benchmark_volatility
        
        if vol_ratio > 1.2:  # Only apply reduction if there's meaningful volatility penalty
            if sharpe_ratio > 15.0:  # NEW: Ultra-extreme Sharpe ratio
                volatility_reduction = 0.85  # 85% reduction for ultra-extreme Sharpe (targets 9992.HK)
            elif sharpe_ratio > 10.0:  # NEW: Extreme Sharpe ratio
                volatility_reduction = 0.75  # 75% reduction for extreme Sharpe
            elif sharpe_ratio > 5.0:  # Enhanced from 2.0 threshold
                volatility_reduction = 0.65  # 65% reduction for exceptional Sharpe
            elif sharpe_ratio > 2.0:
                volatility_reduction = 0.60  # 60% reduction for exceptional Sharpe
            elif sharpe_ratio > 1.75:
                volatility_reduction = 0.50  # 50% reduction for superior Sharpe
            elif sharpe_ratio > 1.5:
                volatility_reduction = 0.40  # 40% reduction for good Sharpe
            elif sharpe_ratio > 1.25:
                volatility_reduction = 0.25  # 25% reduction for moderate Sharpe
        
        total_adjustment = return_bonus  # Volatility reduction applied separately
        
        logger.info(f"ENHANCED REFINEMENT A - Sharpe ratio: {sharpe_ratio:.3f}, Return bonus: {return_bonus:+.1f}, Vol reduction: {volatility_reduction:.1%}")
        
        return {
            'return_bonus': return_bonus,
            'volatility_reduction': volatility_reduction,
            'total_adjustment': total_adjustment,
            'sharpe_ratio': sharpe_ratio
        }
    
    @staticmethod
    def calculate_reliability_adjustment(r_squared, annual_return, benchmark_return, context='standard'):
        """
        CONSOLIDATED REFINEMENT B: Reliability-Based Adjustments
        Single source for all R² adjustments
        ENHANCED with ultra-high R² multipliers for assets like 9992.HK (R² = 0.9721)
        Replaces: R4 (Quality weighting), R5 (Reliability multipliers), R7 (Tightened thresholds)
        """
        if r_squared is None:
            return {'weighting_bonus': 0, 'score_multiplier': 1.0, 'adjustment_type': 'none'}
        
        # Calculate performance quality
        outperformance_ratio = annual_return / benchmark_return if benchmark_return > 0 else 1
        
        # ENHANCED: Ultra-high R² multiplier system for exceptional trend reliability
        if r_squared > 0.95:  # NEW: Ultra-exceptional reliability like 9992.HK (97.21%)
            # Near-perfect trend reliability deserves maximum recognition
            adjustment_type = 'ultra_exceptional_reliability'
            weighting_bonus = 30  # Very strong trend weight bonus
            score_multiplier = 1.40  # 40% boost for near-perfect reliability
        elif r_squared > 0.90:  # NEW: Exceptional reliability threshold 
            # Exceptional reliability like 9992.HK (0.9721)
            adjustment_type = 'exceptional_reliability'
            weighting_bonus = 25  # Strong trend weight bonus
            score_multiplier = 1.35  # 35% boost for exceptional reliability
        elif r_squared > 0.88:  # Ultra-high reliability like 0941.HK (88.76%)
            # Exceptional reliability deserves significant recognition
            adjustment_type = 'ultra_high_reliability'
            weighting_bonus = 20  # Strong trend weight bonus
            score_multiplier = 1.25  # 25% boost for exceptional reliability
        elif r_squared > 0.85 and outperformance_ratio > 1.2:
            # Exceptional reliability + good performance = weighting advantage
            adjustment_type = 'superior_weighting'
            weighting_bonus = 15  # Trend weight bonus
            score_multiplier = 1.20  # 20% boost for high reliability + performance
        elif r_squared > 0.85:
            # High reliability = score multiplier approach
            adjustment_type = 'high_reliability_multiplier'
            weighting_bonus = 15  # Enhanced from 10
            score_multiplier = 1.20  # Enhanced from 1.15 - 20% boost for high reliability
        elif r_squared > 0.75:
            # High reliability = score multiplier approach
            adjustment_type = 'reliability_multiplier'
            weighting_bonus = 0
            if r_squared > 0.80:
                score_multiplier = 1.15  # Enhanced from 1.10 - 15% boost for very good reliability
            else:
                score_multiplier = 1.10  # Enhanced from 1.05 - 10% boost for good reliability
        elif r_squared > 0.65:
            # Moderate reliability = small weighting adjustment
            adjustment_type = 'moderate_weighting'
            weighting_bonus = 5  # Small trend weight bonus
            score_multiplier = 1.05  # Enhanced from 1.0
        else:
            # Low reliability = no adjustment
            adjustment_type = 'none'
            weighting_bonus = 0
            score_multiplier = 1.0
        
        logger.info(f"ENHANCED REFINEMENT B - R²: {r_squared:.3f}, Type: {adjustment_type}, Multiplier: {score_multiplier:.2f}, Weighting bonus: {weighting_bonus:+.1f}")
        
        return {
            'weighting_bonus': weighting_bonus,
            'score_multiplier': score_multiplier,
            'adjustment_type': adjustment_type
        }
    
    @staticmethod
    def calculate_deceleration_penalty(quad_coef, r_squared, linear_coef, trend_type):
        """
        CONSOLIDATED REFINEMENT C: Deceleration Management
        Single source for all deceleration penalties with protection logic
        Enhanced with ultra-high R² protection for assets like 0941.HK
        Replaces: R6 (Enhanced penalties), R11 (Mild penalties), R13 (Coordinated response)
        """
        if quad_coef >= 0:
            return {'penalty': 0, 'protection_applied': False, 'penalty_type': 'none'}
        
        deceleration_strength = abs(quad_coef)
        
        # Check for protection conditions first
        protection_applied = False
        protection_reason = ""
        
        # ENHANCED: Ultra-high R² protection (NEW for 0941.HK type assets)
        if r_squared > 0.88:  # Ultra-high reliability like 0941.HK (88.76%)
            protection_applied = True
            protection_reason = f"ultra_high_reliability (R²: {r_squared:.3f})"
        elif r_squared > 0.85 and deceleration_strength < 0.5:  # High reliability + mild deceleration
            protection_applied = True
            protection_reason = f"high_reliability_mild_decel (R²: {r_squared:.3f}, strength: {deceleration_strength:.3f})"
        
        # Linear dominance protection (from R14 logic)
        elif linear_coef > 0:
            linear_magnitude = abs(linear_coef)
            quad_magnitude = abs(quad_coef)
            coefficient_ratio = linear_magnitude / quad_magnitude if quad_magnitude > 0 else float('inf')
            
            if coefficient_ratio >= 2.0:  # Strong linear dominance
                protection_applied = True
                protection_reason = f"linear_dominance (ratio: {coefficient_ratio:.2f})"
            elif r_squared > 0.90 and coefficient_ratio >= 1.5:  # Ultra-reliable + moderate dominance
                protection_applied = True
                protection_reason = f"ultra_reliable_dominance (R²: {r_squared:.3f}, ratio: {coefficient_ratio:.2f})"
            # ENHANCED: Add protection for moderate-strong linear dominance with good reliability
            elif r_squared > 0.70 and coefficient_ratio >= 1.4:  # Good reliability + decent dominance
                protection_applied = True
                protection_reason = f"good_reliable_dominance (R²: {r_squared:.3f}, ratio: {coefficient_ratio:.2f})"
        
        # Ultra-high reliability protection (from R16 logic)
        if r_squared > 0.94 and deceleration_strength < 0.25:
            protection_applied = True
            protection_reason = f"ultra_reliability (R²: {r_squared:.3f})"
        
        # ENHANCED: High-quality asset protection for moderate deceleration
        # Protect assets with good reliability and moderate deceleration (targets 600298.SS type cases)
        elif r_squared > 0.70 and deceleration_strength < 0.55:  # R² 0.73, quad -0.47 should qualify
            protection_applied = True
            protection_reason = f"high_quality_moderate_decel (R²: {r_squared:.3f}, quad: {quad_coef:.3f})"
        
        # Calculate base penalty if no protection
        if protection_applied:
            penalty = 0
            penalty_type = f"protected_{protection_reason}"
        else:
            # Single graduated penalty system - REDUCED penalties for fairness
            if deceleration_strength > 0.8:
                penalty = -25  # Severe deceleration (reduced from -35)
                penalty_type = "severe"
            elif deceleration_strength > 0.65:
                penalty = -18  # Strong deceleration (reduced from -25) 
                penalty_type = "strong"
            elif deceleration_strength > 0.55:
                penalty = -12  # Moderate deceleration (reduced from -18)
                penalty_type = "moderate"
            elif deceleration_strength > 0.4:
                penalty = -8   # Noticeable deceleration (reduced from -12)
                penalty_type = "noticeable"
            elif deceleration_strength > 0.2:
                penalty = -5   # Mild deceleration (reduced from -8)
                penalty_type = "mild"
            elif deceleration_strength > 0.1:
                penalty = -3   # Minimal deceleration
                penalty_type = "minimal"
            else:
                penalty = -1   # Very minimal deceleration
                penalty_type = "very_minimal"
            
            # ENHANCED: Reduce penalty for high reliability assets (partial protection)
            if r_squared > 0.80 and deceleration_strength < 0.6:
                penalty_reduction = abs(penalty) * 0.5  # 50% reduction for high R² (increased from 40%)
                penalty = min(penalty + penalty_reduction, -1)  # Minimum -1 penalty
                penalty_type += "_reliability_reduced"
            elif r_squared > 0.65 and deceleration_strength < 0.5:
                penalty_reduction = abs(penalty) * 0.3  # 30% reduction for good R²
                penalty = min(penalty + penalty_reduction, -2)  # Minimum -2 penalty
                penalty_type += "_partial_reduction"
        
        logger.info(f"REFINEMENT C - Quad coef: {quad_coef:.3f}, Penalty: {penalty:+.1f}, Type: {penalty_type}, Protected: {protection_applied}")
        
        return {
            'penalty': penalty,
            'protection_applied': protection_applied,
            'penalty_type': penalty_type
        }
    
    @staticmethod
    def calculate_quality_protection(r_squared, sharpe_ratio, outperformance_ratio, quad_coef):
        """
        CONSOLIDATED REFINEMENT D: Quality Protection System
        Single source for quality-based protections and bonuses
        Enhanced with ultra-high R² recognition for assets like 0941.HK
        Replaces: R14 (Coefficient ratio), R15 (Superior fundamentals), R16 (Market index exception)
        """
        if not all([r_squared, sharpe_ratio]):
            return {'protection_bonus': 0, 'protection_type': 'none'}
        
        protection_bonus = 0
        protection_type = 'none'
        
        # ENHANCED: Ultra-high reliability bonuses (NEW for 0941.HK type assets)
        if r_squared > 0.88:  # Ultra-high reliability like 0941.HK (88.76%)
            protection_bonus += 25  # Exceptional reliability recognition
            protection_type = "ultra_reliable"
        elif r_squared > 0.85:  # High reliability
            protection_bonus += 15  # High reliability recognition
            protection_type = "high_reliable"
        elif r_squared > 0.80:  # Very good reliability
            protection_bonus += 8
            protection_type = "very_reliable"
        
        # ENHANCED: Exceptional risk-adjusted performance recognition (targets 600298.SS type cases)
        # 600298.SS: 1.47x Sharpe ratio, R² 0.73, 88% higher return - should get strong recognition
        if sharpe_ratio > 1.4 and r_squared > 0.70 and outperformance_ratio > 1.5:
            protection_bonus += 15  # Strong recognition for exceptional risk-adjusted performance
            protection_type += "_exceptional_risk_adjusted"
        elif sharpe_ratio > 1.3 and r_squared > 0.65 and outperformance_ratio > 1.3:
            protection_bonus += 12  # Good recognition for strong risk-adjusted performance
            protection_type += "_strong_risk_adjusted"
        # Market index / ultra-high quality protection  
        elif r_squared > 0.94 and sharpe_ratio > 1.0:
            protection_bonus += 12  # Strong protection for market indices
            protection_type += "_market_index"
        elif r_squared > 0.85 and sharpe_ratio > 1.5 and outperformance_ratio > 1.3:
            protection_bonus += 10  # Superior fundamentals protection
            protection_type += "_superior_fundamentals"
        elif r_squared > 0.75 and sharpe_ratio > 1.25:
            protection_bonus += 6   # High quality protection
            protection_type += "_high_quality"
        elif r_squared > 0.65 and sharpe_ratio > 1.0:
            protection_bonus += 3   # Moderate quality protection
            protection_type += "_moderate_quality"
        
        # ENHANCED: Additional protection for extreme outperformers with any deceleration
        if outperformance_ratio > 1.8 and quad_coef < 0:  # Reduced threshold from 2.0 to 1.8
            extreme_protection = min(10, (outperformance_ratio - 1.8) * 8)  # More generous formula
            protection_bonus += extreme_protection
            protection_type += '_extreme_performer'
        
        # ENHANCED: High Sharpe ratio bonus for exceptional risk-adjusted performance
        # Give extra credit to stocks that achieve high returns with reasonable volatility
        if sharpe_ratio > 1.4:
            sharpe_bonus = min(8, (sharpe_ratio - 1.4) * 10)  # Up to 8 points for exceptional Sharpe
            protection_bonus += sharpe_bonus
            protection_type += '_high_sharpe'
        
        logger.info(f"REFINEMENT D - R²: {r_squared:.3f}, Sharpe: {sharpe_ratio:.3f}, Protection: {protection_bonus:+.1f}, Type: {protection_type}")
        
        return {
            'protection_bonus': protection_bonus,
            'protection_type': protection_type
        }
    
    @staticmethod
    def get_quality_based_weights(r_squared, sharpe_ratio, risk_adjusted_advantage):
        """
        Determine optimal component weights based on asset quality
        Replaces the multiple weighting systems in R4
        """
        # Calculate combined quality score
        quality_score = 0
        if r_squared:
            quality_score += r_squared * 50  # R² contribution (0-50)
        if sharpe_ratio:
            quality_score += min(sharpe_ratio * 20, 30)  # Sharpe contribution (0-30)
        
        # Determine weighting based on quality and risk profile
        if quality_score >= 70 and risk_adjusted_advantage > 0.10:
            # Superior quality: emphasize trend
            weights = {'trend': 0.60, 'return': 0.30, 'volatility': 0.10}
            weighting_type = "superior_quality"
        elif quality_score >= 60 and risk_adjusted_advantage > 0.05:
            # High quality: enhanced trend weight
            weights = {'trend': 0.55, 'return': 0.35, 'volatility': 0.10}
            weighting_type = "high_quality"
        elif risk_adjusted_advantage < -0.15:
            # Poor risk-adjusted performance: emphasize actual results
            weights = {'trend': 0.35, 'return': 0.50, 'volatility': 0.15}
            weighting_type = "risk_penalized"
        elif quality_score >= 40:
            # Moderate quality: balanced approach
            weights = {'trend': 0.50, 'return': 0.35, 'volatility': 0.15}
            weighting_type = "balanced"
        else:
            # Low quality: return-focused
            weights = {'trend': 0.40, 'return': 0.45, 'volatility': 0.15}
            weighting_type = "return_focused"
        
        logger.info(f"Quality-based weights - Quality score: {quality_score:.1f}, Type: {weighting_type}")
        
        return weights, weighting_type
    
    @staticmethod
    def apply_consolidated_refinements(trend_score, return_score, volatility_score, 
                                     annual_return, annual_volatility, benchmark_return, benchmark_volatility,
                                     r_squared, quad_coef, linear_coef, trend_type):
        """
        Apply all consolidated refinements in proper sequence
        Returns final adjusted scores and comprehensive logging
        """
        results = {
            'original_scores': {
                'trend': trend_score,
                'return': return_score, 
                'volatility': volatility_score
            },
            'adjustments': {},
            'final_scores': {},
            'summary': {}
        }
        
        # REFINEMENT A: Risk-Adjusted Performance
        risk_adjustment = ConsolidatedRefinements.calculate_risk_adjusted_performance(
            annual_return, annual_volatility, benchmark_return, benchmark_volatility)
        results['adjustments']['risk_performance'] = risk_adjustment
        
        # REFINEMENT B: Reliability-Based Adjustments
        reliability_adjustment = ConsolidatedRefinements.calculate_reliability_adjustment(
            r_squared, annual_return, benchmark_return)
        results['adjustments']['reliability'] = reliability_adjustment
        
        # REFINEMENT C: Deceleration Management
        deceleration_adjustment = ConsolidatedRefinements.calculate_deceleration_penalty(
            quad_coef, r_squared, linear_coef, trend_type)
        results['adjustments']['deceleration'] = deceleration_adjustment
        
        # REFINEMENT D: Quality Protection
        outperformance_ratio = annual_return / benchmark_return if benchmark_return > 0 else 1
        quality_protection = ConsolidatedRefinements.calculate_quality_protection(
            r_squared, risk_adjustment.get('sharpe_ratio', 1), outperformance_ratio, quad_coef)
        results['adjustments']['quality_protection'] = quality_protection
        
        # Apply adjustments to scores
        adjusted_return = return_score + risk_adjustment['return_bonus']
        adjusted_volatility = volatility_score * (1 + risk_adjustment['volatility_reduction'])
        adjusted_trend = (trend_score + deceleration_adjustment['penalty'] + 
                         quality_protection['protection_bonus'])
        
        results['final_scores'] = {
            'trend': max(0, adjusted_trend),
            'return': max(0, adjusted_return),
            'volatility': max(0, adjusted_volatility)
        }
        
        # Calculate total adjustments for transparency
        total_adjustment = (risk_adjustment['return_bonus'] + 
                          deceleration_adjustment['penalty'] + 
                          quality_protection['protection_bonus'])
        
        results['summary'] = {
            'total_adjustment': total_adjustment,
            'score_multiplier': reliability_adjustment['score_multiplier'],
            'primary_adjustments': [
                f"Risk: {risk_adjustment['return_bonus']:+.1f}",
                f"Deceleration: {deceleration_adjustment['penalty']:+.1f}",
                f"Protection: {quality_protection['protection_bonus']:+.1f}",
                f"Multiplier: {reliability_adjustment['score_multiplier']:.2f}x"
            ]
        }
        
        logger.info(f"CONSOLIDATED REFINEMENTS - Total adjustment: {total_adjustment:+.1f}, "
                   f"Multiplier: {reliability_adjustment['score_multiplier']:.2f}x")
        
        return results 