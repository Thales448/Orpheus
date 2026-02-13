//! Symbol Research: chart-heavy page — price chart, volatility drift, IV rank/skew, term structure, earnings, key metrics.

use crate::components::Panel;
use crate::state::AppState;
use leptos::*;

fn price_chart_series() -> Vec<(String, f64)> {
    vec![
        ("Jan".into(), 185.2),
        ("Feb".into(), 188.1),
        ("Mar".into(), 175.5),
        ("Apr".into(), 169.0),
        ("May".into(), 189.2),
        ("Jun".into(), 214.2),
        ("Jul".into(), 218.5),
        ("Aug".into(), 225.1),
        ("Sep".into(), 222.0),
        ("Oct".into(), 228.45),
    ]
}

fn volatility_drift_series() -> Vec<(String, f64)> {
    vec![
        ("30d".into(), 0.18),
        ("60d".into(), 0.20),
        ("90d".into(), 0.22),
        ("6m".into(), 0.24),
        ("1y".into(), 0.22),
    ]
}

fn iv_term_series() -> Vec<(String, f64)> {
    vec![
        ("7d".into(), 0.32),
        ("14d".into(), 0.28),
        ("30d".into(), 0.26),
        ("60d".into(), 0.25),
        ("90d".into(), 0.24),
    ]
}

#[component]
pub fn SymbolResearchPage() -> impl IntoView {
    let state = expect_context::<RwSignal<AppState>>();
    let metrics = move || state.get().symbol_metrics.first().cloned().unwrap_or_default();

    view! {
        <div class="page-grid page-grid-symbol">
            <Panel title="Price Chart (with overlays)">
                <div class="chart-container" style="min-height: 200px;">
                    <div class="chart-bars" style="height: 160px;">
                        {price_chart_series().into_iter().enumerate().map(|(_i, (_, v))| {
                            let min = 169.0f64;
                            let max = 228.45f64;
                            let pct = ((v - min) / (max - min)) * 100.0;
                            let class = "chart-bar cyan";
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {:.0}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {price_chart_series().into_iter().map(|(l, _)| view! { <span>{l}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>

            <Panel title="Key Metrics">
                {move || {
                    let m = metrics();
                    view! {
                        <div class="metric-row">
                            <span class="metric-label">Price</span>
                            <span class="metric-value">{format!("${:.2}", m.price)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Change</span>
                            <span class=(if m.change >= 0.0 { "metric-value up" } else { "metric-value down" })>
                                {format!("{:.2}%", m.change_pct)}
                            </span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">52W Range</span>
                            <span class="metric-value">{format!("${:.0} - ${:.0}", m.low_52w, m.high_52w)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">30d Vol</span>
                            <span class="metric-value accent">{format!("{:.0}%", m.volatility_30d * 100.0)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Volume</span>
                            <span class="metric-value">{format!("{:.0}M", m.volume as f64 / 1e6)}</span>
                        </div>
                    }
                }}
            </Panel>

            <Panel title="Volatility Drift">
                <div class="chart-container">
                    <div class="chart-bars">
                        {volatility_drift_series().into_iter().map(|(_, v)| {
                            let pct = (v / 0.25) * 100.0;
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class="chart-bar purple" style=format!("height: {:.0}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {volatility_drift_series().into_iter().map(|(l, _)| view! { <span>{l}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>

            <Panel title="IV Rank & IV Skew">
                <div class="metric-row">
                    <span class="metric-label">IV Rank (30d)</span>
                    <span class="metric-value accent">42%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">IV Percentile</span>
                    <span class="metric-value">38%</span>
                </div>
                <div class="chart-container" style="margin-top: 10px;">
                    <div class="chart-bars" style="height: 60px;">
                        {[0.35, 0.28, 0.26, 0.27, 0.30].into_iter().enumerate().map(|(i, v)| {
                            let pct = (v / 0.35) * 100.0;
                            let class = if i == 2 { "chart-bar cyan" } else { "chart-bar yellow" };
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {:.0}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        <span>90P</span><span>60P</span><span>ATM</span><span>60C</span><span>90C</span>
                    </div>
                </div>
            </Panel>

            <Panel title="Term Structure">
                <div class="chart-container">
                    <div class="chart-bars">
                        {iv_term_series().into_iter().map(|(_, v)| {
                            let pct = (v / 0.32) * 100.0;
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class="chart-bar green" style=format!("height: {:.0}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {iv_term_series().into_iter().map(|(l, _)| view! { <span>{l}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>

            <Panel title="Earnings History">
                {move || {
                    let earnings = state.get().earnings.clone();
                    view! {
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>EPS Est</th>
                                    <th>EPS Act</th>
                                    <th>Surprise %</th>
                                </tr>
                            </thead>
                            <tbody>
                                {earnings.into_iter().map(|e| view! {
                                    <tr>
                                        <td class="highlight">{e.date}</td>
                                        <td>{format!("{:.2}", e.eps_est)}</td>
                                        <td>{format!("{:.2}", e.eps_act)}</td>
                                        <td class="positive">{format!("{:.1}%", e.surprise_pct)}</td>
                                    </tr>
                                }).collect_view()}
                            </tbody>
                        </table>
                    }
                }}
            </Panel>
        </div>
    }
}
