#!/usr/bin/env bash
# ============================================================
# auto_hyperopt.sh — 自动 Hyperopt 循环脚本
# 功能：每周自动运行，对指定策略进行参数优化
# 使用方法：
#   手动运行：    bash scripts/auto_hyperopt.sh
#   设置 cron：   0 2 * * 0 /path/to/scripts/auto_hyperopt.sh
#   指定策略：    STRATEGY=UniversalMACD_V2 bash scripts/auto_hyperopt.sh
# ============================================================

set -euo pipefail  # 严格模式：错误立即退出

# ============================================================
# 配置区域（根据实际情况修改）
# ============================================================

# 基础路径
FREQTRADE_DIR="${FREQTRADE_DIR:-/freqtrade}"
USER_DATA_DIR="${USER_DATA_DIR:-${FREQTRADE_DIR}/user_data}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 策略配置
STRATEGY="${STRATEGY:-AdaptiveMetaStrategy}"
CONFIG="${CONFIG:-${USER_DATA_DIR}/config_spot.json}"
TIMEFRAME="${TIMEFRAME:-15m}"

# Hyperopt 配置
EPOCHS="${EPOCHS:-300}"        # 优化迭代次数
JOBS="${JOBS:--1}"             # 并行核数（-1 = 全部）
SPACES="${SPACES:-buy sell roi stoploss trailing}"  # 优化空间

# 数据配置
DAYS_DATA="${DAYS_DATA:-180}"  # 历史数据天数（6个月）
TIMERANGE=""  # 留空则自动计算

# Loss 函数列表（按优先级排列）
LOSS_FUNCTIONS=(
    "SharpeHyperOptLoss"
    "SortinoHyperOptLoss"
    "CalmarHyperOptLoss"
)

# Telegram 配置（用于通知）
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-CHANGE_ME}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-CHANGE_ME}"

# 日志配置
LOG_DIR="${PROJECT_DIR}/logs/hyperopt"
REPORT_DIR="${PROJECT_DIR}/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/hyperopt_${TIMESTAMP}.log"

# ============================================================
# 工具函数
# ============================================================

# 彩色日志输出
log_info()    { echo "[$(date '+%H:%M:%S')] [INFO]  $*" | tee -a "$LOG_FILE"; }
log_success() { echo "[$(date '+%H:%M:%S')] [成功]  $*" | tee -a "$LOG_FILE"; }
log_warn()    { echo "[$(date '+%H:%M:%S')] [警告]  $*" | tee -a "$LOG_FILE"; }
log_error()   { echo "[$(date '+%H:%M:%S')] [错误]  $*" | tee -a "$LOG_FILE" >&2; }

# 发送 Telegram 通知
send_telegram() {
    local message="$1"
    if [[ "$TELEGRAM_TOKEN" == "CHANGE_ME" ]]; then
        log_warn "Telegram 未配置，跳过通知"
        return 0
    fi
    curl -s -X POST \
        "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${message}" \
        -d "parse_mode=HTML" \
        > /dev/null 2>&1 || log_warn "Telegram 通知发送失败"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 '$1' 未找到，请先安装"
        exit 1
    fi
}

# 运行 freqtrade 命令（支持 Docker 和本地两种模式）
run_freqtrade() {
    if command -v docker &> /dev/null && docker ps | grep -q "freqtrade"; then
        # Docker 模式
        docker exec freqtrade-hyperopt freqtrade "$@"
    else
        # 本地模式
        freqtrade "$@"
    fi
}

# ============================================================
# 初始化
# ============================================================
setup() {
    log_info "============================================================"
    log_info "  Freqtrade 自动 Hyperopt 循环脚本"
    log_info "  策略：${STRATEGY}"
    log_info "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
    log_info "============================================================"

    # 创建目录
    mkdir -p "$LOG_DIR" "$REPORT_DIR"

    # 检查必要命令
    check_command freqtrade || check_command docker

    send_telegram "🚀 <b>Hyperopt 开始</b>
策略：${STRATEGY}
时间：$(date '+%Y-%m-%d %H:%M:%S')
轮次：${EPOCHS}
优化空间：${SPACES}"
}

