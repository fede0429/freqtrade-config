from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class MeanReversionBBStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '15m'
    can_short = False
    startup_candle_count = 100

    minimal_roi = {"0": 0.02, "45": 0.01, "120": 0.0}
    stoploss = -0.06
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bb = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_lower'] = bb['lowerband']
        dataframe['bb_middle'] = bb['middleband']
        dataframe['bb_upper'] = bb['upperband']
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['bb_lower']) &
                (dataframe['rsi'] < 33) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                ((dataframe['close'] > dataframe['bb_middle']) | (dataframe['rsi'] > 58)) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'
        ] = 1
        return dataframe
