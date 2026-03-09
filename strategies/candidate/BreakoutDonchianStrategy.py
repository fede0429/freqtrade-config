from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class BreakoutDonchianStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '15m'
    can_short = False
    startup_candle_count = 80

    minimal_roi = {"0": 0.035, "90": 0.015, "240": 0.0}
    stoploss = -0.09
    trailing_stop = True
    trailing_stop_positive = 0.012
    trailing_stop_positive_offset = 0.022
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    use_exit_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['donchian_high'] = dataframe['high'].rolling(55).max()
        dataframe['donchian_low'] = dataframe['low'].rolling(20).min()
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['donchian_high'].shift(1)) &
                (dataframe['atr_pct'] > 0.006) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['donchian_low'].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'
        ] = 1
        return dataframe
