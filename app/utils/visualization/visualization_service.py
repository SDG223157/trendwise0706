import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.utils.config.layout_config import LAYOUT_CONFIG, CHART_STYLE, TABLE_STYLE
import logging
import yfinance as yf
import re
from app.utils.symbol_utils import normalize_ticker  # Import from new module

logger = logging.getLogger(__name__)


def is_stock(symbol: str) -> bool:
    """
    Determine if a ticker represents a stock or not.
    """
    # Convert TradingView symbol to Yahoo symbol first
    yahoo_symbol = normalize_ticker(symbol)
    symbol = yahoo_symbol.upper()
    
    # Non-stock patterns
    if (symbol.startswith('^') or 
        (symbol.startswith('58') or symbol.startswith('51')) and len(symbol) == 9 or  # Indices
        symbol.endswith('=F') or           # Futures
        symbol.endswith('-USD') or         # Crypto
        symbol.endswith('=X') or           # Forex
        symbol in ['USD', 'EUR', 'GBP', 'JPY', 'CNH', 'HKD', 'CAD', 'AUD'] or  # Major currencies
        any(suffix in symbol for suffix in ['-P', '-C', '-IV', '-UV'])):  # Options, ETF variations
        return False
    
    return True

class VisualizationService:
    """Service class for creating and managing stock analysis visualizations."""

    @staticmethod
    def _get_config(symbol: str):
        """Get the appropriate configuration based on symbol type"""
        layout_type = 'stock' if is_stock(symbol) else 'non_stock'
        return {
            'layout': layout_type,
            'chart_area': LAYOUT_CONFIG['chart_area'][layout_type],
            'tables': LAYOUT_CONFIG['tables'][layout_type],
            'annotations': LAYOUT_CONFIG['annotations'][layout_type],
            'table_style': TABLE_STYLE[layout_type]
        }

    @staticmethod
    def format_number(x, symbol=None):
        """Format numbers with comprehensive handling"""
        if pd.isna(x) or x is None:
            return "N/A"
        try:
            if abs(x) >= 1_000_000:
                # Convert to billions
                value_in_billions = x / 1_000_000_000
                
                # Skip currency prefix for non-currency values and Diluted Shares
                if symbol is None or symbol == 'shares':  # Add special case for shares
                    # Format without currency prefix
                    if abs(value_in_billions) < 10:
                        formatted = f"{abs(value_in_billions):.2f}B"
                    else:
                        formatted = f"{abs(value_in_billions):.1f}B"
                    return f"-{formatted}" if x < 0 else formatted
                
                # Format with currency symbol based on listing market
                if symbol:
                    if symbol.endswith('.HK') or symbol.startswith('HKEX:'):
                        prefix = "HK$"
                    elif symbol.endswith(('.SS', '.SZ')) or any(symbol.startswith(x) for x in ['SSE:', 'SZSE:']):
                        prefix = "¥"
                    elif symbol.endswith('.T') or symbol.startswith('TSE:'):
                        prefix = "¥"
                    elif symbol.endswith('.L') or symbol.startswith('LSE:'):
                        prefix = "£"
                    elif symbol.endswith('.F') or symbol.startswith('XETR:'):
                        prefix = "€"
                    else:
                        prefix = "$"  # Default to USD for US-listed stocks
                else:
                    prefix = "$"  # Default to USD when no symbol provided
                
                # Format with 2 decimal places if under 10B, otherwise no decimals
                if abs(value_in_billions) < 10:
                    formatted = f"{prefix}{abs(value_in_billions):.2f}B"
                else:
                    formatted = f"{prefix}{abs(value_in_billions):.1f}B"
                return f"-{formatted}" if x < 0 else formatted
            else:
                # Format regular numbers without currency symbol
                return f"{x:,.2f}"
        except (TypeError, ValueError):
            return "N/A"

    @staticmethod
    def create_financial_metrics_table(df, config, symbol=None):
        """Create financial metrics tables using provided configuration"""
        if df is None or df.empty or config['layout'] == 'non_stock':
            return None, None

        formatted_df = df.copy()
        # Capitalize first letter of each word in index
        formatted_df.index = formatted_df.index.map(lambda x: ' '.join(word.capitalize() for word in x.split()))
        
        for col in df.columns:
            if col != 'CAGR %':
                # Format each row with appropriate currency handling
                for idx in formatted_df.index:
                    value = formatted_df.loc[idx, col]
                    # Skip currency prefix for Diluted Shares row
                    if idx.lower() == 'diluted shares':
                        formatted_df.loc[idx, col] = VisualizationService.format_number(value, 'shares')
                    else:
                        formatted_df.loc[idx, col] = VisualizationService.format_number(value, symbol)
            else:
                formatted_df[col] = formatted_df[col].apply(
                    lambda x: f"{x:+.2f}%" if pd.notna(x) and x is not None else "N/A"
                )

        metrics_table = go.Table(
            domain=dict(
                x=config['tables']['metrics']['x'],
                y=config['tables']['metrics']['y']
            ),
            header=dict(
                values=['<b>Metric</b>'] + [f'<b>{col}</b>' for col in df.columns],
                **config['table_style']['header']
            ),
            cells=dict(
                values=[
                    formatted_df.index.tolist(),
                    *[formatted_df[col].tolist() for col in formatted_df.columns]
                ],
                **config['table_style']['cells']
            )
        )
        
        growth_table = None
        if not df.empty:
            df_columns = list(df.columns)
            # Get all year columns excluding CAGR
            year_columns = [col for col in df_columns if col != 'CAGR %']
            
            # Calculate growth rates with null checking
            growth_rates = {}
            for metric in df.index:
                rates = []
                for i in range(len(year_columns)-1):
                    curr_col = year_columns[i+1]
                    prev_col = year_columns[i]
                    try:
                        curr_val = df.loc[metric, curr_col]
                        prev_val = df.loc[metric, prev_col]
                        
                        if pd.isna(curr_val) or pd.isna(prev_val) or prev_val == 0:
                            rates.append(None)
                        else:
                            growth_rate = ((curr_val / prev_val) - 1) * 100
                            rates.append(growth_rate)
                    except (TypeError, ZeroDivisionError):
                        rates.append(None)
                
                growth_rates[metric] = rates

            if growth_rates:
                # Format growth rates
                formatted_values = [list(growth_rates.keys())]  # First row is metric names
                growth_years = year_columns[1:]  # Years for growth rates (exclude first year)
                
                # Add the formatted growth rates
                for i in range(len(growth_years)):
                    period_values = []
                    for metric in growth_rates:
                        value = growth_rates[metric][i]
                        if value is None:
                            period_values.append("N/A")
                        else:
                            period_values.append(f"{value:+.1f}%" if value != 0 else "0.0%")
                    formatted_values.append(period_values)
                
                # Create the growth table
                growth_df = pd.DataFrame(growth_rates).T
                growth_df.columns = growth_years
                
                growth_table = go.Table(
                    domain=dict(
                        x=config['tables']['growth']['x'],
                        y=config['tables']['growth']['y']
                    ),
                    header=dict(
                        values=['<b>Metric</b>'] + [f'<b>{year}</b>' for year in growth_years],
                        **config['table_style']['header']
                    ),
                    cells=dict(
                        values=[
                            # Only capitalize the metric names
                            [' '.join(word.capitalize() for word in idx.split()) for idx in growth_df.index],
                            # Keep original formatted values for growth rates
                            *[formatted_values[i+1] for i in range(len(growth_years))]
                        ],
                        **config['table_style']['cells']
                    )
                )
        
        return metrics_table, growth_table

    @staticmethod
    def _analyze_signals(signal_returns):
        """Analyze trading signals and calculate performance metrics"""
        try:
            if not signal_returns:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'average_return': 0
                }

            trades = []
            for signal in signal_returns:
                if 'Trade Return' in signal:
                    trades.append(signal['Trade Return'])

            if not trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'average_return': 0
                }

            winning_trades = len([t for t in trades if t > 0])
            
            return {
                'total_trades': len(trades),
                'win_rate': (winning_trades / len(trades)) * 100 if trades else 0,
                'average_return': sum(trades) / len(trades) if trades else 0
            }
        except Exception as e:
            print(f"Error analyzing signals: {str(e)}")
            return {
                'total_trades': 0,
                'win_rate': 0,
                'average_return': 0
            }

    @staticmethod
    def _get_score_rating(score):
        """Return rating based on score thresholds with star ratings and descriptions"""
        if score >= 105:
            return "★★★★★★★ Elite performers"
        elif score >= 98:
            return "★★★★★★★ Ultra-extreme performers"
        elif score >= 90:
            return "★★★★★★ Very strong performers"
        elif score >= 80:
            return "★★★★★ High performers"
        elif score >= 70:
            return "★★★★ Above benchmark"
        elif score >= 60:
            return "★★★ Decent performance"
        elif score >= 50:
            return "★★ Below average"
        else:
            return "★ Poor performance"

    @staticmethod
    def _get_market_characteristic(score):
        """Get market characteristic for ^GSPC scores (40-90 range)"""
        if score >= 85:
            return 'Exceptional Bull Market'
        elif score >= 80:
            return 'Strong Bull Market'
        elif score >= 75:
            return 'Healthy Bull Market'
        elif score >= 70:
            return 'Neutral Market'
        elif score >= 65:
            return 'Market Correction'
        elif score >= 60:
            return 'Moderate Bear Market'
        elif score >= 55:
            return 'Bear Market'
        elif score >= 50:
            return 'Severe Bear Market'
        elif score >= 45:
            return 'Market Crisis'
        else:
            return 'Market Crash'

    @staticmethod
    def _create_analysis_summary_table(days, end_price, annual_return, 
                                     daily_volatility, annualized_volatility,
                                     r2, regression_formula, final_score,
                                     table_style, table_domain, signal_returns=None, symbol=None,
                                     sp500_raw_score=None, sp500_scaled_score=None):
        """Create the analysis summary table with S&P 500 comparison"""
        # Get currency prefix based on symbol
        currency_prefix = "$"  # Default to USD
        if symbol:
            if symbol.endswith('.HK') or symbol.startswith('HKEX:'):
                currency_prefix = "HK$"
            elif symbol.endswith(('.SS', '.SZ')) or any(symbol.startswith(x) for x in ['SSE:', 'SZSE:']):
                currency_prefix = "¥"
            elif symbol.endswith('.T') or symbol.startswith('TSE:'):
                currency_prefix = "¥"
            elif symbol.endswith('.L') or symbol.startswith('LSE:'):
                currency_prefix = "£"
            elif symbol.endswith('.F') or symbol.startswith('XETR:'):
                currency_prefix = "€"

        # Format score display with integer rounding
        rating = VisualizationService._get_score_rating(final_score)
        
        # Check if we're analyzing the S&P 500 itself
        is_sp500_analysis = False
        if symbol:
            # Normalize symbol and check if it's S&P 500
            normalized_symbol = symbol.upper().replace('^', '').replace('SPX', 'SPY').replace('$SPX', 'SPY')
            is_sp500_analysis = normalized_symbol in ['SPY', '^SPX', 'SPX', '$SPX', 'SP500', 'S&P500', 'GSPC', '^GSPC', 'SPX500']
            # Also check the original symbol with common S&P 500 variations
            is_sp500_analysis = is_sp500_analysis or symbol.upper() in ['^GSPC', '^SPX', 'SPY', '$SPX', 'SPX', 'GSPC']
        
        # Clean score display without market characteristics
        score_display = f"{round(final_score)} ({rating})"
        
        # Format S&P 500 scores for comparison (only if not analyzing S&P 500 itself) with integer rounding
        sp500_comparison = "N/A"
        show_sp500_comparison = False
        if sp500_raw_score is not None and not is_sp500_analysis:
            # Show the raw S&P 500 score for direct comparison without market characteristic
            sp500_rating = VisualizationService._get_score_rating(sp500_raw_score)
            sp500_comparison = f"{round(sp500_raw_score)} ({sp500_rating})"
            show_sp500_comparison = True
        
        # Calculate signal metrics
        signal_metrics = VisualizationService._analyze_signals(signal_returns)
        
        # Create metrics lists - add S&P 500 score if available and not analyzing S&P 500 itself
        metrics = ["Stock Score", 'Regression Formula', 'Regression R²', 'Current Price', 
                  'Annualized Return', 'Annual Volatility', 'Total Trades',
                  'Win Rate', 'Average Trade Return']
        values = [
            score_display,
            regression_formula,
            f"{r2:.4f}",
            f"{currency_prefix}{end_price:.2f}",
            f"{annual_return:.2f}%",
            f"{annualized_volatility:.3f}",
            f"{signal_metrics['total_trades']}",
            f"{signal_metrics['win_rate']:.1f}%",
            f"{signal_metrics['average_return']:.2f}%"
        ]
        
        # Add S&P 500 comparison if data is available and we're not analyzing S&P 500 itself
        if show_sp500_comparison:
            metrics.insert(1, "S&P 500")  # Insert after Stock Score
            values.insert(1, sp500_comparison)
        
        return go.Table(
            domain=dict(x=table_domain['x'], y=table_domain['y']),
            header=dict(values=['<b>Metric</b>', '<b>Value</b>'], **table_style['header']),
            cells=dict(
                values=[metrics, values],
                **table_style['cells']
            )
        )

    @staticmethod
    def _create_trading_signal_table(signal_returns, table_style, table_domain, symbol=None):
        """Create the trading signal analysis table"""
        # Check if there are any signals with either entry or exit information
        if not signal_returns and not any('Exit Date' in signal for signal in signal_returns):
            return go.Table(
                domain=dict(x=table_domain['x'], y=table_domain['y']),
                header=dict(values=['<b>Notice</b>'], **table_style['header']),
                cells=dict(values=[['No trading signals found in the analysis period']], **table_style['cells'])
            )

        # Get currency prefix based on symbol
        currency_prefix = "$"  # Default to USD
        if symbol:
            if symbol.endswith('.HK') or symbol.startswith('HKEX:'):
                currency_prefix = "HK$"
            elif symbol.endswith(('.SS', '.SZ')) or any(symbol.startswith(x) for x in ['SSE:', 'SZSE:']):
                currency_prefix = "¥"
            elif symbol.endswith('.T') or symbol.startswith('TSE:'):
                currency_prefix = "¥"
            elif symbol.endswith('.L') or symbol.startswith('LSE:'):
                currency_prefix = "£"
            elif symbol.endswith('.F') or symbol.startswith('XETR:'):
                currency_prefix = "€"

        trades = []
        buy_signal = None
        for signal in signal_returns:
            if signal['Signal'] == 'Buy':
                buy_signal = signal
                if signal['Status'] == 'Open' and 'Trade Return' in signal:
                    trades.append({
                        'Entry Date': signal['Entry Date'].strftime('%Y-%m-%d'),
                        'Entry Price': f"{currency_prefix}{signal['Entry Price']:.2f}",
                        'Exit Date': 'Open',
                        'Exit Price': f"{currency_prefix}{signal['Current Price']:.2f}",
                        'Return': f"{signal['Trade Return']:.2f}%",
                        'Status': 'Open'
                    })
            elif signal['Signal'] == 'Sell':
                if buy_signal is not None:
                    trades.append({
                        'Entry Date': buy_signal['Entry Date'].strftime('%Y-%m-%d'),
                        'Entry Price': f"{currency_prefix}{buy_signal['Entry Price']:.2f}",
                        'Exit Date': signal['Entry Date'].strftime('%Y-%m-%d'),
                        'Exit Price': f"{currency_prefix}{signal['Entry Price']:.2f}",
                        'Return': f"{signal['Trade Return']:.2f}%",
                        'Status': 'Closed'
                    })
                    buy_signal = None
                elif 'Entry Date' not in signal and 'Exit Date' in signal:
                    trades.append({
                        'Entry Date': 'Unknown',
                        'Entry Price': 'Unknown',
                        'Exit Date': signal['Exit Date'].strftime('%Y-%m-%d'),
                        'Exit Price': f"{currency_prefix}{signal['Exit Price']:.2f}",
                        'Return': signal.get('Trade Return', 'N/A'),
                        'Status': 'Exit Only'
                    })

        return go.Table(
            domain=dict(x=table_domain['x'], y=table_domain['y']),
            header=dict(
                values=['<b>Entry Date</b>', '<b>Entry Price</b>', '<b>Exit Date</b>', 
                    '<b>Exit Price</b>', '<b>Return</b>', '<b>Status</b>'],
                **table_style['header']
            ),
            cells=dict(
                values=[
                    [t.get('Entry Date', '') for t in trades],
                    [t.get('Entry Price', '') for t in trades],
                    [t.get('Exit Date', '') for t in trades],
                    [t.get('Exit Price', '') for t in trades],
                    [t.get('Return', '') for t in trades],
                    [t.get('Status', '') for t in trades]
                ],
                **table_style['cells']
            )
        )
        
    @staticmethod
    def _create_chart_annotations(config, metrics_df=None):
        """Create chart annotations"""
        annotations = []
        
        # Add table headers based on layout type
        table_headers = {
            'analysis_summary': ('Analysis Summary', True),
            'trading_signals': ('Trading Signal Analysis', True),
            'company_info_title': ('Company Information', True)
        }
        
        if config['layout'] == 'stock' and metrics_df is not None:
            table_headers.update({
                'metrics': ('Financial Metrics', True),
                'growth': ('Growth Analysis', True)
            })

        # Get header positions based on layout type
        layout_type = config['layout']  # 'stock' or 'non_stock'
        headers_config = config['annotations'].get('headers', {})

        # Add headers if they are in config and should be shown
        for section, (title, should_show) in table_headers.items():
            if should_show and section in headers_config:
                header_pos = headers_config[section]
                text = header_pos.get('text', title)  # Use custom text if provided
                annotations.append(dict(
                    x=header_pos['x'],
                    y=header_pos['y'],
                    xref='paper',
                    yref='paper',
                    text=f'<b>{text}</b>',
                    showarrow=False,
                    font=dict(size=12),
                    align='left'
                ))

        return annotations

    @staticmethod
    def create_company_info_table(ticker, config):
        """Create company information table using cached yfinance data"""
        try:
            # Convert TradingView symbol to Yahoo Finance symbol
            yahoo_ticker = normalize_ticker(ticker)
            
            # Get company info from cache (much faster!)
            from app.utils.cache.company_info_cache import company_info_cache
            info = company_info_cache.get_basic_company_info(yahoo_ticker)
            
            if not info:
                # Fallback to direct yfinance call if cache fails
                logger.warning(f"Cache miss for {yahoo_ticker}, using direct yfinance")
                yf_ticker = yf.Ticker(yahoo_ticker)
                info = yf_ticker.info
            
            # Currency symbol mapping based on country
            currency_symbols = {
                'United States': '$',
                'China': '¥',
                'Japan': '¥',
                'Hong Kong': 'HK$',
                'United Kingdom': '£',
                'European Union': '€',
                'Australia': 'A$',
                'Canada': 'C$',
                'Switzerland': 'CHF',
                'India': '₹',
                'South Korea': '₩',
                'Singapore': 'S$',
                'Taiwan': 'NT$',
                'Brazil': 'R$'
            }
            
            # Get country and determine currency symbol
            country = info.get('country', 'United States')  # Default to US if country not found
            currency_symbol = currency_symbols.get(country, '$')  # Default to $ if country not in mapping
            
            # Format market cap with appropriate currency symbol
            market_cap = info.get('marketCap')
            market_cap_str = VisualizationService.format_number(market_cap, ticker)
            
            # Select relevant information
            company_data = {
                'Company Name': info.get('longName', info.get('shortName', 'N/A')),
                'Market Cap': market_cap_str,
                'Industry': info.get('industry', 'N/A'),
                'Sector': info.get('sector', 'N/A'),
                'Beta': f"{info.get('beta', 'N/A'):.2f}" if info.get('beta') else 'N/A',
                'Forward P/E': f"{info.get('forwardPE', 'N/A'):.2f}" if info.get('forwardPE') else 'N/A',
                'Dividend Yield': f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else 'N/A',
                'Country': country,
                'Employees': f"{info.get('fullTimeEmployees', 'N/A'):,}" if info.get('fullTimeEmployees') else 'N/A'
            }
            
            # Create table
            company_table = go.Table(
                domain=dict(
                    x=config['tables']['company_info']['x'],
                    y=config['tables']['company_info']['y']
                ),
                header=dict(
                    values=['<b>Metric</b>', '<b>Value</b>'],
                    **config['table_style']['header']
                ),
                cells=dict(
                    values=[
                        list(company_data.keys()),
                        list(company_data.values())
                    ],
                    **config['table_style']['cells']
                )
            )
            
            return company_table
        except Exception as e:
            logger.error(f"Error creating company info table: {str(e)}")
            return None

    @staticmethod
    def create_stock_analysis_chart(symbol, data, analysis_dates, ratios, prices, 
                                  appreciation_pcts, regression_results, 
                                  crossover_data, signal_returns, 
                                  metrics_df, total_height=LAYOUT_CONFIG['total_height']):
        """Create the complete stock analysis chart with all components"""
        config = VisualizationService._get_config(symbol)
        
        # Convert TradingView symbol to Yahoo Finance symbol for display
        yahoo_symbol = normalize_ticker(symbol)
        
        # Adjust total height for non-stocks
        if config['layout'] == 'non_stock':
            total_height *= 0.7

        fig = go.Figure()

        # Add price line
        fig.add_trace(
            go.Scatter(
                x=analysis_dates,
                y=prices,
                name='Price (Log Scale)',
                line=dict(
                    color=CHART_STYLE['colors']['price_line'],
                    **CHART_STYLE['line_styles']['price']
                ),
                yaxis='y2',
                hovertemplate='%{x}<br>' +
                             '<b>Price</b>: $%{y:.2f}<extra></extra>'
            )
        )
        
        # Add regression components
        future_dates = pd.date_range(
            start=data.index[0],
            periods=len(regression_results['predictions']),
            freq='D'
        )
        
        fig.add_trace(
            go.Scatter(
                x=future_dates,
                y=regression_results['predictions'],
                name='Regression',
                line=dict(
                    color=CHART_STYLE['colors']['regression_line'],
                    **CHART_STYLE['line_styles']['regression']
                ),
                yaxis='y2',
                hovertemplate='%{x}<br>' +
                             '<b>Predicted</b>: $%{y:.2f}<extra></extra>'
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=future_dates,
                y=regression_results['upper_band'],
                name='Upper Band',
                line=dict(
                    color=CHART_STYLE['colors']['confidence_band'],
                    **CHART_STYLE['line_styles']['bands']
                ),
                yaxis='y2',
                showlegend=False,
                hovertemplate='%{x}<br>' +
                             '<b>Upper Band</b>: $%{y:.2f}<extra></extra>'
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=future_dates,
                y=regression_results['lower_band'],
                name='Lower Band',
                fill='tonexty',
                fillcolor='rgba(173, 216, 230, 0.2)',
                line=dict(
                    color=CHART_STYLE['colors']['confidence_band'],
                    **CHART_STYLE['line_styles']['bands']
                ),
                yaxis='y2',
                showlegend=False,
                hovertemplate='%{x}<br>' +
                             '<b>Lower Band</b>: $%{y:.2f}<extra></extra>'
            )
        )
        
        # Add technical indicators
        fig.add_trace(
            go.Scatter(
                x=analysis_dates,
                y=ratios,
                name='Retracement Ratio',
                line=dict(
                    color=CHART_STYLE['colors']['retracement_line'],
                    **CHART_STYLE['line_styles']['retracement']
                ),
                hovertemplate='%{x}<br>' +
                             '<b>Ratio</b>: %{y:.1f}%<extra></extra>'
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=analysis_dates,
                y=appreciation_pcts,
                name='Price Position',
                line=dict(
                    color=CHART_STYLE['colors']['position_line'],
                    **CHART_STYLE['line_styles']['position']
                ),
                hovertemplate='%{x}<br>' +
                             '<b>Position</b>: %{y:.1f}%<extra></extra>'
            )
        )
        # Add R-square line (add this code in create_stock_analysis_chart method)
        # Place this after other line traces but before crossover points
        # Add R-square line
        # Add R-square line first with detailed debugging
        # Add R-square line first with detailed logging
        # Add R-square line with contrasting color
        if 'R2_Pct' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=analysis_dates,
                    y=data['R2_Pct'].values,
                    name='R² Quality',
                    line=dict(
                        color='#FF1493',  # Deep pink for high contrast
                        dash='dot',
                        width=2
                    ),
                    hovertemplate='%{x}<br>' +
                                '<b>R²</b>: %{y:.1f}%<extra></extra>'
                )
            )
        # Add price line


        # Add crossover points
        if crossover_data[0]:
            dates, values, directions, prices = crossover_data
            for date, value, direction, price in zip(dates, values, directions, prices):
                color = CHART_STYLE['colors']['bullish_marker'] if direction == 'up' else CHART_STYLE['colors']['bearish_marker']
                formatted_date = date.strftime('%Y-%m-%d')
                base_name = 'Bullish Crossover' if direction == 'up' else 'Bearish Crossover'
                detailed_name = f"({formatted_date}, ${price:.2f})"
                
                fig.add_trace(
                    go.Scatter(
                        x=[date],
                        y=[value],
                        mode='markers',
                        showlegend=False,
                        name=detailed_name,
                        marker=dict(
                            color=color,
                            **CHART_STYLE['marker_styles']['crossover']
                        ),
                        hovertemplate='<b>%{text}</b><br>' +
                                     '%{x}<br>' +
                                     '<b>Value</b>: %{y:.1f}%<br>' +
                                     '<b>Price</b>: $%{customdata:.2f}<extra></extra>',
                        text=[detailed_name],
                        customdata=[price]
                    )
                )
         # Add horizontal lines at key levels
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.1)
        fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.1)
        fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.1)

        # Add metrics tables
        metrics_table, growth_table = VisualizationService.create_financial_metrics_table(metrics_df, config, symbol)
        company_table = None  # Initialize company_table
        # Only get company info for stocks
        if is_stock(symbol):
            company_table = VisualizationService.create_company_info_table(symbol, config)
        
        if metrics_table:
            fig.add_trace(metrics_table)
        if growth_table:
            fig.add_trace(growth_table)
        if company_table:
            fig.add_trace(company_table)

        # Add analysis summary and trading signals tables
        analysis_table = VisualizationService._create_analysis_summary_table(
            days=(data.index[-1] - data.index[0]).days,
            end_price=data['Close'].iloc[-1],
            annual_return=((data['Close'].iloc[-1] / data['Close'].iloc[0]) ** (365 / (data.index[-1] - data.index[0]).days) - 1) * 100,
            daily_volatility=data['Close'].pct_change().std(),
            annualized_volatility=data['Close'].pct_change().std() * np.sqrt(252),
            r2=regression_results['r2'],
            regression_formula=regression_results['equation'],
            final_score=regression_results['total_score']['score'],
            table_style=config['table_style'],
            table_domain=config['tables']['analysis_summary'],
            signal_returns=signal_returns,
            symbol=symbol,
            sp500_raw_score=regression_results['total_score'].get('sp500_raw_score'),
            sp500_scaled_score=regression_results['total_score'].get('sp500_scaled_score')
        )
        fig.add_trace(analysis_table)

        trading_table = VisualizationService._create_trading_signal_table(
            signal_returns,
            table_style=config['table_style'],
            table_domain=config['tables']['trading_signals'],
            symbol=symbol
        )
        fig.add_trace(trading_table)

        # Create and add annotations
        annotations = VisualizationService._create_chart_annotations(config, metrics_df)

        # Update layout
        fig.update_layout(
            title=dict(
                text=f'{yahoo_symbol} Analysis Snapshot',
                x=0.5,
                xanchor='center',
                y=0.95,
                yanchor='top',
                font=dict(size=30)
            ),
            height=total_height,
            showlegend=True,
            hovermode='x unified',
            annotations=annotations,
            xaxis=dict(
                title=None,
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGrey',
                domain=[0.05, 0.95]  # Match table width
            ),
            xaxis2=dict(
                title=None,
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGrey',
                domain=[0.05, 0.95]  # Match table width
            ),
            yaxis=dict(
                title="Ratio and Position (%)",
                ticksuffix="%",
                range=[-10 , 120],
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
                showspikes=True,
                spikesnap='cursor',
                spikemode='across',
                spikethickness=1,
                domain=config['chart_area']['domain']['y'],
                anchor='x'  # Anchor to x-axis
            ),
            yaxis2=dict(
                title="Price (Log Scale)",
                overlaying="y",
                side="right",
                type="log",
                showgrid=False,
                showspikes=True,
                spikesnap='cursor',
                spikemode='across',
                spikethickness=1,
                domain=config['chart_area']['domain']['y'],
                anchor='x'  # Anchor to x-axis
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(
                l=40,  # Reduce left margin
                r=60,  # Reduce right margin
                t=0.05 * total_height,
                b=0.05 * total_height,
                autoexpand=True
            ),
            legend=LAYOUT_CONFIG['legend']  # Use legend configuration from layout_config
        )

        return fig

    @staticmethod
    def print_signal_analysis(signals_df):
        """Print detailed analysis of trading signals with statistics"""
        if signals_df.empty:
            print("No trading signals found in the analysis period.")
            return
            
        print("\nTrading Signal Analysis:")
        print("-" * 50)
        
        trades = []
        buy_signal = None
        
        for _, row in signals_df.iterrows():
            if row['Signal'] == 'Buy':
                buy_signal = row
                if row['Status'] == 'Open' and 'Trade Return' in row:
                    trades.append({
                        'Buy Date': row['Entry Date'],
                        'Buy Price': row['Entry Price'],
                        'Sell Date': 'Open',
                        'Sell Price': row['Current Price'],
                        'Return': row['Trade Return'],
                        'Status': 'Open'
                    })
            elif row['Signal'] == 'Sell' and buy_signal is not None:
                trades.append({
                    'Buy Date': buy_signal['Entry Date'],
                    'Buy Price': buy_signal['Entry Price'],
                    'Sell Date': row['Entry Date'],
                    'Sell Price': row['Entry Price'],
                    'Return': row['Trade Return'],
                    'Status': 'Closed'
                })
                buy_signal = None
        
        for i, trade in enumerate(trades, 1):
            print(f"\nTrade {i}:")
            print(f"Buy:  {trade['Buy Date'].strftime('%Y-%m-%d')} at ${trade['Buy Price']:.2f}")
            if trade['Status'] == 'Open':
                print(f"Current Position: OPEN at ${trade['Sell Price']:.2f}")
            else:
                print(f"Sell: {trade['Sell Date'].strftime('%Y-%m-%d')} at ${trade['Sell Price']:.2f}")
            print(f"Return: {trade['Return']:.2f}%")
            print(f"Status: {trade['Status']}")
        
        if trades:
            returns = [trade['Return'] for trade in trades]
            closed_trades = [t for t in trades if t['Status'] == 'Closed']
            open_trades = [t for t in trades if t['Status'] == 'Open']
            
            print("\nSummary Statistics:")
            print("-" * 50)
            print(f"Total Trades: {len(trades)}")
            print(f"Closed Trades: {len(closed_trades)}")
            print(f"Open Trades: {len(open_trades)}")
            if returns:
                print(f"Average Return per Trade: {np.mean(returns):.2f}%")
                print(f"Best Trade: {max(returns):.2f}%")
                print(f"Worst Trade: {min(returns):.2f}%")
                print(f"Win Rate: {len([r for r in returns if r > 0]) / len(returns) * 100:.1f}%")
            else:
                print("No completed trades to calculate statistics.")