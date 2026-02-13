//! Dashboard: PnL summaries, watchlist, top plays, recent signals, small performance charts.

use crate::components::Panel;
use crate::state::AppState;
use leptos::*;

fn fmt_usd(x: f64) -> String {
    format!("${:.0}", x)
}

#[component]
pub fn DashboardPage() -> impl IntoView {
    let state = expect_context::<RwSignal<AppState>>();

    view! {
        <div class="page-grid page-grid-dashboard">
            <Panel title="PnL Summary">
                {move || {
                    let s = state.get();
                    view! {
                        <div class="metric-row">
                            <span class="metric-label">Total P/L</span>
                            <span class="metric-value accent">{fmt_usd(s.pnl_total)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Daily</span>
                            <span class="metric-value up">{fmt_usd(s.pnl_daily)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Monthly</span>
                            <span class="metric-value up">{fmt_usd(s.pnl_monthly)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Yearly</span>
                            <span class="metric-value up">{fmt_usd(s.pnl_yearly)}</span>
                        </div>
                    }
                }}
            </Panel>

            <Panel title="Watchlist">
                {move || {
                    let list = state.get().watchlist.clone();
                    view! {
                        <ul class="watchlist">
                            {list.into_iter().map(|s| view! {
                                <li class="watchlist-item">
                                    <span class="highlight">{s.clone()}</span>
                                    <span class="metric-value">-</span>
                                </li>
                            }).collect_view()}
                        </ul>
                    }
                }}
            </Panel>

            <Panel title="Top Plays">
                {move || {
                    let plays = state.get().top_plays.clone();
                    view! {
                        <ul class="plays-list">
                            {plays.into_iter().map(|(sym, reason)| view! {
                                <li class="play-item">
                                    <span class="highlight">{sym}</span>
                                    <span class="text-muted" style="font-size: 11px;">{reason}</span>
                                </li>
                            }).collect_view()}
                        </ul>
                    }
                }}
            </Panel>

            <Panel title="Recent Signals / Insights">
                {move || {
                    let signals = state.get().recent_signals.clone();
                    view! {
                        <ul class="signal-list">
                            {signals.into_iter().map(|(title, desc)| view! {
                                <li class="signal-item">
                                    <span class="highlight">{title}</span>
                                    <span style="font-size: 11px; color: var(--text-muted);">{desc}</span>
                                </li>
                            }).collect_view()}
                        </ul>
                    }
                }}
            </Panel>

            <Panel title="Performance (7D)">
                <div class="chart-container">
                    <div class="chart-bars">
                        {[72.0, 68.0, 75.0, 78.0, 82.0, 85.0, 88.0].into_iter().enumerate().map(|(i, pct)| {
                            let class = if i % 3 == 0 { "chart-bar cyan" } else { "chart-bar purple" };
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
                    </div>
                </div>
            </Panel>

            <Panel title="Equity Snapshot">
                <div class="chart-container">
                    <div class="chart-bars">
                        {[40.0, 55.0, 48.0, 65.0, 70.0, 85.0, 78.0, 92.0, 88.0, 95.0].into_iter().enumerate().map(|(i, pct)| {
                            let class = match i % 4 {
                                0 => "chart-bar cyan",
                                1 => "chart-bar green",
                                2 => "chart-bar yellow",
                                _ => "chart-bar purple",
                            };
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {["W1","W2","W3","W4","W5","W6","W7","W8","W9","W10"].into_iter().map(|l| view! { <span>{l}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>
        </div>
    }
}
