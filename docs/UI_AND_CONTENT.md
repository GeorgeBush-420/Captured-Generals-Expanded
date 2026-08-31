# UI, localisation, portraits, and generated content

## Interface files

### `interface/cge_interface.gui`

Defines the actual HOI4 windows and controls. Major sections include:

- `cge_widget_window` — small launcher/count widget.
- `cge_main_window` — captured-general list, sorting controls, executed filter, close button.
- `cge_captured_general_native_entry` — each row: portrait, status overlays, rank/name, traits, stats, origin/captor flags, Overview button.
- `cge_overview_window` — detailed prisoner view.
- Patience panel — six action buttons, timer, progress bar, start/cancel controls.
- Cooperation panel — six action buttons, timer, progress bar, start/cancel controls.
- Profile panel — selected commander's portrait/name/rank/status.
- History panel — operation history.
- POW panel — origin-country POW totals, recruiter, efficiency, and division controls.

### `interface/cge_interface.gfx`

Registers the general CGE sprites used by the GUI.

### `interface/cge_runtime_portraits.gfx`

Large generated/runtime portrait sprite registry. It maps portrait identifiers to graphics so captured/recruited characters can keep a usable portrait in the custom UI.

## Scripted GUI

[`common/scripted_guis/cge_ui_scripted_gui.txt`](../common/scripted_guis/cge_ui_scripted_gui.txt) binds UI widget actions and visibility to script.

The primary GUI is `cge_overview_window_gui`. Its `visible` block checks `cge_show_overview_window`.

The `effects` section translates clicks into gameplay state, for example:

- `cge_overview_patience_decrease_click` selects Harsher Confinement.
- `cge_overview_patience_increase_click` selects Threaten.
- `cge_overview_blackmail_click` selects Blackmail.
- `cge_overview_interrogate_click` selects Interrogate.
- `cge_overview_put_on_trial_click` selects Put on Trial.
- `cge_overview_execute_click` selects Execute.
- Cooperation-side effects do the equivalent for Eased Confinement, Propagandize, Bribe, Extract Intel, Recruit General, and Recruit POWs.

Each selection re-runs `cge_refresh_selected_cache` and `cge_update_timer_frames` so button states and timer art stay synchronized.

Sorting overlay triggers near the bottom of the file expose ascending/descending indicators based on the current sort field/direction.

## Overview effects

[`common/scripted_effects/cge_overview_effects.txt`](../common/scripted_effects/cge_overview_effects.txt) contains UI synchronization helpers:

| Effect | Role |
|---|---|
| `cge_open_overview` | Opens/initializes the overview for a selected slot |
| `cge_update_list_scroll` | Maintains list scrolling state |
| `cge_pow_calc_origin` | Resolves the selected general's origin for POW display |
| `cge_pow_refresh_selected` | Updates selected POW information |
| `cge_pow_refresh` | Refreshes POW UI state |
| `cge_update_selected_progress` | Synchronizes progress bars |
| `cge_refresh_selected_cache` | Copies selected slot values into the UI cache |
| `cge_calc_timer_frame` / `cge_update_timer_frames` | Converts operation timer progress into the circular timer-frame display |

## Portrait handling

[`common/scripted_effects/cge_portrait_assignment.txt`](../common/scripted_effects/cge_portrait_assignment.txt) chooses runtime/fallback portraits. `cge_assign_runtime_portrait_male_pool` handles the large male runtime pool, while `cge_assign_female_portrait` handles female assignments.

[`common/scripted_effects/cge_recruitment_portraits.txt`](../common/scripted_effects/cge_recruitment_portraits.txt) swaps to the appropriate recruited portrait presentation when a commander changes sides.

## Scripted localisation

Scripted localisation lets the UI/events resolve a character, country, trait, or portrait from CGE's stored keys.

- [`cge_scripted_localisation.txt`](../common/scripted_localisation/cge_scripted_localisation.txt) — general CGE text resolvers.
- [`cge_postwar_scripted_localisation.txt`](../common/scripted_localisation/cge_postwar_scripted_localisation.txt) — selected postwar origin/general/destination names.
- [`cge_portrait_resolvers.txt`](../common/scripted_localisation/cge_portrait_resolvers.txt) — large portrait lookup table.
- [`cge_trait_resolvers.txt`](../common/scripted_localisation/cge_trait_resolvers.txt) — large trait lookup table.

## English localisation

- `cge_l_english.yml` — main UI, operations, trial, execution, recruitment, POW text.
- `cge_postwar_l_english.yml` — restoration, repatriation, governor, and recruited-general fate text.
- `cge_registry_l_english.yml` — generated/registry names used by character resolution.
- `cge_runtime_portrait_sprites_l_english.yml` — runtime portrait sprite/localisation bridge.
- `cge_resolver_bridge_l_english.yml` — resolver bridge keys.
- `cge_trait_tooltips_l_english.yml` — trait display/tooltips.

## GFX assets

`gfx/interface/cge_assets/` contains the custom CGE visual assets, including:

- menu/open/close art;
- captured/recruited status overlays;
- execution skull, weapon, crack, portrait tint, and strike-through overlays;
- history background/interior;
- cooperation bar background;
- tiled UI background.

## Files that behave like generated registries

These files are unusually large and should be treated carefully:

- `common/scripted_effects/cge_character_registry.txt`
- `common/scripted_effects/cge_pow_templates.txt`
- `common/scripted_localisation/cge_portrait_resolvers.txt`
- `common/scripted_localisation/cge_trait_resolvers.txt`
- `common/scripted_effects/cge_pow_templates.txt`
- `interface/cge_runtime_portraits.gfx`
- matching large localisation bridge files

A small manual edit can break a lookup chain far away from the edited line. For feature work, prefer changing the smaller orchestration files unless the new feature truly requires adding registry data.
