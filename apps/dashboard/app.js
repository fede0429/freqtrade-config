async function loadReport() {
    try {
        // In a real scenario, this would fetch from an API or list command.
        // For this demo, we'll try to find the reports in the mapped directory.
        const response = await fetch('/api/latest-report');
        const report = await response.json();
        renderDashboard(report);
    } catch (error) {
        console.error('Failed to load report:', error);
        document.getElementById('report-date').innerText = 'Error loading report';
    }
}

function renderDashboard(report) {
    const s = report.summary;
    
    document.getElementById('report-date').innerText = `Report Date: ${s.date}`;
    
    const netPnlEl = document.getElementById('net-pnl');
    netPnlEl.innerText = `${s.net_pnl.toFixed(2)} USD`;
    netPnlEl.className = `card-value ${s.net_pnl >= 0 ? 'success' : 'error'}`;
    
    document.getElementById('pnl-split').innerText = `${s.realized_pnl.toFixed(2)} / ${s.unrealized_pnl.toFixed(2)} USD`;
    document.getElementById('trade-count').innerText = `${s.open_positions} Open / ${s.closed_trades} Closed`;
    document.getElementById('market-regime').innerText = `${report.scanner.market_regime.regime} (${report.scanner.market_regime.market_pressure})`;

    // Strategy Table
    const tableBody = document.querySelector('#strategy-table tbody');
    tableBody.innerHTML = '';
    report.strategies.forEach(st => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${st.name}</td>
            <td>${st.stage}</td>
            <td>${st.exposure_usd.toFixed(2)}</td>
            <td class="${st.realized_pnl >= 0 ? 'success' : 'error'}">${st.realized_pnl.toFixed(2)}</td>
            <td><span class="status-badge status-${st.status}">${st.status}</span></td>
        `;
        tableBody.appendChild(tr);
    });

    // Risk
    const ddRatio = report.risk.current_drawdown_ratio;
    const maxDD = report.risk.max_drawdown_ratio;
    document.getElementById('current-drawdown').innerText = `${(ddRatio * 100).toFixed(2)}%`;
    const fillPercent = Math.min((ddRatio / maxDD) * 100, 100);
    document.getElementById('drawdown-fill').style.width = `${fillPercent}%`;
    
    const guardBadge = document.getElementById('guard-status');
    guardBadge.innerText = report.risk.guard_status.toUpperCase();
    guardBadge.className = `status-badge ${report.risk.guard_status === 'healthy' ? 'status-active' : 'status-idle'}`;

    // Rankings
    renderList('winners-list', report.top_winners);
    renderList('losers-list', report.top_losers);

    // Chart
    initChart(report);
}

function renderList(id, data) {
    const ul = document.getElementById(id);
    ul.innerHTML = '';
    data.forEach(item => {
        const li = document.createElement('li');
        li.style.marginBottom = '0.5rem';
        li.innerHTML = `
            <span style="color: var(--text-dim)">${item.pair}</span> 
            <span style="float: right; font-weight: 600;">${item.pnl_usd.toFixed(2)}</span>
        `;
        ul.appendChild(li);
    });
}

function initChart(report) {
    const ctx = document.getElementById('pnl-chart').getContext('2d');
    
    // Mocking historical data based on current report to show a trend
    const labels = ['Launch', '02:00', '04:00', '08:00', '12:00', 'Current'];
    const pnlData = [0, 5, -2, 10, report.summary.net_pnl * 0.8, report.summary.net_pnl];

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cumulative PnL',
                data: pnlData,
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8b949e' } },
                x: { grid: { display: false }, ticks: { color: '#8b949e' } }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', loadReport);
