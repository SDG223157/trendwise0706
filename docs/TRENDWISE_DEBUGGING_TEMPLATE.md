# TrendWise Scoring Issue Debugging Template

## 🚨 PROMPT TEMPLATE FOR SCORING INCONSISTENCIES

Use this template when you suspect a TrendWise scoring issue (overvaluation, undervaluation, or inconsistency).

---

## **STEP 1: PROBLEM IDENTIFICATION**

```
I found a potential TrendWise scoring issue:

**Asset Details:**
- Symbol: [ASSET_SYMBOL]
- Score: [ASSET_SCORE] ([RATING])
- Your assessment: [OVERVALUED/UNDERVALUED/INCONSISTENT]

**Benchmark Comparison:**
- ^GSPC Score: [GSPC_SCORE] ([RATING]) 
- Expected relationship: [SHOULD BE HIGHER/LOWER/SIMILAR]

**Asset Metrics (from UI/logs):**
- Return: [X.XX%]
- Volatility: [X.XX%] 
- R²: [X.XXXX]
- Regression Formula: [FORMULA]
- Time Period: [XXXX days]

**^GSPC Metrics (from UI/logs):**
- Return: [X.XX%]
- Volatility: [X.XX%]
- R²: [X.XXXX] 
- Regression Formula: [FORMULA]
- Time Period: [XXXX days] (should match asset)

**Suspected Issue:**
[Describe what seems wrong - e.g., "Asset has inferior metrics but scores higher"]

Please analyze this scoring inconsistency and fix any underlying problems.
```

---

## **STEP 2: SYSTEMATIC ANALYSIS CHECKLIST**

When using this template, perform this analysis:

### **A. VERIFY SAME TIME PERIOD** ✅
- [ ] Confirm both asset and ^GSPC use identical time periods
- [ ] Check if dates are synchronized in `_get_sp500_benchmark()`
- [ ] Verify recursive ^GSPC analysis uses same period

### **B. CHECK FOR HARDCODED VALUES** ❌
Search for these problematic patterns:
```python
# RED FLAGS - Replace these with actual values
gspc_typical_r2 = 0.45
gspc_typical_quad_coef = -0.3
gspc_typical_linear_coef = 0.40
sp500_baseline_score = 60.0  # Should be dynamic
```

### **C. VERIFY METRICS EXTRACTION** 🔍
Ensure actual ^GSPC metrics are extracted:
```python
# CORRECT PATTERN
if sp500_analysis and 'total_score' in sp500_analysis:
    gspc_actual_r2 = sp500_analysis['r2']
    trend_details = sp500_analysis['total_score']['components']['trend']['details']
    gspc_actual_quad_coef = trend_details['quad_coef']
```

### **D. ANALYZE COMPARISON RATIOS** 📊
Calculate fair ratios:
- Return ratio: `asset_return / gspc_actual_return`
- Volatility ratio: `asset_volatility / gspc_actual_volatility` 
- R² ratio: `asset_r2 / gspc_actual_r2`
- Trend ratios: Compare actual coefficients

### **E. CHECK PENALTY/BONUS SYSTEMS** ⚖️
- [ ] Verify deceleration penalties are capped appropriately
- [ ] Check return bonus scaling for extreme outperformance
- [ ] Ensure volatility penalties are reasonable
- [ ] Validate protection mechanisms work

---

## **STEP 3: COMMON FIX PATTERNS**

### **Pattern 1: Hardcoded Values Fix**
```python
# REPLACE hardcoded typical values
# FROM:
gspc_typical_r2 = 0.45

# TO:
try:
    if sp500_analysis and 'total_score' in sp500_analysis:
        gspc_actual_r2 = sp500_analysis['r2']
        logger.info(f"Using ACTUAL ^GSPC R²: {gspc_actual_r2:.4f}")
    else:
        gspc_actual_r2 = 0.45  # Fallback only
        logger.warning("Using fallback typical R² value")
except Exception as e:
    logger.error(f"Failed to extract actual R²: {e}")
    gspc_actual_r2 = 0.45
```

### **Pattern 2: Same Period Synchronization**
```python
# ENSURE same period data collection
def _get_sp500_benchmark(data, symbol=None):
    # Extract EXACT same dates from asset data
    end_date = data.index[-1].strftime('%Y-%m-%d')
    start_date = data.index[0].strftime('%Y-%m-%d')
    
    # Fetch ^GSPC for IDENTICAL period
    sp500_data = data_service.get_historical_data('^GSPC', start_date, end_date)
```

### **Pattern 3: Dynamic Baseline Fix**
```python
# USE actual ^GSPC score as baseline
# FROM:
gspc_baseline_score = 60.0  # WRONG

# TO:
gspc_baseline_score = sp500_calculated_score  # Dynamic baseline
```

