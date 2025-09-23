
import math
import time
from binance.client import Client
import csv, os
from analysis_simulation import depreciate, appreciate
import  config as cfg



client = None
def connect_to_binance():
    ''' Connect to the Binance API using the provided API key and secret '''
    try:
        client = Client(cfg.API_KEY, cfg.API_SECRET)
        # Test connectivity
        client.ping()
        print("Successfully connected to the Binance API!")
        return client
    except Exception as e:
        print(f"Error connecting to Binance API: {e}")
        return None


# Function to get current price of a symbol
get_current_price = lambda symbol: client.get_symbol_ticker(symbol=symbol) if client else None




def buy(symbol, quantity):
    ''' Place a market buy order for the given symbol and quantity '''
    try:
        order = client.order_market_buy(
            symbol=symbol,
            quantity=quantity)
        print(f"Buy order placed: {order}")
        return order
    except Exception as e:
        print(f"Error placing buy order: {e}")
        return None
    
def sell(symbol, quantity):
    ''' Place a market sell order for the given symbol and quantity '''
    try:
        order = client.order_market_sell(
            symbol=symbol,
            quantity=quantity)
        print(f"Sell order placed: {order}") 
        return order
    except Exception as e:
        print(f"Error placing sell order: {e}")
        return None

def save_params_to_csv(params, filename='data.csv'):  
    ''' Save parameters to a CSV file '''
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(params.keys())  # write header if file doesn't exist
        writer.writerow(params.values()) 

def read_params_from_csv(filename='data.csv'):
    ''' Read parameters from a CSV file '''
    if not os.path.isfile(filename):
        print(f"File {filename} does not exist.")
        return None
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        params = list(reader)
        if params:
            return params[-1]  # return the last row as a dictionary
        else:
            print(f"No data found in {filename}.")
            return None

def get_quantity_to_trade(symbol=cfg.SYMBOL, amortized_investment=cfg.A):
    # --- Step 1: Get Exchange Information ---
    # This is crucial for getting the trading rules for the symbol
    info = client.get_symbol_info(symbol)

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
    ticker = client.get_ticker(symbol=symbol)
    current_price = float(ticker['lastPrice'])

    # --- Step 4: Calculate the Quantity ---
    # Calculate the raw quantity based on your capital and current price
    raw_quantity = amortized_investment / current_price

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



def TradeBot():
    ''' 
        A bot that trades btcusdt based on market analysis 
        Uses the analysis.py functions to decide when to buy/sell
        Buys when the price is depreciating and sells when appreciating
        Keeps track of current investment and fixed capital
        Uses a simple strategy of buying/selling a fixed amount each time
        Prints the current investment and fixed capital after each trade
        Stops trading when fixed capital is less than the fixed amount to invest
        or when current investment is less than the fixed amount to recover
     '''
    

    # Read initial parameters from data.csv
    params = read_params_from_csv('data.csv')
    current_price=get_current_price(cfg.SYMBOL)
    if(params is None and current_price is not None):
        params = {
            'amortized_investment': cfg.A,  # Amount to invest/recover each time
            'rate': cfg.R,  # Rate of appreciation/depreciation
            'current_investment': cfg.CI,  # Current investment
            'fixed_capital': cfg.FIXED_CAPITAL,  # Fixed capital available
            'symbol': current_price['symbol'],
            'last_trade_price': current_price['price'],
            'quantity_to_trade': 0.0,
            'Actual_order_value': 0.0
        }
        save_params_to_csv(params)
    # else:
    #     print("No initial parameters and cannot get current price")
    #     return # exit if no initial params and cannot get current price

    

    while(True):
        if client is None:
            #connect to binance
            client = connect_to_binance()
            btc_usdt_price=get_current_price(cfg.SYMBOL)
            print(btc_usdt_price) # Expected output: {'symbol': 'BTCUSDT', 'price': '65000.00000000'}
            continue

        try:
            current_price=get_current_price(cfg.SYMBOL)
            if(current_price is None):
                print("Error getting current price")
                time.sleep(10)
                continue
            print("Current Price:", current_price)
            last_price=float(params['last_trade_price'])
            c_p = float(current_price['price'])
            print(f"Last Trade Price: {last_price}, Current Price: {c_p}")
            if(c_p<last_price): # price is depreciating
                #compute depreciation rate in percentage
                rate=round(((last_price-c_p))/last_price*100, 3)
                print(f"Depreciation Rate: {rate}%")
                print(f"Rate to trade {cfg.R}")

                if(rate >= cfg.R): # only trade if rate is greater than configured rate
                    print(f"Price depreciated from {last_price} to {c_p} by {rate}%")
                    # Depreciate current investment and invest amortized amount
                    (new_investment, new_fixed_capital) = depreciate(stop=1, rate=rate, A=int(params['amortized_investment']), CI=float(params['current_investment']), fixed_capital=float(params['fixed_capital']))
                    if(new_fixed_capital < int(params['amortized_investment'])):
                        print("Not enough fixed capital to invest. Stopping trading.")
                        continue

                    # Place buy order
                    (quantity_to_trade, order_value) = get_quantity_to_trade()
                    buy(cfg.SYMBOL, quantity_to_trade)  # Round quantity to 6 decimal places

                    # Update parameters
                    params['current_investment'] = new_investment
                    params['fixed_capital'] = new_fixed_capital
                    params['last_trade_price'] = c_p
                    params['quantity_to_trade'] = float(quantity_to_trade),
                    params['Actual_order_value'] = order_value
                    save_params_to_csv(params)

                    print("Quantity to trade:", quantity_to_trade)


            else: # price is appreciating
                #compute appreciation rate in percentage
                rate=round(((c_p-last_price))/last_price*100, 3)
                print(f"Appreciation Rate: {rate}%")
                print(f"Rate to trade {cfg.R}")
                if(rate >= cfg.R): # only trade if rate is greater than configured rate
                    print(f"Price appreciated from {last_price} to {c_p} by {rate}%")
                    # Appreciate current investment and recover amortized amount
                    (new_investment, new_fixed_capital) = appreciate(stop=1, rate=rate, A=int(params['amortized_investment']), CI=float(params['current_investment']), fixed_capital=float(params['fixed_capital']))
                    if(new_investment < int(params['amortized_investment'])):
                        print("Not enough current investment to recover. Stopping trading.")
                        continue

                    # Place sell order
                    (quantity_to_trade, order_value) = get_quantity_to_trade()
                    sell(cfg.SYMBOL, quantity_to_trade)  # Round quantity to 6 decimal places

                    # Update parameters
                    params['current_investment'] = new_investment
                    params['fixed_capital'] = new_fixed_capital
                    params['last_trade_price'] = c_p
                    params['quantity_to_trade'] = float(quantity_to_trade),
                    params['Actual_order_value'] = order_value

                    print("Quantity to trade:", quantity_to_trade)

            time.sleep(cfg.SLEEP_TIME) # wait for 1 minute before next check    
        except:
            continue    


if __name__ == "__main__":
    TradeBot()  
