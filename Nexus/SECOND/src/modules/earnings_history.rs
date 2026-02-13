use leptos::*;

#[derive(Clone)]
struct EarningsRow {
    date: &'static str,
    eps_est: &'static str,
    eps_act: &'static str,
    surprise: &'static str,
}

#[component]
pub fn EarningsHistory() -> impl IntoView {
    let rows = vec![
        EarningsRow { date: "2024-01-31", eps_est: "2.10", eps_act: "2.18", surprise: "+3.8%" },
        EarningsRow { date: "2023-10-26", eps_est: "1.39", eps_act: "1.46", surprise: "+5.0%" },
        EarningsRow { date: "2023-07-27", eps_est: "1.19", eps_act: "1.26", surprise: "+5.9%" },
        EarningsRow { date: "2023-04-27", eps_est: "1.43", eps_act: "1.52", surprise: "+6.3%" },
    ];

    view! {
        <div class="earnings-history-module">
            <table class="earnings-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>EPS Est</th>
                        <th>EPS Act</th>
                        <th>Surprise</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.into_iter().map(|r| {
                        view! {
                            <tr>
                                <td>{r.date}</td>
                                <td>{r.eps_est}</td>
                                <td>{r.eps_act}</td>
                                <td class="earnings-surprise">{r.surprise}</td>
                            </tr>
                        }
                    }).collect_view()}
                </tbody>
            </table>
        </div>
    }
}
