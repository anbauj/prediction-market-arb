// Main JavaScript Application Controller for Delta-X Arbitrage Terminal

let state = {
    capitalTarget: 1000,
    opportunities: [],
    matchedPairs: [],
    markets: [],
    paperTrades: [],
    paperAnalytics: {},
    stage5Status: {},
    selectedOpp: null,
    riskFilter: 'ALL',
    autoPoll: true,
    pollTimer: null
};

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initEventListeners();
    fetchData();
    startAutoPoll();
});

// Bind global functions to window so inline onclick attributes work flawlessly!
window.setPairStatus = setPairStatus;
window.executePaperTradeById = executePaperTradeById;
window.executePaperTrade = executePaperTrade;

function initNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

            tab.classList.add('active');
            const targetId = tab.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });
}

function initEventListeners() {
    // Capital Slider
    const slider = document.getElementById('capital-slider');
    const valDisplay = document.getElementById('capital-val');
    slider.addEventListener('input', (e) => {
        state.capitalTarget = parseFloat(e.target.value);
        valDisplay.textContent = `$${state.capitalTarget.toLocaleString()}`;
        fetchOpportunities();
    });

    // Refresh Button
    document.getElementById('btn-refresh').addEventListener('click', () => {
        fetch('/api/refresh', { method: 'POST' }).then(() => fetchData());
    });

    // Auto Poll Switch
    const autoSwitch = document.getElementById('toggle-autopoll');
    autoSwitch.addEventListener('change', (e) => {
        state.autoPoll = e.target.checked;
        if (state.autoPoll) startAutoPoll();
        else stopAutoPoll();
    });

    // Risk Filter Pills
    document.querySelectorAll('.filter-pills .pill').forEach(pill => {
        pill.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
            e.target.classList.add('active');
            state.riskFilter = e.target.getAttribute('data-filter');
            renderOpportunitiesTable();
        });
    });

    // Stage 5 Buttons
    document.getElementById('btn-unlock-stage5').addEventListener('click', () => {
        fetch('/api/stage5/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'UNLOCK' })
        }).then(() => fetchStage5Status());
    });

    document.getElementById('btn-kill-switch').addEventListener('click', () => {
        alert("EMERGENCY KILL SWITCH TRIGGERED: All execution routines halted.");
    });
}

function startAutoPoll() {
    stopAutoPoll();
    state.pollTimer = setInterval(() => {
        if (state.autoPoll) {
            fetchData();
        }
    }, 3000);
}

function stopAutoPoll() {
    if (state.pollTimer) {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
    }
}

async function fetchData() {
    await Promise.all([
        fetchMarkets(),
        fetchMatches(),
        fetchOpportunities(),
        fetchPaperAnalytics(),
        fetchStage5Status()
    ]);
}

async function fetchMarkets() {
    try {
        const res = await fetch('/api/markets');
        const data = await res.json();
        if (data.success) {
            state.markets = data.markets;
            document.getElementById('stat-total-markets').textContent = state.markets.length;
        }
    } catch (e) {
        console.error("Error fetching markets:", e);
    }
}

async function fetchMatches() {
    try {
        const res = await fetch('/api/matches');
        const data = await res.json();
        if (data.success) {
            state.matchedPairs = data.pairs;
            
            const verified = state.matchedPairs.filter(p => p.status === 'VERIFIED').length;
            const pending = state.matchedPairs.filter(p => p.status === 'PENDING_REVIEW').length;
            const rejected = state.matchedPairs.filter(p => p.status === 'REJECTED').length;

            document.getElementById('stat-verified-pairs').textContent = verified;
            document.getElementById('audit-pending').textContent = pending;
            document.getElementById('audit-verified').textContent = verified;
            document.getElementById('audit-rejected').textContent = rejected;
            document.getElementById('nav-pending-count').textContent = pending;

            renderMatchingTable();
        }
    } catch (e) {
        console.error("Error fetching matches:", e);
    }
}

async function fetchOpportunities() {
    try {
        const res = await fetch(`/api/opportunities?capital=${state.capitalTarget}`);
        const data = await res.json();
        if (data.success) {
            state.opportunities = data.opportunities;
            renderOpportunitiesTable();
        }
    } catch (e) {
        console.error("Error fetching opportunities:", e);
    }
}

