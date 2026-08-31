# Code reference

This is the implementation-oriented map of the repository. Line links refer to the current documented version and may move after edits.

## `common/on_actions`

### `cge_gameplay_on_actions.txt`

- `on_deployed_leader_defeated` — detects capturable leaders defeated by the human player and calls `cge_register_capture`.
- `on_daily` — initializes registry state, runs the daily captured-general tick, updates visible UI, and runs a true seven-day POW update.
- `on_state_control_changed` — probes prisoner held-state changes and schedules a cleanup if a captured general may have been liberated/rescued.

### `cge_postwar_on_actions.txt`

- `on_peaceconference_ended` — arms exact origin matching from peace-conference scopes and schedules a deferred scan.
- `on_peace` — schedules scans for human countries with an active postwar watcher.

## `common/scripted_effects`

### `cge_core_effects.txt`

| Effect | Purpose |
|---|---|
| `cge_register_capture` | Main capture entry point; snapshots and registers a defeated leader |
| `cge_refresh_alive_count` | Recounts living captured generals |
| `cge_refresh_list_state` | Rebuilds/synchronizes list state after changes |
| `cge_release_remove_selected_slot` | Removes one numbered slot and compacts later slots |
| `cge_remove_released_generals` | Cleans slots whose leaders are no longer valid prisoners |

### `cge_character_registry.txt`

| Effect | Purpose |
|---|---|
| `cge_clear_capture_temp_data` | Clears temporary variables/targets used during snapshotting |
| `cge_snapshot_live_stats_on_from` | Reads live rank/skill/stat information from the character |
| `cge_identify_character_on_from` | Resolves the character into CGE's registry/key system |
| `cge_identify_character_on_from_base` | Base identity lookup implementation |
| `cge_append_capture_trait_id` | Appends a captured trait key into the snapshot |
| `cge_snapshot_live_traits_on_from` | Copies current leader traits into CGE storage |
| `cge_snapshot_held_state_on_from` | Records the state associated with captivity |
| `cge_prepare_capture_snapshot_on_from` | Orchestrates the complete pre-slot snapshot |
| `cge_capture_character_stats` | Final character-stat capture helper |

This is a large registry/lookup file; most feature code should call its public helpers rather than duplicate its identity logic.

### `cge_sorting_effects.txt`

| Effect | Purpose |
|---|---|
| `cge_clear_slot_data` | Reset all fields for one slot |
| `cge_copy_slot_data` | Copy one slot to another during compaction/reordering |
| `cge_mirror_slot_to_character` | Mirror important slot values onto the runtime character |
| `cge_init_slot` / `cge_init_slots` | Initialize one/all slot structures |
| `cge_rebuild_display_unsorted` | Create list display order without sorting |
| `cge_load_candidate_sort_key` | Load the active field for one sort candidate |
| `cge_consider_sort_candidate` | Compare a candidate against current best candidate |
| `cge_sort_display` | Sort the display array |
| `cge_list_init_slots` | Initialize list slot state |
| `cge_list_rebuild` | Rebuild the list from registry data |
| `cge_list_refresh` | Refresh list presentation |
| `cge_list_sync` | Synchronize current sort/display state |
| `cge_list_sync_unsorted` | Synchronize without applying sort |
| `cge_cycle_sort_field` | Change sort direction/field state |
| `cge_reapply_sort` | Reapply current sorting after data changes |
| `cge_sort_*_click` | Per-column click handlers for level/name/attack/defense/planning/logistics/capacity |

### `cge_overview_effects.txt`

| Effect | Purpose |
|---|---|
| `cge_open_overview` | Open overview for selected general and initialize display data |
| `cge_update_list_scroll` | Maintain list scrolling |
| `cge_pow_add_digit` | Numeric helper for POW display calculations |
| `cge_pow_calc_origin` | Resolve selected officer's origin for POW UI |
| `cge_pow_refresh_selected` | Refresh POW values for selected general |
| `cge_pow_refresh` | General POW panel refresh |
| `cge_update_selected_progress` | Update selected operation progress values |
| `cge_refresh_selected_cache` | Copy selected slot state into non-indexed cache/UI variables |
| `cge_calc_timer_frame` | Calculate a timer-circle frame |
| `cge_update_timer_frames` | Refresh both operation timer graphics |

### `cge_operation_effects.txt`

