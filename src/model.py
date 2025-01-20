import logging

import numpy as np
import pandas as pd
import ta
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from config.config import config
from src import notifier


class Model:
    def __init__(self, telegram_token, telegram_chat_id):
        self.model = RandomForestClassifier()
        self.logger = logging.getLogger(__name__)
        self.short_window = config['short_window']
        self.long_window = config['long_window']
        self.notifier = notifier.Notifier(telegram_token, telegram_chat_id)

    def preprocess_data(self, data):
        if data is None or data.empty:
            self.logger.warning("No data received for preprocessing.")
            return None

        self.logger.info(f"Preprocessing {len(data)} rows of data...")

        required_length = max(self.short_window, self.long_window, 14, 10)  # Ensure sufficient rows for indicators
        if len(data) < required_length:
            self.logger.warning(
                f"Not enough data points for indicators calculation. Required: {required_length}, Got: {len(data)}.")
            return None

        try:
            # Log close price distribution
            self.logger.info(f"Close price stats - Min: {data['Close'].min()}, Max: {data['Close'].max()}, "
                        f"Mean: {data['Close'].mean()}, StdDev: {data['Close'].std()}")

            # Calculate Indicators
            data['Short_MA'] = data['Close'].rolling(window=self.short_window).mean()
            data['Long_MA'] = data['Close'].rolling(window=self.long_window).mean()
            data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()

            macd = ta.trend.MACD(data['Close'], window_slow=26, window_fast=12, window_sign=9)
            data['MACD'] = macd.macd()
            data['MACD_Signal'] = macd.macd_signal()

            bollinger = ta.volatility.BollingerBands(data['Close'], window=20, window_dev=2)
            data['Bollinger_Middle'] = bollinger.bollinger_mavg()
            data['Bollinger_Upper'] = bollinger.bollinger_hband()
            data['Bollinger_Lower'] = bollinger.bollinger_lband()  # Correct method

            # Add new features based on price movement
            data['Momentum'] = data['Close'] - data['Close'].shift(10)
            data['ROC'] = data['Close'].diff(10) / data['Close'].shift(10) * 100

            # Log indicator statistics
            self.logger.info(f"Short_MA head: {data['Short_MA'].head()}")
            self.logger.info(f"Long_MA head: {data['Long_MA'].head()}")
            self.logger.info(f"RSI head: {data['RSI'].head()}")
            self.logger.info(f"MACD head: {data['MACD'].head()}")
            self.logger.info(f"Bollinger Upper head: {data['Bollinger_Upper'].head()}")

            # Drop rows with NaN values
            initial_len = len(data)
            data.dropna(inplace=True)
            self.logger.info(
                f"Dropped {initial_len - len(data)} rows due to NaN values. Final data length: {len(data)} rows.")

            if len(data) == 0:
                self.logger.warning("All rows were dropped after NaN removal.")
                return None

            # Signal column: Buy/Sell logic
            data['Signal'] = np.where(
                (data['Short_MA'] > data['Long_MA']) & (data['RSI'] < 70), 1, 0
            )
            self.logger.info(f"Modified Signal distribution: {data['Signal'].value_counts().to_dict()}")
            return data

        except Exception as e:
            self.logger.error(f"Error during preprocessing: {e}")
            return None

    def train_model(self, data):
        if data is None or data.empty:
            self.logger.warning("No data to train on.")
            return False  # Indicate training failure

        self.logger.info("Starting the machine learning model training process...")

        features = [
            'Short_MA', 'Long_MA', 'RSI', 'MACD', 'MACD_Signal',
            'Bollinger_Middle', 'Bollinger_Upper', 'Bollinger_Lower',
            'Momentum', 'ROC'
        ]

        missing_features = [feature for feature in features if feature not in data.columns]
        if missing_features:
            self.logger.warning(f"Missing features in data: {missing_features}")
            features = [feature for feature in features if feature in data.columns]
            self.logger.info(f"Using available features for training: {features}")

        if not features:
            self.logger.error("No available features for training. Skipping this step.")
            return False  # Indicate training failure

        X = data[features]
        y = data['Signal']

        if X.empty or y.empty:
            self.logger.warning("No valid features or target for training.")
            return False  # Indicate training failure

        signal_distribution = dict(pd.Series(y).value_counts())
        self.logger.info(f"Signal distribution for training: {signal_distribution}")
        if len(signal_distribution) < 2:
            self.logger.error("Insufficient signal diversity for training (e.g., all signals are the same).")
            return False  # Indicate training failure

        if len(X) < 10:
            self.logger.error("Insufficient data to train the model. At least 10 rows of data are required.")
            return False  # Indicate training failure

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        try:
            self.logger.info(f"Model state before training: {self.model}")
            self.logger.info(f"Shape of features (X) used for training: {X_train.shape}")
            self.logger.info(f"Shape of target (y) used for training: {y_train.shape}")

            self.model.fit(X_train, y_train)

            self.logger.info("Model training completed.")

            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            self.logger.info(f"Model trained successfully with accuracy: {accuracy * 100:.2f}%.")

        except Exception as e:
            self.logger.error(f"Model training failed with exception: {e}")
            return False  # Indicate training failure

        try:
            self.model.n_features_ = X_train.shape[1]  # Ensure n_features_ is set
            self.logger.info(f"Model successfully trained. Number of features used: {self.model.n_features_}.")
        except Exception as e:
            self.logger.error(f"Failed to set or log model attributes: {e}")
            return False

        self.logger.info(f"Model state after training: {self.model}")
        self.logger.info(f"Model parameters: {self.model.get_params()}")

        return True  # Indicate training success


    def predict_signal(self, data):
        if data is None or data.empty:
            self.logger.warning("No data available for prediction.")
            return None

        self.logger.info("Predicting the next signal based on the latest data...")

        # Features used for prediction
        features = [
            'Short_MA', 'Long_MA', 'RSI', 'MACD', 'MACD_Signal',
            'Bollinger_Middle', 'Bollinger_Upper', 'Bollinger_Lower',
            'Momentum', 'ROC'
        ]
        if 'Volume_MA' in data.columns:
            features.append('Volume_MA')
        if 'Volatility' in data.columns:
            features.append('Volatility')

        # Get the most recent data (row for prediction)
        latest_data = data.tail(1)
        X = latest_data[features]

        try:
            # Ensure the model is trained before making predictions
            if self.model is None or not hasattr(self.model, 'n_features_'):
                self.logger.error("Model is not yet trained. Training is required before making predictions.")
                return None

            # Perform prediction
            prediction = self.model.predict(X)[0]
            self.logger.info(f"Prediction complete. Signal: {'Buy' if prediction == 1 else 'Sell'}")

            # Get explanation for the decision
            explanation = self.get_decision_explanation(latest_data.iloc[0], prediction)

            # Prepare message for Telegram
            decision = "Buy" if prediction == 1 else "Sell"
            close_price = latest_data['Close'].values[0]
            current_time = latest_data.index[0]
            message = (
                f"<b>Trading Signal Alert</b>\n\n"
                f"<b>Signal:</b> {decision}\n"
                f"<b>Time:</b> {current_time}\n"
                f"<b>Close Price:</b> {close_price:.2f}\n\n"
                f"<b>Indicators Summary:</b>\n"
                f"RSI: {latest_data['RSI'].values[0]:.2f}\n"
                f"Short MA: {latest_data['Short_MA'].values[0]:.2f}\n"
                f"Long MA: {latest_data['Long_MA'].values[0]:.2f}\n"
                f"MACD: {latest_data['MACD'].values[0]:.2f}\n"
                f"MACD Signal: {latest_data['MACD_Signal'].values[0]:.2f}\n"
                f"Bollinger Upper: {latest_data['Bollinger_Upper'].values[0]:.2f}\n"
                f"Bollinger Lower: {latest_data['Bollinger_Lower'].values[0]:.2f}\n\n"
                f"<b>Decision Explanation:</b>\n"
                f"{explanation}\n"
            )

            # Send the message to Telegram
            self.notifier.send_telegram_message(message)

            return prediction

        except Exception as e:
            self.logger.error(f"Error during prediction: {e}")
            return None

    def get_decision_explanation(self, row, prediction):
            """
            Generate an explanation for the predicted signal (buy/sell).
            :param row: A row of the DataFrame containing the latest indicator data.
            :param prediction: The prediction output from the model (1 for buy, 0 for sell).
            :return: A text explanation for the decision.
            """
            # Define thresholds (these values may need tuning based on your strategy)
            overbought_threshold = 70  # RSI > 70 indicates overbought
            oversold_threshold = 30  # RSI < 30 indicates oversold

            # Build explanation based on indicators
            explanation = []

            # RSI-based explanation
            if row['RSI'] > overbought_threshold:
                explanation.append(f"RSI indicates overbought (RSI = {row['RSI']:.2f}).")
            elif row['RSI'] < oversold_threshold:
                explanation.append(f"RSI indicates oversold (RSI = {row['RSI']:.2f}).")

            # Moving Average Crossover explanation
            if row['Short_MA'] > row['Long_MA']:
                explanation.append(f"Short-term Moving Average is above Long-term Moving Average (Bullish signal).")
            else:
                explanation.append(f"Short-term Moving Average is below Long-term Moving Average (Bearish signal).")

            # MACD explanation
            if row['MACD'] > row['MACD_Signal']:
                explanation.append(f"MACD is above Signal line (Bullish signal).")
            else:
                explanation.append(f"MACD is below Signal line (Bearish signal).")

            # Bollinger Bands explanation
            if row['Close'] > row['Bollinger_Upper']:
                explanation.append(f"Price is above the Bollinger Upper Band (Overbought).")
            elif row['Close'] < row['Bollinger_Lower']:
                explanation.append(f"Price is below the Bollinger Lower Band (Oversold).")

            # Summarize explanation for the decision
            if prediction == 1:  # Buy
                explanation.append("Decision: BUY based on the above signals.")
            else:  # Sell
                explanation.append("Decision: SELL based on the above signals.")

            return " ".join(explanation)