async function fetchPaperAnalytics() {
    try {
        const res = await fetch('/api/paper/analytics');
        const data = await res.json();
        if (data.success) {
            state.paperAnalytics = data.analytics;
            state.paperTrades = data.trades;

            document.getElementById('stat-paper-pnl').textContent = `$${state.paperAnalytics.total_realized_profit.toFixed(2)}`;
            document.getElementById('paper-stat-total').textContent = state.paperAnalytics.total_trades;
            document.getElementById('paper-stat-winrate').textContent = `${state.paperAnalytics.win_rate}%`;
            document.getElementById('paper-stat-realized-pnl').textContent = `$${state.paperAnalytics.total_realized_profit.toFixed(2)}`;
            document.getElementById('paper-stat-gap').textContent = `${state.paperAnalytics.avg_edge_gap}%`;

            renderPaperTradesTable();
        }
    } catch (e) {
        console.error("Error fetching paper analytics:", e);
    }
}

async function fetchStage5Status() {
    try {
        const res = await fetch('/api/stage5/status');
        const data = await res.json();
        if (data.success) {
            state.stage5Status = data;
            
            const reqMet = data.paper_trades_count >= 5;
            document.getElementById('paper-progress-count').textContent = data.paper_trades_count;
            
            const chkItem = document.getElementById('chk-paper-track');
            const icon = document.getElementById('icon-paper-track');
            
            if (reqMet) {
                chkItem.classList.add('checked');
                icon.className = 'fa-solid fa-circle-check text-emerald';
            } else {
                chkItem.classList.remove('checked');
                icon.className = 'fa-solid fa-circle-xmark text-coral';
            }

            const btnUnlock = document.getElementById('btn-unlock-stage5');
            btnUnlock.disabled = !reqMet;
            
            const badge = document.getElementById('mode-badge-status');
            if (!data.locked) {
                badge.textContent = "LIVE EXECUTION UNLOCKED (SAFETY ACTIVE)";
                badge.className = "mode-badge mode-unlocked";
            }
        }
    } catch (e) {
        console.error("Error fetching stage 5 status:", e);
    }
}

function renderOpportunitiesTable() {
    const tbody = document.getElementById('opp-table-body');
    tbody.innerHTML = '';

    let filtered = state.opportunities;
    if (state.riskFilter === 'LOW') {
        filtered = filtered.filter(o => o.risk_rating === 'LOW');
    }

    document.getElementById('opp-count').textContent = filtered.length;

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:30px; color:var(--text-muted);">No arbitrage spreads detected for selected risk filter.</td></tr>`;
        return;
    }

    filtered.forEach(opp => {
        const tr = document.createElement('tr');
        if (state.selectedOpp && state.selectedOpp.opp_id === opp.opp_id) {
            tr.classList.add('selected');
        }

        const venueBuyClass = getVenueClass(opp.venue_buy);
        const venueSellClass = getVenueClass(opp.venue_sell);
        const riskClass = opp.risk_rating === 'LOW' ? 'green' : (opp.risk_rating === 'MEDIUM' ? 'amber' : 'red');

        tr.innerHTML = `
            <td class="title-cell">
                <strong>${opp.market_buy_title}</strong>
                <span>Buy ${opp.buy_outcome} vs Sell ${opp.sell_outcome}</span>
            </td>
            <td><span class="venue-badge ${venueBuyClass}">${opp.venue_buy}</span> <span class="font-mono">@ $${opp.avg_buy_price.toFixed(2)}</span></td>
            <td><span class="venue-badge ${venueSellClass}">${opp.venue_sell}</span> <span class="font-mono">@ $${opp.avg_sell_price.toFixed(2)}</span></td>
            <td class="font-mono">${opp.executable_size} sets</td>
            <td class="font-mono">$${opp.total_net_cost.toFixed(2)} <br><small class="text-muted">(Fees: $${(opp.fee_buy + opp.fee_sell + opp.gas_cost).toFixed(2)})</small></td>
            <td class="font-mono text-emerald"><strong>+$${opp.net_profit.toFixed(2)}</strong></td>
            <td>
                <span class="font-mono text-emerald"><strong>+${opp.net_roi}%</strong></span><br>
                <small class="text-muted">${opp.annualized_yield}% APR</small>
            </td>
            <td><span class="risk-tag ${riskClass}">${opp.risk_rating} RISK</span></td>
            <td>
                <button class="btn btn-primary btn-sm btn-paper-exec" data-oppid="${opp.opp_id}">
                    <i class="fa-solid fa-play"></i> Paper Trade
                </button>
            </td>
        `;

        tr.addEventListener('click', (e) => {
            if (e.target.closest('.btn-paper-exec')) return;
            state.selectedOpp = opp;
            renderOpportunitiesTable();
            renderDepthLadder(opp);
        });

        tr.querySelector('.btn-paper-exec').addEventListener('click', (e) => {
            e.stopPropagation();
            executePaperTrade(opp);
        });

        tbody.appendChild(tr);
    });

    if (filtered.length > 0 && !state.selectedOpp) {
        state.selectedOpp = filtered[0];
        renderDepthLadder(filtered[0]);
    }
}

