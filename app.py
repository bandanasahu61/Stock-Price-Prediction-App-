from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objs as go
import plotly.utils
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for all routes

def get_usd_to_inr_rate():
    try:
        usdinr = yf.Ticker("INR=X")
        current_rate = usdinr.history(period='1d')['Close'].iloc[-1]
        return current_rate
    except:
        return 83.0

def calculate_prediction(df):
    # Calculate moving averages
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    # Create prediction for next 7 days
    last_date = df.index[-1]
    
    # Generate future dates (next 7 business days)
    future_dates = pd.date_range(last_date + timedelta(days=1), periods=7, freq='B')
    
    # Use last MA5 and MA20 values for prediction
    last_ma5 = df['MA5'].iloc[-1]
    last_ma20 = df['MA20'].iloc[-1]
    last_close = df['Close'].iloc[-1]
    
    # Simple prediction model
    prediction_values = []
    current_value = last_close
    
    for _ in range(7):
        # Predict next value using weighted average of MA5, MA20 and current value
        next_value = (0.5 * current_value + 0.3 * last_ma5 + 0.2 * last_ma20)
        prediction_values.append(next_value)
        current_value = next_value
    
    # Create DataFrame with predictions
    predictions_df = pd.DataFrame(index=future_dates, data={'Predicted': prediction_values})
    return predictions_df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        ticker = request.form['ticker']
        
        # Get stock data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Fetch data using yfinance
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            return jsonify({'error': 'No data found for this ticker'})

        # Get USD to INR conversion rate
        usd_inr_rate = get_usd_to_inr_rate()
        
        # Get predictions
        predictions_df = calculate_prediction(df)

        # Create the plot
        fig = go.Figure()
        
        # Add actual price line
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Close'],
            name='Actual Price (USD)',
            line=dict(color='#00ff88')
        ))
        
        # Add predicted price line
        fig.add_trace(go.Scatter(
            x=predictions_df.index,
            y=predictions_df['Predicted'],
            name='Predicted Price (USD)',
            line=dict(color='#ff9900', dash='dash')
        ))
        
        # Add INR price line
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Close'] * usd_inr_rate,
            name='Actual Price (INR)',
            line=dict(color='#00ff88', dash='dot'),
            visible='legendonly'
        ))
        
        # Add predicted INR price line
        fig.add_trace(go.Scatter(
            x=predictions_df.index,
            y=predictions_df['Predicted'] * usd_inr_rate,
            name='Predicted Price (INR)',
            line=dict(color='#ff9900', dash='dashdot'),
            visible='legendonly'
        ))
        
        # Add volume bar chart
        fig.add_trace(go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            yaxis='y2'
        ))

        # Update layout
        fig.update_layout(
            title=f'{ticker} Stock Price and Prediction (USD & INR)',
            yaxis_title='Price (USD)',
            yaxis2=dict(
                title='Volume',
                overlaying='y',
                side='right'
            ),
            xaxis_title='Date',
            template='plotly_dark',
            height=600,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        # Convert to JSON
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        # Calculate daily returns and price changes
        df['Daily_Return'] = df['Close'].pct_change()
        
        # Calculate price changes
        current_price_usd = float(df['Close'][-1])
        previous_price_usd = float(df['Close'][-2])
        price_change_usd = current_price_usd - previous_price_usd
        
        # Calculate INR values
        current_price_inr = current_price_usd * usd_inr_rate
        price_change_inr = price_change_usd * usd_inr_rate
        
        # Get predicted values
        predicted_price_usd = float(predictions_df['Predicted'].iloc[0])
        predicted_change_usd = predicted_price_usd - current_price_usd
        predicted_price_inr = predicted_price_usd * usd_inr_rate
        predicted_change_inr = predicted_change_usd * usd_inr_rate
        
        return jsonify({
            'status': 'success',
            'plot': graphJSON,
            'data': {
                'last_price_usd': round(current_price_usd, 2),
                'last_price_inr': round(current_price_inr, 2),
                'change_usd': round(price_change_usd, 2),
                'change_inr': round(price_change_inr, 2),
                'change_percent': round(float(df['Daily_Return'][-1] * 100), 2),
                'volume': int(df['Volume'][-1]),
                'high_usd': round(float(df['High'][-1]), 2),
                'high_inr': round(float(df['High'][-1] * usd_inr_rate), 2),
                'low_usd': round(float(df['Low'][-1]), 2),
                'low_inr': round(float(df['Low'][-1] * usd_inr_rate), 2),
                'open_usd': round(float(df['Open'][-1]), 2),
                'open_inr': round(float(df['Open'][-1] * usd_inr_rate), 2),
                'predicted_price_usd': round(predicted_price_usd, 2),
                'predicted_price_inr': round(predicted_price_inr, 2),
                'predicted_change_usd': round(predicted_change_usd, 2),
                'predicted_change_inr': round(predicted_change_inr, 2),
                'usd_inr_rate': round(usd_inr_rate, 2)
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
