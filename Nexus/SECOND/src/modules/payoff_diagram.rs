use leptos::*;

#[component]
pub fn PayoffDiagram() -> impl IntoView {
    // Mock: long call 150, short call 155 (call spread)
    let strikes = vec![145.0, 150.0, 155.0, 160.0];
    let payoffs = vec![-5.0, -5.0, 0.0, 5.0]; // simplified

    view! {
        <div class="payoff-diagram-module">
            <div class="payoff-title">Call spread 150 / 155</div>
            <div class="payoff-chart-placeholder">
                <div class="payoff-y-label">P/L</div>
                <div class="payoff-bars">
                    {strikes.iter().zip(payoffs.iter()).enumerate().map(|(i, (s, p))| {
                        let height: f64 = (*p + 5.0) / 10.0 * 80.0;
                        let class = if *p >= 0.0 { "payoff-bar positive" } else { "payoff-bar negative" };
                        view! {
                            <div class="payoff-bar-wrap" key=i>
                                <div
                                    class=class
                                    style=format!("height: {}%; min-height: 4px;", height.max(4.0))
                                ></div>
                                <span class="payoff-strike">{format!("{:.0}", s)}</span>
                            </div>
                        }
                    }).collect_view()}
                </div>
            </div>
            <div class="payoff-legend">
                <span>Max profit: $500</span>
                <span>Max loss: $500</span>
            </div>
        </div>
    }
}
