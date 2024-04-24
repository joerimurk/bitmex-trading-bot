import hashlib
import hmac
import json
import time
import urllib
import os

from websocket import create_connection

from src.trading_engine.utils.constants import BITMEX_URL, VERB, ENDPOINT

def limit_order(client, symbol, order_quantity, price):
    """Bitmex place limit order"""
    _ = client.Order.Order_new(
        symbol=symbol, ordType="Limit", orderQty=order_quantity, price=price
    ).result()

def get_open_orders(client, symbol):
    """Bitmex get all open orders"""
    return client.Order.Order_getOrders(
        symbol=symbol, filter='{"open": true}'
    ).result()[0]

def cancel_open_orders(client):
    """Bitmex close all open orders"""
    _ = client.Order.Order_cancelAll().result()

def get_open_positions(client, symbol):
    """Bitmex get all open orders"""
    return client.Position.Position_get().result()[0]

def websocket_open_orders(timeout=None):
    """Bitmex websocket for changes in open orders"""
    expires = int(time.time()) + 5
    signature = bitmex_signature(os.getenv("BITMEX_API_SECRET"), VERB, ENDPOINT, expires)

    # Initial connection - BitMEX sends a welcome message.
    ws = create_connection(BITMEX_URL + ENDPOINT, timeout=10)
    result = ws.recv()

    # Send API Key with signed message.
    request = {"op": "authKeyExpires", "args": [os.getenv("BITMEX_API_KEY"), expires, signature]}
    ws.send(json.dumps(request))
    result = ws.recv()

    # Send a request that requires authorization.
    request = {"op": "subscribe", "args": "order"}
    ws.send(json.dumps(request))
    result = ws.recv()

    # CHECK IF ONLY A SINGLE ORDER OPEN
    result = ws.recv()
    # data = json.loads(result)["data"]
    # print(f"Only one order open: {len(data)==1}")
    # print(f"Open order: {data[0]}")

    # Wait for socket to respond
    try:
        result = ws.recv()
        bought_successfully = True
    except:
        bought_successfully = False
        print("5 minutes past, close order")


    ws.close()

    return bought_successfully

def bitmex_signature(apiSecret, verb, url, nonce, postdict=None):
    """Given an API Secret key and data, create a BitMEX-compatible signature."""
    data = ''
    if postdict:
        # separators remove spaces from json
        # BitMEX expects signatures from JSON built without spaces
        data = json.dumps(postdict, separators=(',', ':'))
    parsedURL = urllib.parse.urlparse(url)
    path = parsedURL.path
    if parsedURL.query:
        path = path + '?' + parsedURL.query
    # print("Computing HMAC: %s" % verb + path + str(nonce) + data)
    message = (verb + path + str(nonce) + data).encode('utf-8')
    # print("Signing: %s" % str(message))

    signature = hmac.new(apiSecret.encode('utf-8'), message, digestmod=hashlib.sha256).hexdigest()
    # print("Signature: %s" % signature)
    return signature
