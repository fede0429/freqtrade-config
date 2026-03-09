from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce


class EnsembleLooseStrategy(IStrategy):
    """
    Ensemble 宽松版 — 提高交易频率，保持共振核心逻辑
    
    放宽条件：
    - UMACD 区间从极窄 (-0.032, -0.018) 放宽到 (-0.05, -0.01)
    - Volume 倍率从 4.997 放宽到 3.0
    - RSI 上限从 75 放宽到 80
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '15m'
    max_open_trades = 2
    can_short = False
    
    # 阶梯止盈
    minimal_roi = {
        "0": 0.15,      # 首目标 15%
        "60": 0.08,     # 1小时后 8%
        "180": 0.03,    # 3小时后 3%
        "400": 0
    }
    
    stoploss = -0.25
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_only_offset_is_reached = True
    
    # 放宽的买入参数
    buy_umacd_min = -0.05      # 原 -0.032
    buy_umacd_max = -0.01      # 原 -0.018
    buy_vol_multiplier = 3.0   # 原 4.997
    
    startup_candle_count = 200
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # UMACD
        ema12 = ta.EMA(dataframe, timeperiod=12)
        ema26 = ta.EMA(dataframe, timeperiod=26)
        dataframe['umacd'] = (ema12 / ema26) - 1
        dataframe['umacd_signal'] = ta.EMA(dataframe['umacd'], timeperiod=9)
        
        # Volume
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # Breakout
        dataframe['price_high'] = dataframe['high'].rolling(window=51).max()
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        时间窗口共振逻辑：
        UMACD信号后的3根K线内，如果出现Volume突破，视为有效共振
        """
        # 条件1: UMACD买入信号（标记信号出现的位置）
        dataframe['umacd_buy'] = (
            (dataframe['umacd'] > self.buy_umacd_min) &
            (dataframe['umacd'] < self.buy_umacd_max) &
            (dataframe['umacd'] > dataframe['umacd_signal'])
        )
        
        # 条件2: Volume突破信号
        dataframe['vol_breakout'] = (
            (dataframe['vol_ratio'] > self.buy_vol_multiplier) &
            (dataframe['close'] > dataframe['price_high'].shift(1) * 0.995)
        )
        
        # 时间窗口共振：UMACD信号后3根K线内出现Volume突破
        # 方法：UMACD信号向前传播3根K线，与Volume信号求交集
        umacd_window = (
            dataframe['umacd_buy'] |
            dataframe['umacd_buy'].shift(1) |
            dataframe['umacd_buy'].shift(2) |
            dataframe['umacd_buy'].shift(3)
        )
        
        # 共振条件：在时间窗口内出现Volume突破，且RSI不超买
        dataframe.loc[
            umacd_window &
            dataframe['vol_breakout'] &
            (dataframe['rsi'] < 80),
            'buy'
        ] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        
        # UMACD 死叉
        conditions.append(
            (dataframe['umacd'] > -0.03) &
            (dataframe['umacd'] < dataframe['umacd_signal'])
        )
        
        # RSI 超买
        conditions.append(dataframe['rsi'] > 85)
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'sell'] = 1
        
        return dataframe
