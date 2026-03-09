from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
import talib.abstract as ta
from datetime import datetime
from typing import Optional, Dict, Any
from functools import reduce


class EnsembleHybridStrategy(IStrategy):
    """
    Ensemble Strategy - 策略共振确认系统
    
    核心逻辑：双策略信号共振确认，大幅提升胜率与盈亏比
    - Primary: UniversalMACD（趋势捕捉）
    - Secondary: VolumeBreakout（动量确认）
    
    入场条件（需同时满足）：
    1. UniversalMACD 给出买入信号（umacd 在超卖区间反转）
    2. VolumeBreakout 确认放量突破（价量共振）
    
    退出条件（任一满足）：
    1. ROI 阶梯止盈
    2. UniversalMACD 卖出信号
    3. 硬止损
    """
    
    INTERFACE_VERSION = 3
    
    # 基础配置
    timeframe = '15m'
    max_open_trades = 1
    can_short = False
    
    # 核心止盈止损（Unified 最优参数）
    minimal_roi = {
        "0": 0.221,
        "49": 0.057,
        "160": 0.015,
        "394": 0
    }
    
    stoploss = -0.341
    trailing_stop = False
    
    # UniversalMACD 参数
    buy_umacd_min = -0.03273
    buy_umacd_max = -0.01887
    
    # VolumeBreakout 参数
    buy_lookback_period = 51
    buy_vol_multiplier = 4.997
    
    startup_candle_count = 200
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算两套策略的所有指标"""
        
        # UniversalMACD 指标
        ema12 = ta.EMA(dataframe, timeperiod=12)
        ema26 = ta.EMA(dataframe, timeperiod=26)
        dataframe['umacd'] = (ema12 / ema26) - 1
        dataframe['umacd_signal'] = ta.EMA(dataframe['umacd'], timeperiod=9)
        
        # VolumeBreakout 指标
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        dataframe['price_high_51'] = dataframe['high'].rolling(window=51).max()
        
        # RSI 过滤
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """入场条件：双策略共振确认"""
        conditions = []
        
        # 条件1: UniversalMACD 买入信号
        conditions.append(
            (dataframe['umacd'] > self.buy_umacd_min) &
            (dataframe['umacd'] < self.buy_umacd_max) &
            (dataframe['umacd'] > dataframe['umacd_signal'])
        )
        
        # 条件2: VolumeBreakout 确认
        conditions.append(
            (dataframe['vol_ratio'] > self.buy_vol_multiplier) &
            (dataframe['close'] > dataframe['price_high_51'].shift(1))
        )
        
        # 条件3: RSI 过滤（避免超买）
        conditions.append(dataframe['rsi'] < 75)
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'
            ] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """出场条件：多维度退出"""
        conditions = []
        
        # 条件1: UniversalMACD 卖出信号
        conditions.append(
            (dataframe['umacd'] > -0.00707) &
            (dataframe['umacd'] < -0.02323) &
            (dataframe['umacd'] < dataframe['umacd_signal'])
        )
        
        # 条件2: RSI 超买
        conditions.append(dataframe['rsi'] > 85)
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'sell'
            ] = 1
        
        return dataframe