| Effect | Purpose |
|---|---|
| `cge_pay_patience_cost` | Deduct up-front cost for selected Patience operation |
| `cge_refund_patience_cost` | Refund canceled Patience operation |
| `cge_refund_cooperation_cost` | Refund canceled Cooperation operation |
| `cge_set_patience_duration` | Write the selected Patience operation duration |
| `cge_set_cooperation_duration` | Write the selected Cooperation operation duration |
| `cge_sync_patience_decay` | Recalculate UI-visible weekly decay |
| `cge_update_patience_modifiers` | Recalculate country penalties tied to prisoner operations |
| `cge_history_clear_view` | Clear the displayed operation-history rows |
| `cge_history_load` | Load selected general's saved history into UI variables |
| `cge_history_add_patience` | Append a completed Patience-side operation to history |
| `cge_history_add_cooperation` | Append a completed Cooperation-side operation to history |
| `cge_select_cooperation_op` | Select/copy Cooperation operation state into the slot |
| `cge_pay_cooperation_cost` | Apply Cooperation-side costs/modifiers |
| `cge_cancel_cooperation_state` | Reset Cooperation operation state |
| `cge_update_consumer_penalty` | Recalculate consumer-goods penalty modifier |
| `cge_sync_executed_generals` | Keep execution status mirrored/consistent |
| `cge_execute_selected_general` | Performs live-character execution handling |
| `cge_start_patience_op` / `cge_cancel_patience_op` | Start/cancel selected Patience operation |
| `cge_start_cooperation_op` / `cge_cancel_cooperation_op` | Start/cancel selected Cooperation operation |
| `cge_select_patience_op` / `cge_load_patience_op` | Save/load Patience operation selection |
| `cge_cancel_patience_state` | Reset Patience operation state |
| `cge_trial_start` | Initialize trial variables/targets/event chain |
| `cge_trial_cancel` | Cancel active trial and clean state |
| `cge_trial_finish_condemn` | Apply final condemn route |
| `cge_trial_finish_convict` | Apply final conviction route |
| `cge_trial_finish_plea` | Apply plea agreement and reduced recruitment threshold window |
| `cge_roll_death_overlay` / `cge_roll_death_weapon` | Randomize execution presentation |
| `cge_init_death_overlays` / `cge_assign_death_overlay` | Initialize/apply death overlay state |

### `cge_daily_effects.txt`

| Effect | Purpose |
|---|---|
| `cge_daily_update_captured_generals` | Main daily loop over captured-general slots |
| `cge_slot_count_alive` / `cge_calc_alive_count` | Alive-count helpers |
| `cge_slot_patience_decay` | Applies passive decay/protection rules |
| `cge_slot_tick_operations` | Decrements operation timers and dispatches completions |
| `cge_slot_tick_trial` | Advances trial timing/events |
| `cge_slot_finish_eased` | Finish Eased Confinement special state |
| `cge_slot_repair_execution` | Repair inconsistent execution state |
| `cge_slot_finish_execution` | Finish execution operation and events |
| `cge_slot_finish_patience_op` | Resolve selected Patience-side operation |
| `cge_slot_finish_cooperation_op` | Resolve selected Cooperation-side operation, including recruitment and POW unlock |
| `cge_slot_apply_recruitment` | Normalize slot/UI state after recruitment |
| `cge_slot_calc_consumer_penalty` / `cge_recalc_consumer_penalty` | Compute global consumer-goods modifier from active prisoner states |
| `cge_slot_calc_patience_modifiers` / `cge_recalc_patience_modifiers` | Compute interrogation/trial temporary modifiers |
| `cge_slot_apply_execution` / `cge_apply_executions` | Apply/synchronize executions |

### `cge_event_effects.txt`

`cge_trial_prepare_slot` and `cge_trial_finish_slot_refresh` bridge trial events to the selected slot. The remaining `cge_trial_stage*` effects implement each event option from `cge_trial.1` through `.4`.

### `cge_prisoner_effects.txt`

| Effect | Purpose |
|---|---|
| `cge_pow_origin_derive_total_effect` | Derive total POW pool from origin-country losses/casualties |
| `cge_pow_prepare_template` | Resolve/create the canonical POW division template |
| `cge_pow_refresh_selected_ui_effect` | Push current pool data into the overview |
| `cge_pow_measure_template` | Measure manpower/equipment requirements |
| `cge_pow_raise_division_effect` | Validate/deduct/spawn one POW division |
| `cge_pow_clear_origin_recruiter_effect` | Remove recruiter assignment on an origin pool |
| `cge_pow_calc_bonus` | Calculate recruiter efficiency/capture bonus |
| `cge_pow_clear_ui` | Reset displayed POW values |
| `cge_pow_init_pool_state` | Initialize missing pool state |
| `cge_pow_update_highwater` | Track casualty/pool high-water state |
| `cge_pow_update_baseline` | Update baseline pool from casualties |
| `cge_pow_reset_work` | Clear temporary working values |
| `cge_pow_load_pool` / `cge_pow_store_pool` | Load/store origin-country POW pool state |
| `cge_pow_clear_recruiter_marks` | Remove current recruiter markers |
| `cge_pow_store_recruiter` | Store selected collaborator as recruiter |
| `cge_pow_find_recruiter_mark` | Resolve the saved recruiter character |
| `cge_pow_calc_work_values` | Calculate recruitable/weekly/efficiency working values |
| `cge_pow_refresh_ui` | Refresh POW panel |
| `cge_pow_assign_recruiter` / `cge_pow_unassign_recruiter` | Change recruiter assignment |
| `cge_pow_spend_pool` | Permanently deduct POW manpower spent on formations |
| `cge_pow_weekly_update` | Seven-day passive POW update |
| `cge_pow_clear_recruiter_status` / `cge_pow_apply_recruiter_status` | Manage the recruiter status trait |
| `cge_pow_measure_equipment_need` | Calculate equipment requirement/free captured-rifle amount |
| `cge_pow_spawn_or_fallback_effect` | Spawn the desired division or use fallback behavior |