function renderDepthLadder(opp) {
    const container = document.getElementById('depth-content');
    if (!opp) return;

    // Find market objects for venue links
    const mBuy = state.markets.find(m => m.venue === opp.venue_buy && m.title === opp.market_buy_title);
    const mSell = state.markets.find(m => m.venue === opp.venue_sell && m.title === opp.market_sell_title);

    const buyUrl = mBuy ? mBuy.url : '#';
    const sellUrl = mSell ? mSell.url : '#';

    let buyAsksHtml = '';
    if (mBuy && mBuy.order_book.asks) {
        buyAsksHtml = mBuy.order_book.asks.map(a => `
            <div class="ladder-row ask">
                <span>$${a.price.toFixed(2)}</span>
                <span>${a.size} qty</span>
            </div>
        `).join('');
    }

    let sellAsksHtml = '';
    if (mSell && mSell.order_book.asks) {
        sellAsksHtml = mSell.order_book.asks.map(a => `
            <div class="ladder-row ask">
                <span>$${a.price.toFixed(2)}</span>
                <span>${a.size} qty</span>
            </div>
        `).join('');
    }

    // Step-by-Step Action Blueprint Calculations
    const legACost = (opp.avg_buy_price * opp.executable_size + opp.fee_buy).toFixed(2);
    const legBCost = (opp.avg_sell_price * opp.executable_size + opp.fee_sell + opp.gas_cost).toFixed(2);

    container.innerHTML = `
        <div class="depth-detail-box">
            <!-- Explicit Step-by-Step Execution Plan & Platform Action Blueprint -->
            <div class="action-blueprint-card">
                <div class="blueprint-header">
                    <h4><i class="fa-solid fa-route text-emerald"></i> Explicit Trade Execution Steps</h4>
                    <span class="badge badge-emerald">Locked Arbitrage</span>
                </div>
                
                <div class="step-card">
                    <div class="step-number">1</div>
                    <div class="step-details">
                        <div class="step-title">
                            <strong>Platform A: ${opp.venue_buy}</strong>
                            <a href="${buyUrl}" target="_blank" class="platform-link-btn"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open Market</a>
                        </div>
                        <p class="step-desc">
                            Buy <strong>${opp.executable_size} contracts</strong> of <span class="text-emerald">BUY [${opp.buy_outcome}]</span> at max avg price <strong>$${opp.avg_buy_price.toFixed(2)}</strong>.
                        </p>
                        <div class="step-meta">Estimated Outlay + Fee: <strong>$${legACost}</strong></div>
                    </div>
                </div>

                <div class="step-card">
                    <div class="step-number">2</div>
                    <div class="step-details">
                        <div class="step-title">
                            <strong>Platform B: ${opp.venue_sell}</strong>
                            <a href="${sellUrl}" target="_blank" class="platform-link-btn"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open Market</a>
                        </div>
                        <p class="step-desc">
                            Buy <strong>${opp.executable_size} contracts</strong> of <span class="text-amber">BUY [${opp.sell_outcome}]</span> at max avg price <strong>$${opp.avg_sell_price.toFixed(2)}</strong>.
                        </p>
                        <div class="step-meta">Estimated Outlay + Fee/Gas: <strong>$${legBCost}</strong></div>
                    </div>
                </div>

                <div class="step-card step-settlement">
                    <div class="step-number"><i class="fa-solid fa-lock text-emerald"></i></div>
                    <div class="step-details">
                        <div class="step-title"><strong>Guaranteed Settlement & Net Edge</strong></div>
                        <div class="settlement-grid font-mono">
                            <div>Total Outlay: <strong>$${opp.total_net_cost.toFixed(2)}</strong></div>
                            <div>Guaranteed Payout: <strong>$${opp.guaranteed_payout.toFixed(2)}</strong></div>
                            <div class="text-emerald">Net Profit: <strong>+$${opp.net_profit.toFixed(2)} (+${opp.net_roi}%)</strong></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Order Book Depth Ladder Visualizer -->
            <div class="depth-ladder-grid margin-top">
                <div class="ladder-column">
                    <h4>${opp.venue_buy} (${opp.buy_outcome} Asks)</h4>
                    <div class="ladder-list">
                        ${buyAsksHtml || '<p class="text-muted">No asks</p>'}
                    </div>
                </div>
                <div class="ladder-column">
                    <h4>${opp.venue_sell} (${opp.sell_outcome} Asks)</h4>
                    <div class="ladder-list">
                        ${sellAsksHtml || '<p class="text-muted">No asks</p>'}
                    </div>
                </div>
            </div>

            <button class="btn btn-primary btn-block margin-top" onclick="window.executePaperTradeById('${opp.opp_id}')">
                <i class="fa-solid fa-bolt"></i> Execute Paper Trade ($${opp.net_profit.toFixed(2)} Net Profit)
            </button>
        </div>
    `;
}