### **Pattern 4: Enhanced Logging**
```python
logger.info(f"Asset vs ^GSPC comparison:")
logger.info(f"  Return: {annual_return:.2%} vs {gspc_return:.2%}")
logger.info(f"  Volatility: {annual_volatility:.2%} vs {gspc_volatility:.2%}")
logger.info(f"  R²: {r2:.3f} vs {gspc_actual_r2:.3f}")
logger.info(f"  Quad coef: {coef[2]:.3f} vs {gspc_actual_quad_coef:.3f}")
```

---

## **STEP 4: VERIFICATION TEMPLATE**

After implementing fixes, create verification:

```python
def verify_[ASSET_SYMBOL]_fix():
    """Verify the fix resolves the scoring issue"""
    
    # Asset metrics (same period)
    asset = {
        'symbol': '[ASSET_SYMBOL]',
        'return': [VALUE],
        'volatility': [VALUE], 
        'r2': [VALUE],
        'score_before': [OLD_SCORE],
        'score_after': [NEW_SCORE]
    }
    
    # ^GSPC metrics (same period) 
    gspc = {
        'return': [VALUE],
        'volatility': [VALUE],
        'r2': [VALUE], 
        'score': [GSPC_SCORE]
    }
    
    # Calculate fair ratios
    return_ratio = asset['return'] / gspc['return']
    volatility_ratio = asset['volatility'] / gspc['volatility']
    r2_ratio = asset['r2'] / gspc['r2']
    
    print(f"VERIFICATION RESULTS:")
    print(f"Return ratio: {return_ratio:.3f} ({'BETTER' if return_ratio > 1 else 'WORSE'})")
    print(f"Risk ratio: {volatility_ratio:.3f} ({'RISKIER' if volatility_ratio > 1 else 'SAFER'})")
    print(f"Reliability ratio: {r2_ratio:.3f} ({'BETTER' if r2_ratio > 1 else 'WORSE'})")
    print(f"Score change: {asset['score_before']} → {asset['score_after']} ({asset['score_after'] - asset['score_before']:+.1f})")
    print(f"Relative to ^GSPC: {'ABOVE' if asset['score_after'] > gspc['score'] else 'BELOW'} {gspc['score']}")
```

---

## **STEP 5: DOCUMENTATION TEMPLATE**

Add to `RATING_SYSTEM.md`:

```markdown
### Critical Fix: [ISSUE_DESCRIPTION] ([ASSET_SYMBOL] Case)

**Problem Identified**: [Brief description]
- Asset: [metrics]
- ^GSPC: [metrics] 
- Issue: [what was wrong]

**Root Cause**: [Technical cause]
```python
# BROKEN CODE:
[show problematic code]
```

**Technical Fix Implemented**:
```python
# FIXED CODE:
[show corrected code]
```

**Result**: [Outcome description]
- [Asset] corrected score: [before] → [after]
- Eliminates [specific problem]
- Ensures [improvement]
```

---

## **USAGE EXAMPLE**

**Input:**
```
I found a potential TrendWise scoring issue:

Asset Details:
- Symbol: AAPL
- Score: 78.5 (Very Good)
- Your assessment: OVERVALUED

Benchmark Comparison:
- ^GSPC Score: 72.0 (Very Good)
- Expected relationship: SHOULD BE LOWER

Asset Metrics:
- Return: 9.2%
- Volatility: 22.1%
- R²: 0.7234
- Time Period: 1825 days

^GSPC Metrics: 
- Return: 11.8%
- Volatility: 18.9%
- R²: 0.8956
- Time Period: 1825 days

Suspected Issue: Asset has inferior return, higher volatility, and lower R² but still scores higher than ^GSPC
```

**Expected Actions:**
1. Analyze comparison ratios (all favor ^GSPC)
2. Check for hardcoded values causing artificial advantages
3. Verify same period synchronization
4. Implement fixes following patterns above
5. Document the case study

---

## **QUICK REFERENCE COMMANDS**

```bash
# Search for hardcoded problematic values
grep -n "gspc_typical" app/utils/analysis/analysis_service.py
grep -n "0.45\|0.3\|-0.3" app/utils/analysis/analysis_service.py

# Check ^GSPC baseline usage
grep -n "60.0\|baseline.*60" app/utils/analysis/analysis_service.py

# Verify same period extraction
grep -n "start_date.*index\|end_date.*index" app/utils/analysis/analysis_service.py
```

This template provides a systematic approach to identify, analyze, and fix TrendWise scoring inconsistencies efficiently. 