# ============================================================
# 步骤1：下载最新历史数据
# ============================================================
download_data() {
    log_info "步骤1：下载最新历史数据（${DAYS_DATA} 天）..."

    # 计算时间范围
    local start_date
    start_date=$(date -d "${DAYS_DATA} days ago" '+%Y%m%d' 2>/dev/null || \
                 date -v "-${DAYS_DATA}d" '+%Y%m%d' 2>/dev/null || \
                 python3 -c "from datetime import datetime, timedelta; print((datetime.now() - timedelta(days=${DAYS_DATA})).strftime('%Y%m%d'))")
    TIMERANGE="${start_date}-"

    log_info "时间范围：${TIMERANGE}"

    # 下载主时间框架数据
    if freqtrade download-data \
        --config "$CONFIG" \
        --timerange "$TIMERANGE" \
        --timeframes "$TIMEFRAME" 1h 4h \
        >> "$LOG_FILE" 2>&1; then
        log_success "历史数据下载完成"
    else
        log_warn "数据下载失败或部分失败，继续使用现有数据"
    fi
}

# ============================================================
# 步骤2：运行 Hyperopt 优化（多种 loss function）
# ============================================================
run_hyperopt() {
    local loss_function="$1"
    local epoch_count="${2:-$EPOCHS}"

    log_info "步骤2：运行 Hyperopt（Loss: ${loss_function}，轮次: ${epoch_count}）..."

    local hyperopt_result_dir="${USER_DATA_DIR}/hyperopt_results"
    mkdir -p "$hyperopt_result_dir"

    local hyperopt_args=(
        hyperopt
        --config "$CONFIG"
        --strategy "$STRATEGY"
        --hyperopt-loss "$loss_function"
        --spaces $SPACES
        --epochs "$epoch_count"
        -j "$JOBS"
        --timerange "$TIMERANGE"
        --no-color
        --print-json
    )

    log_info "执行命令：freqtrade ${hyperopt_args[*]}"

    if freqtrade "${hyperopt_args[@]}" \
        > "${LOG_DIR}/hyperopt_${loss_function}_${TIMESTAMP}.json" 2>> "$LOG_FILE"; then
        log_success "Hyperopt 完成（${loss_function}）"
        return 0
    else
        log_error "Hyperopt 失败（${loss_function}）"
        return 1
    fi
}

# ============================================================
# 步骤3：提取最优参数
# ============================================================
extract_best_params() {
    local loss_function="$1"
    local result_file="${LOG_DIR}/hyperopt_${loss_function}_${TIMESTAMP}.json"

    if [[ ! -f "$result_file" ]]; then
        log_warn "结果文件不存在：${result_file}"
        return 1
    fi

    # 使用 Python 解析 JSON 结果（freqtrade hyperopt-show 更方便）
    local best_params
    best_params=$(freqtrade hyperopt-show \
        --config "$CONFIG" \
        --strategy "$STRATEGY" \
        --best \
        -n -1 \
        2>> "$LOG_FILE" || echo "解析失败")

    log_info "最优参数（${loss_function}）：${best_params}"

    # 保存到文件
    local params_file="${REPORT_DIR}/best_params_${STRATEGY}_${loss_function}_${TIMESTAMP}.txt"
    echo "============================================================" > "$params_file"
    echo "  策略：${STRATEGY}" >> "$params_file"
    echo "  Loss：${loss_function}" >> "$params_file"
    echo "  时间：$(date '+%Y-%m-%d %H:%M:%S')" >> "$params_file"
    echo "============================================================" >> "$params_file"
    echo "$best_params" >> "$params_file"

    log_success "参数已保存到：${params_file}"
}

# ============================================================
# 步骤4：回测验证
# ============================================================
run_backtest() {
    log_info "步骤4：回测验证..."

    local backtest_result="${REPORT_DIR}/backtest_${STRATEGY}_${TIMESTAMP}.txt"

    if freqtrade backtesting \
        --config "$CONFIG" \
        --strategy "$STRATEGY" \
        --timerange "$TIMERANGE" \
        --export trades \
        --export-filename "${USER_DATA_DIR}/backtest_results/backtest_${STRATEGY}_${TIMESTAMP}.json" \
        > "$backtest_result" 2>&1; then
        log_success "回测完成"
        # 提取关键指标
        local total_profit wins losses
        total_profit=$(grep "Total profit" "$backtest_result" | tail -1 || echo "N/A")
        wins=$(grep "Wins" "$backtest_result" | tail -1 || echo "N/A")
        log_info "回测结果：${total_profit} | ${wins}"
        return 0
    else
        log_error "回测失败"
        return 1
    fi
}

