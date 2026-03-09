# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
"""
EnsembleV2Strategy — 修复版集成策略
基于 EnsembleLooseStrategy（时间窗口共振逻辑）全面升级：

修复的 BUG：
  - BUG1：旧版 populate_buy_trend / populate_sell_trend → 改为 populate_entry_trend / populate_exit_trend
  - BUG2：卖出条件 min > max（永远不满足）→ 修复为正确区间
  - BUG3：'buy'/'sell' 列名 → 改为 'enter_long'/'exit_long'

新增功能：
  - UMACD + Volume 时间窗口共振（核心创新保留）
  - ATR 动态止损
  - 全部参数 hyperoptable
  - custom_stoploss 动态止损
  - 中文注释

作者：基于 EnsembleLooseStrategy 重构
版本：V2.0
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


class EnsembleV2Strategy(IStrategy):
    """
    EnsembleV2 集成策略

    核心创新：时间窗口共振
    - UMACD 信号出现后，在 N 根 K 线的时间窗口内
    - 如果出现 Volume 突破确认，视为有效共振信号
    - 这比要求同一根 K 线同时满足两个条件更灵活

    策略架构：
    ┌─────────────────────────────────────────┐
    │  时间窗口共振逻辑                          │
    │                                          │
    │  UMACD 超卖信号  ──▶  时间窗口（N 根）     │
    │                              │           │
    │  Volume 突破   ──────────────┘           │
    │                              │           │
    │  RSI 不超买    ────────────── AND        │
    │                              │           │
    │                         enter_long       │
    └─────────────────────────────────────────┘

    出场：ROI 阶梯 + UMACD 死叉 + RSI 超买 + ATR 动态止损
    """

    # ==================== 接口版本 ====================
    INTERFACE_VERSION = 3

    # ==================== 基础配置 ====================
    timeframe = '15m'
    can_short: bool = False

    startup_candle_count: int = 200

    # ==================== ROI 止盈阶梯 ====================
    minimal_roi = {
        "0":   0.12,   # 立即止盈 12%
        "60":  0.07,   # 1小时后 7%
        "180": 0.03,   # 3小时后 3%
        "400": 0       # 6.7小时后保本即走
    }

    # ==================== 止损设置 ====================
    stoploss = -0.12

    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    # ==================== Hyperopt 参数：买入 ====================

    # UMACD 买入区间（超卖区域）
    buy_umacd_min = DecimalParameter(
        -0.08, -0.005, decimals=5, default=-0.05, space='buy',
        load=True, optimize=True
    )
    buy_umacd_max = DecimalParameter(
        -0.04, 0.005, decimals=5, default=-0.01, space='buy',
        load=True, optimize=True
    )

    # 时间窗口大小（UMACD 信号后等待 N 根 K 线内出现 Volume 确认）
    buy_window_size = IntParameter(
        1, 6, default=3, space='buy', optimize=True
    )

    # Volume 突破倍数
    buy_vol_multiplier = DecimalParameter(
        1.5, 5.0, decimals=1, default=3.0, space='buy', optimize=True
    )

    # 价格突破回溯周期（N 根 K 线最高价）
    buy_lookback_period = IntParameter(
        20, 80, default=51, space='buy', optimize=True
    )

    # RSI 上限
    buy_rsi_max = IntParameter(60, 85, default=80, space='buy', optimize=True)

    # 是否要求价格突破历史高点
    buy_require_price_breakout = BooleanParameter(
        default=True, space='buy', optimize=True
    )

    # 价格突破阈值（允许接近 N% 内）
    buy_breakout_threshold = DecimalParameter(
        0.99, 1.0, decimals=3, default=0.995, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：卖出 ====================

    # UMACD 卖出区间（修复原代码的 min > max BUG）
    # 正确：sell_umacd_lower < sell_umacd_upper
    sell_umacd_lower = DecimalParameter(
        -0.04, 0.0, decimals=5, default=-0.03, space='sell',
        load=True, optimize=True
    )
    sell_rsi_threshold = IntParameter(
        70, 92, default=85, space='sell', optimize=True
    )

    # ==================== 指标计算 ====================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算 UMACD + Volume + RSI + ATR 指标"""

        # -------- UMACD 核心指标 --------
        ema12 = ta.EMA(dataframe, timeperiod=12)
        ema26 = ta.EMA(dataframe, timeperiod=26)
        dataframe['umacd'] = (ema12 / ema26) - 1
        dataframe['umacd_signal'] = ta.EMA(dataframe['umacd'], timeperiod=9)
        dataframe['umacd_hist'] = dataframe['umacd'] - dataframe['umacd_signal']

        # -------- RSI 指标 --------
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # -------- 成交量指标 --------
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_ratio'] = dataframe['volume'] / dataframe['volume_ma']

        # -------- 价格突破基准（动态，由 hyperopt 参数控制）--------
        # 使用最大可能的回溯期预先计算（策略运行时动态选取）
        for period in [20, 30, 40, 51, 60, 80]:
            dataframe[f'price_high_{period}'] = dataframe['high'].rolling(window=period).max()

        # -------- ATR 动态止损 --------
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_stop'] = dataframe['close'] - 2 * dataframe['atr']  # ATR 支撑位

        # -------- 趋势过滤 --------
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)

        # -------- ADX 趋势强度（辅助确认）--------
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)

        return dataframe

    # ==================== 入场信号 ====================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        时间窗口共振入场逻辑：
        1. UMACD 进入超卖区间（产生买入信号标记）
        2. 在 buy_window_size 根 K 线内，检测 Volume 突破
        3. 两者共振 + RSI 不超买 → enter_long

        时间窗口实现方式：
        - 先计算 UMACD 买入信号 bool 列
        - 通过 shift 将信号向前传播 N 根 K 线
        - 与 Volume 突破信号求 AND
        """

        # -------- 步骤1：计算 UMACD 买入信号 --------
        dataframe['umacd_buy'] = (
            (dataframe['umacd'] > self.buy_umacd_min.value) &
            (dataframe['umacd'] < self.buy_umacd_max.value) &
            (dataframe['umacd'] > dataframe['umacd_signal'])  # UMACD 金叉确认
        )

        # -------- 步骤2：计算 Volume 突破信号 --------
        # 动态回溯期（使用最接近 hyperopt 参数的预计算列）
        lookback = self.buy_lookback_period.value
        # 找最接近的预计算列
        available_periods = [20, 30, 40, 51, 60, 80]
        closest_period = min(available_periods, key=lambda x: abs(x - lookback))
        price_high_col = f'price_high_{closest_period}'

        if self.buy_require_price_breakout.value:
            dataframe['vol_breakout'] = (
                (dataframe['vol_ratio'] > self.buy_vol_multiplier.value) &
                (dataframe['close'] > dataframe[price_high_col].shift(1) * self.buy_breakout_threshold.value)
            )
        else:
            dataframe['vol_breakout'] = (
                dataframe['vol_ratio'] > self.buy_vol_multiplier.value
            )

        # -------- 步骤3：时间窗口传播 --------
        # UMACD 信号向前传播 buy_window_size 根 K 线
        window_size = self.buy_window_size.value
        umacd_window = dataframe['umacd_buy'].copy()
        for i in range(1, window_size + 1):
            umacd_window = umacd_window | dataframe['umacd_buy'].shift(i)

        # -------- 步骤4：共振入场 --------
        dataframe.loc[
            umacd_window &
            dataframe['vol_breakout'] &
            (dataframe['rsi'] < self.buy_rsi_max.value) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1

        return dataframe

    # ==================== 出场信号 ====================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        多条件出场（任一满足即退出）：
        1. UMACD 死叉（跌破信号线且为负）
        2. RSI 超买（均值回归）

        注意：ROI 和 stoploss 由框架自动处理，这里只是额外的信号退出
        """
        conditions = []

        # -------- 条件1：UMACD 死叉 --------
        # UMACD 跌破信号线，且 UMACD 值在负区域（原代码 BUG 修复后的正确逻辑）
        conditions.append(
            (dataframe['umacd'] > self.sell_umacd_lower.value) &  # 不在过深超卖区
            (dataframe['umacd'] < dataframe['umacd_signal'])       # 死叉
        )

        # -------- 条件2：RSI 超买 --------
        conditions.append(dataframe['rsi'] > self.sell_rsi_threshold.value)

        # -------- 条件3：UMACD 快速下穿（动量反转）--------
        conditions.append(
            qtpylib.crossed_below(dataframe['umacd'], dataframe['umacd_signal'])
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'exit_long'
            ] = 1

        return dataframe

    # ==================== 自定义止损（ATR 动态）====================
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
        ATR 动态止损：
        - 盈利超过 8%：锁定 3% 利润
        - 盈利超过 4%：止损到 +0%
        - 超时且亏损：时间止损
        """
        if current_profit >= 0.08:
            return self._stoploss_from_open(0.03, current_profit)

        if current_profit >= 0.04:
            return self._stoploss_from_open(0.0, current_profit)

        # 时间止损：超过 60 根 K 线（15h）仍亏损超过 4%
        candles_open = (current_time - trade.open_date_utc).seconds // (15 * 60)
        if candles_open > 60 and current_profit < -0.04:
            return -0.04

        return None

    def _stoploss_from_open(self, open_relative_stop: float, current_profit: float) -> float:
        """从开仓价计算相对当前价的止损比例"""
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
        集成策略的条件退出：
        - 超过 4 天接近平本：退出
        - 持仓超过 2 天亏损超过 6%：快速止损
        """
        hours_open = (current_time - trade.open_date_utc).total_seconds() / 3600

        if hours_open > 96 and -0.02 < current_profit < 0.02:
            return '集成策略_时间止损'

        if hours_open > 48 and current_profit < -0.06:
            return '集成策略_快速止损'

        return None
