use crate::models::{GridPosition, GridSize, ModuleInstanceId, PlacedModule};
use leptos::*;
use std::collections::HashSet;

/// In-memory layout state for one workspace (snap-to-grid, positions, sizes).
#[derive(Clone, Default)]
pub struct WorkspaceLayoutState {
    pub modules: Vec<PlacedModule>,
    pub next_id: u64,
    pub grid_cols: u32,
    pub grid_rows: u32,
}

impl WorkspaceLayoutState {
    pub fn new() -> Self {
        Self {
            modules: Vec::new(),
            next_id: 1,
            grid_cols: 12,
            grid_rows: 24,
        }
    }

    pub fn add_module(&mut self, kind: impl Into<String>, position: GridPosition, size: GridSize) {
        let id = ModuleInstanceId(self.next_id);
        self.next_id += 1;
        let kind = kind.into();
        let position = snap_position(position, self.grid_cols, self.grid_rows);
        let size = clamp_size(size);
        self.modules.push(PlacedModule::new(id, kind, position, size));
    }

    pub fn remove_module(&mut self, id: ModuleInstanceId) {
        self.modules.retain(|m| m.id != id);
    }

    pub fn move_module(&mut self, id: ModuleInstanceId, position: GridPosition) {
        if let Some(m) = self.modules.iter_mut().find(|x| x.id == id) {
            m.position = snap_position(position, self.grid_cols, self.grid_rows);
        }
    }

    pub fn resize_module(&mut self, id: ModuleInstanceId, size: GridSize) {
        if let Some(m) = self.modules.iter_mut().find(|x| x.id == id) {
            m.size = clamp_size(size);
        }
    }

    fn occupied_cells(&self) -> HashSet<(u32, u32)> {
        let mut set = HashSet::new();
        for m in &self.modules {
            for c in m.position.col..(m.position.col + m.size.w) {
                for r in m.position.row..(m.position.row + m.size.h) {
                    set.insert((c, r));
                }
            }
        }
        set
    }

    /// Find first free cell that can fit (w, h). Simple left-to-right, top-to-bottom.
    pub fn find_free_region(&self, w: u32, h: u32) -> Option<GridPosition> {
        let occupied = self.occupied_cells();
        for row in 0..self.grid_rows.saturating_sub(h) {
            for col in 0..self.grid_cols.saturating_sub(w) {
                let mut ok = true;
                for c in col..(col + w) {
                    for r in row..(row + h) {
                        if occupied.contains(&(c, r)) {
                            ok = false;
                            break;
                        }
                    }
                    if !ok {
                        break;
                    }
                }
                if ok {
                    return Some(GridPosition { col, row });
                }
            }
        }
        None
    }
}

fn snap_position(p: GridPosition, max_col: u32, max_row: u32) -> GridPosition {
    GridPosition {
        col: p.col.min(max_col.saturating_sub(1)),
        row: p.row.min(max_row.saturating_sub(1)),
    }
}

fn clamp_size(s: GridSize) -> GridSize {
    GridSize {
        w: s.w.clamp(1, 12),
        h: s.h.clamp(1, 8),
    }
}

#[component]
pub fn Workspace(
    layout: RwSignal<WorkspaceLayoutState>,
    children: Children,
) -> impl IntoView {
    let state = move || layout.get();
    let grid_style = move || {
        let s = state();
        format!(
            "display: grid; grid-template-columns: repeat({}, 1fr); grid-template-rows: repeat({}, minmax(80px, auto)); gap: 12px; padding: 16px; min-height: 100%;",
            s.grid_cols,
            s.grid_rows,
        )
    };

    view! {
        <div class="workspace-grid" style=grid_style>
            {children()}
        </div>
    }
}
