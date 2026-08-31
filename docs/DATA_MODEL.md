# Data model

CGE's most important implementation choice is that it stores captured commanders in **numbered country-level slots** and keeps a live character event target attached to each slot.

## Slot indexing

`cge_captured_general_count` is the current high-level slot count. Most loops run from `1` through that count and put the current index in `cge_slot_iter` or `cge_slot_arg`.

A slot is considered populated when the player country has:

```text
cge_has_candidate_<slot>
```

The live character for the slot is kept as:

```text
event_target:cge_slot_<slot>_runtime_leader
```

Many slot fields are generated through `meta_effect` because HOI4 script cannot otherwise dynamically substitute a variable index into a variable/flag name.

## Important slot fields

The complete slot schema is spread across the sorting/character-registry files, but these fields are particularly important to gameplay:

| Pattern | Meaning |
|---|---|
| `cge_slot_N_character_key` | Stable/generated character identity key used by CGE |
| `cge_slot_N_origin_country` | Scoped variable/reference for the commander's historical country of origin |
| `cge_slot_N_held_state` | State in which the prisoner is being held / capture-rescue bookkeeping |
| `cge_slot_N_patience` | Persistent Patience value |
| `cge_slot_N_cooperation` | Persistent Cooperation value |
| `cge_slot_N_executed` | Execution state |
| `cge_slot_N_recruited` | General has been recruited into the captor's service |
| `cge_slot_N_pow_collaborator` | Recruit POWs has been completed for this general |
| `cge_slot_N_blackmail_used` | Prevents repeat successful Blackmail |
| `cge_slot_N_*_timer_*` | Patience/Cooperation operation timer state |
| `cge_slot_N_*_selected_action` | Operation selected for that side of the overview |
| `cge_slot_N_history_*` | Per-general operation history, up to the displayed history capacity |
| `cge_slot_N_recruitment_date` | Date the officer changed sides |

When a slot is removed, [`cge_release_remove_selected_slot`](../common/scripted_effects/cge_core_effects.txt#L106) compacts the registry so later loops still operate over a contiguous set.

## Character flags

Important character-side mirrors include:

| Flag | Meaning |
|---|---|
| `cge_captured_by_player` | Character is currently considered a CGE prisoner of the player |
| `cge_bribed_by_player` | Successful bribe state |
| `cge_recruited_by_player` | Character was recruited into the player's army |
| `cge_pow_recruitment_unlocked` | Character completed Recruit POWs and can act as a collaborator/recruiter |
| `cge_postwar_fate_processed` | Temporary marker preventing duplicate fate events in one origin pass |
| `cge_postwar_processed_this_settlement` | Temporary postwar settlement bookkeeping |
| `cge_postwar_repatriate_remove` | Temporary marker used while removing a repatriated slot |

## UI cache

The UI loads the selected slot into non-indexed variables such as:

- `cge_cache_valid`
- `cge_cache_executed`
- `cge_cache_recruited`
- `cge_cache_bribed`
- `cge_cache_pow_collab`
- `cge_cache_patience`
- `cge_cache_cooperation`
- trial state cache variables

The overview itself uses `cge_overview_*` variables for the displayed values, operation selections, timers, history rows, POW pool values, and sorting state.

[`cge_refresh_selected_cache`](../common/scripted_effects/cge_overview_effects.txt#L252) is therefore one of the most important UI synchronization effects.

## POW origin-country state

POW pools are stored on/associated with the **origin country**, while the captor loads them into working/UI variables. Important concepts include:

- total/baseline POW pool;
- recruitable POW pool;
- spent POW manpower;
- current recruiter character key;
- recruiter efficiency;
- measured template manpower/equipment requirements.

The load/modify/store flow is visible in:

- [`cge_pow_load_pool`](../common/scripted_effects/cge_prisoner_effects.txt#L598)
- [`cge_pow_store_pool`](../common/scripted_effects/cge_prisoner_effects.txt#L611)
- [`cge_pow_store_recruiter`](../common/scripted_effects/cge_prisoner_effects.txt#L631)
- [`cge_pow_weekly_update`](../common/scripted_effects/cge_prisoner_effects.txt#L851)

Per-slot wrappers in `cge_slot_effects.txt` bridge a selected general's origin to those origin-country pool effects.

## Postwar state

The postwar system uses country flags plus global event targets as a small state machine.

### Core event targets

| Event target | Meaning |
|---|---|
| `cge_postwar_origin` | Historical origin currently being settled |
| `cge_postwar_destination` | Country to which prisoners should return / subject government being managed |
| `cge_postwar_general` | Recruited officer currently making/receiving a postwar decision |
| `cge_postwar_watch_captor` | Human captor during peace-detection loops |
| `cge_postwar_detected_origin` | Origin found by peace detection |
| `cge_postwar_candidate_1..3` | Governor candidates on the current page |

Display arrays such as `cge_postwar_origin_display`, `cge_postwar_destination_display`, and `cge_postwar_general_display` exist because scripted localisation often resolves more reliably from arrays than from transient event targets.

### Core country flags

| Flag | Meaning |
|---|---|
| `cge_postwar_watch_active` | Captor has at least one origin whose war-end transition still matters |
| `cge_postwar_was_at_war_with_player` | Stored on an origin country to remember that it was at war with the captor |
| `cge_postwar_queue_active` | An origin queue is currently being processed |
| `cge_postwar_current_origin` | Temporary marker on the historical origin being processed |
| `cge_postwar_waiting_for_general_decision` | Prevents another general decision from being scheduled simultaneously |
| `cge_postwar_destination_is_subject` | Resolved destination is a player subject; enables governor phase |
| `cge_postwar_governor_considered` | Governor offer has already been considered for this origin pass |
| `cge_postwar_waiting_for_governor` | Governor proposal is pending |
| `cge_postwar_fate_phase_active` | Recruited-general fate scan has been initialized |
| `cge_postwar_autonomy_request_fired` | Restoration request was generated in the current collaborator scan |
| `cge_postwar_has_cge_governor` | Subject currently has a CGE-installed military governor |

### Core arrays/variables

- `cge_postwar_origin_queue` — origins waiting to be settled.
- `cge_postwar_autonomy_candidates` — recruited officers eligible to make the one random restoration request.
- `cge_postwar_selected_slot` — slot tied to the current general decision.
- `cge_postwar_governor_cursor` — pagination cursor.
- `cge_postwar_candidate_slot_1..3` — selected candidate slots for the current governor page.
- `cge_postwar_installed_by_country` — stored on the subject to remember the installing overlord.
