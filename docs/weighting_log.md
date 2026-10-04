# Weighting methods: logbook

This logbook tracks the work to replace judgment-set pillar weights with
quantifiable methods. It's written so that a new Claude session with no
memory can resume from it alone. Read CURRENT STATE first. The history at
the bottom is append-only and timestamped.

## CURRENT STATE

Overwritten at every update.

- **Updated:** 2026-10-04 01:08 UTC
- **Branch:** `feat/weighting-methods`, based on `main` at `1575003`.
- **Phase and step:** Phase 1, monetized cost. Step: writing
  `scratch/weighting/common.py` and `scratch/weighting/monetize.py`.
- **Done:** Phase 0 (summary, plan, decisions approved).
- **In progress:** Phase 1 code. Nothing from Phase 1 is committed yet.
- **Exact next action:** finish `monetize.py`, run it, write the Phase 1
  results into the history, commit, push, and open the draft PR.
- **Files a new session must recreate** (gitignored, not in the repo):
  - Python env: `python -m venv .venv`, then
    `.venv/Scripts/pip install -r requirements.txt` (Windows) or
    `.venv/bin/pip install -r requirements.txt` (macOS).
  - Raw NRI county table, needed for the hazard cost:
    `python -c "from etl.adapters import nri; from pathlib import Path; nri.fetch(Path('data/raw'))"`
    from the repo root. It writes `data/raw/nri/nri_counties.csv`.
  - Not needed for this work: `data/raw/lbnl/` and the untracked
    `scratch/analysis.py` and `scratch/lbnl_unmatched.py` from an earlier
    review. Leave them uncommitted.
- **Tooling notes:**
  - On the Windows machine, `gh` is at `C:\Program Files\GitHub CLI\gh.exe`
    and isn't on the Git Bash PATH. It's authenticated as `ValsTRM`.
  - Git has no global identity on the Windows machine. Commits pass
    `-c user.name="Valaya Choudhary" -c user.email=35052710+ValsTRM@users.noreply.github.com`.
- **Approved decisions** (2026-10-04 01:05 UTC):
  1. Cooling: evaporative where `water_stress_bws` is at most 2, otherwise
     dry. PUE and carbon follow the choice. Dry everywhere is a
     sensitivity.
  2. New York moratorium: 12 months at p=1 as the base case. Basis: 8
     months left on EO 62, plus about a 1/3 chance that the Responsible
     Data Center Development Act is signed and starts a fresh 12-month
     clock (8 + 12 x 0.33, about 12). Sensitivities at 8 and 20 months.
  3. Monthly delay cost: $25M default, with $10M and $50M as sensitivities,
     because delay before construction costs less than delay mid-build.
  4. CRITIC and entropy: primary run on raw values winsorized at the 1st
     and 99th percentiles, then min-max scaled. The percentile version is
     the sensitivity. Weights apply at the column level in a scratch
     composite, not summed into pillars and run through the engine.
     Pillar-summed weights are reported only for comparison, with the
     column-count bias noted.
  5. Franklin versus Grant: report which pillar fails Franklin's floor and
     by how much, the composite crossing point with the floor off, and the
     energy and carbon weight at which Franklin clears the floor. Note in
     the docs that the floor is itself a judgment rule.
  6. Water price: $7 per 1,000 gallons, labeled as an assumption, with $3
     and $15 as sensitivities. No research subagent.
  7. Queue age: report how many gate-passing counties have a null queue age
     and take the national median. Report time to power's variance share
     with all counties and with imputed counties excluded.
  8. Git: commit after each phase, with a one-line summary and a body
     covering what, why, key results, and new assumptions. Stage only
     `scratch/weighting/`, `docs/weighting.md`, `docs/img/`, and this log.
  9. Pull request: after Phase 1, push and open a draft PR from
     `feat/weighting-methods` to `main` titled "Weighting methods:
     monetized cost, SMAA, CRITIC, revealed preference, consensus". Update
     its description after every phase. Mark it ready for review only
     after Phase 5. Never merge. Never push to `main`.
  10. Logging: update this log, then commit and push it, after each phase,
      after each decision, and before any long-running step.
