use leptos::*;

#[component]
pub fn BacktestEditor() -> impl IntoView {
    let code = r#"// Mock backtest script
symbol = "AAPL"
start = "2023-01-01"
end = "2024-01-01"

def on_bar(data):
    if data.close > data.sma(20):
        buy(symbol, 1)
    else:
        sell(symbol, 1)

run_backtest()"#;

    view! {
        <div class="backtest-editor-module">
            <pre class="backtest-code"><code>{code}</code></pre>
            <div class="backtest-actions">
                <button type="button" class="backtest-run">Run backtest</button>
                <span class="backtest-hint">Mock editor - no execution</span>
            </div>
        </div>
    }
}
