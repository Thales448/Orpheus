//! Sell / Hold / Buy gauge with needle. Value in [-1, 1] or [0, 1] for momentum indicators.

use leptos::*;

/// Value in [-1, 1]: -1 = Sell, 0 = Hold, 1 = Buy.
#[component]
pub fn SignalGauge(
    /// Indicator name (e.g. RSI, MACD).
    title: String,
    /// Signal in [-1, 1]. You can map your indicator here later.
    value: f64,
) -> impl IntoView {
    let value = value.clamp(-1.0, 1.0);
    // Needle: 0° = Buy (right), 90° = Hold (top), 180° = Sell (left)
    let angle_deg = 90.0 - (value + 1.0) * 90.0; // -1 -> 180, 0 -> 90, 1 -> 0
    let size = 120u32;
    let cx = size as f64 / 2.0;
    let cy = size as f64 / 2.0;
    let r = (size as f64 / 2.0) - 8.0;

    // Semicircle path (upper half): 180° to 0°
    let start_x = cx - r;
    let start_y = cy;
    let end_x = cx + r;
    let end_y = cy;
    let arc = format!("A {:.2} {:.2} 0 0 1 {:.2} {:.2}", r, r, end_x, end_y);
    let bg_path = format!("M {:.2} {:.2} {} L {:.2} {:.2} Z", start_x, start_y, arc, start_x, start_y);

    // Three segments: Sell (0-60°), Hold (60-120°), Buy (120-180°) in our coordinate system
    // We draw as three arcs. Angle 0 = right, 90 = top, 180 = left.
    // Sell: from 180° to 120° (left third)
    // Hold: 120° to 60° (middle)
    // Buy: 60° to 0° (right third)
    let to_rad = std::f64::consts::PI / 180.0;
    let seg = |start_deg: f64, end_deg: f64| {
        let x1 = cx + r * (start_deg * to_rad).cos();
        let y1 = cy - r * (start_deg * to_rad).sin();
        let x2 = cx + r * (end_deg * to_rad).cos();
        let y2 = cy - r * (end_deg * to_rad).sin();
        let sweep = if start_deg > end_deg { 1 } else { 0 };
        format!(
            "M {:.2} {:.2} L {:.2} {:.2} A {:.2} {:.2} 0 0 {} {:.2} {:.2} Z",
            cx, cy, x1, y1, r, r, sweep, x2, y2
        )
    };
    let sell_path = seg(180.0, 120.0);
    let hold_path = seg(120.0, 60.0);
    let buy_path = seg(60.0, 0.0);

    // Needle: line from center to right, then rotate
    let needle_len = r - 6.0;

    view! {
        <div class="signal-gauge">
            <span class="signal-gauge-title">{title}</span>
            <svg class="signal-gauge-svg" viewBox=format!("0 0 {} {}", size, size) preserveAspectRatio="xMidYMid meet">
                <path d=bg_path fill="var(--bg-chart)" stroke="var(--border-subtle)" stroke-width="1"/>
                <path d=sell_path fill="var(--accent-red)" opacity="0.4"/>
                <path d=hold_path fill="var(--accent-yellow)" opacity="0.4"/>
                <path d=buy_path fill="var(--accent-green)" opacity="0.4"/>
                <g transform=format!("rotate({:.1} {:.1} {:.1})", angle_deg, cx, cy)>
                    <line
                        x1=cx
                        y1=cy
                        x2=cx + needle_len
                        y2=cy
                        stroke="var(--text-primary)"
                        stroke-width="2"
                        stroke-linecap="round"
                    />
                    <circle cx=cx cy=cy r="4" fill="var(--accent-cyan)"/>
                </g>
            </svg>
            <div class="signal-gauge-labels">
                <span class="gauge-label sell">Sell</span>
                <span class="gauge-label hold">Hold</span>
                <span class="gauge-label buy">Buy</span>
            </div>
        </div>
    }
}