# ============================================================
# 步骤5：生成 Markdown 报告
# ============================================================
generate_report() {
    log_info "步骤5：生成优化报告..."

    local report_file="${REPORT_DIR}/hyperopt_report_${STRATEGY}_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Hyperopt 优化报告

**策略：** ${STRATEGY}
**时间：** $(date '+%Y-%m-%d %H:%M:%S')
**历史数据：** ${DAYS_DATA} 天（时间范围：${TIMERANGE}）
**迭代轮次：** ${EPOCHS}
**优化空间：** ${SPACES}

---

## 运行摘要

| Loss 函数 | 状态 | 参数文件 |
|-----------|------|----------|
EOF

    for loss in "${LOSS_FUNCTIONS[@]}"; do
        local params_file="${REPORT_DIR}/best_params_${STRATEGY}_${loss}_${TIMESTAMP}.txt"
        if [[ -f "$params_file" ]]; then
            echo "| ${loss} | ✅ 成功 | ${params_file} |" >> "$report_file"
        else
            echo "| ${loss} | ❌ 失败 | - |" >> "$report_file"
        fi
    done

    cat >> "$report_file" << EOF

---

## 回测验证

$(cat "${REPORT_DIR}/backtest_${STRATEGY}_${TIMESTAMP}.txt" 2>/dev/null || echo "回测结果未找到")

---

## 下一步建议

1. 检查各 Loss 函数的最优参数，选择最适合的
2. 将最优参数复制到策略文件的 \`buy_params\`/\`sell_params\` 中
3. 在 dry_run 模式下运行至少 7 天验证
4. 观察实盘表现后决定是否切换

---

*生成时间：$(date '+%Y-%m-%d %H:%M:%S')*
EOF

    log_success "报告已生成：${report_file}"
    echo "$report_file"
}

# ============================================================
# 步骤6：发送最终报告
# ============================================================
send_final_report() {
    local report_file="$1"
    local status="$2"

    local emoji
    if [[ "$status" == "success" ]]; then
        emoji="✅"
    else
        emoji="⚠️"
    fi

    local report_summary=""
    if [[ -f "$report_file" ]]; then
        # 截取报告前 500 字符
        report_summary=$(head -c 500 "$report_file")
    fi

    send_telegram "${emoji} <b>Hyperopt 完成</b>
策略：${STRATEGY}
状态：${status}
时间：$(date '+%Y-%m-%d %H:%M:%S')

<pre>${report_summary}</pre>"
}

# ============================================================
# 主流程
# ============================================================
main() {
    local overall_status="success"

    # 初始化
    setup

    # 步骤1：下载数据
    download_data || log_warn "数据下载跳过"

    # 步骤2-3：对每种 Loss function 运行 Hyperopt
    local best_loss=""
    for loss in "${LOSS_FUNCTIONS[@]}"; do
        log_info "-------- 开始优化（${loss}）--------"
        if run_hyperopt "$loss" "$EPOCHS"; then
            extract_best_params "$loss" || true
            if [[ -z "$best_loss" ]]; then
                best_loss="$loss"  # 以第一个成功的作为主要结果
            fi
        else
            log_error "Loss ${loss} 优化失败"
            overall_status="partial"
        fi
        log_info "-------- 完成优化（${loss}）--------"
        # 等待 30 秒冷却（避免 API 频率限制）
        sleep 30
    done

    # 步骤4：回测验证
    run_backtest || overall_status="partial"

    # 步骤5：生成报告
    local report_file
    report_file=$(generate_report)

    # 步骤6：发送通知
    send_final_report "$report_file" "$overall_status"

    log_info "============================================================"
    log_info "  自动 Hyperopt 循环完成"
    log_info "  状态：${overall_status}"
    log_info "  日志：${LOG_FILE}"
    log_info "  报告：${report_file}"
    log_info "============================================================"

    # 根据状态返回退出码
    if [[ "$overall_status" == "success" ]]; then
        exit 0
    else
        exit 1
    fi
}

# ============================================================
# 入口
# ============================================================
# 捕获中断信号
trap 'log_error "脚本被中断"; send_telegram "❌ Hyperopt 被中断：${STRATEGY}"; exit 1' SIGINT SIGTERM

# 运行主流程
main "$@"
