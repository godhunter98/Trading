from kiteconnect import KiteConnect
import datetime
import time

# Kite Connect API credentials
api_key = "your_api_key"
api_secret = "your_api_secret"
access_token = "your_access_token"

# Initialize Kite Connect API
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

# Define the stock symbol for NIFTY futures
nifty_futures_symbol = "NIFTY23JUNFUT"  # Example symbol for NIFTY futures (update based on the current contract)

# Function to place an order and return the entry price
def place_order(transaction_type, symbol, quantity):
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NFO,
            tradingsymbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_MARKET,
            validity=kite.VALIDITY_DAY
        )
        print(f"Order placed successfully. Order ID: {order_id}")
        # Fetch the order details to get the average price
        order = kite.orders()[-1]
        entry_price = order['average_price']
        return entry_price
    except Exception as e:
        print(f"Order placement failed: {e}")
        return None

# Function to get the trading symbol for the options
def get_option_trading_symbol(stock_symbol, expiry_date, strike_price, option_type):
    return f"{stock_symbol}{expiry_date}{strike_price}{option_type}"

# Function to get the NIFTY futures price
def get_nifty_futures_price():
    try:
        quote = kite.ltp(f"NSE:{nifty_futures_symbol}")
        return quote[f"NSE:{nifty_futures_symbol}"]["last_price"]
    except Exception as e:
        print(f"Failed to fetch NIFTY futures price: {e}")
        return None

# Function to get the nearest expiry date (Thursday) for the current week
def get_nearest_expiry_date():
    today = datetime.date.today()
    days_ahead = 3 - today.weekday()  # 3 corresponds to Thursday (0=Monday, 1=Tuesday, ..., 6=Sunday)
    if days_ahead < 0:
        days_ahead += 7
    expiry_date = today + datetime.timedelta(days=days_ahead)
    return expiry_date.strftime("%y%b").upper()

# Function to place a market order to close a position
def place_market_order(transaction_type, symbol, quantity):
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NFO,
            tradingsymbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_MARKET,
            validity=kite.VALIDITY_DAY
        )
        print(f"Market order placed successfully to close position. Order ID: {order_id}")
    except Exception as e:
        print(f"Market order placement failed: {e}")

# Main function to execute the 9:20 AM short straddle with stop-loss
def execute_short_straddle():
    # Wait until 9:20 AM
    target_time = datetime.datetime.now().replace(hour=9, minute=20, second=0, microsecond=0)
    while datetime.datetime.now() < target_time:
        time.sleep(1)

    # Get the NIFTY futures price
    nifty_futures_price = get_nifty_futures_price()
    if nifty_futures_price is None:
        print("Unable to get NIFTY futures price. Exiting.")
        return

    # Calculate the closest strike price (nearest 50 points)
    closest_strike_price = round(nifty_futures_price / 50) * 50

    # Get the nearest expiry date
    expiry_date = get_nearest_expiry_date()

    # Define the options symbols
    call_option_symbol = get_option_trading_symbol("NIFTY", expiry_date, closest_strike_price, "CE")
    put_option_symbol = get_option_trading_symbol("NIFTY", expiry_date, closest_strike_price, "PE")

    # Define the quantity for the options
    quantity = 50  # Example quantity (should be in multiples of the lot size)

    # Place the sell orders and get the entry prices
    call_entry_price = place_order(kite.TRANSACTION_TYPE_SELL, call_option_symbol, quantity)
    put_entry_price = place_order(kite.TRANSACTION_TYPE_SELL, put_option_symbol, quantity)

    if call_entry_price is None or put_entry_price is None:
        print("Unable to place initial orders. Exiting.")
        return

    # Calculate the stop-loss prices (10% above the entry prices)
    call_stop_loss_price = call_entry_price * 1.10
    put_stop_loss_price = put_entry_price * 1.10

    # Monitor prices and place stop-loss orders if necessary
    while True:
        try:
            # Fetch the latest prices
            call_option_price = kite.ltp(f"NFO:{call_option_symbol}")[f"NFO:{call_option_symbol}"]["last_price"]
            put_option_price = kite.ltp(f"NFO:{put_option_symbol}")[f"NFO:{put_option_symbol}"]["last_price"]

            # Check if the stop-loss conditions are met
            if call_option_price >= call_stop_loss_price:
                place_market_order(kite.TRANSACTION_TYPE_BUY, call_option_symbol, quantity)
                print(f"Call option hit stop-loss at {call_option_price}.")
                break

            if put_option_price >= put_stop_loss_price:
                place_market_order(kite.TRANSACTION_TYPE_BUY, put_option_symbol, quantity)
                print(f"Put option hit stop-loss at {put_option_price}.")
                break

            # Sleep for a short interval before checking again
            time.sleep(5)

        except Exception as e:
            print(f"Error in monitoring prices: {e}")
            time.sleep(5)  # Sleep for a while before retrying

if __name__ == "__main__":
    execute_short_straddle()