- **Open questions waiting on the user:** none.

## Background

The balanced preset's pillar weights were set by judgment. The #1 county
changed from Berkshire, MA to Grant, WA when the cost pillar went from about
2.6% of the composite to 15%. A judge will ask why the weights are what they
are. The goal is to answer with methods that derive weights from data or
from stated, priced assumptions, and to show whether they agree.

The flip had two causes, not one. `docs/deck.md` credits both the new cost
pillar and the correction of Massachusetts' closed data center tax
exemption. Don't attribute the whole flip to weights.

## Status

| Phase | Method | Status | Output |
| --- | --- | --- | --- |
| 0 | Get current, summarize, plan | done | this file |
| 1 | Monetized total cost of siting | in progress | `scratch/weighting/monetize.py` |
| 2 | Weight-space mapping (SMAA) | not started | `scratch/weighting/smaa.py` |
| 3 | CRITIC and entropy weights | not started | `scratch/weighting/critic.py` |
| 4 | Revealed preference | not started | `scratch/weighting/revealed.py` |
| 5 | Consensus and write-up | not started | `scratch/weighting/consensus.py`, `docs/weighting.md`, `docs/img/` |

## Rules

- Don't change `engine/`, `etl/`, `app/`, or `results/`. Analysis code reads
  them through their Python interfaces.
- Scripts go in `scratch/weighting/`. Charts go in `docs/img/`. Raw
  downloads go in `data/raw/`, which is gitignored.
- Never fabricate a rate or a column. If one is missing, say so and skip it
  or use a documented fallback.
- Each phase report stays under 15 lines. If a phase runs more than 50% over
  its time estimate, stop, record what exists, and move on.
- Time estimates: Phase 1 about 90 minutes, Phases 2 to 5 about 30 each.

## Plan

A shared helper, `scratch/weighting/common.py`, loads the county table,
applies the balanced gates once through `engine.rank.apply_gates`, and
builds pillar scores with `engine.rank.score`.

**Phase 1, monetized cost.** For each gate-passing county, a 300 MW IT
campus at load factor 0.8, NPV over 25 years at 7%. Each cost component maps
to the pillar it replaces:

| Component | Method | Pillar |
| --- | --- | --- |
| Energy | facility MWh times state industrial price | cost |
| Carbon | tonnes CO2 at the eGRID subregion rate times $0, $51, $190, $300 per tonne | energy_carbon |
| Water | volume times base price times (1 + Aqueduct stress) | water |
| Hazard | sum of NRI `*_ALRB` over 17 hazards times $10B asset value | climate_resilience |
| Time to power | queue age beyond 2 years times 12 times the monthly delay cost | grid_infrastructure |
| Moratorium | 12 months at p=1 for active, 12 at p=0.5 for pending, 6 at p=0.3 for recorded pushback, times the monthly delay cost | permitting |
| Not monetized | fiber, land, community stay gates only | land, community |

Time to power and moratorium are one-time costs. Their annual equivalent is
the cost times the capital recovery factor at 7% over 25 years. The variance
share of each component is cov(component, total) / var(total), so shares
sum to 1 and can be negative. Outputs: ranked NPV lists, variance shares at
each carbon price, a cost-versus-CO2 chart with the Pareto frontier and
Grant's BPA range, and breakeven carbon prices against Grant at both the
regional rate (632 lb/MWh) and the BPA rate.

**Phase 2, SMAA.** Score and gate once, then 5,000 weight vectors drawn
from Dirichlet(1) over the 8 pillars, with the composite computed as a
matrix product and the engine's floor-first ordering kept. Self-check:
balanced weights must reproduce the top 10 in `results/balanced.csv`.