### `cge_pow_templates.txt`

Large generated/compatibility implementation. Main public helpers:

- `cge_pow_select_template`
- `cge_pow_probe_manpower`
- `cge_pow_measure_equipment`
- `cge_pow_spawn_template`
- `cge_pow_spawn_origin`
- `cge_pow_spawn_selected`

### `cge_slot_effects.txt`

This file contains small per-slot wrappers used by systems that need a dynamic slot index.

| Effect | Purpose |
|---|---|
| `cge_slot_rescue_probe` | Detect whether a changed state may have freed a prisoner |
| `cge_slot_postwar_init` | Clear fate marker on eligible recruited officers at phase start |
| `cge_slot_postwar_fate` | Pick the next recruited officer and roll return/stay preference |
| `cge_slot_postwar_cleanup` | Clear temporary fate markers |
| `cge_slot_postwar_autonomy_candidate` | Add eligible recruited officer to restoration-request candidate array |
| `cge_slot_governor_probe` | Test whether slot can be a military governor |
| `cge_slot_clear_postwar_flag` | Clear settlement marker on one slot's character |
| `cge_slot_arm_origin` | Mark exact peace-conference origin and activate watcher |
| `cge_slot_postwar_watch` | Remember that this origin was at war with the captor |
| `cge_slot_postwar_detect` | Detect transition to peace and queue the origin |
| `cge_slot_sync_patience_decay` | Selected-slot decay helper |
| `cge_slot_pow_*` | Bridge selected slot/origin into POW pool load/store/recruiter/weekly operations |
| `cge_slot_init_death_overlay` | Initialize execution overlay state for one slot |

### `cge_postwar_effects.txt`

| Effect | Purpose |
|---|---|
| `cge_postwar_prepare_event` | Populate display arrays/event data before visible postwar events |
| `cge_postwar_begin_origin` | Resolve destination, ordinary repatriation, then start origin processing |
| `cge_postwar_begin_origin_core` | Initialize per-origin state and branch based on war/existence |
| `cge_postwar_finish_origin` | Route through governor phase if needed, otherwise final cleanup |
| `cge_postwar_finish_origin_core` | Clear origin state and advance queue/watch scan |
| `cge_postwar_repatriate` | Send ordinary prisoners home/remove their slots |
| `cge_postwar_scan_collaborators` | Central postwar dispatcher for governor/restoration/fate phases |
| `cge_postwar_try_autonomy_request` | Build recruited-officer pool and randomly fire one restoration request |
| `cge_postwar_scan_recruited_fates` | Process recruited officers' return/stay choices one by one |
| `cge_postwar_send_home` | Release selected officer to destination and remove CGE slot |
| `cge_postwar_reimprison` | Revoke recruited/collaborator state and return selected officer to captivity |
| `cge_postwar_restore_origin_as_puppet` | Restore annexed origin, preserve player cores/claims, and arm governor path |
| `cge_postwar_offer_governor` | Check for candidates and schedule governor proposal |
| `cge_postwar_build_governor_page` | Load up to three governor candidates and pagination state |
| `cge_postwar_appoint_selected_governor` | Transfer/promote chosen general into subject leadership |
| `cge_postwar_watch_tick` | Run peace-state watch and detection over all slots |
| `cge_postwar_arm_exact_peace_origin` | Use peace-conference origin scope to arm relevant slots |
| `cge_postwar_schedule_event_scan` | One-hour deferred scan with duplicate guard |
| `cge_postwar_refresh_list` | Refresh CGE list after postwar changes |
| `cge_postwar_remove_selected_slot` | Remove the currently selected postwar slot |
| `cge_postwar_remove_repatriated` | Find/remove character marked for repatriation |
| `cge_postwar_continue_after_ordinary` | Pause for repatriation info event or continue immediately |
| `cge_postwar_resolve_destination` | Determine historical/subject destination for postwar returns |
| `cge_postwar_keep_selected_general` | Resolve “remain in our service” choice |
| `cge_postwar_clean_governor_traits` | Remove stale governor state from invalid/non-subject countries |
| `cge_postwar_halve_stats` | Halve selected officer's Patience and Cooperation |

