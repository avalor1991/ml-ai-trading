# ml-ai-trading
```markdown
# ML AI Trading Bot

This project is a machine learning-based trading bot that uses technical indicators to predict buy and sell signals for cryptocurrency trading on KuCoin Futures. The bot fetches historical data, preprocesses it, trains a machine learning model, and places orders based on the predicted signals.

## Features

- Fetches historical data from KuCoin Futures
- Preprocesses data to calculate technical indicators
- Trains a machine learning model to predict buy/sell signals
- Places orders on KuCoin Futures based on the predicted signals
- Monitors open trades and manages stop-loss and take-profit levels
- Sends notifications via Telegram

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/ml-ai-trading.git
    cd ml-ai-trading
    ```

2. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Configuration

Update the `config/config.py` file with your KuCoin API credentials and other configuration settings:
```python
config = {
    'symbols': ['BTC-USD'],
    'short_window': #,
    'long_window': #,
    'tp_percentage': #,
    'sl_percentage': #,
    'leverage': #,
    'investment_amount': #,
    'interval': '#',
    'period': '#',
    'sleep_time': #,
    'api_key': '#',
    'api_secret': 'your_api_secret',
    'passphrase': 'your_passphrase',
    'check_interval': #,
    'telegram_token': 'your_telegram_token',
    'telegram_chat_id': 'your_telegram_chat_id'
}
```

## Usage

Run the bot with the following command:
```sh
python bot.py
```

## Logging

Logs are stored in the `logs` directory. You can view the logs to monitor the bot's activity and debug any issues.

## Dependencies

- `requests`
- `numpy`
- `scikit-learn`
- `ccxt`
- `tabulate`
- `pandas`
- `ta`

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
```

Make sure to replace `yourusername`, `your_api_key`, `your_api_secret`, `your_passphrase`, `your_telegram_token`, and `your_telegram_chat_id` with your actual values.
