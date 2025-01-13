import pandas as pd
from datetime import datetime
import logging

class DataFetcher:
    def __init__(self, kucoin, interval):
        self.kucoin = kucoin
        self.interval = interval
        self.logger = logging.getLogger(__name__)

    def fetch_data(self, symbol):
        self.logger.info(f"Fetching extended historical data for {symbol} from KuCoin...")
        try:
            symbol_kucoin = symbol.replace("-", "/").replace("USD", "USDT:USDT")
            max_days_supported = 30
            since_time = (datetime.utcnow() - pd.Timedelta(days=max_days_supported)).timestamp() * 1000
            now_time = datetime.utcnow().timestamp() * 1000
            all_data = []

            while since_time < now_time:
                try:
                    self.logger.info(f"Requesting data for {symbol_kucoin} starting from {since_time}...")
                    ohlcv = self.kucoin.fetch_ohlcv(symbol_kucoin, timeframe=self.interval, since=int(since_time))
                    if not ohlcv:
                        self.logger.warning(f"No data returned for {symbol_kucoin}. Stopping fetch.")
                        break
                    all_data.extend(ohlcv)
                    last_timestamp = ohlcv[-1][0]
                    if last_timestamp <= since_time:
                        self.logger.warning(f"Stale data detected for {symbol}. Ending data fetch loop.")
                        break
                    since_time = last_timestamp + 1
                except Exception as e:
                    self.logger.error(f"Error in fetching OHLCV data for {symbol_kucoin}: {e}")
                    break

            if all_data:
                data = pd.DataFrame(all_data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                data['Timestamp'] = pd.to_datetime(data['Timestamp'], unit='ms')
                data.set_index('Timestamp', inplace=True)
                self.logger.info(f"Final dataset contains {len(data)} rows for {symbol}.")
                return data
            else:
                self.logger.warning(f"No data fetched for {symbol}. Returning None.")
                return None
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None