# src/visualization/visualization_service.py

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.utils.config.layout_config import LAYOUT_CONFIG, CHART_STYLE, TABLE_STYLE

class VisualizationService:
    """Service class for creating and managing stock analysis visualizations."""

    @staticmethod
    def format_number(x):
        """Format numbers with comprehensive handling"""
        if pd.isna(x) or x is None:
            return "N/A"
        try:
            if abs(x) >= 1_000_000:
                return f"-{abs(x/1_000_000):,.0f}M" if x < 0 else f"{x/1_000_000:,.0f}M"
            else:
                return f"{x:,.2f}"
        except (TypeError, ValueError):
            return "N/A"

    @staticmethod
    def format_growth_values(growth_rates):
        """Format growth rates for display"""
        if not growth_rates:
            return []
        
        metrics = list(growth_rates.keys())
        if not metrics or not growth_rates[metrics[0]]:
            return []
        
        periods = len(growth_rates[metrics[0]])
        formatted_values = [metrics]
        
        for i in range(periods):
            period_values = []
            for metric in metrics:
                value = growth_rates[metric][i]
                if value is None:
                    period_values.append("N/A")
                else:
                    period_values.append(f"{value:+.1f}%" if value != 0 else "0.0%")
            formatted_values.append(period_values)
        
        return formatted_values

    @staticmethod
    def create_financial_metrics_table(df):
        """Create financial metrics tables"""
        if df is None or df.empty:
            return None, None

        formatted_df = df.copy()
        for col in df.columns:
            if col != 'CAGR %':
                formatted_df[col] = formatted_df[col].apply(VisualizationService.format_number)
            else:
                formatted_df[col] = formatted_df[col].apply(
                    lambda x: f"{x:+.2f}" if pd.notna(x) and x is not None else "N/A"
                )

        metrics_table = go.Table(
            domain=dict(
                x=LAYOUT_CONFIG['tables']['metrics']['x'],
                y=LAYOUT_CONFIG['tables']['metrics']['y']
            ),
            header=dict(
                values=['<b>Metric</b>'] + [f'<b>{col}</b>' for col in df.columns],
                **TABLE_STYLE['header']
            ),
            cells=dict(
                values=[
                    formatted_df.index.tolist(),
                    *[formatted_df[col].tolist() for col in formatted_df.columns]
                ],
                **TABLE_STYLE['cells']
            )
        )
        
        growth_table = None
        if not df.empty:
            df_columns = list(df.columns)
            year_columns = df_columns[1:-1]
            growth_rates = {
                metric: [
                    ((df.loc[metric, col] / df.loc[metric, prev_col] - 1) * 100)
                    if df.loc[metric, prev_col] != 0 else None
                    for prev_col, col in zip(year_columns[:-1], year_columns[1:])
                ]
                for metric in df.index
            }
            
            if growth_rates:
                formatted_values = VisualizationService.format_growth_values(growth_rates)
                if formatted_values:
                    growth_table = go.Table(
                        domain=dict(
                            x=LAYOUT_CONFIG['tables']['growth']['x'],
                            y=LAYOUT_CONFIG['tables']['growth']['y']
                        ),
                        header=dict(
                            values=['<b>Metric</b>'] + [f'<b>{year_columns[i]}</b>' 
                                   for i in range(1, len(year_columns))],
                            **TABLE_STYLE['header']
                        ),
                        cells=dict(
                            values=formatted_values,
                            **TABLE_STYLE['cells']
                        )
                    )
        
        return metrics_table, growth_table

    @staticmethod
    def _create_analysis_summary_table(days, end_price, annual_return, 
                                     daily_volatility, annualized_volatility, r2):
        """Create the analysis summary table"""
        return go.Table(
            domain=dict(
                x=LAYOUT_CONFIG['tables']['analysis_summary']['x'],
                y=LAYOUT_CONFIG['tables']['analysis_summary']['y']
            ),
            header=dict(
                values=['<b>Metric</b>', '<b>Value</b>'],
                **TABLE_STYLE['header']
            ),
            cells=dict(
                values=[
                    ['Total Days', 'Current Price', 'Annualized Return', 
                     'Daily Volatility', 'Annual Volatility', 'Regression R²'],
                    [
                        f"{days:,d}",
                        f"${end_price:.2f}",
                        f"{annual_return:.2f}%",
                        f"{daily_volatility:.3f}",
                        f"{annualized_volatility:.3f}",
                        f"{r2:.4f}"
                    ]
                ],
                **TABLE_STYLE['cells']
            )
        )

    @staticmethod
    def _create_trading_signal_table(signal_returns):
        """Create the trading signal analysis table"""
        if not signal_returns:
            return go.Table(
                domain=dict(
                    x=LAYOUT_CONFIG['tables']['trading_signals']['x'],
                    y=LAYOUT_CONFIG['tables']['trading_signals']['y']
                ),
                header=dict(
                    values=['<b>Notice</b>'],
                    **TABLE_STYLE['header']
                ),
                cells=dict(
                    values=[['No trading signals found in the analysis period']],
                    **TABLE_STYLE['cells']
                )
            )

        trades = []
        buy_signal = None
        for signal in signal_returns:
            if signal['Signal'] == 'Buy':
                buy_signal = signal
                if signal['Status'] == 'Open' and 'Trade Return' in signal:
                    trades.append({
                        'Entry Date': signal['Entry Date'].strftime('%Y-%m-%d'),
                        'Entry Price': signal['Entry Price'],
                        'Exit Date': 'Open',
                        'Exit Price': signal['Current Price'],
                        'Return': signal['Trade Return'],
                        'Status': 'Open'
                    })
            elif signal['Signal'] == 'Sell' and buy_signal is not None:
                trades.append({
                    'Entry Date': buy_signal['Entry Date'].strftime('%Y-%m-%d'),
                    'Entry Price': buy_signal['Entry Price'],
                    'Exit Date': signal['Entry Date'].strftime('%Y-%m-%d'),
                    'Exit Price': signal['Entry Price'],
                    'Return': signal['Trade Return'],
                    'Status': 'Closed'
                })
                buy_signal = None

        return go.Table(
            domain=dict(
                x=LAYOUT_CONFIG['tables']['trading_signals']['x'],
                y=LAYOUT_CONFIG['tables']['trading_signals']['y']
            ),
            header=dict(
                values=['<b>Entry Date</b>', '<b>Entry Price</b>', '<b>Exit Date</b>', 
                       '<b>Exit Price</b>', '<b>Return</b>', '<b>Status</b>'],
                **TABLE_STYLE['header']
            ),
            cells=dict(
                values=[
                    [t['Entry Date'] for t in trades],
                    [f"${t['Entry Price']:.2f}" for t in trades],
                    [t['Exit Date'] for t in trades],
                    [f"${t['Exit Price']:.2f}" for t in trades],
                    [f"{t['Return']:.2f}%" for t in trades],
                    [t['Status'] for t in trades]
                ],
                **TABLE_STYLE['cells']
            )
        )

    @staticmethod
    def _create_chart_annotations(start_price, end_price, annual_return, daily_volatility,
                                annualized_volatility, regression_results, total_return, 
                                signal_returns):
        """Create chart annotations"""
        annotations = []
        config = LAYOUT_CONFIG['annotations']
        
        # Stats annotations
        stats_info = [
            {
                'pos': config['stats']['price'],
                'text': f'<b>Price Analysis</b><br>' + 
                       f'Start: ${start_price:.2f}<br>' +
                       f'Current: ${end_price:.2f}<br>' +
                       f'Return: {annual_return:.2f}%'
            },
            {
                'pos': config['stats']['regression'],
                'text': f'<b>Regression Analysis</b><br>' +
                       f'{regression_results["equation"]}<br>' +
                       f'R² = {regression_results["r2"]:.4f}'
            },
            {
                'pos': config['stats']['volatility'],
                'text': f'<b>Volatility Analysis</b><br>' +
                       f'Daily: {daily_volatility:.3f}<br>' +
                       f'Annual: {annualized_volatility:.3f}'
            },
            {
                'pos': config['stats']['signals'],
                'text': f'<b>Signal Analysis</b><br>' +
                       f'Total Return: {total_return:.2f}%<br>' +
                       f'Trades: {len([s for s in signal_returns if s["Signal"] == "Buy"])}'
            }
        ]

        # Add stats annotations
        for info in stats_info:
            annotations.append(dict(
                x=info['pos']['x'],
                y=info['pos']['y'],
                xref='paper',
                yref='paper',
                text=info['text'],
                showarrow=False,
                font=dict(size=12),
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1,
                align='left'
            ))

        # Add table headers
        table_headers = {
            'analysis_summary': 'Analysis Summary',
            'trading_signals': 'Trading Signal Analysis',
            'metrics': 'Financial Metrics',
            'growth': 'Growth Analysis'
        }

        for section, title in table_headers.items():
            header_pos = config['headers'][section]
            annotations.append(dict(
                x=header_pos['x'],
                y=header_pos['y'],
                xref='paper',
                yref='paper',
                text=f'<b>{title}</b>',
                showarrow=False,
                font=dict(size=14),
                align='left'
            ))

        return annotations

    @staticmethod
    def create_stock_analysis_chart(symbol, data, analysis_dates, ratios, prices, 
                                  appreciation_pcts, regression_results, 
                                  crossover_data, signal_returns, 
                                  metrics_df, total_height=1400):
        """Create the complete stock analysis chart with all components"""
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
                hovertemplate='<b>Date</b>: %{x}<br>' +
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
                hovertemplate='<b>Date</b>: %{x}<br>' +
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
                hovertemplate='<b>Date</b>: %{x}<br>' +
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
                hovertemplate='<b>Date</b>: %{x}<br>' +
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
                hovertemplate='<b>Date</b>: %{x}<br>' +
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
                hovertemplate='<b>Date</b>: %{x}<br>' +
                             '<b>Position</b>: %{y:.1f}%<extra></extra>'
            )
        )
        
        # Add crossover points
        if crossover_data[0]:
            dates, values, directions, prices = crossover_data
            for date, value, direction, price in zip(dates, values, directions, prices):
                color = CHART_STYLE['colors']['bullish_marker'] if direction == 'up' else CHART_STYLE['colors']['bearish_marker']
                formatted_date = date.strftime('%Y-%m-%d')
                base_name = 'Bullish Crossover' if direction == 'up' else 'Bearish Crossover'
                detailed_name = f"{base_name} ({formatted_date}, ${price:.2f})"
                
                fig.add_trace(
                    go.Scatter(
                        x=[date],
                        y=[value],
                        mode='markers',
                        name=detailed_name,
                        marker=dict(
                            color=color,
                            **CHART_STYLE['marker_styles']['crossover']
                        ),
                        hovertemplate='<b>%{text}</b><br>' +
                                     '<b>Date</b>: %{x}<br>' +
                                     '<b>Value</b>: %{y:.1f}%<br>' +
                                     '<b>Price</b>: $%{customdata:.2f}<extra></extra>',
                        text=[detailed_name],
                        customdata=[price]
                    )
                )

        # Calculate metrics for annotations
        start_price = data['Close'].iloc[0]
        end_price = data['Close'].iloc[-1]
        days = (data.index[-1] - data.index[0]).days
        annual_return = ((end_price / start_price) ** (365 / days) - 1) * 100
        daily_volatility = data['Close'].pct_change().std()
        annualized_volatility = daily_volatility * np.sqrt(252)
        total_return = sum(s.get('Trade Return', 0) for s in signal_returns if 'Trade Return' in s)

        # Add metrics tables
        if metrics_df is not None:
            metrics_table, growth_table = VisualizationService.create_financial_metrics_table(metrics_df)
            if metrics_table:
                fig.add_trace(metrics_table)
            if growth_table:
                fig.add_trace(growth_table)

        # Add analysis summary table
        analysis_table = VisualizationService._create_analysis_summary_table(
            days=days,
            end_price=end_price,
            annual_return=annual_return,
            daily_volatility=daily_volatility,
            annualized_volatility=annualized_volatility,
            r2=regression_results['r2']
        )
        fig.add_trace(analysis_table)

        # Add trading signals table
        trading_table = VisualizationService._create_trading_signal_table(signal_returns)
        fig.add_trace(trading_table)

        # Create and add annotations
        annotations = VisualizationService._create_chart_annotations(
            start_price, end_price, annual_return, daily_volatility,
            annualized_volatility, regression_results, total_return, signal_returns
        )

        # Update layout
        fig.update_layout(
            title=dict(
                text=f'{symbol} Technical Analysis ({days} Days)',
                x=0.5,
                xanchor='center',
                font=dict(size=24)
            ),
            height=total_height,
            showlegend=True,
            hovermode='x unified',
            annotations=annotations,
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
                showspikes=True,
                spikesnap='cursor',
                spikemode='across',
                spikethickness=1,
                domain=LAYOUT_CONFIG['chart_area']['domain']['x']
            ),
            yaxis=dict(
                title="Ratio and Position (%)",
                ticksuffix="%",
                range=[-10, 120],
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
                showspikes=True,
                spikesnap='cursor',
                spikemode='across',
                spikethickness=1,
                domain=LAYOUT_CONFIG['chart_area']['domain']['y']
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
                domain=LAYOUT_CONFIG['chart_area']['domain']['y']
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(
                l=50, 
                r=50, 
                t=LAYOUT_CONFIG['spacing']['margin']['top'] * total_height,
                b=LAYOUT_CONFIG['spacing']['margin']['bottom'] * total_height
            ),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=1.15,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1,
                font=dict(size=11)
            )
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