function renderMatchingTable() {
    const tbody = document.getElementById('matching-table-body');
    tbody.innerHTML = '';

    if (state.matchedPairs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:30px;">No candidate matched pairs discovered.</td></tr>`;
        return;
    }

    state.matchedPairs.forEach(p => {
        const tr = document.createElement('tr');
        const flagsHtml = p.risk_flags.map(f => {
            const cls = f === 'LOW_RISK_MATCH' ? 'green' : 'amber';
            return `<span class="risk-tag ${cls}">${f}</span>`;
        }).join('');

        const statusClass = p.status === 'VERIFIED' ? 'green' : (p.status === 'REJECTED' ? 'red' : 'amber');

        tr.innerHTML = `
            <td class="font-mono"><strong>${p.similarity_score}%</strong></td>
            <td class="title-cell">
                <strong>${p.market_a.title}</strong>
                <span>${p.market_a.venue} | ${p.market_a.resolution_source}</span>
            </td>
            <td class="title-cell">
                <strong>${p.market_b.title}</strong>
                <span>${p.market_b.venue} | ${p.market_b.resolution_source}</span>
            </td>
            <td>${flagsHtml}</td>
            <td><span class="risk-tag ${statusClass}">${p.status}</span></td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-outline btn-sm" onclick="window.setPairStatus('${p.pair_id}', 'VERIFIED')">
                        <i class="fa-solid fa-check text-emerald"></i> Verify
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="window.setPairStatus('${p.pair_id}', 'REJECTED')">
                        <i class="fa-solid fa-xmark text-coral"></i> Reject
                    </button>
                </div>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

function renderPaperTradesTable() {
    const tbody = document.getElementById('paper-trades-body');
    tbody.innerHTML = '';

    if (state.paperTrades.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:30px; color:var(--text-muted);">No paper trades executed yet. Execute paper trades from Stage 1 scanner.</td></tr>`;
        return;
    }

    state.paperTrades.slice().reverse().forEach(t => {
        const tr = document.createElement('tr');
        const timeStr = new Date(t.timestamp * 1000).toLocaleTimeString();
        const statusClass = t.status === 'SETTLED_WIN' ? 'green' : 'red';

        tr.innerHTML = `
            <td class="font-mono">#${t.trade_id.slice(-6)} <br><small class="text-muted">${timeStr}</small></td>
            <td class="title-cell">
                <strong>${t.venue_buy} vs ${t.venue_sell}</strong>
                <span>Pair ID: ${t.pair_id}</span>
            </td>
            <td class="font-mono">$${t.target_capital}</td>
            <td class="font-mono text-emerald">+${t.detected_net_roi}%</td>
            <td class="font-mono text-amber">-${t.simulated_slippage_decay}%</td>
            <td class="font-mono text-emerald"><strong>+${t.realized_net_roi}%</strong></td>
            <td class="font-mono text-emerald"><strong>+$${t.realized_net_profit.toFixed(2)}</strong></td>
            <td class="font-mono text-amber">${t.realized_gap}%</td>
            <td><span class="risk-tag ${statusClass}">${t.status}</span></td>
        `;

        tbody.appendChild(tr);
    });
}

async function setPairStatus(pairId, status) {
    try {
        const res = await fetch('/api/matches/status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pair_id: pairId, status: status })
        });
        const data = await res.json();
        if (data.success) {
            await fetchData();
        }
    } catch (e) {
        console.error("Error setting pair status:", e);
    }
}

async function executePaperTrade(opp) {
    try {
        const res = await fetch('/api/paper/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ opportunity: opp })
        });
        const data = await res.json();
        if (data.success) {
            await fetchData();
            alert(`Paper trade executed successfully!\nRealized Profit: +$${data.trade.realized_net_profit.toFixed(2)} (Edge Realization Gap: ${data.trade.realized_gap}%)`);
        }
    } catch (e) {
        console.error("Error executing paper trade:", e);
    }
}

function executePaperTradeById(oppId) {
    const opp = state.opportunities.find(o => o.opp_id === oppId);
    if (opp) executePaperTrade(opp);
}

function getVenueClass(venue) {
    if (venue === 'Kalshi') return 'venue-kalshi';
    if (venue === 'Polymarket') return 'venue-poly';
    return 'venue-prophet';
}
