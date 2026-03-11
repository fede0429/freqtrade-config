# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""
UniversalMACD V2 — 现货优化版
基于原始 UniversalMACD.py 全面升级：
  - 修复 API（populate_entry_trend / populate_exit_trend）
  - 添加 RSI + Volume 双重过滤
  - 添加 trailing_stop
  - 所有参数完全 hyperoptable
  - 自定义止损方法（custom_stoploss）
  - 自定义退出方法（custom_exit）
  - 仅现货用，can_short = False

作者：基于 Masoud Azizi 原始 UniversalMACD 重构
版本：V2.0
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union, Dict
from functools import reduce

# freqtrade 核心导入
from freqtrade.strategy import (
    DecimalParameter,
    IntParameter,
    BooleanParameter,
    IStrategy,
    merge_informative_pair
)
from freqtrade.persistence import Trade
import freqtrade.vendor.qtpylib.indicators as qtpylib

# 技术指标库
import talib.abstract as ta


class UniversalMACD_V2(IStrategy):
    """
    UniversalMACD V2 现货优化版

    核心逻辑：
    - UMACD（EMA12/EMA26 比值偏差）作为主信号
    - RSI 过滤极端超买/超卖区间
    - Volume 过滤低流动性假信号
    - ATR 动态 trailing stop 保护利润
    - 自定义止损：跌破 ATR 支撑时提前平仓

    适用场景：
    - 现货市场（can_short = False）
    - 时间框架：5m / 15m
    - 资金规模：500-2000 USDT
    """

    # ==================== 接口版本 ====================
    INTERFACE_VERSION = 3

    # ==================== 基础配置 ====================
    timeframe = '15m'         # 主时间框架
    can_short: bool = False   # 现货模式，不做空

    # 启动所需最小 K 线数量（EMA26 + 信号线需要 200 根）
    startup_candle_count: int = 200

    # ==================== ROI 止盈阶梯 ====================
    # 说明：hyperopt 会优化这些值，这里是保守起点
    minimal_roi = {
        "0":   0.15,   # 立即止盈 15%（保守）
        "60":  0.08,   # 1小时后 8%
        "180": 0.04,   # 3小时后 4%
        "360": 0.02,   # 6小时后 2%
        "720": 0       # 12小时后 0%（只要盈利就走）
    }

    # ==================== 止损设置 ====================
    stoploss = -0.10          # 硬止损 10%（相对保守）

    # trailing stop：在盈利 3% 时激活，每回撤 2% 止损
    trailing_stop = True
    trailing_stop_positive = 0.02          # 激活后的跟踪止损距离
    trailing_stop_positive_offset = 0.03   # 盈利超过 3% 才激活 trailing
    trailing_only_offset_is_reached = True # 只有到达 offset 才开始 trailing

    # ==================== Hyperopt 参数：买入 ====================
    # UMACD 区间（EMA12/EMA26 比值 - 1）
    buy_umacd_min = DecimalParameter(
        -0.06, 0.0, decimals=5, default=-0.03273, space='buy',
        load=True, optimize=True
    )
    buy_umacd_max = DecimalParameter(
        -0.04, 0.01, decimals=5, default=-0.01887, space='buy',
        load=True, optimize=True
    )
    # 要求 UMACD 在信号线上方（动量确认）
    buy_require_cross_above = BooleanParameter(
        default=True, space='buy', optimize=True
    )
    # RSI 过滤上限（避免超买）
    buy_rsi_max = IntParameter(
        50, 80, default=70, space='buy', optimize=True
    )
    # RSI 过滤下限（避免极端超卖反弹陷阱）
    buy_rsi_min = IntParameter(
        20, 50, default=30, space='buy', optimize=True
    )
    # Volume 倍数过滤（成交量须高于 N 倍均量）
    buy_volume_factor = DecimalParameter(
        0.5, 3.0, decimals=1, default=1.0, space='buy', optimize=True
    )
    # EMA 趋势过滤（价格须在 EMA200 上方）
    buy_ema200_filter = BooleanParameter(
        default=False, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：卖出 ====================
    sell_umacd_min = DecimalParameter(
        -0.04, 0.02, decimals=5, default=-0.02323, space='sell',
        load=True, optimize=True
    )
    sell_umacd_max = DecimalParameter(
        -0.02, 0.04, decimals=5, default=-0.00707, space='sell',
        load=True, optimize=True
    )
    sell_rsi_min = IntParameter(
        65, 90, default=80, space='sell', optimize=True
    )

    # ==================== Hyperopt 参数：ROI（通过 roi space 优化）====================
    # ROI 由 freqtrade hyperopt 的 roi space 自动优化，无需手动定义参数

    # ==================== 指标计算 ====================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算所有技术指标"""

        # -------- UMACD 核心指标 --------
        # EMA12 和 EMA26（用于计算比值偏差）
        dataframe['ma12'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ma26'] = ta.EMA(dataframe, timeperiod=26)
        # UMACD = (EMA12 / EMA26) - 1，反映 EMA 偏差百分比
        dataframe['umacd'] = (dataframe['ma12'] / dataframe['ma26']) - 1
        # UMACD 信号线（9 周期 EMA 平滑）
        dataframe['umacd_signal'] = ta.EMA(dataframe['umacd'], timeperiod=9)
        # UMACD 柱状图（用于判断金叉/死叉方向）
        dataframe['umacd_hist'] = dataframe['umacd'] - dataframe['umacd_signal']

        # -------- RSI 指标 --------
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        # RSI 平滑版（减少噪声）
        dataframe['rsi_smooth'] = ta.EMA(dataframe['rsi'], timeperiod=3)

        # -------- 成交量指标 --------
        # 20 周期成交量均线
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        # 成交量比率
        dataframe['vol_ratio'] = dataframe['volume'] / dataframe['volume_ma']

        # -------- ATR 波动率指标 --------
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']  # ATR 占价格百分比

        # -------- 趋势过滤器 --------
        # EMA200 长期趋势
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        # EMA50 中期趋势
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)

        # -------- 布林带（辅助参考）--------
        bb = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_upper'] = bb['upperband']
        dataframe['bb_lower'] = bb['lowerband']
        dataframe['bb_mid'] = bb['middleband']
        # BB 宽度（衡量波动率）
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_mid']

        # -------- MACD 标准版（辅助确认）--------
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']

        return dataframe

    # ==================== 入场信号 ====================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        买入条件（现货只做多）：
        1. UMACD 在指定区间内（超卖反弹区域）
        2. UMACD 在信号线上方（动量向上，可选）
        3. RSI 不在超买区
        4. 成交量高于均量
        5. 可选：价格在 EMA200 上方（趋势过滤）
        """
        conditions = []

        # -------- 主要条件：UMACD 区间 --------
        conditions.append(
            dataframe['umacd'].between(
                self.buy_umacd_min.value,
                self.buy_umacd_max.value
            )
        )

        # -------- 可选：UMACD 金叉确认 --------
        if self.buy_require_cross_above.value:
            conditions.append(dataframe['umacd'] > dataframe['umacd_signal'])

        # -------- RSI 双向过滤 --------
        conditions.append(dataframe['rsi'] < self.buy_rsi_max.value)
        conditions.append(dataframe['rsi'] > self.buy_rsi_min.value)

        # -------- 成交量过滤（避免低流动性假信号）--------
        conditions.append(
            dataframe['vol_ratio'] >= self.buy_volume_factor.value
        )

        # -------- 可选：EMA200 趋势过滤 --------
        if self.buy_ema200_filter.value:
            conditions.append(dataframe['close'] > dataframe['ema200'])

        # -------- 必要条件：成交量不为零 --------
        conditions.append(dataframe['volume'] > 0)

        # -------- 生成信号 --------
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'
            ] = 1

        return dataframe

    # ==================== 出场信号 ====================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        卖出条件（任一满足即退出）：
        1. UMACD 进入死叉区间（获利了结）
        2. RSI 超买（均值回归）
        3. UMACD 跌破信号线且为负值
        """
        conditions = []

        # -------- 条件1：UMACD 进入卖出区间 --------
        # 修复原始代码 BUG：原代码 min > max，条件永远不满足
        # 正确：sell_min < sell_max，UMACD 在此区间表示超买/回调
        cond_umacd = (
            (dataframe['umacd'] > self.sell_umacd_min.value) &
            (dataframe['umacd'] < self.sell_umacd_max.value)
        )
        conditions.append(cond_umacd)

        # -------- 条件2：RSI 超买 --------
        conditions.append(dataframe['rsi'] > self.sell_rsi_min.value)

        # -------- 条件3：UMACD 死叉（UMACD 跌破信号线）--------
        conditions.append(
            qtpylib.crossed_below(dataframe['umacd'], dataframe['umacd_signal'])
        )

        # -------- 生成信号（任一条件满足即退出）--------
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'exit_long'
            ] = 1

        return dataframe

    # ==================== 自定义止损 ====================
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
        动态止损逻辑：
        - 若已盈利超过 5%，将止损提升到 -1%（保护利润）
        - 若已盈利超过 10%，将止损提升到 +2%（锁定利润）
        - 若持仓超过 2 天仍亏损，提前止损（时间止损）
        - 其他情况：返回 None（使用策略默认止损）
        """
        # 盈利保护：盈利超过 10%，锁定至少 2% 利润
        if current_profit >= 0.10:
            return stoploss_from_open(0.02, current_profit, is_short=False)

        # 盈利保护：盈利超过 5%，止损提升到 -1%
        if current_profit >= 0.05:
            return stoploss_from_open(-0.01, current_profit, is_short=False)

        # 时间止损：超过 48 根 K 线（15m * 48 = 12 小时）仍亏损超过 3%
        candles_open = (current_time - trade.open_date_utc).seconds // (15 * 60)
        if candles_open > 48 and current_profit < -0.03:
            return -0.03  # 强制止损

        # 默认：使用策略的 stoploss 设定
        return None

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
        条件退出逻辑（比信号更灵活的退出机制）：
        - 持仓超过 3 天且利润接近 0：退出避免机会成本
        - 持仓超过 1 天且亏损超过 7%：提前止损
        """
        # 计算持仓时间（小时）
        hours_open = (current_time - trade.open_date_utc).seconds / 3600

        # 时间+利润双重判断：超过 72 小时，利润在 -2% 到 +1% 之间（几乎白跑）
        if hours_open > 72 and -0.02 < current_profit < 0.01:
            return '时间止损_接近平本'

        # 快速止损：24 小时内亏损超过 7%
        if hours_open > 24 and current_profit < -0.07:
            return '快速止损_超时亏损'

        return None


# ==================== 工具函数 ====================
def stoploss_from_open(
    open_relative_stop: float,
    current_profit: float,
    is_short: bool = False
) -> float:
    """
    从开仓价格计算相对止损比例
    用于将 '从开仓价止损 X%' 转换为 '从当前价止损 Y%'

    参数：
    - open_relative_stop: 相对开仓价的止损（如 0.02 表示开仓价 +2%）
    - current_profit: 当前利润（如 0.10 表示盈利 10%）
    - is_short: 是否做空

    返回：
    - 相对当前价的止损比例（负数）
    """
    if is_short:
        return -1 + (1 - open_relative_stop) / (1 - current_profit)
    else:
        return -1 + (1 + open_relative_stop) / (1 + current_profit)

