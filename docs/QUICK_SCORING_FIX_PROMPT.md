# 🚨 QUICK TrendWise SCORING ISSUE PROMPT

**Copy this template and fill in the values when you find a scoring inconsistency:**

---

## **SCORING ISSUE REPORT**

I found a potential TrendWise scoring issue:

**Asset Details:**
- Symbol: `[SYMBOL]`
- Score: `[SCORE]` (`[RATING]`)
- Assessment: `[OVERVALUED/UNDERVALUED/INCONSISTENT]`

**Benchmark Comparison:**
- ^GSPC Score: `[GSPC_SCORE]` (`[RATING]`) 
- Expected: Asset should be `[HIGHER/LOWER/SIMILAR]` than ^GSPC

**Asset Metrics:**
- Return: `[X.XX%]`
- Volatility: `[X.XX%]` 
- R²: `[X.XXXX]`
- Regression: `[FORMULA]`
- Period: `[XXXX days]`

**^GSPC Metrics (same period):**
- Return: `[X.XX%]`
- Volatility: `[X.XX%]`
- R²: `[X.XXXX]` 
- Regression: `[FORMULA]`
- Period: `[XXXX days]`

**Issue Description:**
`[Describe the inconsistency - e.g., "Asset has worse metrics but scores higher"]`

**Please analyze and fix this scoring inconsistency using the systematic debugging approach.**

---

## **EXAMPLE (601398.SS Case):**

I found a potential TrendWise scoring issue:

**Asset Details:**
- Symbol: `601398.SS`
- Score: `75.8` (`Very Good`)
- Assessment: `OVERVALUED`

**Benchmark Comparison:**
- ^GSPC Score: `72.0` (`Very Good`) 
- Expected: Asset should be `LOWER` than ^GSPC

**Asset Metrics:**
- Return: `8.48%`
- Volatility: `19.4%` 
- R²: `0.6532`
- Regression: `Ln(y) = 0.17(x/3648)² + 0.45(x/3648) + 1.09`
- Period: `3650 days`

**^GSPC Metrics (same period):**
- Return: `10.93%`
- Volatility: `18.4%`
- R²: `0.9447` 
- Regression: `Ln(y) = 0.02(x/3648)² + 1.08(x/3648) + 7.56`
- Period: `3650 days`

**Issue Description:**
`Asset has inferior return (8.48% vs 10.93%), higher volatility (19.4% vs 18.4%), and much lower R² (0.6532 vs 0.9447), yet scores higher than ^GSPC. This suggests the system is using incorrect ^GSPC comparison values.`

**Please analyze and fix this scoring inconsistency using the systematic debugging approach.** 