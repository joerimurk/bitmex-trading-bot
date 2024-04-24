import numpy as np


def price_stability(client, symbol, stability):
    """Calculate whether the price is stable enough to trade"""
    # Get close prices per minute
    trades = client.Trade.Trade_getBucketed(
        symbol=symbol, binSize="1m", reverse=True
    ).result()[0]

    close = [trade["open"] for trade in trades]
    # Calculate 10m moving average of closing prices
    ma_10 = moving_average(close, 10)
    # Calculate standard deviation for the 10m moving average of the last 10 minutes
    # Divide by the current moving average / stability measure to make it a function of the price
    # This is needed because the scale of the std changes with the price of BTC
    trade_std = np.std(np.array(ma_10)[:10]) / (ma_10[0] / stability)
    # Trade indication based on the std
    trade_ind = trade_std < 1
    # Calculate buy and sell price
    buy_price = np.round(ma_10[0] - 0.0005 * ma_10[0], 0)

    return trade_ind, buy_price, np.round(trade_std, 2)


def moving_average(data: list, timeframe: int):
    """Calculate moving average"""
    i = 0
    moving_averages = []

    while i < len(data) - timeframe + 1:
        this_window = data[i : i + timeframe]
        window_average = sum(this_window) / timeframe
        moving_averages.append(window_average)
        i += 1

    return moving_averages
