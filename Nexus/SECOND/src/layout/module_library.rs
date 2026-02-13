use crate::models::modules::{all_module_meta, ModuleMeta};
use crate::models::{GridPosition, GridSize};
use crate::layout::workspace::WorkspaceLayoutState;
use leptos::*;

#[component]
pub fn ModuleLibrary(
    layout: RwSignal<WorkspaceLayoutState>,
) -> impl IntoView {
    let modules = all_module_meta();

    view! {
        <aside class="module-library">
            <div class="module-library-header">
                <h2>Module Library</h2>
                <p class="module-library-hint">Drag or click to add to workspace</p>
            </div>
            <ul class="module-library-list">
                {modules
                    .into_iter()
                    .map(|meta| {
                        let layout = layout;
                        view! {
                            <li class="module-library-item" key=meta.id>
                                <ModuleLibraryCard meta=meta layout=layout />
                            </li>
                        }
                    })
                    .collect_view()}
            </ul>
        </aside>
    }
}

#[component]
fn ModuleLibraryCard(
    meta: ModuleMeta,
    layout: RwSignal<WorkspaceLayoutState>,
) -> impl IntoView {
    let meta_id = meta.id.to_string();
    let on_click = move |_| {
        let pos = layout.get().find_free_region(meta.default_width, meta.default_height)
            .unwrap_or(GridPosition { col: 0, row: 0 });
        let size = GridSize {
            w: meta.default_width,
            h: meta.default_height,
        };
        layout.update(|s| {
            s.add_module(meta_id.clone(), pos, size);
        });
    };

    view! {
        <button
            type="button"
            class="module-library-card"
            on:click=on_click
            title=meta.description
            data-module-id=meta.id
        >
            <span class="module-library-card-name">{meta.name}</span>
            <span class="module-library-card-desc">{meta.description}</span>
        </button>
    }
}
