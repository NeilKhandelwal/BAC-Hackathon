# Weighting methods: logbook

This logbook tracks the work to replace judgment-set pillar weights with
quantifiable methods. It's written so that a new Claude session with no
memory can resume from it alone. Read CURRENT STATE first. The history at
the bottom is append-only and timestamped.

## CURRENT STATE

Overwritten at every update.

- **Updated:** 2026-10-04 02:59 UTC
- **Branch:** `feat/weighting-methods`, based on `main` at `1575003`.
- **Pull request:** draft PR #35,
  https://github.com/NeilKhandelwal/BAC-Hackathon/pull/35. To edit its
  description, fetch the current body with
  `gh pr view 35 --json body --jq .body > pr_body.md`, edit the Results
  and Checklist sections, then run `gh pr edit 35 --body-file pr_body.md`.
  Keep the body file outside the repo.
- **Phase and step:** revision round 1 on PR #35 (user request at
  02:58 UTC, 60-minute timebox, ends about 03:58 UTC). PR is open, not
  merged.
- **Done in this round:** AI footer removed from the PR body; PR comments
  posted asking Neil about a squash merge and surfacing the 90% against
  30% energy-and-carbon finding.
- **In progress:** an Opus research subagent is verifying the WA data
  center sales tax exemption (RCW 82.08.986, 82.12.986) for Clark and
  Grant, any NY exemption for Franklin, and sourced sales tax rates. If a
  new session starts and the result is lost, rerun that research.
- **Exact next action:** in order, per approved decisions 17 to 21:
  1. Add the sales tax component to `monetize.py` once the rates and
     eligibility are sourced (or flagged unverified).
  2. Neil's review items in `scratch/weighting/revisions.py`:
     non-negative variance shares, time to power with imputed counties at
     $0 and excluded, Grant's evidence-based delay, dry cooling everywhere
     for Clark against Grant, hazard asset value $3B, and one table of the
     top 10 and the four focus counties' ranks under every method.
  3. Rerun `montecarlo.py` (BPA run) and `consensus.py` with the tax
     component; report Clark, Franklin, and Grant with and without tax and
     at refresh cycles of 4 and 6 years.
  4. Consult the advisor before writing the final recommendation.
  5. Update `docs/weighting.md`, this log, and the PR body.
- **Reproduce:** from the repo root, after fetching raw NRI (below):
  `.venv/Scripts/python.exe scratch/weighting/monetize.py`, then
  `.venv/Scripts/python.exe scratch/weighting/montecarlo.py`, then
  `.venv/Scripts/python.exe scratch/weighting/smaa.py`, `critic.py`,
  `revealed.py`, and `consensus.py` in that order. Each rewrites its
  files in `scratch/weighting/out/` and its chart in `docs/img/`.
- **Advisor rule (from the user):** consult the advisor before finalizing a
  Monte Carlo design, when judging whether the top 3 is a real tie, before
  writing the Phase 5 recommendation, and whenever results look
  implausible. Log each consultation and what changed.
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
  - **No AI attribution (Neil's rule, 2026-10-04 02:58 UTC):** no
    Co-Authored-By trailers on new commits and no "Generated with" footer
    in the PR body. Don't rewrite existing history.
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
  11. Pre-Phase 2 checks (2026-10-04 01:20 UTC): report whether Clark's
      queue age is real; if imputed, rerun $190/t with imputed counties at
      the 75th-percentile queue age. Run 1,000 Monte Carlo draws: state
      price ±20%, subregion carbon rate ±20%, delay cost U($10M, $50M), NY
      moratorium U(8, 20) months, carbon price U($100, $300). Report each
      county's share of draws at #1 and in the top 3. Note in
      `docs/weighting.md` that hazard costs exclude downtime.
  13. Phase 3 (2026-10-04 01:40 UTC): raw-value CRITIC and entropy only,
      column-level weights, 30-minute timebox. Skip the percentile
      sensitivity. Report the top 10 under each and the ranks of Clark,
      Franklin, and Grant. Then go straight into Phase 4 as specified.
  14. Fairness fix before Phase 5: Clark WA gets the same BPA new-load
      range as Grant ($80 to $132/MWh) and the same BPA-like supply carbon
      option. Franklin NY stays at the state average, flagged as having no
      sourced new-load rate. Don't invent one. Rerun the 1,000-draw Monte
      Carlo with Clark and Grant both drawing from the BPA range; report #1
      and top-3 shares for Clark, Franklin, and Grant.
  15. Phase 5 framing: two stages. The engine screens and shortlists
      (gates and scores), then the monetized model ranks the shortlist in
      dollars and tonnes, with Monte Carlo and SMAA as robustness tests.
      Use the Franklin versus Grant carbon example (2.7 times real gap
      against 97th versus 94th percentile) as the reason dollars are the
      ranking stage.
  16. Phase 5 recommendation: consult the advisor first and log what it
      said. Name one featured county and two alternatives, each with the
      condition under which it would win (for example, carbon price above
      X or new-load rate below Y).
  17. Revision round 1 (2026-10-04 02:58 UTC), process: remove the AI
      footer from the PR body; no Co-Authored-By trailers from now on; don't
      rewrite history; ask Neil in a PR comment whether he wants a squash
      merge with a clean message.
  18. Sales and use tax: verify the WA exemption (RCW 82.08.986 and
      82.12.986) for Clark and Grant, and whether NY has one for Franklin;
      cite sources, flag anything unverified, invent nothing. Add a tax
      component: taxable equipment capex (default $4B) times the county's
      combined state and local rate (sourced, or a documented default),
      refreshed every 5 years (parameter), discounted at 7%; exempt
      counties pay 0. Rerun $190/t and the BPA Monte Carlo; report Clark,
      Franklin, and Grant with and without tax and at 4- and 6-year
      refresh.
  19. Neil's review items: non-negative variance shares (standalone or
      Shapley) and whether the order changes; time to power with imputed
      counties at $0 and with them excluded; Grant's row from its own
      evidence in research/risk.md and research/implementation.md, stating
      no other county has equivalent evidence; cooling stated as a modeling
      choice, with Clark against Grant under dry cooling everywhere; hazard
      asset value at $3B as well as $10B; one table of the top 10 and the
      ranks of Grant, Clark, Franklin, and Berkshire under balanced,
      monetized $190, SMAA, CRITIC, entropy, revealed preference, and
      consensus.
  20. Surface to Neil in a PR comment: energy and carbon carry about 90%
      of dollar variance at every carbon price; balanced gives them about
      30%.
  21. Update docs/weighting.md, this log, and the PR body. Revise the
      recommendation if the tax component changes the order; give each of
      the three counties its win condition. Consult the advisor before the
      final recommendation.
  12. Phase 2 additions: run SMAA with the floor on and off. Report which
      pillar fails Franklin's floor and by how much. Report rank-1 and
      top-10 acceptability for Clark WA, Franklin NY, and Grant WA under
      both settings.
