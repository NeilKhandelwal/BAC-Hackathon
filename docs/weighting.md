# Pillar weighting: methods and results

Status: draft. Phase 5 completes this document. The process, decisions, and
interim results are in `docs/weighting_log.md`.

## Method notes

These notes apply to the methods below and to any slide that cites them.

- **Hazard cost understates hazard risk for a data center.** The monetized
  model prices hazards with FEMA NRI building expected-annual-loss rates
  times the campus asset value. Building loss rates cover physical damage
  only. They exclude downtime, lost revenue, and service-level penalties,
  which dominate the cost of an outage at a data center. Treat the hazard
  component as a floor.
- **The pillar floor is a judgment rule.** The engine ranks every county
  below the 10th percentile on any non-exempt pillar under every county
  that isn't. That threshold and the exemption of permitting were chosen,
  not derived. Floor membership doesn't depend on the weights unless a
  weight is zero, so no weighting method can lift a county over the floor.
  Results are reported with the floor on and off where it matters.
