import time
import math
import logging
import csv
from datetime import datetime
import os
from tabulate import tabulate  # Ensure the correct import

class OrderManager:
    def __init__(self, kucoin, config, log_file):
        self.kucoin = kucoin
        self.config = config
        self.log_file = log_file
        self.open_orders = []
        self.logger = logging.getLogger(__name__)
        self.initialize_log_file()

    def initialize_log_file(self):
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            self.logger.info(f"Created missing directory: {log_dir}")

        with open(self.log_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                'timestamp', 'symbol', 'direction', 'order_size', 'entry_price',
                'exit_price', 'stop_loss', 'take_profit'
            ])
        self.logger.info(f"Log file initialized at: {self.log_file}")

    def format_symbol(self, symbol):
        return symbol.replace("-", "/").replace("USD", "USDT:USDT")

    def place_order(self, symbol, signal):
        if signal is None:
            self.logger.warning(f"No signal available to place an order for {symbol}.")
            return

        formatted_symbol = self.format_symbol(symbol)
        self.logger.info(f"Placing order for {formatted_symbol}. Signal: {'BUY' if signal == 1 else 'SELL'}")

        for order in self.open_orders:
            if order['symbol'] == formatted_symbol and (
                    (signal == 1 and order['direction'] == 'buy') or (signal == 0 and order['direction'] == 'sell')):
                self.logger.info(
                    f"An open {'BUY' if signal == 1 else 'SELL'} order already exists for {formatted_symbol}. Skipping.")
                return

        try:
            ticker = self.kucoin.fetch_ticker(formatted_symbol)
            current_price = ticker['last']
            self.logger.info(f"Current price for {formatted_symbol}: {current_price}")

            order_size = (self.config['investment_amount'] * self.config['leverage']) / current_price
            if order_size < 1:
                self.logger.warning("Order size is too small. Adjusting investment_amount.")
                self.config['investment_amount'] = math.ceil(current_price / self.config['leverage'])
                order_size = (self.config['investment_amount'] * self.config['leverage']) / current_price
                self.logger.info(f"Adjusted investment amount: {self.config['investment_amount']}")

            side = 'buy' if signal == 1 else 'sell'
            stop_loss_price = current_price * (
                        1 - self.config['sl_percentage'] / 100) if side == 'buy' else current_price * (
                        1 + self.config['sl_percentage'] / 100)
            take_profit_price = current_price * (
                        1 + self.config['tp_percentage'] / 100) if side == 'buy' else current_price * (
                        1 - self.config['tp_percentage'] / 100)

            client_oid = f"order_{int(time.time())}"
            for attempt in range(3):
                try:
                    order = self.kucoin.create_order(
                        symbol=formatted_symbol,
                        type='market',
                        side=side,
                        amount=order_size,
                        params={
                            'leverage': self.config['leverage'],
                            'marginMode': 'ISOLATED',
                            'clientOid': client_oid,
                            'reduceOnly': False
                        }
                    )
                    self.logger.info(
                        f"Order placed: {side.upper()} {formatted_symbol}, Size: {order_size}, Price: {current_price}")
                    self.logger.info(f"SL: {stop_loss_price}, TP: {take_profit_price}")
                    self.open_orders.append({
                        'symbol': formatted_symbol,
                        'direction': side,
                        'order_size': order_size,
                        'entry_price': current_price,
                        'stop_loss_price': stop_loss_price,
                        'take_profit_price': take_profit_price
                    })
                    self.show_open_trades()
                    break
                except Exception as e:
                    self.logger.error(f"Order placement attempt {attempt + 1} failed for {symbol}: {e}")
                    time.sleep(5)
                    continue
        except Exception as e:
            self.logger.error(f"Order placement failed for {symbol}: {e}")

    def monitor_trades(self):
        for order in self.open_orders[:]:
            current_price = self.kucoin.fetch_ticker(order['symbol'])['last']
            if order['direction'] == 'buy':
                if current_price <= order['stop_loss_price'] or current_price >= order['take_profit_price']:
                    self.close_order(order, current_price)
            else:
                if current_price >= order['stop_loss_price'] or current_price <= order['take_profit_price']:
                    self.close_order(order, current_price)

        self.show_open_trades()

    def show_open_trades(self):
        if not self.open_orders:
            self.logger.info("No open trades to display.")
            return

        self.logger.info("Open trades summary:")
        table = []
        headers = ["Symbol", "Direction", "Order Size", "Entry Price", "Current Price", "Stop Loss", "Take Profit", "Profit Percentage"]
        for order in self.open_orders:
            try:
                current_price = self.kucoin.fetch_ticker(order['symbol'])['last']
                profit_percentage = self.calculate_profit_percentage(order['entry_price'], current_price, order['direction'])
                table.append([
                    order['symbol'],
                    order['direction'].capitalize(),
                    order['order_size'],
                    order['entry_price'],
                    current_price,
                    order['stop_loss_price'],
                    order['take_profit_price'],
                    f"{profit_percentage:.2f}%"
                ])
            except Exception as e:
                self.logger.error(f"Failed to fetch price for {order['symbol']}: {e}")

        if table:
            self.logger.info("\n" + tabulate(table, headers, tablefmt="grid"))

    def calculate_profit_percentage(self, entry_price, current_price, direction):
        if direction == 'buy':
            profit_percentage = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_percentage = ((entry_price - current_price) / entry_price) * 100
        return profit_percentage

    def close_order(self, order, current_price):
        direction = 'sell' if order['direction'] == 'buy' else 'buy'

        try:
            for attempt in range(3):
                try:
                    self.kucoin.create_order(
                        symbol=order['symbol'],
                        type='market',
                        side=direction,
                        amount=order['order_size'],
                        params={'reduceOnly': True}
                    )
                    self.logger.info(f"Closed {order['direction']} order for {order['order_size']} {order['symbol']} at price {current_price}")
                    self.log_trade(order, current_price)
                    self.open_orders.remove(order)
                    break
                except Exception as e:
                    self.logger.error(f"Attempt {attempt + 1}: Failed to close order for {order['symbol']}: {e}")
                    time.sleep(5)
                    continue
        except Exception as e:
            self.logger.error(f"Failed to process closing order for {order['symbol']}: {e}")

    def log_trade(self, order, exit_price):
        with open(self.log_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                order['symbol'],
                order['direction'],
                order['order_size'],
                order['entry_price'],
                exit_price,
                order['stop_loss_price'],
                order['take_profit_price']
            ])
        self.logger.info(f"Trade logged for {order['symbol']}.")