- **Open questions waiting on the user:** which county the deck features
  (see Exact next action).

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
| 1 | Monetized total cost of siting | done | `scratch/weighting/monetize.py`, `docs/img/cost_vs_co2.png` |
| 2 | Weight-space mapping (SMAA) | done | `scratch/weighting/smaa.py`, `docs/img/smaa_acceptability.png` |
| 3 | CRITIC and entropy weights | done | `scratch/weighting/critic.py` |
| 4 | Revealed preference | done | `scratch/weighting/revealed.py` |
| 5 | Consensus and write-up | done | `scratch/weighting/consensus.py`, `docs/weighting.md`, `docs/img/` |

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

### 2026-10-04 01:00 UTC (approximate), Phase 0: get current

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

### 2026-10-04 01:14 UTC, Phase 1: monetized cost

Script: `scratch/weighting/monetize.py`. Full printout:
`scratch/weighting/out/monetize_report.txt`. Per-county costs:
`scratch/weighting/out/monetized_costs.csv`. Key numbers as JSON:
`scratch/weighting/out/monetize_summary.json`.

**Headline.** At $190/t, Pacific Northwest and North Country New York
counties sit within about 1.5% of each other: Clark WA $3.496B, Franklin NY
$3.545B, and Grant WA $3.547B without its time-to-power charge. Which one
comes first depends on the monthly delay cost and the queue-age proxy.
Clark WA is #1 in 8 of 9 sensitivity runs, including with time to power
switched off. Franklin is #1 only at a $10M monthly delay cost or an
8-month New York moratorium.

**Setup.** 1,565 gate-passing counties, annuity factor 11.654 (7%, 25
years). Cooling: 826 evaporative, 739 dry. The NRI building loss rates
summed over 17 hazards equal NRI's composite EAL_VALB / BUILDVALUE to
machine precision for 95% of counties. The largest gap is 8% (Kittitas,
WA, FIPS 53037). Queue age is null for 1,072 of 1,565 counties (68%). They
take the national median of 2.89 years, which is a $265M one-time
time-to-power cost each at $25M per month.

**Rankings by 25-year NPV.**

| Basis | Top 10 |
| --- | --- |
| Private only ($0 carbon) | Curry NM, Bossier LA, Richland LA, Payne OK, Choctaw OK, St. Landry LA, Noble OK, Hansford TX, Tulsa OK, Pittsburg OK |
| Private + $51/t | Curry NM, Clark WA, Bossier LA, Richland LA, El Paso TX, Grayson TX, Robertson TX, Houston TX, Payne OK, Choctaw OK |
| Private + $190/t | Clark WA ($3.50B), Franklin NY ($3.54B), Schuyler NY, Clinton NY, Chautauqua NY, Tompkins NY, Niagara NY, Walla Walla WA, Chesterfield SC, Whitman WA |
| Private + $300/t | Franklin NY, Schuyler NY, Clinton NY, Chautauqua NY, Tompkins NY, Niagara NY, Saratoga NY, Ontario NY, Oneida NY, Lewis NY |

