//! Backtesting Lab: script editor, parameter controls, equity curve, results table, logs.

use crate::components::Panel;
use crate::state::AppState;
use leptos::*;

const DEFAULT_SCRIPT: &str = r#"// Nexus backtest script (mocked)
fn on_bar(symbol: &str, bar: Bar) {
    if bar.close > bar.ema_20 {
        buy(symbol, 1);
    } else if bar.close < bar.ema_20 {
        sell(symbol, 1);
    }
}

fn on_init() {
    set_universe(["AAPL", "MSFT", "GOOGL"]);
    set_frequency(Daily);
}
"#;

#[component]
pub fn BacktestingLabPage() -> impl IntoView {
    let state = expect_context::<RwSignal<AppState>>();

    view! {
        <div class="page-grid page-grid-backtest">
            <Panel title="Script Editor">
                <pre class="backtest-editor">{DEFAULT_SCRIPT}</pre>
                <div class="backtest-actions">
                    <button type="button" class="backtest-run">Run Backtest</button>
                    <span class="text-muted" style="font-size: 11px;">Parameters applied from sidebar</span>
                </div>
            </Panel>

            <Panel title="Parameter Controls">
                <div class="sidebar-section">
                    <div class="sidebar-label">Start date</div>
                    <input type="text" class="sidebar-control" value="2024-01-01" />
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-label">End date</div>
                    <input type="text" class="sidebar-control" value="2024-12-31" />
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-label">Initial capital</div>
                    <input type="text" class="sidebar-control" value="100000" />
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-label">Commission</div>
                    <input type="text" class="sidebar-control" value="0.0" />
                </div>
            </Panel>

            <Panel title="Equity Curve">
                {move || {
                    let curve = state.get().backtest_result.equity_curve.clone();
                    let max = curve.iter().cloned().fold(0.0f64, f64::max).max(1.0);
                    view! {
                        <div class="chart-container">
                            <div class="chart-bars" style="height: 120px;">
                                {curve.into_iter().map(|v| {
                                    let pct = (v / max) * 100.0;
                                    view! {
                                        <div class="chart-bar-wrap">
                                            <div class="chart-bar cyan" style=format!("height: {:.0}%", pct)></div>
                                        </div>
                                    }
                                }).collect_view()}
                            </div>
                            <div class="chart-labels">
                                {["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15"].into_iter().map(|l| view! { <span>{l}</span> }).collect_view()}
                            </div>
                        </div>
                    }
                }}
            </Panel>

            <Panel title="Results Table">
                {move || {
                    let r = state.get().backtest_result.clone();
                    view! {
                        <table class="data-table">
                            <tbody>
                                <tr><td class="metric-label">Total return</td><td class="metric-value up">{format!("{:.1}%", r.total_return_pct)}</td></tr>
                                <tr><td class="metric-label">Sharpe</td><td class="metric-value">{format!("{:.2}", r.sharpe)}</td></tr>
                                <tr><td class="metric-label">Max drawdown</td><td class="metric-value down">{format!("{:.1}%", r.max_drawdown_pct)}</td></tr>
                                <tr><td class="metric-label">Win rate</td><td class="metric-value">{format!("{:.0}%", r.win_rate_pct)}</td></tr>
                                <tr><td class="metric-label">Trades</td><td class="metric-value">{r.trades}</td></tr>
                            </tbody>
                        </table>
                    }
                }}
            </Panel>

            <Panel title="Logs">
                <div class="logs-panel">
                    <div class="log-line">[INFO] Backtest started: 2024-01-01 to 2024-12-31</div>
                    <div class="log-line">[INFO] Universe: AAPL, MSFT, GOOGL</div>
                    <div class="log-line">[INFO] Initial capital: $100,000</div>
                    <div class="log-line">[INFO] Run complete. 142 trades executed.</div>
                    <div class="log-line">[INFO] Total return: 12.4% | Sharpe: 1.35</div>
                </div>
            </Panel>
        </div>
    }
}
