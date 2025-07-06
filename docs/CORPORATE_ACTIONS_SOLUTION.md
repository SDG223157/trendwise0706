# Corporate Actions Detection & Data Consistency Solution

## Problem Statement

When stock splits or dividends occur, simply appending new historical data to existing database tables creates **price inconsistencies** because:

1. **Existing data**: Based on pre-split/pre-dividend prices
2. **New data**: Automatically adjusted for splits/dividends by yfinance
3. **Result**: Inconsistent price series that breaks analysis

### Example: 1211.HK Corporate Actions

From the database table `his_1211_hk`:
```
Date         | Close    | Dividends | Stock Splits
2025-06-10   | 135.60   | 4.341992  | 3.0
2025-06-11   | 140.80   | 0.0       | 0.0
2025-06-12   | 134.40   | 0.0       | 0.0
2025-06-13   | 131.10   | 0.0       | 0.0
```

## The Problem

If we only append the latest 20 days of data to update to today:

1. **Existing data (before 2025-06-10)**: Pre-split prices (higher values)
2. **New data (after 2025-06-10)**: Post-split adjusted prices (lower values)
3. **Result**: Artificial price jump/drop that never actually occurred

## Solution Implementation

### Enhanced `get_historical_data()` Method

The `DataService.get_historical_data()` method now includes:

1. **Corporate Actions Detection**: Check new data for splits/dividends
2. **Automatic Full Refresh**: If corporate actions found, refresh entire dataset
3. **Price Consistency**: Ensures all data uses the same adjustment basis

### Key Changes

#### 1. Corporate Actions Detection Function
```python
def check_for_corporate_actions_in_data(self, df: pd.DataFrame) -> bool:
    """Check if DataFrame contains any corporate actions"""
    has_dividends = (df['Dividends'] > 0).any()
    has_splits = (df['Stock Splits'] > 0).any()
    return has_dividends or has_splits
```

#### 2. Enhanced Data Update Logic
```python
# Before combining new data with existing data
if self.check_for_corporate_actions_in_data(new_data):
    logging.warning(f"Corporate actions detected in new data for {ticker}!")
    logging.warning("Refreshing entire historical dataset to ensure price consistency...")
    success = self.store_historical_data(ticker)  # Full refresh
    # Return refreshed data instead of combined data
```

## Trigger Scenarios

The system automatically detects and handles corporate actions in these scenarios:

### Scenario 1: Extending Historical Range
When requesting data before the existing database range:
- ✅ **Enhanced**: Checks new historical data for corporate actions
- ✅ **Action**: Full refresh if corporate actions detected

### Scenario 2: Updating Recent Data
When updating database with recent data (daily updates):
- ✅ **Enhanced**: Checks last 10+ days for corporate actions  
- ✅ **Action**: Full refresh if corporate actions detected

### Scenario 3: Fresh Data Requests
When no existing data in database:
- ✅ **Standard**: Fetches complete dataset (already consistent)

## Benefits

### 1. Price Consistency
- All prices use the same adjustment basis
- No artificial jumps/drops in price series
- Accurate technical analysis and calculations

### 2. Automatic Detection
- No manual intervention required
- Detects both dividends and stock splits
- Logs detailed information about detected actions

### 3. Performance Optimization
- Only refreshes when necessary
- Preserves fast incremental updates for clean data
- Minimal impact on normal operations

## Logging Output

When corporate actions are detected:

```
INFO - Corporate actions detected: Dividends=True, Stock Splits=True
INFO - Dividend dates: ['2025-06-10']
INFO - Stock split dates: ['2025-06-10']  
WARNING - Corporate actions detected in new data for 1211.HK!
WARNING - Refreshing entire historical dataset to ensure price consistency...
```

## Testing

### Test Data: 1211.HK
- **Dividend**: 4.341992 on 2025-06-10
- **Stock Split**: 3.0x on 2025-06-10
- **Result**: Automatic full refresh triggered

### Test Data: AAPL  
- **Dividends**: Regular quarterly dividends
- **Stock Splits**: None in recent period
- **Result**: Automatic refresh triggered for dividend periods

## Implementation Files

### Modified Files
- `app/utils/data/data_service.py`: Enhanced with corporate actions detection
- `test_corporate_actions_detection.py`: Verification script

### Key Methods
- `check_for_corporate_actions_in_data()`: Detection logic
- `get_historical_data()`: Enhanced update logic with corporate actions handling

## Usage

The enhancement is **automatically active** - no configuration required:

```python
from app.utils.data.data_service import DataService

ds = DataService()
# This will automatically detect and handle corporate actions
data = ds.get_historical_data('1211.HK', '2024-01-01', '2025-06-15')
```

## Future Enhancements

### Potential Improvements
1. **Corporate Actions API**: Direct integration with corporate actions feeds
2. **Notification System**: Alert users when corporate actions trigger refresh
3. **Selective Refresh**: Only refresh affected date ranges
4. **Validation Checks**: Compare pre/post refresh data for consistency

### Performance Monitoring
- Track frequency of corporate actions detection
- Monitor refresh performance impact
- Optimize detection algorithms based on usage patterns

---

## Summary

This solution ensures **data integrity** by automatically detecting corporate actions in new data and triggering full dataset refreshes when needed. This prevents the price inconsistencies that would otherwise break stock analysis and calculations.

The system is **transparent**, **automatic**, and **performance-optimized** - it only refreshes when absolutely necessary while maintaining complete price consistency across all historical data. 