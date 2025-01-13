class SimulationEngine:
    """
       Mock simulation engine for testing price movements and API responses.
       """

    def __init__(self):
        self.current_price = 2000  # Initial mock price
        self.price_movement = [2000, 2025, 2050, 2100, 2175, 2150, 2080, 2030, 2000, 1950]  # Mock price movements
        self.index = 0

    def fetch_ohlcv(self, symbol, timeframe, since=None):
        """
        Mock fetching OHLCV data with advancing timestamps.
        """
        if since is None:
            since = 1658438400000  # Default start timestamp if not provided

        # Produce candles with advancing timestamps
        mock_data = [
            [since + (i * 60 * 1000), 2000 + i, 2005 + i, 1995 + i, 2000 + i, 1000]
            for i in range(10)
        ]  # Generate 10 candles, each 1 minute apart
        return mock_data

    def fetch_ticker(self, symbol):
        """
           Mock fetching ticker data.
           """
        mock_price = self.price_movement[self.index % len(self.price_movement)]
        self.index += 1
        return {'last': mock_price}

    def create_order(self, **kwargs):
        """
           Mock order creation.
           """
        mock_order = kwargs
        mock_order['status'] = 'open'
        return mock_order
