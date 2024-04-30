import time

import numpy as np
import websocket
from loguru import logger
import json


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


def get_open_positions(client):
    """Bitmex get all open orders"""
    return client.Position.Position_get().result()[0]


def calculate_order_price(price, margin, positive):
    """Calculate price based on positive or negative margin"""
    if positive:
        return np.round(price + (margin * price), 1)
    else:
        return np.round(price - (margin * price), 1)


class WebsocketPrice:
    def __init__(
        self,
        client,
        symbol: str = "ETHUSD",
        buy_price: float = None,
        sell_price: float = None,
        timeout: float = None,
    ):
        """Websocket for current price"""

        self.client = client
        self.symbol = symbol
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.timeout = timeout

        if not self.buy_price:
            self.buy_price = -np.inf
        if not self.sell_price:
            self.sell_price = np.inf
        if not self.timeout:
            self.timeout = np.inf

        self.buy_price_reached = False
        self.sell_price_reached = False
        self.timeout_reached = False

        self.start_time = time.time()

    def on_message(self, ws, message):
        """Function called everytime the price changes"""
        current_price = self.get_price(message)
        if current_price:
            if current_price <= self.buy_price:
                self.buy_price_reached = True
                ws.close()
            elif current_price >= self.sell_price:
                self.sell_price_reached = True
                ws.close()

        if (time.time() - self.start_time) > self.timeout:
            self.timeout_reached = True
            ws.close()

    def on_error(self, ws, error):
        """Function called after an error"""
        logger.error(error)

    def on_close(self, ws, a, b):
        """Function called when closing websocket"""
        logger.info("### closed ###")

    @staticmethod
    def get_price(message):
        """Get price from websocket output"""
        # load message from websocket
        message = json.loads(message)

        # find price in message
        if "data" in message.keys():
            if "lastPrice" in message["data"][0].keys():
                return message["data"][0]["lastPrice"]
        return None

    def start_websocket(self):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            f"wss://ws.bitmex.com/realtime?subscribe=instrument:{self.symbol}",
            on_message=self.on_message,
            on_close=self.on_close,
            on_error=self.on_error,
        )
        ws.run_forever()

        return self.buy_price_reached, self.sell_price_reached, self.timeout_reached
