import warnings
import time
import os
from config.config import config
from src.data_fetcher import DataFetcher
from src.model import Model
from src.order_manager import OrderManager
from src.notifier import Notifier
from src.logger import setup_logger
import ccxt  # Import the ccxt library
from simulation_engine import SimulationEngine


# Ignore warnings
warnings.filterwarnings("ignore")

class MovingAverageCrossoverML:
    def __init__(self, config, telegram_token, telegram_chat_id, simulation_mode=False):
        self.config = config
        self.model = Model(config['telegram_token'], config['telegram_chat_id'])
        self.symbols = config['symbols']
        self.short_window = config['short_window']
        self.long_window = config['long_window']
        self.tp_percentage = config['tp_percentage']
        self.sl_percentage = config['sl_percentage']
        self.leverage = config['leverage']
        self.investment_amount = config['investment_amount']
        self.interval = config['interval']
        self.period = config['period']
        self.sleep_time = config['sleep_time']
        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.passphrase = config['passphrase']
        self.check_interval = config['check_interval']
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.log_file = os.path.join(os.path.dirname(__file__), '../data/trade_log.csv')
        self.logger = setup_logger()

        if simulation_mode:
            self.kucoin = SimulationEngine()  # Use the mock simulation engine
            self.logger.info("Simulation mode enabled. Mock data will be used for all trades and price movements.")
        else:
            self.kucoin = ccxt.kucoinfutures({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'password': self.passphrase,
                'enableRateLimit': True,
            })
            self.logger.info("Connected to live KuCoin Futures for real trading.")

        self.open_orders = []
        self.usdt_balance = 0
        if not simulation_mode:  # Only check live connection in real mode
            self.check_connection()

        self.data_fetcher = DataFetcher(self.kucoin, self.interval)
        self.order_manager = OrderManager(self.kucoin, self.config, self.log_file)
        self.notifier = Notifier(self.telegram_token, self.telegram_chat_id)

    def check_connection(self):
        try:
            balance = self.kucoin.fetch_balance()
            self.usdt_balance = balance['total'].get('USDT', 0)
            self.logger.info("Successfully connected to KuCoin Futures.")
            self.logger.info(f"Available balance in your futures account: USDT {self.usdt_balance}")
        except Exception as e:
            self.logger.error(f"Error connecting to KuCoin Futures: {e}")

    def run(self):
        """
        The main method to fetch data, train the model, predict signals, and manage trades.
        """
        while True:
            for symbol in self.symbols:
                self.logger.info(f"Fetching latest data and predicting signal for {symbol}...")

                # Fetch data
                data = self.data_fetcher.fetch_data(symbol)
                if data is None:
                    self.logger.warning(f"Skipping {symbol} due to missing data.")
                    continue

                # Preprocess data
                live_data = self.model.preprocess_data(data.tail(100))
                if live_data is None:
                    self.logger.warning(f"Skipping {symbol} due to preprocessing failure.")
                    continue

                self.logger.info(
                    f"Final Signal distribution: {live_data['Signal'].value_counts().to_dict() if 'Signal' in live_data else 'No Signals'}")

                # Train the model if it is not yet trained, or if this is the first cycle
                if not hasattr(self.model, 'n_features_'):
                    self.logger.info(f"Model is not trained. Training the model with data for {symbol}...")
                    if not self.model.train_model(live_data):  # Train the model with available data
                        self.logger.error("Model validation failed after training in the run cycle.")
                        self.logger.info(f"Model object: {self.model}")
                        continue  # Skip processing if training failed
                    self.logger.info(
                        f"Model is ready for predictions. Features: {getattr(self.model, 'n_features_', 'Unknown')}")

                # Predict the signal
                new_signal = self.model.predict_signal(live_data)
                if new_signal is None:
                    self.logger.warning(f"No valid signal for {symbol}. Skipping.")
                    continue

                self.logger.info(f"New Signal for {symbol}: {'BUY' if new_signal == 1 else 'SELL'}")

                # Check if any open orders exist
                formatted_symbol = self.order_manager.format_symbol(symbol)
                existing_order = next(
                    (order for order in self.order_manager.open_orders if order['symbol'] == formatted_symbol),
                    None
                )

                if existing_order:
                    # Log the existing order and signal comparison
                    self.logger.info(
                        f"Existing order for {symbol}: {existing_order}. Signal: {'BUY' if new_signal == 1 else 'SELL'}")

                    # Check for conflicting signals
                    current_price = self.data_fetcher.kucoin.fetch_ticker(formatted_symbol)['last']
                    if ((existing_order['direction'] == 'buy' and new_signal == 0) or
                            (existing_order['direction'] == 'sell' and new_signal == 1)):
                        self.logger.info(f"Conflicting signal for {symbol}. Closing open order and placing a new one.")
                        self.order_manager.close_order(existing_order, current_price)
                        self.order_manager.place_order(symbol, new_signal)
                    else:
                        self.logger.info(f"Signal unchanged for {symbol}. No action taken.")
                else:
                    self.logger.info(
                        f"No existing order for {symbol}. Placing a new {'BUY' if new_signal == 1 else 'SELL'} order.")
                    self.order_manager.place_order(symbol, new_signal)

            self.logger.info("Monitoring open trades...")
            self.order_manager.monitor_trades()

            # Pause for the configured check interval
            self.logger.info(f"Sleeping for {self.check_interval} minutes before next cycle...")
            time.sleep(self.check_interval * 60)


# Run the bot
bot = MovingAverageCrossoverML(
    config,
    telegram_token=config['telegram_token'],
    telegram_chat_id=config['telegram_chat_id'],
    simulation_mode=False  # Use simulation mode for testing
)
bot.run()