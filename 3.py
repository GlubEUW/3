import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

COMMODITIES = {"IBM": "IBM"}

STARTING_CASH = 10000
FEE = 0.001
COOLDOWN_DAYS = 30

def load_data(symbol: str, interval: str, period: str) -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.empty:
        raise RuntimeError(f"Yahoo Finance returned no data for {symbol}")
    df.columns = df.columns.get_level_values(0).str.lower()
    return df

def commodity_channel_index(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    roll = tp.rolling(period)
    mean_dev = roll.apply(lambda v: np.abs(v - v.mean()).mean(), raw=True)
    return (tp - roll.mean()) / (0.015 * mean_dev)

def sharpe(df, risk_free_rate: float = 0.041, periods_per_year = 252):
    returns = df['portfolio_value'].pct_change().dropna()
    returns -= risk_free_rate/periods_per_year
    standard_deviation = returns.std(ddof = 1)
    if(np.isnan(standard_deviation) or standard_deviation == 0):
        return 0.0

    sharpe_ratio = (returns.mean() / standard_deviation) * np.sqrt(periods_per_year)
    
    
    return sharpe_ratio
    
def sell(money, stocks, stock_price):
    money += stocks * stock_price
    money -= stocks * stock_price * FEE
    return money

def buy(money, stock_price, stop_loss_percent, take_profit_percent):
    stocks = math.floor(money / (stock_price * (1 + FEE)))
    money -= stocks * stock_price * (1 + FEE)
    current_stop_loss = stock_price * (1 - stop_loss_percent)
    current_take_profit = stock_price * (1 + take_profit_percent)
    return (money, stocks, current_stop_loss, current_take_profit)

def strategy(df, stop_loss_percent: float = 0.1, take_profit_percent: float = 0.1, cci_absolute: float = 100):
    isBought = False
    money = STARTING_CASH
    stocks = 0
    value = []
    cooldown = 0

    df['buying_days'] = False
    df['stop_loss_days'] = False
    df['take_profit_days'] = False

    df["cci"] = commodity_channel_index(df)

    for date, row in df.iterrows():
        current_cci = row['cci']
        stock_price = row['close']

        cooldown -= 1
        
        if(isBought):
            if(row['low'] <= current_stop_loss):
                money = sell(money, stocks, min(row['open'], current_stop_loss))
                stocks = 0
                isBought = False
                df.loc[date, 'stop_loss_days'] = True
            elif(row['high'] >= current_take_profit):
                money = sell(money, stocks, max(row['open'], current_take_profit))
                stocks = 0
                isBought = False
                df.loc[date, 'take_profit_days'] = True

        elif(current_cci < -cci_absolute and cooldown <= 0):
            (money, stocks, current_stop_loss, current_take_profit) = buy(money, stock_price, stop_loss_percent, take_profit_percent)
            isBought = True
            cooldown = COOLDOWN_DAYS
            df.loc[date, 'buying_days'] = True
            

        portfolio_value = money + stock_price * stocks
        value.append(portfolio_value)
    df['portfolio_value'] = value
    #print(df['profit'])

    return df, sharpe(df)
    

def plot_graphs(df, name):
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), dpi=400, sharex=True)


    ax1.plot(df.index, df['close'])

    buying_df = df[df['buying_days'] == True]
    take_profit_df = df[df['take_profit_days'] == True]
    stop_loss_df = df[df['stop_loss_days'] == True]
        
    ax1.plot(buying_df.index, buying_df['close'], 'go', label='Buying')
    ax1.plot(take_profit_df.index, take_profit_df['close'], 'ro', label='Take profit')
    ax1.plot(stop_loss_df.index, stop_loss_df['close'], 'rx', label='Stop Loss')

    ax1.legend()


    ax2.plot(df.index, df['portfolio_value'])


    ax3.plot(df.index, df['cci'])
    fig.tight_layout()
    fig.savefig(name)

def brute(df):
    best = -10
    best_i = 0
    best_j = 0
    best_u = 0
    for i in range(50, 200, 5):
        for j in range(1, 50, 5):
            for u in range(1, 50, 5):
                _, sharp = strategy(df.copy(), j/100, u/100, i)
                if(sharp > best):
                    best = sharp
                    best_i = i
                    best_j = j
                    best_u = u
    print(best)
    print(f"{best_i} {best_j} {best_u}")

if __name__ == "__main__":
    data = load_data(COMMODITIES["IBM"], "1d", "10y")
    df1, s = strategy(data.copy(),0.16, 0.26, 165)
    print("optimized strategy sharper: {s}")
    plot_graphs(df1, "Optimized")
    df2, s = strategy(data.copy())
    print("UNoptimized strategy sharper: {s}")
        
    plot_graphs(df2, "Not_optimized")

    # this has been run before but is commented out for speed as it takes a while
    # optimal numbers are 0.16 0.26 165
    #brute(df)


    