# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
"""
UniversalMACD Futures — 永续合约版
基于 UniversalMACD_V2.py 修改，支持做空：
  - can_short = True（永续合约双向交易）
  - 添加做空信号（enter_short / exit_short）
  - 更严格的止损（永续合约杠杆风险更高）
  - 适配永续合约特性（隔离保证金 3x）
  - 做空信号：UMACD 进入高位超买区域向下反转

作者：基于 UniversalMACD_V2 扩展
版本：Futures 1.0
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union
from functools import reduce

# freqtrade 核心导入
from freqtrade.strategy import (
    DecimalParameter,
    IntParameter,
    BooleanParameter,
    IStrategy
)
from freqtrade.persistence import Trade
import freqtrade.vendor.qtpylib.indicators as qtpylib

# 技术指标库
import talib.abstract as ta


class UniversalMACD_Futures(IStrategy):
    """
    UniversalMACD 永续合约版

    核心特性：
    - 双向交易（做多 + 做空）
    - 更严格的止损（-5% ~ -8%，避免杠杆爆仓）
    - 做空条件：UMACD 进入正值超买区反转
    - 与现货版共享大部分逻辑，但风控参数更保守

    风控提醒：
    - 使用前请确认 config_futures.json 已设置 leverage_config
    - 建议杠杆不超过 3x
    - max_open_trades 建议 <= 3
    """

    # ==================== 接口版本 ====================
    INTERFACE_VERSION = 3

    # ==================== 基础配置 ====================
    timeframe = '15m'
    can_short: bool = True    # 永续合约，支持双向交易

    startup_candle_count: int = 200

    # ==================== ROI 止盈阶梯（更保守）====================
    minimal_roi = {
        "0":   0.08,   # 立即止盈 8%（永续保守）
        "60":  0.05,   # 1小时后 5%
        "180": 0.03,   # 3小时后 3%
        "360": 0.01,   # 6小时后 1%
        "720": 0       # 12小时后保本即走
    }

    # ==================== 止损设置（更严格）====================
    stoploss = -0.07          # 硬止损 7%（永续合约更严格）

    # trailing stop（更紧）
    trailing_stop = True
    trailing_stop_positive = 0.015         # 激活后跟踪 1.5%
    trailing_stop_positive_offset = 0.025  # 盈利超过 2.5% 才激活
    trailing_only_offset_is_reached = True

    # ==================== Hyperopt 参数：做多买入 ====================
    # UMACD 超卖区间（做多入场）
    buy_umacd_min = DecimalParameter(
        -0.06, 0.0, decimals=5, default=-0.03273, space='buy',
        load=True, optimize=True
    )
    buy_umacd_max = DecimalParameter(
        -0.04, 0.005, decimals=5, default=-0.01887, space='buy',
        load=True, optimize=True
    )
    buy_rsi_max = IntParameter(60, 75, default=65, space='buy', optimize=True)
    buy_rsi_min = IntParameter(25, 50, default=35, space='buy', optimize=True)
    buy_volume_factor = DecimalParameter(
        0.8, 2.5, decimals=1, default=1.2, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：做多卖出 ====================
    sell_umacd_min = DecimalParameter(
        -0.03, 0.02, decimals=5, default=-0.02323, space='sell',
        load=True, optimize=True
    )
    sell_umacd_max = DecimalParameter(
        -0.01, 0.04, decimals=5, default=-0.00707, space='sell',
        load=True, optimize=True
    )
    sell_rsi_min = IntParameter(65, 85, default=75, space='sell', optimize=True)

    # ==================== Hyperopt 参数：做空 ====================
    # UMACD 超买区间（做空入场）- 正值区域表示超买
    short_umacd_min = DecimalParameter(
        0.0, 0.04, decimals=5, default=0.01500, space='sell',
        load=True, optimize=True
    )
    short_umacd_max = DecimalParameter(
        0.02, 0.06, decimals=5, default=0.03000, space='sell',
        load=True, optimize=True
    )
    short_rsi_min = IntParameter(65, 85, default=75, space='sell', optimize=True)
    short_rsi_max = IntParameter(75, 95, default=85, space='sell', optimize=True)
    short_volume_factor = DecimalParameter(
        0.8, 2.5, decimals=1, default=1.2, space='sell', optimize=True
    )

    # ==================== 指标计算 ====================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算双向交易所需的全部指标"""

        # -------- UMACD 核心指标 --------
        dataframe['ma12'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ma26'] = ta.EMA(dataframe, timeperiod=26)
        dataframe['umacd'] = (dataframe['ma12'] / dataframe['ma26']) - 1
        dataframe['umacd_signal'] = ta.EMA(dataframe['umacd'], timeperiod=9)
        dataframe['umacd_hist'] = dataframe['umacd'] - dataframe['umacd_signal']

        # -------- RSI 指标 --------
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # -------- 成交量指标 --------
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_ratio'] = dataframe['volume'] / dataframe['volume_ma']

        # -------- ATR 波动率 --------
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']

        # -------- 趋势过滤器 --------
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)

        # -------- ADX 趋势强度（永续合约重要）--------
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        # +DI 和 -DI（方向指标）
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)

        # -------- 布林带 --------
        bb = ta.BBANDS(dataframe, timeperiod=20)
        dataframe['bb_upper'] = bb['upperband']
        dataframe['bb_lower'] = bb['lowerband']
        dataframe['bb_mid'] = bb['middleband']

        return dataframe

    # ==================== 做多入场信号 ====================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        做多条件（UMACD 超卖区反弹）：
        1. UMACD 在超卖区间
        2. UMACD 在信号线上方（动量向上）
        3. RSI 不超买
        4. 成交量放大
        """
        # -------- 做多信号 --------
        long_conditions = []

        long_conditions.append(
            dataframe['umacd'].between(
                self.buy_umacd_min.value,
                self.buy_umacd_max.value
            )
        )
        long_conditions.append(dataframe['umacd'] > dataframe['umacd_signal'])
        long_conditions.append(dataframe['rsi'] < self.buy_rsi_max.value)
        long_conditions.append(dataframe['rsi'] > self.buy_rsi_min.value)
        long_conditions.append(dataframe['vol_ratio'] >= self.buy_volume_factor.value)
        long_conditions.append(dataframe['volume'] > 0)

        if long_conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, long_conditions),
                'enter_long'
            ] = 1

        # -------- 做空信号（永续合约专属）--------
        short_conditions = []

        # UMACD 进入超买区间（正值高位）
        short_conditions.append(
            dataframe['umacd'].between(
                self.short_umacd_min.value,
                self.short_umacd_max.value
            )
        )
        # UMACD 向下死叉（动量向下）
        short_conditions.append(dataframe['umacd'] < dataframe['umacd_signal'])
        # RSI 超买区间
        short_conditions.append(dataframe['rsi'] > self.short_rsi_min.value)
        short_conditions.append(dataframe['rsi'] < self.short_rsi_max.value)
        # 成交量放大（确认卖压）
        short_conditions.append(dataframe['vol_ratio'] >= self.short_volume_factor.value)
        short_conditions.append(dataframe['volume'] > 0)

        if short_conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, short_conditions),
                'enter_short'
            ] = 1

        return dataframe

    # ==================== 做多出场信号 ====================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        做多出场（UMACD 超买或死叉）
        做空出场（UMACD 超卖或金叉）
        """
        # -------- 做多出场 --------
        exit_long_conditions = []

        exit_long_conditions.append(
            (dataframe['umacd'] > self.sell_umacd_min.value) &
            (dataframe['umacd'] < self.sell_umacd_max.value)
        )
        exit_long_conditions.append(dataframe['rsi'] > self.sell_rsi_min.value)
        exit_long_conditions.append(
            qtpylib.crossed_below(dataframe['umacd'], dataframe['umacd_signal'])
        )

        if exit_long_conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, exit_long_conditions),
                'exit_long'
            ] = 1

        # -------- 做空出场（UMACD 从超买区回落，金叉）--------
        exit_short_conditions = []

        # UMACD 金叉（从负区域上穿信号线）
        exit_short_conditions.append(
            qtpylib.crossed_above(dataframe['umacd'], dataframe['umacd_signal'])
        )
        # UMACD 进入超卖区（空单目标位）
        exit_short_conditions.append(
            dataframe['umacd'].between(
                self.buy_umacd_min.value,
                self.buy_umacd_max.value
            )
        )
        # RSI 超卖（空单目标位）
        exit_short_conditions.append(dataframe['rsi'] < 35)

        if exit_short_conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, exit_short_conditions),
                'exit_short'
            ] = 1

        return dataframe

    # ==================== 自定义止损（永续合约版）====================
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs
    ) -> Optional[float]:
        """
        永续合约动态止损（更严格）：
        - 盈利 >= 8%：锁定 3% 利润
        - 盈利 >= 4%：止损提升到 -0.5%
        - 持仓超过 24 小时亏损：提前止损防杠杆损失扩大
        """
        # 盈利锁定：盈利超过 8%，止损到 +3%
        if current_profit >= 0.08:
            return self._stoploss_from_open(0.03, current_profit, trade.is_short)

        # 盈利保护：盈利超过 4%，止损到 -0.5%
        if current_profit >= 0.04:
            return self._stoploss_from_open(-0.005, current_profit, trade.is_short)

        # 时间止损：超过 24 小时仍亏损 2% 以上（永续合约资金费用损耗）
        hours_open = (current_time - trade.open_date_utc).seconds / 3600
        if hours_open > 24 and current_profit < -0.02:
            return -0.02  # 强制止损

        return None

    def _stoploss_from_open(
        self,
        open_relative_stop: float,
        current_profit: float,
        is_short: bool
    ) -> float:
        """从开仓价计算相对当前价的止损比例"""
        if is_short:
            return -1 + (1 - open_relative_stop) / (1 - current_profit)
        else:
            return -1 + (1 + open_relative_stop) / (1 + current_profit)

    # ==================== 自定义退出 ====================
    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[Union[str, bool]]:
        """
        条件退出（永续合约更积极）：
        - 超过 48 小时接近盈亏平衡：退出（节省资金费）
        - 超过 12 小时亏损超 5%：快速止损
        """
        hours_open = (current_time - trade.open_date_utc).seconds / 3600

        # 接近平本退出（永续合约资金费持续损耗）
        if hours_open > 48 and -0.01 < current_profit < 0.015:
            return '永续_时间止损'

        # 快速止损
        if hours_open > 12 and current_profit < -0.05:
            return '永续_快速止损'

        return None
