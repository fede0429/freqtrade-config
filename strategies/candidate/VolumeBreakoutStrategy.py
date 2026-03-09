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
import pandas_ta as pta

class VolumeBreakoutStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '15m'
    can_short = False

    # Default ROI and Stoploss
    minimal_roi = {"0": 0.05, "30": 0.02, "60": 0.01, "120": 0}
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # Hyperopt parameters
    buy_vol_multiplier = DecimalParameter(1.5, 5.0, default=3.0, space='buy')
    buy_lookback_period = IntParameter(20, 100, default=50, space='buy')

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Volume SMA
        dataframe['volume_sma'] = dataframe['volume'].rolling(window=20).mean()
        # High lookback
        dataframe['highest_high'] = dataframe['high'].rolling(window=self.buy_lookback_period.value).max().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(dataframe['close'] > dataframe['highest_high'])
        conditions.append(dataframe['volume'] > (dataframe['volume_sma'] * self.buy_vol_multiplier.value))
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        return dataframe