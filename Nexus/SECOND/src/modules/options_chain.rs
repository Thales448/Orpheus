use leptos::*;

#[derive(Clone)]
struct ChainRow {
    strike: f64,
    call_bid: f64,
    call_ask: f64,
    put_bid: f64,
    put_ask: f64,
}

#[component]
pub fn OptionsChain() -> impl IntoView {
    let rows = vec![
        ChainRow { strike: 145.0, call_bid: 8.20, call_ask: 8.50, put_bid: 2.10, put_ask: 2.30 },
        ChainRow { strike: 150.0, call_bid: 4.80, call_ask: 5.00, put_bid: 4.20, put_ask: 4.45 },
        ChainRow { strike: 152.5, call_bid: 3.10, call_ask: 3.35, put_bid: 5.80, put_ask: 6.00 },
        ChainRow { strike: 155.0, call_bid: 1.95, call_ask: 2.10, put_bid: 7.90, put_ask: 8.15 },
        ChainRow { strike: 157.5, call_bid: 1.10, call_ask: 1.22, put_bid: 10.20, put_ask: 10.50 },
    ];
    let underlying = 152.5;

    view! {
        <div class="options-chain-module">
            <div class="options-chain-underlying">Underlying: {format!("{:.2}", underlying)}</div>
            <table class="options-chain-table">
                <thead>
                    <tr>
                        <th>Calls</th>
                        <th>Strike</th>
                        <th>Puts</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.into_iter().map(|r| {
                        view! {
                            <tr>
                                <td class="options-chain-bid-ask">{format!("{:.2} / {:.2}", r.call_bid, r.call_ask)}</td>
                                <td class="options-chain-strike">{format!("{:.1}", r.strike)}</td>
                                <td class="options-chain-bid-ask">{format!("{:.2} / {:.2}", r.put_bid, r.put_ask)}</td>
                            </tr>
                        }
                    }).collect_view()}
                </tbody>
            </table>
        </div>
    }
}
