//! Options Analysis: chain table, filters, strategy suggestion, payoff diagram, greeks summary.

use crate::components::Panel;
use crate::state::{AppState, OptionKind};
use leptos::*;

#[component]
pub fn OptionsAnalysisPage() -> impl IntoView {
    let state = expect_context::<RwSignal<AppState>>();

    view! {
        <div class="page-grid page-grid-options">
            <Panel title="Options Chain (Calls / Puts, Greeks, IV, Bid/Ask)">
                {move || {
                    let chain = state.get().options_chain.clone();
                    view! {
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Strike</th>
                                    <th>Type</th>
                                    <th>Bid</th>
                                    <th>Ask</th>
                                    <th>IV</th>
                                    <th>Delta</th>
                                    <th>Gamma</th>
                                    <th>Theta</th>
                                    <th>Vega</th>
                                </tr>
                            </thead>
                            <tbody>
                                {chain.into_iter().map(|c| view! {
                                    <tr>
                                        <td class="highlight">{format!("{:.0}", c.strike)}</td>
                                        <td>{if c.kind == OptionKind::Call { "Call" } else { "Put" }}</td>
                                        <td>{format!("{:.2}", c.bid)}</td>
                                        <td>{format!("{:.2}", c.ask)}</td>
                                        <td>{format!("{:.0}%", c.iv * 100.0)}</td>
                                        <td>{format!("{:.2}", c.greeks.delta)}</td>
                                        <td>{format!("{:.3}", c.greeks.gamma)}</td>
                                        <td>{format!("{:.2}", c.greeks.theta)}</td>
                                        <td>{format!("{:.2}", c.greeks.vega)}</td>
                                    </tr>
                                }).collect_view()}
                            </tbody>
                        </table>
                    }
                }}
            </Panel>

            <Panel title="Filters (DTE, Strike, Delta)">
                <div class="sidebar-section">
                    <div class="sidebar-label">DTE</div>
                    <input type="text" class="sidebar-control" value="7 - 45" />
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-label">Strike range</div>
                    <input type="text" class="sidebar-control" placeholder="220 - 235" />
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-label">Delta</div>
                    <select class="sidebar-control">
                        <option value="">All</option>
<option value="30">&lt;= 30</option>
                                <option value="50">&lt;= 50</option>
                    </select>
                </div>
            </Panel>

            <Panel title="Strategy Suggestion">
                <div class="metric-row">
                    <span class="metric-label">Suggested</span>
                    <span class="metric-value accent">Short strangle 30Δ</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Credit</span>
                    <span class="metric-value up">$2.85</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Prob. OTM</span>
                    <span class="metric-value">72%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Max loss</span>
                    <span class="metric-value down">Unlimited</span>
                </div>
            </Panel>

            <Panel title="Payoff Diagram">
                <div class="chart-container">
                    <div class="chart-bars" style="height: 100px;">
                        {[0.0, 10.0, 25.0, 50.0, 75.0, 90.0, 70.0, 40.0, 0.0, -20.0].into_iter().enumerate().map(|(_i, v)| {
                            let (class, h) = if v >= 0.0 {
                                ("chart-bar green", (v / 90.0_f64 * 100.0).min(100.0))
                            } else {
                                ("chart-bar red", (-v / 20.0_f64 * 40.0).min(100.0))
                            };
                            view! {
                                <div class="chart-bar-wrap">
                                    <div class=class style=format!("height: {:.0}%", h)></div>
                                </div>
                            }
                        }).collect_view()}
                    </div>
                    <div class="chart-labels">
                        {["210","215","220","225","230","235","240","245","250","255"].into_iter().map(|l| view! { <span>{l}</span> }).collect_view()}
                    </div>
                </div>
            </Panel>

            <Panel title="Greeks Summary">
                {move || {
                    let g = state.get().options_chain.first().map(|c| c.greeks.clone()).unwrap_or_default();
                    view! {
                        <div class="metric-row">
                            <span class="metric-label">Delta</span>
                            <span class="metric-value accent">{format!("{:.2}", g.delta)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Gamma</span>
                            <span class="metric-value">{format!("{:.3}", g.gamma)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Theta</span>
                            <span class="metric-value down">{format!("{:.2}", g.theta)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Vega</span>
                            <span class="metric-value">{format!("{:.2}", g.vega)}</span>
                        </div>
                    }
                }}
            </Panel>
        </div>
    }
}
