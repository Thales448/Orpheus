use serde::{Deserialize, Serialize};

/// Grid position (column, row) in grid units.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct GridPosition {
    pub col: u32,
    pub row: u32,
}

/// Size in grid units (span columns, span rows).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct GridSize {
    pub w: u32,
    pub h: u32,
}

/// Unique id for a placed module instance.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ModuleInstanceId(pub u64);

/// A module instance placed on the grid.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PlacedModule {
    pub id: ModuleInstanceId,
    pub kind: String,
    pub position: GridPosition,
    pub size: GridSize,
}

impl PlacedModule {
    pub fn new(id: ModuleInstanceId, kind: impl Into<String>, position: GridPosition, size: GridSize) -> Self {
        Self {
            id,
            kind: kind.into(),
            position,
            size,
        }
    }
}