Grant, WA ranks 546th on private cost and 92nd at $190. Two things cost it:
a $463M time-to-power charge from its LBNL queue median age of 3.54 years,
and dry cooling forced by Aqueduct water stress of 3.6. Clark, WA has the
same state price and eGRID subregion, a queue age of 2.09 years, and
evaporative cooling, so Clark dominates Grant on both cost and CO2. Grant
is not on the Pareto frontier. Of the $465M private gap between Grant and
Clark, $437M is the time-to-power charge. The repo's own research supports
a real delay at Grant even though the proxy is a generation queue:
`research/risk.md` and `research/implementation.md` report about 800 MW of
large-load requests in Grant PUD's queue, no spare hydro, and Quincy
transmission upgrades due in 2027 and 2029.

**Variance shares, the data-implied weights.** Share of the cross-county
variance in total NPV, cov(component, total) / var(total):

| Carbon price | energy (cost) | carbon (energy_carbon) | time to power (grid) | hazard (climate) | water | moratorium (permitting) |
| --- | --- | --- | --- | --- | --- | --- |
| $0 | 0.885 | 0.000 | 0.106 | 0.006 | -0.010 | 0.013 |
| $51 | 0.887 | -0.002 | 0.111 | 0.009 | -0.011 | 0.005 |
| $190 | 0.550 | 0.379 | 0.079 | 0.012 | -0.008 | -0.014 |
| $300 | 0.295 | 0.668 | 0.048 | 0.010 | -0.005 | -0.017 |

With imputed queue counties excluded (n=493), time to power's share at
$190 rises from 0.079 to 0.151, and energy and carbon become 0.573 and
0.282. Land and community get 0 because they aren't monetized. Under any
carbon price, energy and carbon explain about 90% of the spread, while
water, hazard, and moratorium are each under 2%.

**Pareto frontier**, cleanest first: Hamilton NY, Essex NY, Franklin NY,
Haywood NC, Avery NC, Susquehanna PA, Buncombe NC, Lancaster SC, Kershaw
SC, Chesterfield SC, Clark WA, El Paso TX, Bossier LA, Curry NM.

**Breakeven carbon price against Grant.** Against Grant at the Northwest
average rate (700 kt/yr, $211M/yr private), Franklin overtakes Grant at
$99/t, Essex and Hamilton at about $155/t, Buncombe NC at $51/t, and
Kershaw SC at $37/t. Chesterfield SC and Clark WA are already cheaper and
cleaner. Against Grant with BPA-like supply (212 lb/MWh, 236 kt/yr), no
gate-passing county is cleaner, so no breakeven exists. At BPA's $80/MWh,
Grant ($245M/yr, 236 kt) beats Franklin ($255M/yr, 260 kt) on both axes. At
$132/MWh, Grant costs $372M/yr.

