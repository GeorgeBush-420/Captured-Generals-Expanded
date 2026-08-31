# Debugging guide

CGE already emits several useful `log =` messages, especially in the postwar system. HOI4's `game.log` and `error.log` are the first places to check when a flow appears to stop.

## Postwar flow

Search `game.log` for `CGE_POSTWAR`.

Expected rough sequence after a relevant war ends:

```text
CGE_POSTWAR peaceconference armed ...
CGE_POSTWAR deferred peace scan ...
CGE_POSTWAR detected peace ...
CGE_POSTWAR processing origin=...
CGE_POSTWAR BEGIN origin=...
```

Then one or more of:

```text
CGE_POSTWAR ordinary prisoners repatriated...
CGE_POSTWAR_AUTONOMY randomly selected ... to request restoration ...
CGE_POSTWAR restored homeland ... marked for military-governor selection.
CGE_POSTWAR restored destination rebound to subject ... governor path armed.
CGE_POSTWAR governor phase precedes recruited-general fate phase.
CGE_POSTWAR at least one recruited governor candidate exists ...
CGE_POSTWAR governor candidate exists; scheduling governor proposal.
CGE_POSTWAR installed custom military governor.
CGE_POSTWAR_FATE ...
```

### Restoration event does not fire

Check these conditions in order:

1. The captured/recruited general still exists in a populated CGE slot.
2. That slot's `cge_slot_N_origin_country` is the country whose war ended.
3. The historical origin no longer exists.
4. The player owns at least one state that is a core of that origin.
5. At least one such state is neither a player core nor a player claim.
6. The officer is living and either `cge_slot_N_recruited > 0` or has `cge_recruited_by_player`.
7. The log reaches `cge_postwar_scan_collaborators` after ordinary prisoner handling.
8. `CGE_POSTWAR_AUTONOMY randomly selected ...` appears. If it does, `cge_postwar.4` has been scheduled for one hour later.

Relevant code: [`cge_postwar_try_autonomy_request`](../common/scripted_effects/cge_postwar_effects.txt#L417).

### Restoration fires but governor proposal does not

After accepting `cge_postwar.4`, look for:

```text
CGE_POSTWAR restored destination rebound to subject ... governor path armed.
```

If that is absent, inspect [`cge_postwar_restore_origin_as_puppet`](../common/scripted_effects/cge_postwar_effects.txt#L620).

If it is present but `.5` still does not fire, verify that at least one remaining CGE slot from the same origin passes [`cge_slot_governor_probe`](../common/scripted_effects/cge_slot_effects.txt#L119): living and recruited. The restoration-request officer can itself be a candidate unless removed/reimprisoned by another branch.

### Peace is never detected

Check whether `cge_postwar_watch_active` is set on the player and whether the origin has/previously received `cge_postwar_was_at_war_with_player`.

The relevant chain is:

```text
on_peaceconference_ended / on_peace
 -> cge_postwar_schedule_event_scan
 -> cge_postwar.99
 -> cge_postwar_watch_tick
 -> cge_slot_postwar_watch
 -> cge_slot_postwar_detect
```

## Capture issues

Capture starts in [`on_deployed_leader_defeated`](../common/on_actions/cge_gameplay_on_actions.txt) and requires `can_be_captured = yes` plus the player scope check. The registration entry point is [`cge_register_capture`](../common/scripted_effects/cge_core_effects.txt#L3).

If the character exists but never appears in the list, inspect `cge_prepare_capture_snapshot_on_from`, `cge_init_slot`, and `cge_list_refresh`/`cge_list_sync`.

## UI appears stale

The most common synchronization helpers are:

- `cge_refresh_selected_cache`
- `cge_update_timer_frames`
- `cge_refresh_list_after_change`
- `cge_pow_refresh_ui`
- `cge_main_window_dirty`

If script state is correct but the screen is stale, trace whether the action that changed state calls the appropriate refresh helper.

## Operation does not start

Eligibility is controlled by [`common/scripted_triggers/cge_triggers.txt`](../common/scripted_triggers/cge_triggers.txt). Check the matching `cge_can_*` trigger first, then verify the UI click selected the expected action number and that the start effect wrote the slot timer/pending state.

## Operation completes with the wrong result

Start/cancel logic is in `cge_operation_effects.txt`, but completion logic is in `cge_daily_effects.txt`. Debug the latter when the timer reached zero correctly but the actual gameplay result is wrong.

## POW division problems

Useful checkpoints are:

1. `cge_pow_load_pool`
2. `cge_pow_calc_work_values`
3. `cge_pow_prepare_template`
4. `cge_pow_measure_template`
5. `cge_pow_raise_division_effect`
6. `cge_pow_spawn_or_fallback_effect`

A failed raise can result from insufficient recruitable POW manpower, inability to measure a valid template, or inability to spawn in the capital. The UI has separate localisation for each failure state.