**Phase 3, CRITIC and entropy.** Primary run on winsorized, min-max-scaled
raw values; percentile version as a sensitivity. Column-level scratch
composite. Lists column pairs with |r| above 0.8.

**Phase 4, revealed preference.** L2 logistic regression with 5-fold cross
validation on whether a county has an existing data center, trained on all
3,109 counties, with a population-only baseline AUC. Columns where the
industry's sign opposes the pillar direction are listed before any
coefficient becomes a weight. The phase stops if AUC is below 0.65.

**Phase 5, consensus.** Borda count across the top 20 of each method, then
`docs/weighting.md` and charts in `docs/img/`.

## History

### 2026-10-04 00:30 UTC, Phase 0: get current

**Repo state.** `main` is at `1575003` (PR #33, BPA rate constant). The test
suite gives 138 passed, 8 skipped, 1 xfailed. The skips are adapter tests
that need raw files in `data/raw/`. The xfail is the Genesee, MI
population-decline test, marked as a known limitation.

**Current model.** Eight pillars, each the mean of national percentiles of
its columns. The composite is the weighted mean of pillar scores. Balanced
weights:

| Pillar | Weight |
| --- | --- |
| energy_carbon | 0.153 |
| water | 0.119 |
| climate_resilience | 0.119 |
| grid_infrastructure | 0.153 |
| land | 0.068 |
| community | 0.085 |
| permitting | 0.153 |
| cost | 0.150 |

A county below the 10th percentile on any pillar ranks below every county
that isn't. Permitting is exempt from that floor. Balanced gates: inland and
coastal flood percentile at most 90, wildfire and hurricane at most 95,
queue median age at most 5 years, plant capacity within 100 km at least 5
times facility MW, no active county moratorium, fiber share at least 0.2,
population at least 5,000. The water stress gate applies only to
evaporative or hybrid cooling, and balanced uses dry cooling. Of 3,109
counties, 1,565 pass the gates and 915 pass the floor.

**Data with real values.** eGRID subregion CO2 and renewable share, LBNL
queue (queue age is null for 2,185 of 3,109 counties), FEMA NRI hazard
percentiles, CMRA climate, Aqueduct water stress, US Drought Monitor, FCC
fiber, FracTracker facilities and moratoria, and the state industrial
electricity price, which has one value per state.

**Missing columns.** Solar, grid water intensity, SAIDI, distance to an
internet exchange, the four land-cover shares, greenhouse acres, and both
permitting model outputs. The engine skips them.

**Current ranking.** Grant, WA is #1 with robustness 1.00. Franklin, NY is
986th and Berkshire, MA is 1,013th; both fail the pillar floor.

**Findings that shape the plan.**

- New York's state moratorium flag is real: Executive Order 62, a
  statewide data center moratorium from 2026-06-04 to 2027-06-04. It is not
  a crypto-only rule.
- The NRI feature service carries raw building loss rates (`*_ALRB`) for 17
  hazards, so the hazard cost can use rates instead of percentiles. Drought
  has no building rate, only an agriculture rate.
- Entropy and CRITIC applied to percentiles are close to degenerate.
  Percentiles are near-uniform, so entropy weights come out nearly equal and
  CRITIC's spread term is almost constant. Summing column weights into
  pillars also favors pillars with many columns: climate resilience has 8,
  cost has 1.
- Franklin, NY fails the pillar floor. Under the engine's ordering, no
  energy and carbon weight makes it pass Grant while it stays below the
  floor.
- `docs/` has no "How the data center siting engine works" summary. Phase 0
  used the code, `docs/conditions.md`, and `docs/deck.md`.

### 2026-10-04 01:05 UTC, decisions approved

The user approved the plan with the changes recorded under Approved
decisions in CURRENT STATE: CRITIC and entropy flipped to raw values as the
primary run with column-level weights, delay cost and moratorium duration
sensitivities added, a queue-imputation check added, and the git and pull
request rules.
