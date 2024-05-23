import os

import bitmex
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.constants import (BUY_EXTRA_MARGIN, ORDER_QUANTITY, PROFIT_MARGIN,
                             STABILITY, SYMBOL, TIMEOUT)
from utils.database_orm import Base
from utils.trading_algorithm import TradingAlgorthm

BITMEX_CLIENT = bitmex.bitmex(
    api_key=os.getenv("BITMEX_API_KEY"),
    api_secret=os.getenv("BITMEX_API_SECRET"),
    test=False,
)

if __name__ == "__main__":

    # create database if its not there yet
    engine = create_engine("sqlite:///app/trades.db")
    Base.metadata.create_all(engine)

    # database session
    Session = sessionmaker(bind=engine)
    session = Session()

    TradingAlgorthm(
        client=BITMEX_CLIENT,
        symbol=SYMBOL,
        stability=STABILITY,
        profit_margin=PROFIT_MARGIN,
        buy_extra_margin=BUY_EXTRA_MARGIN,
        order_size=ORDER_QUANTITY,
        timeout=TIMEOUT,
        session=session,
    ).run()
