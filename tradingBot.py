import math
import time
import csv
import os
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceAPIException, BinanceAPIException
from dotenv import load_dotenv

# --- Load Environment Variables for Security ---
load_dotenv()

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TradingBot:
    def __init__(self, symbol, amortized_investment, rate, fixed_capital, csv_file='data.csv', sleep_time=60, current_investment=0.0):
        """
        Initializes the trading bot with configuration parameters.
        Args:
            symbol (str): Trading pair symbol (e.g., "BTCUSDT").
            amortized_investment (float): Amount to invest/recover each time in USDT.
            rate (float): Rate of appreciation/depreciation in percentage.
            fixed_capital (float): Fixed capital available in USDT.
            csv_file (str): Path to the CSV file for saving/loading state.
            sleep_time (int): Time to wait between price checks in seconds.
            current_investment (float): Current investment in BTC or USDT equivalent.
        """
        # Configuration
        self.symbol = symbol
        self.amortized_investment = float(amortized_investment)
        self.rate = float(rate)
        self.fixed_capital = float(fixed_capital)
        self.csv_file = csv_file
        self.sleep_time = int(sleep_time)

        # State Variables
        self.last_trade_price = None
        self.current_investment = current_investment
        self.client = self._connect_to_binance()

        # Initialize from file or set defaults
        self._load_state()

    def _connect_to_binance(self):
        """Connect to the Binance API and return a client instance."""
        try:
            api_key = os.getenv("BINANCE_API_KEY")
            api_secret = os.getenv("BINANCE_API_SECRET")
            if not api_key or not api_secret:
                logging.error("API keys are not set in environment variables.")
                return None

            client = Client(api_key, api_secret)
            client.ping()
            logging.info("Successfully connected to the Binance API!")
            return client
        except BinanceAPIException as e:
            logging.error(f"Binance API connection error: {e}")
            return None
        except Exception as e:
            logging.error(f"General connection error: {e}")
            return None

    def _get_market_data(self):
        """Get the latest price and symbol information, with robust error handling."""
        try:
            info = self.client.get_symbol_info(self.symbol)
            ticker = self.client.get_ticker(symbol=self.symbol)
            return info, float(ticker['lastPrice'])
        except BinanceAPIException as e:
            if e.code == -1003:
                logging.warning("Rate limit exceeded. Waiting for 5 minutes.")
                time.sleep(300)
            else:
                logging.error(f"API Error getting market data: {e}. Skipping trade cycle.")
            return None, None
        except Exception as e:
            logging.error(f"General error getting market data: {e}. Skipping trade cycle.")
            return None, None

    def _get_quantity_to_trade(self, info, current_price, investment_amount):
         # --- Step 1: Get Exchange Information ---
        # This is crucial for getting the trading rules for the symbol
        info = self.client.get_symbol_info(self.symbol)

        # --- Step 2: Get Trading Filters ---
        # Find the filters that determine min/max quantities and price
        step_size = 0.0
        min_notional = 0.0

        for f in info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = float(f['stepSize'])
            elif f['filterType'] == 'MIN_NOTIONAL':
                min_notional = float(f['minNotional'])

        if step_size == 0.0:
            print("Could not retrieve step size.")
            exit()

        # --- Step 3: Get Current Price ---
        ticker = self.client.get_ticker(symbol=self.symbol)
        current_price = float(ticker['lastPrice'])

        # --- Step 4: Calculate the Quantity ---
        # Calculate the raw quantity based on your capital and current price
        raw_quantity = self.amortized_investment / current_price

        # --- Step 5: Round Down to the Correct Lot Size ---
        # This is the most critical part. We use the step_size to round down
        # to the nearest valid quantity.
        # We use a math trick to handle floating point precision issues.
        quantity_to_buy = math.floor(raw_quantity / step_size) * step_size

        # --- Final Check ---
        # Make sure the calculated quantity is greater than the MIN_NOTIONAL
        order_value = quantity_to_buy * current_price
        if order_value < min_notional:
            print(f"Calculated order value {order_value} is less than the minimum notional {min_notional}.")
            print("Cannot place order with this small amount of capital.")
            quantity_to_buy = 0.0
        else:
            print(f"Current price: {current_price}")
            print(f"Step size: {step_size}")
            print(f"Raw quantity: {raw_quantity}")
            print(f"Final quantity to buy: {quantity_to_buy}")
            print(f"Total order value: {order_value}")

        return quantity_to_buy, order_value

    def _get_valid_price(self, info, price):
        """Rounds the price to the nearest tick size for a valid limit order."""
        try:
            tick_size = float(next(f['tickSize'] for f in info['filters'] if f['filterType'] == 'PRICE_FILTER'))
            return math.floor(price / tick_size) * tick_size
        except (StopIteration, KeyError) as e:
            logging.error(f"Could not retrieve PRICE_FILTER: {e}")
            return price

    def _place_order(self, order_type, quantity, price):
        """Places a limit buy or sell order."""
        try:
            if order_type == "buy":
                order = self.client.order_limit_buy(symbol=self.symbol, quantity=quantity, price=f"{price:.6f}")
            elif order_type == "sell":
                order = self.client.order_limit_sell(symbol=self.symbol, quantity=quantity, price=f"{price:.6f}")
            else:
                logging.error("Invalid order type.")
                return None
            
            logging.info(f"{order_type.capitalize()} order placed: {order}")
            return order
        except BinanceAPIException as e:
            logging.error(f"API Error placing order: {e}")
            return None
        except Exception as e:
            logging.error(f"General error placing order: {e}")
            return None
    
    def _save_state(self):
        """Saves bot's state to a CSV file."""
        if self.last_trade_price is None:
            logging.warning("No state to save.")
            return

        params = {
            'amortized_investment': self.amortized_investment,
            'rate': self.rate,
            'current_investment': self.current_investment,
            'fixed_capital': self.fixed_capital,
            'last_trade_price': self.last_trade_price
        }

        file_exists = os.path.isfile(self.csv_file)
        with open(self.csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=params.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(params)
        logging.info("Bot state saved.")

    def _load_state(self):
        """Loads bot's state from a CSV file."""
        if not os.path.isfile(self.csv_file):
            logging.info("No state file found. Initializing with default parameters.")
            return
        
        with open(self.csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            params = list(reader)
            if params:
                last_state = params[-1]
                self.last_trade_price = float(last_state['last_trade_price'])
                self.current_investment = float(last_state['current_investment'])
                self.fixed_capital = float(last_state['fixed_capital'])
                logging.info("Bot state loaded from CSV.")
            else:
                logging.info("State file is empty. Initializing with default parameters.")

    def run_bot(self):
        """Main loop for the trading bot."""
        while not self.client:
            self.client = self._connect_to_binance() # Retry connection
            logging.error("Failed to connect to Binance API. Retrying in 1 minute.")
            time.sleep(30)
    

        if self.last_trade_price is None:
            # Initial run, get a starting price
            info, current_price = self._get_market_data()
            if current_price:
                self.last_trade_price = current_price
                logging.info(f"Initialized with starting price: {self.last_trade_price}")
            else:
                logging.error("Could not get initial price. Exiting.")
                return
        
        while True:
            info, current_price = self._get_market_data()
            if not current_price:
                time.sleep(self.sleep_time)
                continue
            
            rate = round((abs(current_price - self.last_trade_price) / self.last_trade_price) * 100, 3)
            logging.info(f"Current Price: {current_price}, Last Trade Price: {self.last_trade_price}, Rate Change: {rate}%")
            if current_price < self.last_trade_price and rate >= self.rate:
                # Price is depreciating
                logging.info(f"Price depreciated by {rate}%. Considering buy order.")
                # Simplified logic to fit a single file example
                # In a real bot, you'd calculate new investment/capital here
                if self.fixed_capital >= self.amortized_investment:
                    quantity, order_value = self._get_quantity_to_trade(info, current_price, self.amortized_investment)
                    if quantity > 0:
                        limit_price = self._get_valid_price(info, current_price)
                        order = self._place_order("buy", quantity, limit_price)
                        if order:
                            self.last_trade_price = current_price # Update state after successful trade
                            self._save_state()
                else:
                    logging.warning("Not enough fixed capital to invest. Stopping trading.")
                    break
            
            elif current_price > self.last_trade_price and rate >= self.rate:
                # Price is appreciating
                logging.info(f"Price appreciated by {rate}%. Considering sell order.")
                # Simplified logic
                if self.current_investment >= self.amortized_investment:
                    quantity, order_value = self._get_quantity_to_trade(info, current_price, self.amortized_investment)
                    if quantity > 0:
                        limit_price = self._get_valid_price(info, current_price)
                        order = self._place_order("sell", quantity, limit_price)
                        if order:
                            self.last_trade_price = current_price # Update state after successful trade
                            self._save_state()
                else:
                    logging.warning("Not enough current investment to recover. Stopping trading.")
                    break

            time.sleep(self.sleep_time)

if __name__ == "__main__":
    # Ensure you have a .env file with your API keys
    # Example .env content:
    
    SYMBOL = os.getenv("SYMBOL") # Trading pair symbol
    AMORTIZED_INVESTMENT = os.getenv("AMORTIZED_INVESTMENT") # In USDT
    RATE = os.getenv("RATE") # Percentage
    FIXED_CAPITAL = os.getenv('FIXED_CAPITAL') # In USDT
    CURRENT_INVESTMENT = os.getenv('CURRENT_INVESTMENT') # In SYBOL UNITS  equivalent
    # print(SYMBOL, AMORTIZED_INVESTMENT, RATE, FIXED_CAPITAL, CURRENT_INVESTMENT)

    bot = TradingBot(
        symbol=SYMBOL,
        amortized_investment=AMORTIZED_INVESTMENT,
        rate=RATE,
        fixed_capital=FIXED_CAPITAL,
        sleep_time=60
    )
    bot.run_bot()