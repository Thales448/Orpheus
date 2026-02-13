//! Settings: application preferences (mocked).

use crate::components::Panel;
use leptos::*;

#[component]
pub fn SettingsPage() -> impl IntoView {
    view! {
        <div class="page-grid" style="grid-template-columns: 1fr; max-width: 560px;">
            <Panel title="Preferences">
                <div class="settings-section">
                    <div class="settings-section-title">Display</div>
                    <div class="settings-row">
                        <label for="theme">Theme</label>
                        <select id="theme" class="sidebar-control" style="width: 140px;">
                            <option value="dark">Dark (default)</option>
                        </select>
                    </div>
                    <div class="settings-row">
                        <label for="density">Density</label>
                        <select id="density" class="sidebar-control" style="width: 140px;">
                            <option value="compact">Compact</option>
                            <option value="comfortable">Comfortable</option>
                        </select>
                    </div>
                </div>
                <div class="settings-section">
                    <div class="settings-section-title">Data</div>
                    <div class="settings-row">
                        <label for="tz">Timezone</label>
                        <select id="tz" class="sidebar-control" style="width: 140px;">
                            <option value="America/New_York">America/New_York</option>
                            <option value="UTC">UTC</option>
                        </select>
                    </div>
                    <div class="settings-row">
                        <label for="num_format">Number format</label>
                        <select id="num_format" class="sidebar-control" style="width: 140px;">
                            <option value="us">US (1,234.56)</option>
                            <option value="eu">EU (1.234,56)</option>
                        </select>
                    </div>
                </div>
                <div class="settings-section">
                    <div class="settings-section-title">Backtesting</div>
                    <div class="settings-row">
                        <label for="default_capital">Default initial capital</label>
                        <input id="default_capital" type="text" class="sidebar-control" style="width: 120px;" value="100000" />
                    </div>
                </div>
            </Panel>
        </div>
    }
}