### Small helper files

- `cge_list_effects.txt` — `cge_refresh_list_after_change`, a common post-change list/UI refresh helper.
- `cge_portrait_assignment.txt` — runtime/fallback/female portrait assignment.
- `cge_recruitment_portraits.txt` — recruited portrait replacement.

## `common/scripted_triggers/cge_triggers.txt`

| Trigger | Purpose |
|---|---|
| `cge_is_selected_harsh` / `cge_is_selected_eased` | Current confinement state checks |
| `cge_can_harsher_confinement` | Alive/actionable, enough PP, not eased |
| `cge_can_threaten` | Alive/actionable, enough CP |
| `cge_can_blackmail` | Actionable, unused balance, enough PP |
| `cge_can_interrogate` | Actionable prisoner |
| `cge_can_trial` | Actionable, not already trial-complete, enough PP |
| `cge_can_execute` | Actionable, zero-value execution condition, enough PP |
| `cge_can_patience_operation` | Dispatcher for selected Patience action |
| `cge_patience_70_days` / `cge_patience_140_days` | UI duration grouping helpers |
| `cge_cooperation_70_days` | UI duration grouping helper |
| `cge_is_selected_recruited` | Current slot is recruited |
| `cge_is_selected_bribed` | Current slot was bribed |
| `cge_is_selected_actionable` | Alive and not recruited |
| `cge_can_eased_confinement` | Alive, enough PP, not harsh |
| `cge_can_propagandize` | Alive |
| `cge_can_bribe` | Alive and not already bribed |
| `cge_can_extract_intel` | Alive, Cooperation/Patience thresholds, enough CP |
| `cge_can_recruit_general` | Normal or plea-window recruitment thresholds and PP |
| `cge_can_recruit_pows` | 100 Cooperation, >75 Patience, not already unlocked |
| `cge_can_cooperation_operation` | Dispatcher for selected Cooperation action |
| `cge_is_selected_alive` / `cge_is_selected_executed` | Execution-state helpers |
| `cge_can_selected_blackmail` / `cge_blackmail_done` | One-time Blackmail guard |
| `cge_can_selected_execute` | Requires zero Patience and Cooperation |
| `cge_pow_unlocked` | Recruit POWs has been completed |
| `cge_pow_collaborator` | Alive, unrecruited POW collaborator status |
| `cge_trial_complete` | Trial completion status |
| `cge_trial_plea_active` | Reduced recruitment threshold window active |

## Events

### `events/cge_gameplay_events.txt`

| Event | Purpose |
|---|---|
| `cge.1` | Hidden: show main CGE window flag |
| `cge.2` | Hidden: hide main CGE window flag |
| `cge_execution.1` | Local execution acknowledgement/event |
| `cge_execution_news.1` | Major execution news event with executor/origin/third-party options |
| `cge_recruitment.1` | Recruited commander's “changes sides” event |
| `cge_trial.1` | Trial stage 1: choose public/military/plea route |
| `cge_trial.2` | Trial stage 2: react to testimony/defiance |
| `cge_trial.3` | Trial stage 3: route-specific handling |
| `cge_trial.4` | Trial stage 4: condemn/convict/plea verdict |
| `cge_state_rescue_refresh.1` | Hidden cleanup after relevant state control changes |

### `events/cge_postwar_events.txt`

See the full table and flow in [`POSTWAR_SYSTEM.md`](POSTWAR_SYSTEM.md).

## Traits/modifiers

### `common/unit_leader/cge_pow_recruiter_status_traits.txt`

`cge_pow_recruiter_status` is a status trait applied while a collaborator is assigned to POW recruitment. It sets `skill_bonus_factor = -1` and `cannot_use_abilities = 1`, effectively taking that officer off normal command duty.

### `common/country_leader/cge_postwar_traits.txt`

`cge_postwar_eager_collaborator` is applied to a CGE-installed military governor. It reduces autonomy gain and increases civilian-industry transfer to the overlord.

### `common/dynamic_modifiers/cge_dynamic_modifiers.txt`

- `cge_cooperation_consumer_goods_penalty` — dynamic consumer-goods penalty from concessions/propaganda/bribes.
- `cge_patience_interrogation_pp_penalty` — Political Power Gain penalty while interrogations run.
- `cge_patience_trial_consumer_goods_penalty` — consumer-goods penalty while trials run.

## Localisation and graphics

See [`UI_AND_CONTENT.md`](UI_AND_CONTENT.md) for the localisation, scripted-localisation, interface, sprite, portrait, and generated-registry files.
