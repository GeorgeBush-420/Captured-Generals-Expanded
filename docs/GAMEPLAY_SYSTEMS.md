# Gameplay systems

This page describes the mechanics as implemented by the current scripts. User-facing wording comes from [`localisation/english/cge_l_english.yml`](../localisation/english/cge_l_english.yml).

## Captured-general overview

A captured commander receives persistent **Patience** and **Cooperation** values and can be managed through the CGE overview window. The current selected slot is copied into `cge_overview_*`/`cge_cache_*` variables for display and trigger checks.

### Patience-side operations

| Operation | Duration | Cost | Main result |
|---|---:|---|---|
| Harsher Confinement | 30 days | 50 Political Power | -10 Patience; doubles normal weekly Patience decay while active |
| Threaten | 30 days | 10 Command Power | ±25 Patience depending on success; success chance falls with rank/level |
| Blackmail | 70 days | 100 Political Power | +50 Patience; one successful use per captured general |
| Interrogate | 70 days | -10% Political Power Gain while active | Chance/guarantee to gain Army Intel; failure costs Patience |
| Put on Trial | 140 days | 100 Political Power + 5% Consumer Goods Factor while active | Runs the four-stage trial chain; pauses passive Patience and Cooperation decay |
| Execute | 30 days | 200 Political Power + 1 manpower | Permanently executes the commander; requires exactly 0 Patience and 0 Cooperation |

Costs that are paid up front are refunded when the operation is canceled. The relevant cost and duration code starts at [`cge_pay_patience_cost`](../common/scripted_effects/cge_operation_effects.txt#L2) and [`cge_set_patience_duration`](../common/scripted_effects/cge_operation_effects.txt#L24).

### Cooperation-side operations

| Operation | Duration | Requirements / cost | Main result |
|---|---:|---|---|
| Eased Confinement | 30 days | 50 Political Power | +10 Cooperation; suppresses Patience decay while active and for 70 days afterward |
| Propagandize | 70 days | +10% Consumer Goods Factor while active | Cooperation gain = `30 × ruling-party popularity`, clamped to 10–30 |
| Bribe | 30 days | Must not have been bribed already | +35 Cooperation; persistent +10% consumer-goods penalty while that bribed general remains imprisoned |
| Extract Intel | 70 days | 50+ Cooperation, >25 Patience, 10 Command Power | +10 intel in all four categories, +10% decryption, -10 Patience |
| Recruit General | 30 days | 200 Political Power; normally 75+ Cooperation and 50+ Patience | Releases the prisoner and transfers them into the player's army |
| Recruit POWs | 70 days | 100 Cooperation and >75 Patience; one-time unlock | Turns the officer into a POW collaborator/recruiter candidate without recruiting them as a normal general |

The eligibility rules are centralized in [`common/scripted_triggers/cge_triggers.txt`](../common/scripted_triggers/cge_triggers.txt), especially `cge_can_recruit_general` and `cge_can_recruit_pows`.

## Passive decay

Normal weekly Patience decay is 1%. Harsher Confinement raises it to 2%. Eased Confinement suppresses Patience decay while active and for its protection period. Cooperation decay is calculated from the prisoner's current state and is also paused during an active trial.

The daily engine-side tick is [`cge_daily_update_captured_generals`](../common/scripted_effects/cge_daily_effects.txt#L1); the UI-facing decay calculation is synchronized through [`cge_sync_patience_decay`](../common/scripted_effects/cge_operation_effects.txt#L139).

## Trials

A trial lasts 140 days and launches four decision stages.

1. **Purpose of the trial** (`cge_trial.1`): public show trial, military tribunal, or plea negotiations.
2. **Prisoner reaction** (`cge_trial.2`): press harder, preserve credibility, or offer leniency.
3. **Route-specific handling** (`cge_trial.3`): propaganda/control, exemplary/legal military route, or formal/hardline plea bargaining.
4. **Verdict** (`cge_trial.4`): condemn, convict, or accept a plea agreement when allowed.

The option effects are small wrappers in [`common/scripted_effects/cge_event_effects.txt`](../common/scripted_effects/cge_event_effects.txt). This keeps event files mostly declarative.

A successful plea agreement grants +25 Cooperation and +5 Patience, with route-dependent bonuses. It also enables a 70-day reduced recruitment threshold: **50 Cooperation / 25 Patience** instead of the normal 75/50 requirement.

## Recruitment

When Recruit General completes, the slot is marked recruited, the character is released from captivity, nationality is changed to the captor, `cge_recruited_by_player` is set, the recruited portrait is applied, and `cge_recruitment.1` is fired.

The recruitment event grants the captor +5% War Support and +5% ruling-party popularity.

The main completion path is in [`cge_slot_finish_cooperation_op`](../common/scripted_effects/cge_daily_effects.txt#L897).

## Execution

Execution is only available when both Patience and Cooperation are exactly zero and costs 200 Political Power plus 1 manpower. When completed, the character is marked executed, receives a randomized death overlay/weapon presentation, and the local execution event plus major news event are fired.

The captor gains +5% War Support; the origin country receives -5% War Support where applicable.

Relevant code:

- [`cge_execute_selected_general`](../common/scripted_effects/cge_operation_effects.txt#L698)
- [`cge_slot_finish_execution`](../common/scripted_effects/cge_daily_effects.txt#L492)
- [`cge_execution.1`](../events/cge_gameplay_events.txt#L27)
- [`cge_execution_news.1`](../events/cge_gameplay_events.txt#L41)

## POW recruitment

POW recruitment is tracked per origin country.

### Pool size

The base Total POW pool uses **25% of cumulative casualties inflicted on that origin country**. Manpower spent on raised POW divisions is permanently deducted from the pool.

### Recruitable POWs

A repaired/initialized pool begins with 10% of its total as recruitable manpower. Recruitable manpower then grows weekly.

Base weekly conversion is **0.5% of Total POWs**, even with no recruiter. Recruiter efficiency can raise the weekly conversion rate toward **1.0%**.

### Recruiter efficiency

A collaborator assigned as recruiter adds a bonus based on general level:

| Level | Bonus |
|---:|---:|
| 1 | +5 percentage points |
| 2 | +9 |
| 3 | +13 |
| 4 | +17 |
| 5 | +21 |
| 6 | +23 |
| 7+ | +25 |

Field Marshals add +2, with the recruiter bonus capped at +25. This raises the underlying capture/free-rifle rate from 25% toward a maximum of 50%.

While assigned, the recruiter receives `cge_pow_recruiter_status`, which removes command skill effects and disables commander abilities.

### Raising a division

`cge_pow_raise_division_effect` attempts to raise an origin-named POW division in the capital. The canonical default is nine infantry battalions with low equipment priority. The mod measures the actual template manpower requirement before deducting POW manpower and supplies line-infantry rifles according to the current 25–50% capture/free-rifle rate.

The core implementation is [`common/scripted_effects/cge_prisoner_effects.txt`](../common/scripted_effects/cge_prisoner_effects.txt), while [`cge_pow_templates.txt`](../common/scripted_effects/cge_pow_templates.txt) contains the large template compatibility/spawn machinery.
