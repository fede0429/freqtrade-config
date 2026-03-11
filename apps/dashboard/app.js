const DATA_PATHS = [
    '/api/validation-summary',
    '/validation/data/validation_dashboard_latest.json',
    './data/validation_dashboard_latest.json',
];

async function loadDashboard() {
    try {
        clearErrorState();
        const payload = await fetchSummary();
        renderDashboard(payload);
    } catch (error) {
        console.error('Failed to load validation dashboard:', error);
        showErrorState(error.message || 'Failed to load validation payload.');
    }
}

async function fetchSummary() {
    let lastError = null;

    for (const path of DATA_PATHS) {
        try {
            const response = await fetch(path, { cache: 'no-store' });
            if (!response.ok) {
                lastError = new Error(`Validation feed responded with ${response.status} for ${path}`);
                continue;
            }

            const payload = await response.json();
            validatePayload(payload, path);
            return payload;
        } catch (error) {
            console.warn(`Fetch failed for ${path}`, error);
            lastError = error;
        }
    }

    throw lastError || new Error('No validation data source available.');
}

function validatePayload(payload, path) {
    if (!payload || typeof payload !== 'object') {
        throw new Error(`Validation payload from ${path} is empty.`);
    }
    if (!payload.summary || typeof payload.summary !== 'object') {
        throw new Error(`Validation payload from ${path} is missing summary.`);
    }
    if (!Array.isArray(payload.bots)) {
        throw new Error(`Validation payload from ${path} is missing bot cards.`);
    }
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

function showErrorState(message) {
    const banner = document.getElementById('error-banner');
    const messageNode = document.getElementById('error-message');
    const generatedAt = document.getElementById('generated-at');

    generatedAt.innerText = 'Validation feed unavailable';
    messageNode.innerText = `${message} Auto-retry is still active.`;
    banner.hidden = false;

    document.getElementById('empty-state').hidden = false;
    document.getElementById('bot-panels').innerHTML = '';
}

function clearErrorState() {
    document.getElementById('error-banner').hidden = true;
    document.getElementById('empty-state').hidden = true;
}

function renderDashboard(payload) {
    const summary = payload.summary || {};
    const bots = Array.isArray(payload.bots) ? payload.bots : [];

    document.getElementById('generated-at').innerText = payload.generated_at_rome
        ? `Updated ${payload.generated_at_rome}`
        : 'Validation feed loaded';
    document.getElementById('timezone-note').innerText = payload.log_timezone_note || 'Timezone note unavailable';

    document.getElementById('overall-status').innerText = String(payload.overall_status || '--').toUpperCase();
    document.getElementById('overall-detail').innerText = `${Number(summary.bots_running || 0)}/${Number(summary.total_bots || 0)} bots running | guards healthy: ${boolLabel(summary.all_guards_healthy)}`;
    document.getElementById('total-wallet').innerText = money(summary.total_wallet_usd);
    document.getElementById('allocated-wallet').innerText = money(summary.total_allocated_usd);
    document.getElementById('total-trades').innerText = String(summary.total_trades || 0);
    document.getElementById('activity-detail').innerText = `${Number(summary.total_open_positions || 0)} open positions across both bots`;

    const panels = document.getElementById('bot-panels');
    panels.innerHTML = '';

    if (!bots.length) {
        document.getElementById('empty-state').hidden = false;
        return;
    }

    document.getElementById('empty-state').hidden = true;
    bots.forEach((bot) => panels.appendChild(renderBotCard(bot)));
}

function renderBotCard(bot) {
    const template = document.getElementById('bot-template');
    const node = template.content.cloneNode(true);

    node.querySelector('.bot-market').innerText = String(bot.market_type || '--').toUpperCase();
    node.querySelector('.bot-name').innerText = bot.label || '--';

    const statusPill = node.querySelector('.status-pill');
    const state = String(bot.state || 'unknown').toLowerCase();
    statusPill.innerText = state.toUpperCase();
    statusPill.className = `status-pill ${state === 'running' ? 'status-ok' : 'status-bad'}`;

    node.querySelector('.strategy-value').innerText = bot.strategy || '--';
    node.querySelector('.mode-value').innerText = `${bot.timeframe || '--'} | ${bot.margin_mode || '--'}`;
    node.querySelector('.wallet-value').innerText = money(bot.wallet_total_usd);
    node.querySelector('.allocated-value').innerText = `${money(bot.wallet_allocated_usd)} (${pct(bot.tradable_balance_ratio)})`;
    node.querySelector('.trades-value').innerText = `${Number(bot.trade_count || 0)} total / ${Number(bot.open_positions || 0)} open`;
    node.querySelector('.scanner-value').innerText = `${Number(bot.scanner_selected_count || 0)}/${Number(bot.scanner_candidate_count || 0)} live`;

    node.querySelector('.dry-run-value').innerText = boolLabel(bot.dry_run);
    node.querySelector('.guard-value').innerText = String(bot.guard_status || '--').toUpperCase();
    node.querySelector('.preflight-value').innerText = boolLabel(bot.preflight_approved);
    node.querySelector('.first-trade-value').innerText = bot.waiting_for_first_trade ? 'WAITING' : 'STARTED';

    node.querySelector('.timeframe-value').innerText = bot.timeframe || '--';
    node.querySelector('.margin-value').innerText = bot.short_allowed ? `${bot.margin_mode || '--'} / short` : (bot.margin_mode || '--');
    node.querySelector('.winrate-value').innerText = pct(bot.winrate);
    node.querySelector('.drawdown-value').innerText = pct(bot.current_drawdown_ratio);

    const pairsList = node.querySelector('.pairs-list');
    const topPairs = Array.isArray(bot.top_pairs) ? bot.top_pairs : [];
    if (!topPairs.length) {
        pairsList.innerHTML = '<span class="chip chip-muted">No approved pairs yet</span>';
    } else {
        topPairs.forEach((pair) => {
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
    const notes = Array.isArray(bot.issues) && bot.issues.length ? bot.issues : ['No active issues detected'];
    notes.forEach((item) => {
        const li = document.createElement('li');
        li.innerText = item;
        issuesList.appendChild(li);
    });

    return node;
}

document.addEventListener('DOMContentLoaded', loadDashboard);
window.setInterval(loadDashboard, 60000);