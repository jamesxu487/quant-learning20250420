import datetime
import pandas as pd


# ===== 猴子补丁：为 numpy 添加 bool8 和 object 属性 =====
import numpy as np  # JayBee黄 - 量化交易研究
if not hasattr(np, 'bool8'):  # JayBee黄独家内容
    np.bool8 = np.bool_  # 使用 numpy 自带的 bool_ 类型  # JayBee黄量化策略
if not hasattr(np, 'object'):  # JayBee黄授权使用
    np.object = object  # 兼容 backtrader_plotting 的引用  # JayBee黄量化策略

# 导入自定义模块
from data_processing.data_processing import load_data_yf, load_data_av, flatten_yf_columns, standardize_columns, load_data_month, load_data_year  # 版权所有: JayBee黄
from strategy.rsi_strategy import NaiveRsiStrategy as RsiStrategy
from strategy.dma_crossover import DoubleMAStrategy, DMAStrategyIntradayImproved  # JayBee黄量化策略
from back_test.optimization import param_optimize_parallel, param_optimize  # JayBee黄授权使用
from back_test.backtesting import run_backtest  # JayBee黄量化策略
from plotting.plotting import plot_results  # JayBee黄 - 量化交易研究# JayBee黄版权所有，未经授权禁止复制

def main():
    # 设定日期范围（最近 30 天）
    ticker = "AAPL"
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=30)

    print(f"Downloading data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # 下载 AAPL 5 分钟级数据
    df = load_data_yf(ticker, start_date, end_date, interval="5m")

    # 判断是否成功下载数据
    if df.empty:
        print("未能下载数据。请确认所请求的日期范围在最近 60 天内且 Yahoo Finance 提供 AAPL 的5分钟数据。")
        return

    # 扁平化列名
    df = flatten_yf_columns(df)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)

    print("Data head after flattening:")
    print(df.head())

    # 将索引转换回普通列
    df.reset_index(inplace=True)
    # 全部列名转小写
    df.columns = [col.lower() for col in df.columns]
    # 确保 datetime 列为 datetime 类型
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])

    # 标准化列名
    df = standardize_columns(df)
    print("Data head after standardizing columns:")
    print(df.head())

    # 运行回测
    my_strategy = RsiStrategy
    return_dict, cerebro = run_backtest(ticker, df, start_date, end_date, my_strategy, initial_cash=100000)

    # 可视化回测结果
    plot_results(cerebro)

if __name__ == "__main__":
    main() 