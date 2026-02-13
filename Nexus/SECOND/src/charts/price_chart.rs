//! Customizable price chart: main series + extensible overlay layer.
//! Add support levels, GEX levels, trend channels later via overlays.

use leptos::*;

/// Single point in a price series (time can be label or numeric).
#[derive(Clone)]
pub struct PricePoint {
    pub label: String,
    pub value: f64,
}

/// Overlay kind for future customization (support, GEX, channel, etc.).
#[derive(Clone)]
pub enum ChartOverlayKind {
    /// Horizontal level (support/resistance, GEX level, etc.)
    HorizontalLevel { value: f64, label: String },
    /// Trend channel: two parallel lines (top and bottom values per point)
    TrendChannel { top: Vec<f64>, bottom: Vec<f64>, label: String },
    /// Vertical line at index (e.g. event)
    VerticalLine { index: usize, label: String },
}

/// One overlay to draw on the chart (extensible).
#[derive(Clone)]
pub struct ChartOverlay {
    pub kind: ChartOverlayKind,
    pub color: Option<String>,
}

#[component]
pub fn PriceChart(series: Vec<PricePoint>, overlays: Vec<ChartOverlay>) -> impl IntoView {
    let height = 320u32;
    let width = 800u32;
    let padding = (50, 40, 40, 60); // top, right, bottom, left
    let chart_w = width - padding.1 - padding.3;
    let chart_h = height - padding.0 - padding.2;

    if series.is_empty() {
        return view! {
            <div class="price-chart-container">
                <svg class="price-chart-svg" viewBox=format!("0 0 {} {}", width, height) preserveAspectRatio="xMidYMid meet">
                    <text x={width/2} y={height/2} text-anchor="middle" class="chart-no-data">No data</text>
                </svg>
            </div>
        }.into_view();
    }

    let min_y = series.iter().map(|p| p.value).fold(f64::INFINITY, f64::min);
    let max_y = series.iter().map(|p| p.value).fold(f64::NEG_INFINITY, f64::max);
    let range_y = (max_y - min_y).max(0.01);
    let n = series.len();
    let step_x = if n <= 1 { 0.0 } else { chart_w as f64 / (n - 1) as f64 };

    let points: Vec<(f64, f64)> = series
        .iter()
        .enumerate()
        .map(|(i, p)| {
            let x = padding.3 as f64 + i as f64 * step_x;
            let y = padding.0 as f64 + chart_h as f64 - (p.value - min_y) / range_y * chart_h as f64;
            (x, y)
        })
        .collect();

    let bottom_y = padding.0 as f64 + chart_h as f64;
    let area_path = if points.len() >= 2 {
        let first = &points[0];
        let last = points.last().unwrap();
        let mid: String = points
            .iter()
            .map(|(x, y)| format!("L {:.2} {:.2}", x, y))
            .collect::<Vec<_>>()
            .join(" ");
        format!(
            "M {:.2} {:.2} L {:.2} {:.2} {} L {:.2} {:.2} Z",
            first.0, bottom_y, first.0, first.1, mid, last.0, bottom_y
        )
    } else {
        String::new()
    };
    let line_path = points
        .iter()
        .enumerate()
        .map(|(i, (x, y))| if i == 0 { format!("M {:.2} {:.2}", x, y) } else { format!(" L {:.2} {:.2}", x, y) })
        .collect::<String>();

    // Overlay elements (extensible: support levels, GEX, channels)
    let overlay_views: Vec<leptos::View> = overlays
        .iter()
        .map(|ov| {
            match &ov.kind {
                ChartOverlayKind::HorizontalLevel { value, label } => {
                    let y = padding.0 as f64 + chart_h as f64 - (value - min_y) / range_y * chart_h as f64;
                    let color = ov.color.clone().unwrap_or_else(|| "var(--accent-purple)".to_string());
                    view! {
                        <g class="chart-overlay level">
                            <line
                                x1=padding.3
                                y1=y
                                x2=width - padding.1
                                y2=y
                                stroke=color.clone()
                                stroke-width="1"
                                stroke-dasharray="4 4"
                                opacity="0.8"
                            />
                            <text x=padding.3 - 6 y=y dy="0.35em" text-anchor="end" class="chart-overlay-label" fill=color>
                                {label.clone()}
                            </text>
                        </g>
                    }
                    .into_view()
                }
                ChartOverlayKind::TrendChannel { top, bottom, label } => {
                    if top.len() != bottom.len() || top.len() != series.len() {
                        return view! { <g class="chart-overlay"></g> }.into_view();
                    }
                    let step = if series.len() <= 1 { 0.0 } else { chart_w as f64 / (series.len() - 1) as f64 };
                    let top_pts: String = top.iter().enumerate().map(|(i, v)| {
                        let x = padding.3 as f64 + i as f64 * step;
                        let y = padding.0 as f64 + chart_h as f64 - (v - min_y) / range_y * chart_h as f64;
                        format!("{:.2},{:.2} ", x, y)
                    }).collect();
                    let bottom_pts: String = bottom.iter().enumerate().map(|(i, v)| {
                        let x = padding.3 as f64 + i as f64 * step;
                        let y = padding.0 as f64 + chart_h as f64 - (v - min_y) / range_y * chart_h as f64;
                        format!("{:.2},{:.2} ", x, y)
                    }).collect();
                    let color = ov.color.clone().unwrap_or_else(|| "var(--accent-cyan)".to_string());
                    view! {
                        <g class="chart-overlay channel">
                            <polyline points=top_pts fill="none" stroke=color.clone() stroke-width="1" opacity="0.7"/>
                            <polyline points=bottom_pts fill="none" stroke=color stroke-width="1" opacity="0.7"/>
                            <text x=padding.3 y=padding.0 - 8 class="chart-overlay-label">{label.clone()}</text>
                        </g>
                    }
                    .into_view()
                }
                ChartOverlayKind::VerticalLine { index, label } => {
                    let x = padding.3 as f64 + *index as f64 * step_x;
                    let color = ov.color.clone().unwrap_or_else(|| "var(--accent-yellow)".to_string());
                    view! {
                        <g class="chart-overlay vline">
                            <line x1=x y1=padding.0 x2=x y2=height - padding.2 stroke=color.clone() stroke-width="1" stroke-dasharray="2 2" opacity="0.8"/>
                            <text x=x y=padding.0 - 6 text-anchor="middle" class="chart-overlay-label" fill=color>{label.clone()}</text>
                        </g>
                    }
                    .into_view()
                }
            }
        })
        .collect();

    let overlay_elements = overlay_views.into_iter().collect_view();

    let y_ticks = 5;
    let y_tick_values: Vec<f64> = (0..=y_ticks)
        .map(|i| min_y + range_y * (i as f64 / y_ticks as f64))
        .collect();

    view! {
        <div class="price-chart-container">
            <svg class="price-chart-svg" viewBox=format!("0 0 {} {}", width, height) preserveAspectRatio="xMidYMid meet">
                <defs>
                    <linearGradient id="price-area-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stop-color="var(--accent-cyan)" stop-opacity="0.3"/>
                        <stop offset="100%" stop-color="var(--accent-cyan)" stop-opacity="0"/>
                    </linearGradient>
                </defs>
                <g class="chart-grid">
                    {y_tick_values.iter().enumerate().map(|(i, _)| {
                        let y = padding.0 as f64 + chart_h as f64 * (1.0 - i as f64 / y_ticks as f64);
                        view! {
                            <line
                                x1=padding.3
                                y1=y
                                x2=width - padding.1
                                y2=y
                                stroke="var(--border-subtle)"
                                stroke-width="0.5"
                            />
                        }
                    }).collect_view()}
                </g>
                <g class="chart-overlays">
                    {overlay_elements}
                </g>
                <path d=area_path fill="url(#price-area-gradient)"/>
                <path d=line_path fill="none" stroke="var(--accent-cyan)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <g class="chart-axis-y">
                    {y_tick_values.iter().enumerate().map(|(i, v)| {
                        let y = padding.0 as f64 + chart_h as f64 * (1.0 - i as f64 / y_ticks as f64);
                        view! {
                            <text x=padding.3 - 8 y=y dy="0.35em" text-anchor="end" class="chart-tick-label">
                                {format!("{:.0}", v)}
                            </text>
                        }
                    }).collect_view()}
                </g>
                <g class="chart-axis-x">
                    {series.iter().enumerate().filter(|(i, _)| n <= 20 || i % (n / 10).max(1) == 0).map(|(i, p)| {
                        let x = padding.3 as f64 + i as f64 * step_x;
                        view! {
                            <text x=x y=height - padding.2 + 18 text-anchor="middle" class="chart-tick-label">
                                {p.label.clone()}
                            </text>
                        }
                    }).collect_view()}
                </g>
            </svg>
        </div>
    }.into_view()
}
