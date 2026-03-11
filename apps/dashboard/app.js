const DATA_PATHS = ['./data/validation_dashboard_latest.json', '/api/validation-summary'];

async function loadDashboard() {
    try {
        const payload = await fetchSummary();
        renderDashboard(payload);
    } catch (error) {
        console.error('Failed to load validation dashboard:', error);
        document.getElementById('generated-at').innerText = 'Failed to load validation payload';
    }
}

async function fetchSummary() {
    for (const path of DATA_PATHS) {
        try {
            const response = await fetch(path, { cache: 'no-store' });
            if (!response.ok) {
                continue;
            }
            return await response.json();
        } catch (error) {
            console.warn(`Fetch failed for ${path}`, error);
        }
    }
    throw new Error('No validation data source available');
}

function money(value) {
    return `${Number(value || 0).toFixed(2)} USD`;
}

function pct(value) {
    return `${(Number(value || 0) * 100).toFixed(2)}%`;
}

function boolLabel(value, positive = 'YES', negative = 'NO') {
    return value ? positive : negative;
}

function renderDashboard(payload) {
    const summary = payload.summary;
    document.getElementById('generated-at').innerText = `Updated ${payload.generated_at_rome}`;
    document.getElementById('timezone-note').innerText = payload.log_timezone_note;

    document.getElementById('overall-status').innerText = payload.overall_status.toUpperCase();
    document.getElementById('overall-detail').innerText = `${summary.bots_running}/${summary.total_bots} bots running | guards healthy: ${boolLabel(summary.all_guards_healthy)}`;
    document.getElementById('total-wallet').innerText = money(summary.total_wallet_usd);
    document.getElementById('allocated-wallet').innerText = money(summary.total_allocated_usd);
    document.getElementById('total-trades').innerText = String(summary.total_trades);
    document.getElementById('activity-detail').innerText = `${summary.total_open_positions} open positions across both bots`;

    const panels = document.getElementById('bot-panels');
    panels.innerHTML = '';
    payload.bots.forEach((bot) => panels.appendChild(renderBotCard(bot)));
}

function renderBotCard(bot) {
    const template = document.getElementById('bot-template');
    const node = template.content.cloneNode(true);

    node.querySelector('.bot-market').innerText = bot.market_type.toUpperCase();
    node.querySelector('.bot-name').innerText = bot.label;

    const statusPill = node.querySelector('.status-pill');
    statusPill.innerText = bot.state.toUpperCase();
    statusPill.className = `status-pill ${bot.state === 'running' ? 'status-ok' : 'status-bad'}`;

    node.querySelector('.strategy-value').innerText = bot.strategy;
    node.querySelector('.mode-value').innerText = `${bot.timeframe} | ${bot.margin_mode}`;
    node.querySelector('.wallet-value').innerText = money(bot.wallet_total_usd);
    node.querySelector('.allocated-value').innerText = `${money(bot.wallet_allocated_usd)} (${pct(bot.tradable_balance_ratio)})`;
    node.querySelector('.trades-value').innerText = `${bot.trade_count} total / ${bot.open_positions} open`;
    node.querySelector('.scanner-value').innerText = `${bot.scanner_selected_count}/${bot.scanner_candidate_count} live`;

    node.querySelector('.dry-run-value').innerText = boolLabel(bot.dry_run);
    node.querySelector('.guard-value').innerText = String(bot.guard_status || '--').toUpperCase();
    node.querySelector('.preflight-value').innerText = boolLabel(bot.preflight_approved);
    node.querySelector('.first-trade-value').innerText = bot.waiting_for_first_trade ? 'WAITING' : 'STARTED';

    node.querySelector('.timeframe-value').innerText = bot.timeframe;
    node.querySelector('.margin-value').innerText = bot.short_allowed ? `${bot.margin_mode} / short` : bot.margin_mode;
    node.querySelector('.winrate-value').innerText = pct(bot.winrate);
    node.querySelector('.drawdown-value').innerText = pct(bot.current_drawdown_ratio);

    const pairsList = node.querySelector('.pairs-list');
    if (!bot.top_pairs.length) {
        pairsList.innerHTML = '<span class="chip chip-muted">No approved pairs yet</span>';
    } else {
        bot.top_pairs.forEach((pair) => {
            const chip = document.createElement('span');
            chip.className = 'chip';
            chip.innerText = pair;
            pairsList.appendChild(chip);
        });
    }

    const heartbeatLine = node.querySelector('.heartbeat-line');
    heartbeatLine.innerText = bot.last_heartbeat_rome
        ? `Latest heartbeat (Rome): ${bot.last_heartbeat_rome}`
        : 'No heartbeat found in log yet';

    const issuesList = node.querySelector('.issues-list');
    const notes = bot.issues.length ? bot.issues : ['No active issues detected'];
    notes.forEach((item) => {
        const li = document.createElement('li');
        li.innerText = item;
        issuesList.appendChild(li);
    });

    return node;
}

document.addEventListener('DOMContentLoaded', loadDashboard);
window.setInterval(loadDashboard, 60000);