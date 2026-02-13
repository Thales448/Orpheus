//! Portfolio Metrics: net greeks, exposure by symbol/sector, positions table, risk graph, P/L history.

use crate::components::Panel;
use crate::state::AppState;
use leptos::*;

fn fmt_usd(x: f64) -> String {
    format!("${:.0}", x)
}

fn exposure_by_symbol() -> Vec<(String, f64)> {
    vec![
        ("AAPL".into(), 38.2),
        ("NVDA".into(), 22.1),
        ("MSFT".into(), 18.5),
        ("GOOGL".into(), 12.0),
        ("META".into(), 9.2),
    ]
}

fn exposure_by_sector() -> Vec<(String, f64)> {
    vec![
        ("Technology".into(), 52.0),
        ("Communication".into(), 18.0),
        ("Healthcare".into(), 15.0),
        ("Consumer".into(), 10.0),
        ("Other".into(), 5.0),
    ]
}

#[component]
pub fn PortfolioMetricsPage() -> impl IntoView {
    let state = expect_context::<RwSignal<AppState>>();

    view! {
        <div class="page-grid page-grid-portfolio">
            <Panel title="Net Greeks">
                {move || {
                    let g = state.get().net_greeks;
                    view! {
                        <div class="metric-row">
                            <span class="metric-label">Delta</span>
                            <span class="metric-value accent">{format!("{:.1}", g.delta)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Gamma</span>
                            <span class="metric-value">{format!("{:.1}", g.gamma)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Theta</span>
                            <span class="metric-value down">{format!("{:.1}", g.theta)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Vega</span>
                            <span class="metric-value">{format!("{:.1}", g.vega)}</span>
                        </div>
                    }
                }}
            </Panel>

            <Panel title="Exposure by Symbol">
                <div class="chart-container">
                    <div class="chart-bars" style="height: 80px;">
                        {exposure_by_symbol().into_iter().map(|(_, pct)| {
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class="chart-bar cyan" style=format!("height: {}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {exposure_by_symbol().into_iter().map(|(s, _)| view! { <span>{s}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>

            <Panel title="Exposure by Sector">
                <div class="chart-container">
                    <div class="chart-bars" style="height: 80px;">
                        {exposure_by_sector().into_iter().enumerate().map(|(i, (_, pct))| {
                            let class = match i % 4 {
                                0 => "chart-bar purple",
                                1 => "chart-bar green",
                                2 => "chart-bar yellow",
                                _ => "chart-bar cyan",
                            };
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {}%", pct)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {exposure_by_sector().into_iter().map(|(s, _)| view! { <span>{s}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>

            <Panel title="Positions Table">
                {move || {
                    let positions = state.get().portfolio_positions.clone();
                    view! {
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Qty</th>
                                    <th>Mkt Value</th>
                                    <th>P/L</th>
                                    <th>P/L %</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions.into_iter().map(|p| view! {
                                    <tr>
                                        <td class="highlight">{p.symbol}</td>
                                        <td>{p.quantity}</td>
                                        <td>{fmt_usd(p.market_value.abs())}</td>
                                        <td class=(if p.pnl >= 0.0 { "positive" } else { "negative" })>
                                            {fmt_usd(p.pnl)}
                                        </td>
                                        <td class=(if p.pnl_pct >= 0.0 { "positive" } else { "negative" })>
                                            {format!("{:.2}%", p.pnl_pct)}
                                        </td>
                                    </tr>
                                }).collect_view()}
                            </tbody>
                        </table>
                    }
                }}
            </Panel>

            <Panel title="Risk Graph">
                <div class="chart-container" style="min-height: 140px;">
                    <div class="chart-bars" style="height: 120px;">
                        {[30.0, 50.0, 75.0, 90.0, 85.0, 70.0, 55.0, 40.0, 25.0].into_iter().enumerate().map(|(i, v)| {
                            let class = if i < 4 { "chart-bar cyan" } else { "chart-bar red" };
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {}%", v)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {["-10%","-5%","0","+5%","+10%","+15%","+20%","+25%","+30%"].into_iter().map(|l| view! { <span>{l}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>

            <Panel title="P/L History">
                <div class="chart-container">
                    <div class="chart-bars" style="height: 100px;">
                        {[55.0, 58.0, 62.0, 65.0, 70.0, 72.0, 75.0, 78.0, 82.0, 85.0, 88.0, 92.0, 95.0, 98.0, 100.0].into_iter().enumerate().map(|(_i, v)| {
                            let class = "chart-bar green";
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {}%", v)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {["W1","W2","W3","W4","W5","W6","W7","W8","W9","W10","W11","W12","W13","W14","W15"].into_iter().map(|l| view! { <span>{l}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>
        </div>
    }
}
