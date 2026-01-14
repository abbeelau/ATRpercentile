import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go

# === ATR Percentile Indicator ===
def calculate_atr_percentile(df, atr_length=5, lookback_days=126):
    """
    Calculate ATR and its percentile rank over a lookback period.
    
    Returns:
    - atr_score: 1 if percentile > 50, else 0
    - atr_percentile: the actual percentile value
    """
    df = df.copy()
    
    # Calculate True Range
    df['tr1'] = df['High'] - df['Low']
    df['tr2'] = abs(df['High'] - df['Close'].shift(1))
    df['tr3'] = abs(df['Low'] - df['Close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    # Calculate ATR (using EMA for smoothing, similar to Pine Script's RMA)
    df['atr'] = df['tr'].ewm(alpha=1/atr_length, adjust=False).mean()
    
    # Calculate percentile rank over rolling window
    def percentile_rank(series):
        if len(series) < 20:
            return np.nan
        current_value = series.iloc[-1]
        return (series <= current_value).sum() / len(series) * 100
    
    df['atr_percentile'] = df['atr'].rolling(
        window=lookback_days, 
        min_periods=20
    ).apply(percentile_rank, raw=False)
    
    # Clean up temporary columns
    df.drop(['tr1', 'tr2', 'tr3', 'tr'], axis=1, inplace=True)
    
    return df

def get_atr_score(df):
    """
    Extract ATR score and percentile for checklist.
    Returns: (score, percentile_value, atr_value)
    """
    if df is None or len(df) == 0:
        return 0, None, None
    
    latest = df.iloc[-1]
    atr_percentile = latest.get('atr_percentile', None)
    atr_value = latest.get('atr', None)
    
    if pd.isna(atr_percentile):
        return 0, None, None
    
    # Score: 1 if percentile > 50, else 0
    score = 1 if atr_percentile > 50 else 0
    
    return score, round(atr_percentile, 1), round(atr_value, 4)

# === Main Analysis Function ===
def analyze_stock(ticker, period='1y', atr_length=5, lookback_days=126):
    """Complete stock analysis with ATR indicator"""
    try:
        # Download data
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        if df.empty:
            return None, "Unable to fetch data for this ticker"
        
        # Calculate ATR percentile
        df = calculate_atr_percentile(df, atr_length, lookback_days)
        
        # Get scores
        atr_score, atr_pct, atr_value = get_atr_score(df)
        
        # Get stock info
        info = stock.info
        current_price = df['Close'].iloc[-1]
        
        return {
            'ticker': ticker.upper(),
            'data': df,
            'atr_score': atr_score,
            'atr_percentile': atr_pct,
            'atr_value': atr_value,
            'current_price': current_price,
            'company_name': info.get('longName', ticker),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A')
        }, None
        
    except Exception as e:
        return None, f"Error analyzing {ticker}: {str(e)}"

# === Streamlit UI ===
def main():
    st.set_page_config(
        page_title="ATR Percentile Analyzer",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 ATR Percentile Analyzer")
    st.markdown("*Track Average True Range (ATR) volatility percentile for systematic trading*")
    
    # Sidebar inputs
    with st.sidebar:
        st.header("⚙️ Settings")
        
        ticker = st.text_input(
            "Stock Ticker", 
            value="AAPL",
            help="Enter stock symbol (e.g., AAPL, TSLA, MSFT)"
        ).upper()
        
        st.divider()
        
        period = st.selectbox(
            "Analysis Period", 
            ['2y', '1y', '6mo', '3mo'], 
            index=1,
            help="Historical data period for analysis"
        )
        
        atr_length = st.number_input(
            "ATR Length",
            min_value=1,
            max_value=50,
            value=5,
            help="Period for ATR calculation"
        )
        
        lookback_days = st.number_input(
            "Lookback Days",
            min_value=20,
            max_value=500,
            value=126,
            help="Days to calculate percentile (126 ≈ 6 months)"
        )
        
        st.divider()
        
        analyze_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)
        
        st.divider()
        st.markdown("### 📖 How to Use")
        st.markdown("""
        **ATR Percentile Score:**
        - **Score = 1**: ATR > 50th percentile (Higher volatility)
        - **Score = 0**: ATR ≤ 50th percentile (Lower volatility)
        
        **Interpretation:**
        - **Low percentile (<20%)**: Very calm market, potential breakout setup
        - **Mid percentile (40-60%)**: Normal volatility
        - **High percentile (>80%)**: Elevated volatility, caution advised
        """)
    
    # Main content
    if analyze_btn or ticker:
        with st.spinner(f"Analyzing {ticker}..."):
            result, error = analyze_stock(ticker, period, atr_length, lookback_days)
        
        if error:
            st.error(error)
            return
        
        if result:
            # === Header Section ===
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.subheader(f"{result['ticker']}")
                st.caption(f"{result['company_name']}")
                st.caption(f"{result['sector']} • {result['industry']}")
            
            with col2:
                st.metric("Current Price", f"${result['current_price']:.2f}")
            
            with col3:
                st.metric("ATR Value", f"{result['atr_value']:.4f}" if result['atr_value'] else "N/A")
            
            with col4:
                # Score display with color
                score = result['atr_score']
                score_emoji = "🟢" if score == 1 else "🔴"
                st.metric("Score", f"{score} {score_emoji}")
            
            st.divider()
            
            # === ATR Percentile Display ===
            st.header("📈 ATR Percentile Analysis")
            
            if result['atr_percentile'] is not None:
                percentile = result['atr_percentile']
                
                # Large percentile display
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    # Color coding based on percentile
                    if percentile < 20:
                        color = "🟢"
                        interpretation = "Very Low Volatility"
                        description = "Potential breakout setup - Market is very calm"
                    elif percentile < 40:
                        color = "🟡"
                        interpretation = "Below Average Volatility"
                        description = "Quieter than usual market conditions"
                    elif percentile < 60:
                        color = "🔵"
                        interpretation = "Normal Volatility"
                        description = "Average market volatility"
                    elif percentile < 80:
                        color = "🟠"
                        interpretation = "Above Average Volatility"
                        description = "More active than usual"
                    else:
                        color = "🔴"
                        interpretation = "Very High Volatility"
                        description = "Elevated risk - Consider wider stops"
                    
                    st.markdown(f"### {color} {percentile}%")
                    st.markdown(f"**{interpretation}**")
                    st.caption(description)
                
                st.divider()
                
                # Percentile gauge chart
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = percentile,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "ATR Percentile", 'font': {'size': 24}},
                    gauge = {
                        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkgray"},
                        'bar': {'color': "darkblue"},
                        'bgcolor': "white",
                        'borderwidth': 2,
                        'bordercolor': "gray",
                        'steps': [
                            {'range': [0, 20], 'color': '#90EE90'},
                            {'range': [20, 40], 'color': '#FFFFE0'},
                            {'range': [40, 60], 'color': '#ADD8E6'},
                            {'range': [60, 80], 'color': '#FFB84D'},
                            {'range': [80, 100], 'color': '#FFB6C1'}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 50
                        }
                    }
                ))
                
                fig_gauge.update_layout(
                    height=400,
                    margin=dict(l=20, r=20, t=80, b=20)
                )
                
                st.plotly_chart(fig_gauge, use_container_width=True)
                
            else:
                st.warning("Not enough data to calculate ATR percentile. Try a longer period.")
            
            st.divider()
            
            # === ATR Time Series Chart ===
            st.header("📉 ATR Percentile History")
            
            df = result['data']
            
            # Filter out NaN values for cleaner chart
            df_plot = df[df['atr_percentile'].notna()].copy()
            
            if len(df_plot) > 0:
                fig = go.Figure()
                
                # ATR Percentile line
                fig.add_trace(go.Scatter(
                    x=df_plot.index,
                    y=df_plot['atr_percentile'],
                    name='ATR Percentile',
                    line=dict(color='#1f77b4', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(31, 119, 180, 0.1)'
                ))
                
                # Reference lines
                fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                             annotation_text="50th Percentile", annotation_position="right")
                fig.add_hline(y=20, line_dash="dot", line_color="green", 
                             annotation_text="20th (Low)", annotation_position="right")
                fig.add_hline(y=80, line_dash="dot", line_color="red", 
                             annotation_text="80th (High)", annotation_position="right")
                
                # Highlight current level
                current_pct = df_plot['atr_percentile'].iloc[-1]
                fig.add_trace(go.Scatter(
                    x=[df_plot.index[-1]],
                    y=[current_pct],
                    mode='markers',
                    marker=dict(size=12, color='red', symbol='diamond'),
                    name='Current',
                    showlegend=True
                ))
                
                fig.update_layout(
                    title=f"ATR({atr_length}) Percentile - {lookback_days} Day Lookback",
                    xaxis_title="Date",
                    yaxis_title="Percentile (%)",
                    hovermode='x unified',
                    height=500,
                    yaxis=dict(range=[0, 100])
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # === Price Chart with ATR overlay ===
                st.header("💹 Price Chart")
                
                fig_price = go.Figure()
                
                # Price candlestick
                fig_price.add_trace(go.Candlestick(
                    x=df_plot.index,
                    open=df_plot['Open'],
                    high=df_plot['High'],
                    low=df_plot['Low'],
                    close=df_plot['Close'],
                    name='Price'
                ))
                
                fig_price.update_layout(
                    title=f"{result['ticker']} Price Chart",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    hovermode='x unified',
                    height=500,
                    xaxis_rangeslider_visible=False
                )
                
                st.plotly_chart(fig_price, use_container_width=True)
                
                # === Data Table ===
                with st.expander("📊 View Raw Data"):
                    display_df = df_plot[['Close', 'atr', 'atr_percentile']].tail(50).copy()
                    display_df.columns = ['Close Price', 'ATR', 'ATR Percentile']
                    display_df = display_df.iloc[::-1]  # Reverse to show most recent first
                    st.dataframe(display_df, use_container_width=True)
            
            else:
                st.warning("Not enough data to generate charts.")
    
    else:
        # Welcome screen
        st.info("👈 Enter a stock ticker in the sidebar and click Analyze to get started!")
        
        st.markdown("""
        ### About This Tool
        
        This application calculates the **ATR (Average True Range) Percentile** for stocks, 
        helping you identify volatility levels for systematic trading decisions.
        
        **What is ATR Percentile?**
        - Measures where current ATR sits relative to historical ATR values
        - 50th percentile = median volatility over the lookback period
        - Higher percentile = higher current volatility vs. historical average
        
        **Scoring System:**
        - Score of **1** = ATR > 50th percentile (elevated volatility)
        - Score of **0** = ATR ≤ 50th percentile (below median volatility)
        
        **Trading Applications:**
        - Low ATR percentile (<20%): Potential breakout setup, tighter stops
        - High ATR percentile (>80%): Elevated risk, wider stops recommended
        - Use with other indicators for complete trading system
        """)

if __name__ == "__main__":
    main()
