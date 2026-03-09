# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame
from functools import reduce
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IntParameter, IStrategy)
import talib.abstract as ta

class ExtremeReboundStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '15m'
    can_short = False

    # Default ROI and Stoploss
    minimal_roi = {"0": 0.03, "15": 0.01, "30": 0}
    stoploss = -0.05
    trailing_stop = False

    # Hyperopt parameters
    buy_rsi_threshold = IntParameter(10, 30, default=20, space='buy')
    buy_atr_multiplier = DecimalParameter(1.1, 3.0, default=1.5, space='buy')

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_sma'] = dataframe['atr'].rolling(window=20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(dataframe['rsi'] < self.buy_rsi_threshold.value)
        conditions.append(dataframe['atr'] > (dataframe['atr_sma'] * self.buy_atr_multiplier.value))
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit if RSI recovers above 50 or handled by ROI
        dataframe.loc[
            (dataframe['rsi'] > 50),
            'exit_long'] = 1
        return dataframe