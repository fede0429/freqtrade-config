from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class HighRiskStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    stoploss = -0.05
    minimal_roi = {"0": 0.05}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["mfi"] = ta.MFI(dataframe, timeperiod=14)
        dataframe["bb_lower"] = ta.BBANDS(dataframe, timeperiod=20)["lowerband"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 30) & 
            (dataframe["mfi"] < 30) & 
            (dataframe["close"] < dataframe["bb_lower"]), 
            "enter_long"
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] > 70), "exit_long"] = 1
        return dataframe
