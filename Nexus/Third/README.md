# Nexus Quant Research (Third)

Professional web-based quantitative research tool for options, portfolio metrics, and backtesting. Built with **Rust**, **Leptos** (WASM), and **TailwindCSS**. Pure frontend with mocked data.

## Run

```bash
trunk serve
```

Then open **http://127.0.0.1:3000** (or the URL printed by Trunk).

If `trunk` is not in your PATH:

```bash
~/.cargo/bin/trunk serve
```

Or install: `cargo install trunk`

## Pages

- **Dashboard** — PnL summaries, watchlist, top plays, recent signals, performance charts
- **Symbol Research** — Price chart, volatility drift, IV rank/skew, term structure, earnings, key metrics
- **Options Analysis** — Options chain, filters (DTE, strike, delta), strategy suggestion, payoff diagram, greeks
- **Portfolio Metrics** — Net greeks, exposure by symbol/sector, positions table, risk graph, P/L history
- **Backtesting Lab** — Script editor, parameter controls, equity curve, results table, logs
- **Settings** — Display and data preferences

## Tech

- **Rust** + **Leptos 0.6** (CSR) + **leptos_router**
- **TailwindCSS** (config present; main styles in `style.css`)
- No backend, no APIs, no networking; all data from `src/state.rs` (mocked)

## Layout

- Top navigation bar with page links
- Left sidebar for contextual controls (symbol, DTE, delta)
- Main content: fixed panel grid per page (no draggable widgets)

Visual style: deep navy/blue-black gradient, floating panels with subtle glow borders, chart-heavy, professional quant analytics look.
