from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class TrendEMAStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '15m'
    can_short = False
    startup_candle_count = 200

    minimal_roi = {"0": 0.03, "60": 0.015, "180": 0.0}
    stoploss = -0.08
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    use_exit_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema50']) &
                (dataframe['ema50'] > dataframe['ema200']) &
                (dataframe['adx'] > 22) &
                (dataframe['rsi'] > 52) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                ((dataframe['close'] < dataframe['ema50']) | (dataframe['rsi'] < 45)) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'
        ] = 1
        return dataframe