**Sensitivities** (#1 at private + $190; Grant and Franklin ranks):

| Variant | #1 | Grant | Franklin | Energy share | Carbon share | Time-to-power share |
| --- | --- | --- | --- | --- | --- | --- |
| Base | Clark WA | 92 | 2 | 0.550 | 0.379 | 0.079 |
| Dry cooling everywhere | Clark WA | 63 | 2 | 0.531 | 0.392 | 0.078 |
| Water $3 / $15 per kgal | Clark WA | 102 / 74 | 2 / 2 | about 0.55 | about 0.38 | 0.079 |
| Delay $10M per month | Franklin NY | 35 | 1 | 0.561 | 0.419 | 0.021 |
| Delay $50M per month | Clark WA | 255 | 10 | 0.494 | 0.298 | 0.221 |
| NY moratorium 8 months | Franklin NY | 93 | 1 | 0.543 | 0.383 | 0.079 |
| NY moratorium 20 months | Clark WA | 74 | 5 | 0.563 | 0.371 | 0.081 |
| Time to power off | Clark WA | 8 | 7 | n/a | n/a | 0 |

With time to power off, the top 5 at $190 is Clark WA, Whitman WA, Asotin
WA, Saratoga NY, Ontario NY, and #1 leads #2 by 0.14%.

**Variance shares are not percentile weights.** A share of dollar variance
says which costs separate counties. It doesn't carry over one-to-one to the
engine's percentile composite, where every pillar is spread evenly from 0
to 100. Phase 5 runs the engine once with the $190 shares and reports how
much its top 10 overlaps the NPV top 10.

**Implausible or fragile.**

- Energy uses one state average price, so energy cost doesn't vary inside
  a state. Carbon uses the eGRID subregion average, not marginal or
  contracted supply. Together they carry about 90% of the variance.
- Time to power uses LBNL generation-queue age as a proxy for how long a
  new load waits. It isn't a load-interconnection measure, and 68% of
  counties are imputed.
- Only Grant gets a new-load rate scenario (BPA). Other counties are priced
  at their state average, which may also understate what a new large load
  pays.
- Imputation favors counties without queue data over slow known ones and
  penalizes them against fast known ones: an imputed county pays $265M, a
  county with a known queue age under 2 years pays $0. Imputed counties are
  46% of the top 50 at $190 against 68% of all gate passers.
- Water's share is slightly negative. Evaporative cooling raises water
  cost but lowers PUE, so the counties that get it pay more for water and
  less for energy and carbon. Water cost therefore moves against the total.

### 2026-10-04 01:18 UTC, draft PR opened

Draft PR #35 opened from `feat/weighting-methods` to `main`, with the
problem statement, methods table, Phase 1 results, assumptions, known
limitations, and the phase checklist.

### 2026-10-04 01:29 UTC, pre-Phase 2 checks and Monte Carlo design

**Clark WA's queue age is real**, not imputed: 2.09 years, a $25.9M
time-to-power charge, against Grant's 3.54 years and $463M. The
75th-percentile imputation rerun was conditional on Clark being imputed,
so it was not triggered. For reference, the national 75th-percentile
queue age is 4.01 years.

**Franklin NY's floor failure.** Franklin passes the gates but fails the
pillar floor on cost: its cost pillar is at the 6.5th national
percentile, 3.5 points under the floor of 10. NY's industrial price is
9.17 cents/kWh. Floor membership doesn't depend on the weights unless a
weight is 0, so no energy and carbon weight lifts Franklin over the floor.
It clears only if the cost weight is 0, cost is exempt, or the floor is 6.5
or lower. With the floor on, Franklin's SMAA rank-1 acceptability is 0 by
construction.

**`docs/weighting.md` created** as a stub with two method notes: hazard
cost uses building loss rates and excludes downtime, so it understates
hazard risk; and the pillar floor is a judgment rule.

**Advisor consulted on the Monte Carlo design.** Changes it made:

- Price and carbon multipliers are drawn independently per state and per
  eGRID subregion in each draw, not as one national multiplier, which would
  only rescale costs. Delay cost, moratorium months, and carbon price are
  drawn once per draw. The delay cost applies to both time to power and
  moratorium. Only active-moratorium months vary.
- Self-check before the run: with multipliers 1, $25M, 12 months, and
  $190/t, one draw must reproduce `total_190` exactly.
- Counties that share a state and subregion move together, so the run
  ranks state-and-subregion clusters. Report a cluster-level #1 share next
  to the per-county shares. Grant against Clark is structural (same price
  and grid, Grant has the longer queue and dry cooling); if Clark wins every
  draw, report that as structural, not as a probability.
- Answer "is the tie real" with P(Clark beats Franklin) and its standard
  error, plus win rates by tercile of delay cost, moratorium months, and
  carbon price.
- Report the share of #1 draws won by counties with an imputed queue age.
- Grant with BPA-like supply goes on its own labeled line, computed on the
  same draws: energy at U($80, $132)/MWh and carbon at 212 lb/MWh. It stays
  out of the main ranking because no other county gets a contracted-supply
  scenario.

### 2026-10-04 01:36 UTC, Monte Carlo results: the tie is real and two-way

Script: `scratch/weighting/montecarlo.py`. Printout:
`scratch/weighting/out/montecarlo_report.txt`. JSON:
`scratch/weighting/out/montecarlo_summary.json`. Chart:
`docs/img/mc_winners.png`. 1,000 draws, seed 42. The self-check reproduced
the $190/t totals from `monetize.py` exactly.

**Headline.** Franklin NY overtakes Clark WA above a carbon price of about
$200/t at base prices, $25M per month of delay, and a 12-month NY
moratorium. Below it, Clark wins. The crossover moves with the delay
assumptions:

| Delay cost | NY moratorium | Crossover carbon price |
| --- | --- | --- |
| $25M per month | 12 months | $200/t |
| $10M per month | 12 months | $166/t |
| $50M per month | 12 months | $256/t |
| $25M per month | 8 months | $180/t |
| $25M per month | 20 months | $241/t |

**Shares across draws.** No county is #1 in a majority of draws:

| County | #1 | Top 3 |
| --- | --- | --- |
| Clark, WA | 26.6% | 35.2% |
| Franklin, NY | 24.7% | 34.3% |
| Chesterfield, SC | 11.2% | 18.3% |
| Schuyler, NY | 0% | 30.1% |
| Clinton, NY | 0% | 23.2% |
| Grant, WA | 0% | 0% |

Clark beats Franklin in 59.3% ± 3.0% of draws (95% interval). That number
is Monte Carlo sampling error under the chosen ranges, which are centered
near the $200/t crossover. It isn't a probability about the world.

**What drives the Clark versus Franklin gap.** A linear regression of the
gap on the seven drivers has R² 0.983. Share of the gap's variance: NY
price 0.31, carbon price 0.28, WA price 0.15, NWPP carbon rate 0.12, delay
cost 0.08, NY moratorium months 0.04, NYUP carbon rate 0.02. State
electricity prices together (0.46) move the gap more than the carbon
price. The earlier commit message `eb090db` said carbon price drives it;
that was wrong, and this entry corrects it. Carbon price is the largest
single policy lever.

**Grant WA.** Clark beats Grant in every draw. That's structural: same
state price, same eGRID subregion, and Grant has the longer queue and dry
cooling. Grant's place in the Phase 1 near tie depended on removing its
time-to-power charge. With BPA-like supply (energy U($80, $132)/MWh,
212 lb/MWh), Grant's median rank is 246, it's #1 in 3.2% of draws, and it
beats Clark in 13.6%.

**Cluster check.** Counties that share a state and subregion move
together. Clark wins every draw its cluster (WA / NWPP) wins, and Franklin
every draw NY / NYUP wins, so the county and cluster shares are the same.
The other 49% of #1 draws go to 22 other clusters. Their winning state's
drawn price multiplier averages 0.84 to 0.88, against 0.90 for Clark and
0.91 for Franklin, so minor winners need a deeper price cut. Treat
Chesterfield SC's 11% as a contender only with that caveat.

**Imputation isn't steering the winner.** Counties with an imputed queue
age win 1.1% of draws.

**Advisor consulted on whether the tie is real.** Changes it made:

- Lead with the crossover carbon price, not with 59%. Overlay crossover
  lines on the chart.
- Regress the gap on all drivers before claiming one dominates. That
  regression reversed the carbon-price claim.
- Check the winners' price multipliers before reading minor-state wins as
  contenders.
- State plainly that Grant isn't in the tie under the monetized model.

Earlier history headings were re-stamped from commit times; the first
versions used estimated times.

### 2026-10-04 01:38 UTC, Phase 2: SMAA weight-space mapping

Script: `scratch/weighting/smaa.py`. Printout:
`scratch/weighting/out/smaa_report.txt`. Per-county table:
`scratch/weighting/out/smaa_acceptability.csv`. JSON:
`scratch/weighting/out/smaa_summary.json`. Chart:
`docs/img/smaa_acceptability.png`. 5,000 Dirichlet(1) weight vectors over
the 8 pillars, seed 0. The self-check reproduced the top 10 in
`results/balanced.csv` exactly.

**No county wins under most weightings.** The best rank-1 acceptability is
12.4%. Grant WA has the highest top-10 acceptability under both settings.

| County | Rank-1, floor on | Top-10, floor on | Rank-1, floor off | Top-10, floor off |
| --- | --- | --- | --- | --- |
| Grant, WA | 12.4% | 50.5% | 8.0% | 34.9% |
| Whitman, WA | 12.4% | 44.7% | 7.1% | 31.3% |
| Wayne, TN | 10.9% | 42.1% | 7.5% | 30.8% |
| Trumbull, OH | 9.1% | 32.4% | 7.2% | 24.8% |
| Clark, WA | 6.7% | 29.6% | 4.9% | 20.6% |
| Franklin, NY | 0% (fails floor) | 0% (fails floor) | 7.1% | 24.3% |

Floor off adds Hamilton OH (7.2%), Caddo OK, Sullivan TN, and Hamilton NY
to the rank-1 list. All of them fail the floor.

**Value system behind each winner** (mean weights over the draws it
wins, floor on unless noted):

- Grant WA: grid 0.21, land 0.17, energy_carbon 0.16; cost 0.08, water
  0.06.
- Whitman WA: land 0.20, water 0.19, energy_carbon 0.17.
- Wayne TN: permitting 0.28.
- Trumbull OH: community 0.28, water 0.18.
- Clark WA: water 0.27, cost 0.17, climate 0.14.
- Franklin NY, floor off: water 0.27, energy_carbon 0.17, cost 0.035.

**Franklin and the floor.** Franklin fails on cost: 6.5th percentile
against a floor of 10, a 3.5-point miss. With the floor on, its rank-1
and top-10 acceptability are 0 by construction. No energy_carbon weight
changes that, because floor membership doesn't depend on positive
weights.

**Franklin against Grant and Clark with the floor off**, raising the
energy_carbon weight and scaling the other pillars in balanced
proportion: Franklin passes Clark at an energy_carbon weight of 0.384 and
Grant at 0.788. Balanced uses 0.153.

**Engine and monetized model disagree, and percentiles are why.** In
dollars, Franklin emits 2.7 times less CO2 than Grant (260 against 700
kt/yr). In the engine, Grant's energy_carbon pillar sits at the 94th
percentile and Franklin's at the 97th. The pillar mixes grid carbon with
renewable share, clean queue MW, and clean capacity within 100 km, where
Grant scores near the top, and percentile scoring compresses a large
physical gap into a few points. That's why the engine needs an
energy_carbon weight of 0.79 before Franklin passes Grant, while the
monetized model has Franklin passing Grant at $99/t.

### 2026-10-04 01:48 UTC, Phase 3: CRITIC and entropy on raw values

Script: `scratch/weighting/critic.py`. Printout:
`scratch/weighting/out/critic_report.txt`. Weights:
`scratch/weighting/out/critic_weights.csv`. Ranks:
`scratch/weighting/out/critic_ranks.csv`. JSON:
`scratch/weighting/out/critic_summary.json`. 35 scored columns with data,
1,565 gate-passing counties. Raw values get their pillars.yaml transform,
are winsorized at the 1st and 99th percentiles, min-max scaled, and
flipped where lower is better. Nulls take the column median for the
weight calculation only (queue age 1,072, queue withdrawal 710, state
policy 349). The composite is the weighted mean of each county's non-null
scaled columns, with no pillar floor. Took about 5 minutes of the
30-minute timebox. The percentile sensitivity was skipped as instructed.

**Top 10.**

| Method | Top 10 | Clark | Franklin | Grant |
| --- | --- | --- | --- | --- |
| CRITIC | Washington OR, Rock Island IL, Dakota MN, Multnomah OR, St. Joseph IN, Scott IA, Monroe NY, Ramsey MN, Onondaga NY, Erie NY | 27 | 64 | 12 |
| Entropy | Bexar TX, Milam TX, Salt Lake UT, Clark NV, Cook IL, Washington OR, El Paso CO, Berks PA, Wayne MI, St. Louis MO | 338 | 392 | 50 |

Six of CRITIC's top 10 and two of entropy's fail the balanced pillar
floor.

**Pillar-summed weights** (comparison only; the composite uses column
weights):

| Pillar | Columns | CRITIC | Entropy | Equal per column | Balanced |
| --- | --- | --- | --- | --- | --- |
| climate_resilience | 8 | 0.254 | 0.091 | 0.229 | 0.119 |
| energy_carbon | 6 | 0.180 | 0.268 | 0.171 | 0.153 |
| grid_infrastructure | 6 | 0.151 | 0.430 | 0.171 | 0.153 |
| community | 5 | 0.136 | 0.141 | 0.143 | 0.085 |
| water | 4 | 0.121 | 0.037 | 0.114 | 0.119 |
| permitting | 3 | 0.097 | 0.024 | 0.086 | 0.153 |
| land | 2 | 0.044 | 0.008 | 0.057 | 0.068 |
| cost | 1 | 0.018 | 0.002 | 0.029 | 0.150 |

**What the weights show.**

- CRITIC is close to equal weight per column: column weights range from
  0.016 to 0.042. Correlations are mostly low, so the conflict term
  (sum of 1 - r) is between 33 and 36 for every column, and CRITIC
  reduces to spread times a near constant. Pillar sums therefore track
  column count: climate resilience gets 0.254 from 8 columns.
- Entropy gives `dc_existing_count` 0.198 of all weight, because 88% of
  gate passers have no data center and entropy rewards sparse,
  concentrated columns. Entropy's top 10 is the big metros with existing
  clusters. That's a property of the method, not evidence those counties
  are good sustainable sites. Entropy also depends on how a column is
  coded: after the lower_better flip, a mostly-zero column becomes mostly
  ones, reads as near-uniform, and gets almost no weight. Coastal flood
  shows this (0.0019), while sparse higher_better columns such as
  `dc_existing_count` get large weights. Entropy's ranking reflects coding
  choices, so Phase 5 reports the consensus with and without it.
- Both methods nearly ignore cost (0.018 and 0.002). The industrial price
  has one value per state, so its spread after winsorizing is small.
- Only two pairs exceed |r| 0.8. `cdd_hist` with `days_above_95f_hist`
  (r 0.80) is the only pair CRITIC down-weights, by about 6 to 9% against
  the mean column weight (0.0286). `pop_density_per_sqkm` with
  `population` has r -0.87 after direction coding, so each gets 1 - r of
  about 1.87, the largest conflict term: CRITIC up-weights that pair.
  Their slightly below-mean weights come from their spread. The pair also
  shows a tension in the pillars: land rewards low density while community
  rewards high population, two opposite readings of one fact.
- Queue age's very low weights (CRITIC 0.0177, entropy 0.0038) are partly
  an artifact: 68% of its values take the median for the weight
  calculation, which shrinks its spread.

### 2026-10-04 01:52 UTC, advisor consulted on Phase 3 and the next two designs

**Phase 3.** The entropy result is a method artifact; keep it, don't tune
it. Changes made to the Phase 3 entry: entropy's dependence on how a
column is coded, the corrected reading of the density and population pair
(CRITIC up-weights it), the note that median imputation shrinks queue
age's weight, and the heading time.

**Phase 4 guards adopted.** Fit the imputer and scaler inside stratified
5-fold cross validation. Lead with the AUC lift over a population-only
model, since population alone will likely clear 0.65. Call a column a
sign conflict only if its univariate correlation with the outcome has the
same sign as its coefficient. Report how much of each pillar's revealed
weight comes from sign-conflicting columns. "Five biggest disagreements"
means the largest rank differences among gate passers in the combined top
20 of revealed preference and monetized $190/t.

**BPA fairness Monte Carlo design adopted.** One BPA rate per draw for
Clark and Grant (one tariff), reusing the same seed and BPA draws so the
run pairs with the original; report how many draws change winner. BPA
carbon fixed at `BPA_CO2_LB_MWH` with no multiplier. Self-check: with
Clark and Grant at the WA average times the WA multiplier and at NWPP
times its multiplier, totals must match the original run. Clark at
212 lb/MWh may emit less than Franklin, which would remove the $200/t
crossover; compute the Clark-Franklin breakeven BPA rate as a function of
carbon price. Report both runs side by side as bounds: BPA's whole range
sits above WA's $66/MWh average while Franklin keeps NY's average, and
other WA counties keep the WA average. Also compute what Grant needs to
beat Clark (shorter delay or a lower rate).

**Phase 5 heads-up.** Land isn't monetized, and Clark's land pillar is at
the 22nd percentile. The recommendation must address it.

### 2026-10-04 01:52 UTC, Phase 4: revealed preference

Script: `scratch/weighting/revealed.py`. Printout:
`scratch/weighting/out/revealed_report.txt`. Ranks:
`scratch/weighting/out/revealed_ranks.csv`. JSON:
`scratch/weighting/out/revealed_summary.json`. Outcome: at least one
existing FracTracker data center (184 of 3,109 counties, 5.9%). 34
features, every scored column with data except `dc_existing_count`. L2
logistic regression, median imputation and standardization fit inside
stratified 5-fold cross validation, seed 0, trained on all counties.

**Fit.** Out-of-fold AUC 0.905, above the 0.65 stop rule. Population
alone gives 0.855, so the other 33 columns add 0.050. Most of what
predicts an existing data center is population.

**Pillar weights from absolute standardized coefficients:**

| Pillar | Revealed | Share from sign conflicts | Balanced | CRITIC |
| --- | --- | --- | --- | --- |
| climate_resilience | 0.227 | 0.12 | 0.119 | 0.254 |
| energy_carbon | 0.173 | 0.23 | 0.153 | 0.180 |
| community | 0.146 | 0.06 | 0.085 | 0.136 |
| land | 0.129 | 0.64 | 0.068 | 0.044 |
| water | 0.125 | 0.24 | 0.119 | 0.121 |
| grid_infrastructure | 0.083 | 0 | 0.153 | 0.150 |
| cost | 0.060 | 0 | 0.150 | 0.018 |
| permitting | 0.056 | 0.73 | 0.153 | 0.096 |

**Sign conflicts**, where industry's preference runs against the pillar
direction and the univariate correlation agrees with the coefficient:
`pop_density_per_sqkm` (industry prefers dense counties; land prefers
sparse), `state_policy_risk` (more data centers where states have
restriction bills, likely reverse causation), `wind_speed_100m_ms`,
`nri_drought_score`, `days_above_95f_hist`, `unemployment_rate_pct_2023`.
Aligned and strong: lower grid CO2 (-0.69), lower industrial price
(-0.65), more plant capacity within 100 km (+0.49), fewer hurricanes and
heat waves.

**Industry picks** (gate passers with no data center, highest
predicted probability): Multnomah OR, El Paso TX, Wake NC, Monroe NY,
Ramsey MN, Ector TX, Dauphin PA, York PA, Jefferson KY, Spartanburg SC.
Their monetized $190/t ranks run from 23 (Monroe) to 1,289 (Ramsey).

**Five biggest disagreements** (largest rank gaps in the combined top 20
of revealed preference and monetized $190/t): Cook IL (revealed 19,
monetized 1,409), Clark NV (18 against 1,408), Wayne MI (3 against
1,386), Hennepin MN (16 against 1,320), Allegheny PA (10 against 1,271).
All five are metros with existing clusters on carbon-heavy or expensive
grids. Revealed preference and the sustainability rankings measure
different things.

**Focus counties.** Clark WA: probability 0.33, revealed rank 103, no
existing data center. Grant WA: 0.28, rank 120, has data centers.
Franklin NY: 0.04, rank 548.

**Caveat.** FracTracker's existing facilities reflect past siting, much
of it near metros for latency, not where a 300 MW AI campus would go.
The weights describe the existing fleet, not a target.

### 2026-10-04 01:55 UTC, BPA fairness fix and Monte Carlo rerun

Changes: `monetize.py` now gives Clark WA the same BPA new-load scenario
as Grant WA ($80 to $132/MWh, 212 lb CO2/MWh) and computes each
contender's winning condition. `montecarlo.py` reruns the same 1,000
draws (seed 42) with Clark and Grant both paying the drawn BPA rate (one
tariff, one draw) at BPA's carbon rate with no multiplier. Franklin NY
stays at the NY state average: there is no sourced new-load rate for New
York, and none was invented. A self-check confirmed the original WA totals
before the swap. Chart: `docs/img/mc_winners_bpa.png`. The cost chart
`docs/img/cost_vs_co2.png` now shows Clark's BPA range too.

**Clark with BPA supply emits less than Franklin**: 228 kt/yr against
260 kt. Grant with BPA supply: 236 kt. So in this scenario the carbon
price no longer decides Clark against Franklin; the BPA rate does. At base
delay cost and NY moratorium months, Clark (BPA) costs less than Franklin
when the BPA rate is below:

| Carbon price | Breakeven BPA rate |
| --- | --- |
| $0/t | $101.4/MWh |
| $100/t | $102.8/MWh |
| $190/t | $104.0/MWh |
| $300/t | $105.5/MWh |

At $190/t the breakeven moves to $98.0/MWh at $10M per month of delay
and $113.9/MWh at $50M.

**BPA Monte Carlo shares** (same draws as the state-average run):

| County | #1, BPA run | Top 3, BPA run | #1, state-average run | Top 3, state-average run |
| --- | --- | --- | --- | --- |
| Clark, WA | 27.2% | 31.8% | 26.6% | 35.2% |
| Franklin, NY | 20.1% | 34.3% | 24.7% | 34.3% |
| Grant, WA | 0% | 3.8% | 0% | 0% |

Clark beats Franklin in 53% of BPA draws: 91% when the BPA rate is in the
low tercile ($80 to $99), 51% in the middle ($99 to $114), and 18% in
the high tercile ($114 to $132). Clark beats Grant in every draw again;
that's structural. 39% of draws change winner against the state-average
run. Walla Walla WA takes #1 in 6.4% of BPA draws because it keeps the WA
state average while Clark pays BPA's rate. That's a partial application of
the scenario, not a finding.

**The two runs are bounds.** BPA's whole range sits above WA's $66/MWh
state average while Franklin keeps NY's average, so the BPA run tilts
against WA. The state-average run tilts toward WA. Clark leads Franklin in
both.

**What Grant needs to beat Clark.** At $190/t on the same supply, Grant
costs $514M more (state average) or $494M to $541M more (BPA). That's
20.6 months of delay at $25M per month, more than Grant's whole 18.5-month
time-to-power charge, so shorter delay alone can't close it. Grant needs
both its queue cleared to Clark's level and a rate about $2/MWh below
Clark's; with its current queue, it needs a rate $18/MWh below Clark's.
The rest of the gap after delay comes from dry cooling (water stress 3.6)
raising its PUE.

### 2026-10-04 02:01 UTC, Phase 5: consensus, two-stage shortlist, recommendation

Script: `scratch/weighting/consensus.py`. Printout:
`scratch/weighting/out/consensus_report.txt`. Ranks:
`scratch/weighting/out/consensus_ranks.csv`. JSON:
`scratch/weighting/out/consensus_summary.json`. Chart:
`docs/img/weights_by_method.png`. Write-up: `docs/weighting.md`.

**Consensus.** Borda over each method's top 20. Without entropy: Clark WA
50, Whitman WA 49, Grant WA 48, Scott IA 44, Washington OR 39, Wayne TN 37,
Rock Island IL 31, Grady OK 27, Mayes OK 26, Multnomah OR 26. With entropy,
Washington OR leads (54) and Clark is second (50). Franklin NY scores 19
either way.

**Two-stage framework.** Shortlist: counties that at least 1% of SMAA
weightings put in the top 10, floor off (161 counties). Ranked by 25-year
cost at $190/t: Clark, Franklin, Clinton NY, Chautauqua NY, Niagara NY,
Walla Walla WA, Chesterfield SC, Whitman WA, Marlboro SC, Oneida NY. Grant
is 28th. Clark is #1 under all four shortlist rules (1% or 5%, floor on or
off); Franklin drops out with the floor on.

