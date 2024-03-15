from func_utils import format_number
from datetime import datetime, timedelta
import time
from pprint import pprint

import pytz
 
from dateutil import tz

#Get existing open positions
def is_open_positions(client, market):

    time.sleep(0.2)

    all_positions = client.private.get_positions(
        market = market,
        status = "OPEN"
    )

    # Determine if open
    if len(all_positions.data["positions"]) > 0:
        return True
    else:
        return False

# Check order status
def check_order_status(client, order_id):
    order = client.private.get_order_by_id(order_id)
    if order.data:
        if "order" in order.data.keys():
            return order.data["order"]["status"]
    return "FAILED"

def set_expiration_time(client, timezone='UTC', delta_seconds=70):
    server_time_res = client.public.get_time()
    server_time = server_time_res.data
 
    # Convert server time to datetime object without timezone information
    naive_datetime = datetime.fromisoformat(server_time['iso'].replace('Z', ''))
 
    # Assign UTC to the naive datetime and then convert to the desired timezone
    utc_datetime = naive_datetime.replace(tzinfo=tz.tzutc())
    target_timezone = tz.gettz(timezone)
    local_datetime = utc_datetime.astimezone(target_timezone)
 
    # Calculate expiration time in the target timezone
    expiration_time = local_datetime + timedelta(seconds=delta_seconds)
 
    return expiration_time



# Place market order
def place_market_order(client, market, side, size, price, reduce_only):
    #Get Position ID

    account_response = client.private.get_account()
    position_id = account_response.data['account']['positionId']

    #Get expiration time
    server_time = client.public.get_time()
    expiration = set_expiration_time(client, timezone='UTC+05:00', delta_seconds=70)
    #expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', "")) + timedelta(seconds = 120)

    placed_order = client.private.create_order(
        position_id=position_id, # required for creating the order signature
        market= market,
        side=side,
        order_type="MARKET",
        post_only=False,
        size=size,
        price= price,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force="FOK",
        reduce_only = reduce_only
    )

    #Return results
    return placed_order.data




# Abort all postions

def abort_all_positions(client):
    
    # Cancell all orders
    client.private.cancel_all_orders()

    #Protect API
    time.sleep(0.5)

    #Get markets for reference of tick size
    markets = client.public.get_markets().data

    pprint(markets)

    #Protect API
    time.sleep(0.5)

    #Get all open positions 
    positions = client.private.get_positions(status="OPEN")
    all_positions = positions.data["positions"]

    # Handle open positions
    close_orders = []
    if len(all_positions) > 0:
        
        for position in all_positions:

            market = position['market']

            #Determine side
            side = "BUY"
            if position["side"] == "LONG":
                side = "SELL"
            
            price = float(position["entryPrice"])
            accept_price = price*1.7 if side == "BUY" else price*0.3
            tick_size = markets["markets"][market]["tickSize"]
            accept_price = format_number(accept_price, tick_size)
       

            #Place Order to close
            order = place_market_order(
                client,
                market,
                side,
                position["sumOpen"],
                accept_price,
                True,   
            )

            #Append the result
            close_orders.append(order)

            time.sleep(0.2)

        return close_orders

