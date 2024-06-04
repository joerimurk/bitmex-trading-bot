import os
import time
import uuid
from datetime import datetime

import numpy as np
from loguru import logger
from utils.bitmex_helpers import (WebsocketPrice, cancel_open_orders,
                                  get_balance, get_filled_price, limit_order)
from utils.database_orm import Balance, Orders
from utils.price_stability import price_stability

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class TradingAlgorthm:
    """
    Defines the trading algorithm which contains the following steps..
    """

    def __init__(
        self,
        client,
        symbol,
        stability,
        profit_margin,
        buy_extra_margin,
        order_size,
        timeout,
        session,
        telegram_bot,
    ):
        self.client = client
        self.symbol = symbol
        self.stability = stability
        self.profit_margin = profit_margin
        self.buy_extra_margin = buy_extra_margin
        self.order_size = order_size
        self.timeout = timeout
        self.session = session
        self.telegram_bot = telegram_bot

    def run(self):
        """
        Runs the trading algorithm
        """
        while True:
            # get price stability
            trade_ind, average_price, trade_std = price_stability(
                client=self.client,
                symbol=self.symbol,
                stability=self.stability,
            )

            # check if price stable enough
            if trade_ind:
                pre_balance = get_balance(self.client)
                logger.info(f"Start trading, volatility low enough: {trade_std}")

            # if not stable enough, wait a minute and start over
            else:
                logger.info(
                    f"Wait for trading, standard deviation too high: {trade_std}"
                )
                time.sleep(60)
                continue

            # set buy order and start order websocket
            bought_successfully, bought_price = self.set_first_buy_order(average_price)

            # if not bought successfully, start over
            if not bought_successfully:
                cancel_open_orders(self.client)
                logger.info(
                    "Buy order cancelled, 5 minutes have passed, start over again.."
                )
                continue

            # get buy price and set new buy and sell price
            sold_successfully, price, sell_order_id = self.set_buy_extra_and_sell_order(
                bought_price
            )

            # sold position, start trading again
            if sold_successfully:
                self.get_profit(pre_balance, sell_order_id)
                self.session.commit()
                continue
            else:
                # bought extra so new sell order
                sold_successfully, sell_order_id = self.set_sell_order(
                    bought_price, price
                )
                self.get_profit(pre_balance, sell_order_id)
                self.session.commit()
                continue

    def set_first_buy_order(self, average_price):
        """
        Set first buy order.

        Returns True if buy price is reached within the timeout time,
        otherwise False.
        """
        # calculate the buy price based on the average price
        buy_price = self.calculate_order_price(
            price=average_price, margin=(self.profit_margin / 2), positive=False
        )
        # place buy order
        order_id = limit_order(self.client, self.symbol, self.order_size, buy_price)
        logger.info(f"Buy order placed: {self.order_size} contract(s) at {buy_price}")

        # while loop for if connection drops with websocket
        while True:
            buy_price_reached, _, timeout_reached = WebsocketPrice(
                client=self.client,
                symbol=self.symbol,
                buy_price=buy_price,
                timeout=self.timeout,
            ).start_websocket()

            if buy_price_reached:
                # check if buy order filled
                bought_price = get_filled_price(self.client, order_id)

                order = Orders(
                    order_id=order_id,
                    quantity=self.order_size,
                    price=bought_price,
                    timestamp=datetime.now(),
                )
                self.telegram_bot.send_message(
                    TELEGRAM_CHAT_ID,
                    f"{self.order_size} contracts bought at {bought_price}",
                )
                self.session.add(order)

                logger.info(
                    f"Buy order filled, open position: {self.order_size} contract(s) at {bought_price}"
                )
                return True, bought_price

            elif timeout_reached:
                return False, None

    def set_buy_extra_and_sell_order(self, bought_price):
        """Set buy extra and sell order"""
        # Calculate buy extra and sell price
        buy_extra_price = self.calculate_order_price(
            price=bought_price, margin=self.buy_extra_margin, positive=False
        )
        sell_price = self.calculate_order_price(
            price=bought_price, margin=self.profit_margin, positive=True
        )

        # Place buy and sell order
        buy_order_id = limit_order(
            self.client, self.symbol, self.order_size, buy_extra_price
        )
        sell_order_id = limit_order(
            self.client, self.symbol, -self.order_size, sell_price
        )
        logger.info(
            f"Buy order placed: {self.order_size} contract(s) at {buy_extra_price}"
        )
        logger.info(
            f"Sell order placed: {-self.order_size} contract(s) at {sell_price}"
        )

        # while loop for if connection drops with websocket
        while True:
            buy_price_reached, sell_price_reached, _ = WebsocketPrice(
                client=self.client,
                symbol=self.symbol,
                buy_price=buy_extra_price,
                sell_price=sell_price,
            ).start_websocket()

            if sell_price_reached:
                cancel_open_orders(self.client)
                sell_price = get_filled_price(self.client, sell_order_id)
                order = Orders(
                    order_id=sell_order_id,
                    quantity=-self.order_size,
                    price=sell_price,
                    timestamp=datetime.now(),
                )
                self.telegram_bot.send_message(
                    TELEGRAM_CHAT_ID,
                    f"{self.order_size} contracts sold at {sell_price}",
                )
                self.session.add(order)

                return True, sell_price, sell_order_id

            elif buy_price_reached:
                cancel_open_orders(self.client)
                second_buy_price = get_filled_price(self.client, buy_order_id)
                order = Orders(
                    order_id=buy_order_id,
                    quantity=self.order_size,
                    price=second_buy_price,
                    timestamp=datetime.now(),
                )
                self.telegram_bot.send_message(
                    TELEGRAM_CHAT_ID,
                    f"{self.order_size} contracts bought at {second_buy_price}",
                )
                self.session.add(order)

                return False, second_buy_price, None

    def set_sell_order(self, first_buy_price, second_buy_price):
        """Set final sell order"""
        average_price = np.round((first_buy_price + second_buy_price) / 2, 2)

        logger.info(
            f"Buy order filled, open position: {self.order_size*2} contract(s) at {average_price}"
        )

        sell_price = self.calculate_order_price(
            price=average_price, margin=self.profit_margin, positive=True
        )
        order_id = limit_order(
            self.client, self.symbol, -2 * self.order_size, sell_price
        )
        logger.info(
            f"Sell order placed: {-2 * self.order_size} contract(s) at {sell_price}"
        )

        while True:
            _, sell_price_reached, _ = WebsocketPrice(
                client=self.client,
                symbol=self.symbol,
                sell_price=sell_price,
            ).start_websocket()

            if sell_price_reached:
                sell_price = get_filled_price(self.client, order_id)
                order = Orders(
                    order_id=order_id,
                    quantity=-2 * self.order_size,
                    price=sell_price,
                    timestamp=datetime.now(),
                )
                self.telegram_bot.send_message(
                    TELEGRAM_CHAT_ID,
                    f"{-2 * self.order_size} contracts sold at {sell_price}",
                )
                self.session.add(order)

                return sell_price, order_id

    def calculate_order_price(self, price, margin, positive):
        """Calculate price based on positive or negative margin"""
        if positive:
            return np.round(price + (margin * price), 1)
        else:
            return np.round(price - (margin * price), 1)

    def get_profit(self, pre_balance, sell_order_id):
        """Get profit"""
        # sleep to make sure balance is updated
        time.sleep(10)
        post_balance = get_balance(self.client)

        balance = Balance(
            id=str(uuid.uuid4()),
            balance_before=pre_balance,
            balance_after=post_balance,
            timestamp=datetime.now(),
            sell_order_id=sell_order_id,
        )
        self.session.add(balance)
        logger.success(
            f"Done trading, profit made: {post_balance-pre_balance} BTC (... euro)"
        )