**Engine run with the monetized implied weights** (cost 0.54,
energy_carbon 0.37, grid 0.08, climate 0.01): its top 10 is Oklahoma and
Texas counties and shares 0 counties with the dollar top 10. This and the
2.7x carbon example are the two reasons dollars do the ranking.

**Advisor consulted before the recommendation.** It agreed with featuring
Clark and set the wording: Clark leads in every scenario tested but not
decisively. Checks it asked for, and their results:

- **Queue baseline sensitivities added to `monetize.py`.** At 2.0 and 2.5
  years Clark is #1. At 1.5 years Franklin is #1 and Clark 6th. Clark leads
  Franklin by $48.7M at $190/t, 1.95 months of delay, so Clark leads only
  if it can energize within about 2.25 years.
- **Repo search for Clark's utility** (Clark County, Clark Public
  Utilities, Vancouver, Camas, Ridgefield in `research/` and `docs/`):
  nothing beyond a demo-script mention. Power availability is the top
  diligence item, stated as a threshold, not inferred.
- **Shortlist rule check:** done, as above.
- **Clark's weak spots named in the write-up:** land pillar 22nd
  percentile (314 people per km²), fiber 29%, 4.7 GW of plants within
  100 km against Grant's 16.2 GW, no existing FracTracker facility.
- **Deck conflict stated:** featuring Clark means reworking
  `docs/deck.md`, `docs/demo_script.md`, `research/implementation.md`,
  and `research/risk.md`, which this branch doesn't touch.
- **Structure:** stage 2 is the primary ranking, Borda is a cross-check,
  and the variance shares are labeled as weights on dollars, not engine
  weights.

**Recommendation in `docs/weighting.md`.** Featured: Clark WA.
Alternative 1: Franklin NY, if the carbon price is above about $200/t at
state-average power, Clark's new-load rate is above about $104/MWh, or
Clark's power arrives about 2 months later than the proxy. Alternative 2:
Grant WA, if its queue clears to Clark's level and its power costs about
$2/MWh less than Clark's ($18/MWh less with its current queue).
