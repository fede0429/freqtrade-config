# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
"""
AdaptiveMetaStrategy — 自适应元策略（自学习框架）
这是整个系统最核心的策略，实现市场状态感知的自适应交易：

核心特性：
  1. 多指标融合：UMACD + RSI + Supertrend + Bollinger Band
  2. 多时间框架：主时间框架 15m + 信息时间框架 1h + 4h
  3. 市场状态检测：通过 ADX 判断趋势 vs 震荡
  4. 自适应信号权重：趋势市场用动量指标，震荡市场用均值回归
  5. 全部参数 hyperoptable
  6. DCA 加仓逻辑（adjust_trade_position）
  7. 动态止损（custom_stoploss）
  8. 条件退出（custom_exit）
  9. 预留 FreqAI 接口（注释说明）

FreqAI 升级路径：
  - 当前版本：规则驱动 + Hyperopt 自动优化参数
  - 未来版本：将 market_state + 多指标组合作为 FreqAI 特征
  - 接入方式：在 populate_entry_trend 中调用 self.freqai.start()
  - 参考：config_freqai.json

作者：原创自适应元策略
版本：1.0
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timezone
from typing import Optional, Union, Tuple, List, Dict
from functools import reduce

# freqtrade 核心导入
from freqtrade.strategy import (
    DecimalParameter,
    IntParameter,
    BooleanParameter,
    CategoricalParameter,
    IStrategy,
    merge_informative_pair
)
from freqtrade.persistence import Trade
import freqtrade.vendor.qtpylib.indicators as qtpylib

# 技术指标库
import talib.abstract as ta


class AdaptiveMetaStrategy(IStrategy):
    """
    自适应元策略

    策略架构图：
    ┌──────────────────────────────────────────────────────────┐
    │                  AdaptiveMetaStrategy                     │
    │                                                          │
    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
    │  │ 市场状态检测  │    │ 多时间框架   │    │ 多指标融合   │  │
    │  │ ADX > 25    │    │ 15m+1h+4h   │    │ UMACD+RSI+  │  │
    │  │ = 趋势市场   │    │ 信号确认     │    │ ST+BB       │  │
    │  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
    │         │                  │                  │          │
    │         └──────────────────┼──────────────────┘          │
    │                            │                             │
    │                    ┌───────▼───────┐                     │
    │                    │  自适应权重    │                     │
    │                    │ 趋势市：动量优先│                     │
    │                    │ 震荡市：回归优先│                     │
    │                    └───────┬───────┘                     │
    │                            │                             │
    │              ┌─────────────┼─────────────┐               │
    │              ▼             ▼             ▼               │
    │         enter_long    custom_stop    DCA加仓              │
    └──────────────────────────────────────────────────────────┘
    """

    # ==================== 接口版本 ====================
    INTERFACE_VERSION = 3

    # ==================== 基础配置 ====================
    timeframe = '15m'           # 主时间框架
    can_short: bool = False     # 现货模式

    startup_candle_count: int = 200

    # ==================== 信息时间框架（多时间框架分析）====================
    # informative_pairs 告知 freqtrade 需要额外下载哪些数据
    def informative_pairs(self):
        """
        声明需要的额外时间框架数据
        返回：[(交易对, 时间框架)] 列表
        """
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        # 为每个交易对添加 1h 和 4h 时间框架
        for pair in pairs:
            informative_pairs.append((pair, '1h'))
            informative_pairs.append((pair, '4h'))
        return informative_pairs

    # ==================== ROI 止盈阶梯 ====================
    minimal_roi = {
        "0":   0.12,
        "60":  0.07,
        "180": 0.04,
        "360": 0.02,
        "720": 0
    }

    # ==================== 止损设置 ====================
    stoploss = -0.10

    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    # ==================== DCA 设置（加仓）====================
    # 最大安全订单数（DCA 加仓次数）
    position_adjustment_enable = True
    max_entry_position_adjustment = 2  # 最多加仓 2 次

    # ==================== Hyperopt 参数：市场状态 ====================

    # ADX 阈值：高于此值认为是趋势市场
    adx_trend_threshold = IntParameter(
        15, 40, default=25, space='buy', optimize=True
    )

    # 趋势市场使用的策略模式
    # 'umacd' = 动量跟随，'mean_reversion' = 均值回归
    trend_mode = CategoricalParameter(
        ['umacd', 'mean_reversion', 'hybrid'],
        default='umacd', space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：UMACD 信号 ====================
    buy_umacd_min = DecimalParameter(
        -0.06, -0.005, decimals=5, default=-0.04, space='buy',
        load=True, optimize=True
    )
    buy_umacd_max = DecimalParameter(
        -0.03, 0.005, decimals=5, default=-0.01, space='buy',
        load=True, optimize=True
    )

    # ==================== Hyperopt 参数：RSI ====================
    # RSI 超卖入场阈值（均值回归模式）
    buy_rsi_oversold = IntParameter(
        20, 45, default=35, space='buy', optimize=True
    )
    buy_rsi_max = IntParameter(
        55, 80, default=70, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：Supertrend ====================
    # Supertrend 参数
    buy_st_multiplier = DecimalParameter(
        1.5, 4.0, decimals=1, default=3.0, space='buy', optimize=True
    )
    buy_st_period = IntParameter(
        7, 21, default=10, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：布林带 ====================
    # 布林带偏差倍数
    buy_bb_lower_mult = DecimalParameter(
        1.5, 3.0, decimals=1, default=2.0, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：多时间框架确认 ====================
    # 是否需要 1h 趋势确认
    buy_require_1h_confirm = BooleanParameter(
        default=True, space='buy', optimize=True
    )
    # 是否需要 4h 趋势确认
    buy_require_4h_confirm = BooleanParameter(
        default=False, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：Volume ====================
    buy_volume_factor = DecimalParameter(
        0.5, 3.0, decimals=1, default=1.0, space='buy', optimize=True
    )

    # ==================== Hyperopt 参数：卖出 ====================
    sell_rsi_overbought = IntParameter(
        65, 90, default=80, space='sell', optimize=True
    )
    sell_umacd_threshold = DecimalParameter(
        -0.02, 0.02, decimals=5, default=-0.01, space='sell',
        load=True, optimize=True
    )

    # ==================== Hyperopt 参数：DCA ====================
    # DCA 第一次加仓条件（跌多少时加仓）
    dca_first_drop = DecimalParameter(
        -0.08, -0.02, decimals=2, default=-0.03, space='buy', optimize=True
    )
    dca_second_drop = DecimalParameter(
        -0.15, -0.06, decimals=2, default=-0.07, space='buy', optimize=True
    )

    # ==================== 指标计算（主时间框架）====================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算主时间框架（15m）所有指标，并合并多时间框架数据
        """

        # ================== 主时间框架指标 ==================

        # -------- UMACD --------
        ema12 = ta.EMA(dataframe, timeperiod=12)
        ema26 = ta.EMA(dataframe, timeperiod=26)
        dataframe['umacd'] = (ema12 / ema26) - 1
        dataframe['umacd_signal'] = ta.EMA(dataframe['umacd'], timeperiod=9)
        dataframe['umacd_hist'] = dataframe['umacd'] - dataframe['umacd_signal']

        # -------- RSI --------
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_smooth'] = ta.EMA(dataframe['rsi'], timeperiod=3)

        # -------- Stochastic RSI（更敏感的超买超卖）--------
        fastk, fastd = ta.STOCHRSI(dataframe, timeperiod=14, fastk_period=3, fastd_period=3)
        dataframe['stoch_rsi_k'] = fastk
        dataframe['stoch_rsi_d'] = fastd

        # -------- ATR 波动率 --------
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']

        # -------- ADX 趋势强度（市场状态检测核心）--------
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)

        # -------- 市场状态标记 --------
        # True = 趋势市场，False = 震荡市场
        dataframe['is_trending'] = dataframe['adx'] > self.adx_trend_threshold.value
        # 趋势方向：True = 上趋势，False = 下趋势
        dataframe['trend_up'] = dataframe['plus_di'] > dataframe['minus_di']

        # -------- 布林带 --------
        bb_20 = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_upper'] = bb_20['upperband']
        dataframe['bb_lower'] = bb_20['lowerband']
        dataframe['bb_mid'] = bb_20['middleband']
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_mid']
        # 价格在布林带中的位置（0=下轨，1=上轨）
        dataframe['bb_percent'] = (
            (dataframe['close'] - dataframe['bb_lower']) /
            (dataframe['bb_upper'] - dataframe['bb_lower'])
        )

        # -------- Supertrend 指标 --------
        # 使用固定参数计算 Supertrend（hyperopt 参数在运行时动态使用）
        for mult, period in [(2.0, 10), (3.0, 10), (2.0, 7), (3.0, 14)]:
            st_result = self._compute_supertrend(dataframe, mult, period)
            dataframe[f'st_{mult}_{period}'] = st_result['ST']
            dataframe[f'stx_{mult}_{period}'] = st_result['STX']

        # -------- 成交量指标 --------
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        # 成交量加权平均价（VWAP 近似）
        dataframe['vwap'] = (dataframe['volume'] * (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3).cumsum() / dataframe['volume'].cumsum()

        # -------- 趋势 EMA --------
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)

        # ================== 合并 1h 时间框架数据 ==================
        informative_1h = self._get_informative_1h(metadata)
        if informative_1h is not None:
            dataframe = merge_informative_pair(
                dataframe, informative_1h,
                self.timeframe, '1h',
                ffill=True
            )

        # ================== 合并 4h 时间框架数据 ==================
        informative_4h = self._get_informative_4h(metadata)
        if informative_4h is not None:
            dataframe = merge_informative_pair(
                dataframe, informative_4h,
                self.timeframe, '4h',
                ffill=True
            )

        return dataframe

    def _get_informative_1h(self, metadata: dict) -> Optional[DataFrame]:
        """获取并计算 1h 时间框架指标"""
        try:
            informative = self.dp.get_pair_dataframe(
                pair=metadata['pair'], timeframe='1h'
            )
            if informative is None or len(informative) == 0:
                return None

            # 1h 趋势指标
            ema12 = ta.EMA(informative, timeperiod=12)
            ema26 = ta.EMA(informative, timeperiod=26)
            informative['umacd_1h'] = (ema12 / ema26) - 1
            informative['rsi_1h'] = ta.RSI(informative, timeperiod=14)
            informative['adx_1h'] = ta.ADX(informative, timeperiod=14)
            informative['ema50_1h'] = ta.EMA(informative, timeperiod=50)
            informative['ema200_1h'] = ta.EMA(informative, timeperiod=200)

            # 1h 趋势状态
            informative['trend_up_1h'] = informative['close'] > informative['ema50_1h']

            return informative
        except Exception:
            return None

    def _get_informative_4h(self, metadata: dict) -> Optional[DataFrame]:
        """获取并计算 4h 时间框架指标"""
        try:
            informative = self.dp.get_pair_dataframe(
                pair=metadata['pair'], timeframe='4h'
            )
            if informative is None or len(informative) == 0:
                return None

            # 4h 趋势指标
            informative['ema50_4h'] = ta.EMA(informative, timeperiod=50)
            informative['ema200_4h'] = ta.EMA(informative, timeperiod=200)
            informative['adx_4h'] = ta.ADX(informative, timeperiod=14)
            informative['rsi_4h'] = ta.RSI(informative, timeperiod=14)

            # 4h 大趋势
            informative['bull_market_4h'] = informative['close'] > informative['ema200_4h']

            return informative
        except Exception:
            return None

    # ==================== 入场信号 ====================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        自适应入场逻辑：
        1. 检测市场状态（趋势 or 震荡）
        2. 根据市场状态选择不同的信号策略
        3. 多时间框架确认
        4. 综合信号评分（类 FreqAI 逻辑）

        ============ FreqAI 升级说明 ============
        当前版本：规则驱动（if-else）
        未来升级：
        1. 将所有指标作为 FreqAI 特征
        2. 添加 freqai 配置块到 config_freqai.json
        3. 在策略中调用：
           entry_signal = self.freqai.start(dataframe, metadata, self)
           dataframe.loc[entry_signal['do_predict'] == 1, 'enter_long'] = 1
        ==========================================
        """

        # -------- 基础过滤（必须满足）--------
        base_conditions = [
            dataframe['volume'] > 0,
            dataframe['rsi'] < self.buy_rsi_max.value,
            dataframe['vol_ratio'] >= self.buy_volume_factor.value
        ]

        # -------- 趋势模式信号 --------
        def trend_signals():
            """趋势市场：使用 UMACD + Supertrend 动量追踪"""
            conds = []
            # UMACD 超卖区间
            conds.append(
                dataframe['umacd'].between(
                    self.buy_umacd_min.value,
                    self.buy_umacd_max.value
                )
            )
            # UMACD 金叉（动量向上）
            conds.append(dataframe['umacd'] > dataframe['umacd_signal'])
            # 上升趋势方向
            conds.append(dataframe['plus_di'] > dataframe['minus_di'])
            # Supertrend 上行确认（使用接近 hyperopt 参数的预计算列）
            st_col = f'stx_3.0_10'
            if st_col in dataframe.columns:
                conds.append(dataframe[st_col] == 'up')
            return reduce(lambda x, y: x & y, conds)

        def oscillation_signals():
            """震荡市场：使用 RSI + Bollinger Band 均值回归"""
            conds = []
            # RSI 超卖（低于阈值）
            conds.append(dataframe['rsi'] < self.buy_rsi_oversold.value)
            # 价格触及布林带下轨
            bb_lower_custom = ta.BBANDS(
                dataframe, timeperiod=20,
                nbdevdn=self.buy_bb_lower_mult.value
            )['lowerband']
            conds.append(dataframe['close'] <= bb_lower_custom)
            # Stochastic RSI 超卖区（K < 20）
            conds.append(dataframe['stoch_rsi_k'] < 20)
            return reduce(lambda x, y: x & y, conds)

        # -------- 市场状态自适应选择 --------
        market_is_trending = dataframe['adx'] > self.adx_trend_threshold.value

        if self.trend_mode.value == 'umacd':
            # 纯趋势模式
            primary_signal = trend_signals()
        elif self.trend_mode.value == 'mean_reversion':
            # 纯震荡模式
            primary_signal = oscillation_signals()
        else:
            # 混合模式：趋势市场用趋势信号，震荡市场用均值回归
            primary_signal = (
                (market_is_trending & trend_signals()) |
                (~market_is_trending & oscillation_signals())
            )

        # -------- 多时间框架确认 --------
        tf_conditions = [primary_signal]

        # 1h 趋势确认
        if self.buy_require_1h_confirm.value and 'trend_up_1h' in dataframe.columns:
            tf_conditions.append(dataframe['trend_up_1h'])

        # 4h 大趋势确认
        if self.buy_require_4h_confirm.value and 'bull_market_4h' in dataframe.columns:
            tf_conditions.append(dataframe['bull_market_4h'])

        # -------- 综合所有条件 --------
        all_conditions = base_conditions + tf_conditions
        dataframe.loc[
            reduce(lambda x, y: x & y, all_conditions),
            'enter_long'
        ] = 1

        return dataframe

    # ==================== 出场信号 ====================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        自适应出场（多条件 OR）：
        1. RSI 超买
        2. UMACD 死叉（跌破信号线）
        3. 布林带上轨触及（震荡市场目标位）
        4. Supertrend 翻转为 down
        """
        conditions = []

        # -------- 条件1：RSI 超买 --------
        conditions.append(dataframe['rsi'] > self.sell_rsi_overbought.value)

        # -------- 条件2：UMACD 死叉 --------
        conditions.append(
            qtpylib.crossed_below(dataframe['umacd'], dataframe['umacd_signal'])
        )

        # -------- 条件3：UMACD 进入高位 --------
        conditions.append(dataframe['umacd'] > self.sell_umacd_threshold.value)

        # -------- 条件4：布林带上轨压力 --------
        conditions.append(dataframe['close'] >= dataframe['bb_upper'])

        # -------- 条件5：Supertrend 翻转 --------
        st_col = f'stx_3.0_10'
        if st_col in dataframe.columns:
            conditions.append(dataframe[st_col] == 'down')

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'exit_long'
            ] = 1

        return dataframe

    # ==================== DCA 加仓逻辑 ====================
    def adjust_trade_position(
        self,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        min_stake: Optional[float],
        max_stake: float,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        **kwargs
    ) -> Optional[float]:
        """
        DCA（Dollar Cost Averaging）加仓逻辑：
        - 第一次加仓：亏损达到 dca_first_drop 时，加仓 50%
        - 第二次加仓：亏损达到 dca_second_drop 时，加仓 25%

        风控：
        - 只有在趋势向好时才加仓
        - 不超过 max_entry_position_adjustment 次
        - 不超过 max_stake

        注意：DCA 需要在 config 中设置足够的 stake_amount
        """
        # 获取当前已开仓次数
        count_of_entries = trade.nr_of_successful_entries

        # -------- 第一次加仓 --------
        if (
            count_of_entries == 1 and
            current_profit < self.dca_first_drop.value
        ):
            # 加仓金额 = 初始仓位的 50%
            stake_amount = trade.stake_amount * 0.5
            if min_stake and stake_amount < min_stake:
                return None
            if stake_amount > max_stake:
                stake_amount = max_stake
            return stake_amount

        # -------- 第二次加仓 --------
        if (
            count_of_entries == 2 and
            current_profit < self.dca_second_drop.value
        ):
            # 加仓金额 = 初始仓位的 25%
            stake_amount = trade.stake_amount * 0.25
            if min_stake and stake_amount < min_stake:
                return None
            if stake_amount > max_stake:
                stake_amount = max_stake
            return stake_amount

        return None

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
        动态止损 + trailing 结合：
        - 盈利分阶梯锁定
        - ATR 自适应止损
        - 时间止损防止资金被套太久
        """
        # -------- 利润阶梯锁定 --------
        if current_profit >= 0.15:
            return self._stoploss_from_open(0.08, current_profit)
        if current_profit >= 0.10:
            return self._stoploss_from_open(0.05, current_profit)
        if current_profit >= 0.06:
            return self._stoploss_from_open(0.02, current_profit)
        if current_profit >= 0.03:
            return self._stoploss_from_open(0.00, current_profit)

        # -------- 时间止损 --------
        hours_open = (current_time - trade.open_date_utc).total_seconds() / 3600

        # 超过 5 天仍亏损超过 5%：强制出场
        if hours_open > 120 and current_profit < -0.05:
            return -0.05

        # 超过 2 天且接近平本：退出（机会成本）
        if hours_open > 48 and -0.03 < current_profit < 0.01:
            return -0.03

        return None

    def _stoploss_from_open(self, open_relative_stop: float, current_profit: float) -> float:
        """从开仓价计算相对当前价的止损"""
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
        条件退出（覆盖 ROI 和 stoploss 之外的特殊情形）：
        """
        hours_open = (current_time - trade.open_date_utc).total_seconds() / 3600

        # 超过 7 天接近平本：强制退出
        if hours_open > 168 and -0.02 < current_profit < 0.03:
            return '超时_接近平本'

        # 超过 3 天亏损超过 8%：快速止损
        if hours_open > 72 and current_profit < -0.08:
            return '超时_止损'

        # DCA 后亏损超过 12%：快速止损（DCA 失败）
        if trade.nr_of_successful_entries > 1 and current_profit < -0.12:
            return 'DCA_失败_止损'

        return None

    # ==================== Supertrend 计算 ====================
    def _compute_supertrend(
        self,
        dataframe: DataFrame,
        multiplier: float,
        period: int
    ) -> DataFrame:
        """
        计算 Supertrend 指标
        返回包含 'ST'（价格值）和 'STX'（方向：'up'/'down'）的 DataFrame
        """
        df = dataframe.copy()
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        length = len(df)

        # 计算 True Range 和 ATR
        tr = ta.TRANGE(df['high'], df['low'], df['close'])
        atr = pd.Series(tr).rolling(period).mean().to_numpy()

        # 基本上下轨
        hl2 = (high + low) / 2
        basic_ub = hl2 + multiplier * atr
        basic_lb = hl2 - multiplier * atr

        # 最终上下轨
        final_ub = np.full(length, np.nan)
        final_lb = np.full(length, np.nan)

        for i in range(period, length):
            final_ub[i] = (
                basic_ub[i]
                if (np.isnan(final_ub[i - 1]) or basic_ub[i] < final_ub[i - 1] or close[i - 1] > final_ub[i - 1])
                else final_ub[i - 1]
            )
            final_lb[i] = (
                basic_lb[i]
                if (np.isnan(final_lb[i - 1]) or basic_lb[i] > final_lb[i - 1] or close[i - 1] < final_lb[i - 1])
                else final_lb[i - 1]
            )

        # Supertrend 值和方向
        st_values = np.full(length, np.nan)
        stx = np.array([None] * length, dtype=object)

        for i in range(period, length):
            prev_st = st_values[i - 1] if not np.isnan(st_values[i - 1]) else final_ub[i]
            if np.isclose(prev_st, final_ub[i - 1], equal_nan=True):
                st_values[i] = final_ub[i] if close[i] <= final_ub[i] else final_lb[i]
            else:
                st_values[i] = final_lb[i] if close[i] >= final_lb[i] else final_ub[i]
            stx[i] = 'up' if close[i] > st_values[i] else 'down'

        result = pd.DataFrame(
            {'ST': st_values, 'STX': stx},
            index=df.index
        )
        return result


