# Dev checkpoint selection: exact metric populations (2026-09-04)

Selection metric: dev_assigned_policy_and_functional
Population: concision=full, BOTH formats, filter=attempted (truncated/malformed count as failures)
Split: dev only (ssrf_redirect). No held-out test rows in any sweep.

| ckpt | functional | conditional (pass|functional) | joint = SELECTION |
|------|-----------|-------------------------------|-------------------|
| 18   | 11/48 = .2292 | 6/11 = .5455 | 6/48 = .1250  <- selected |
| 36   |  9/48 = .1875 | 4/9  = .4444 | 4/48 = .0833 |
| 54   | 15/48 = .3125 | 5/15 = .3333 | 5/48 = .1042 |

Identity P(F and P) = P(F) * P(P|F) holds exactly for all three.

Per-format detail (dev-18): structured/full 7/24 functional, 5/7 conditional, 5/24 joint;
freeform/full 4/24 functional, 1/4 conditional, 1/24 joint.

Interpretation constraints:
- Checkpoint 18 RANKED HIGHEST on the single-task development metric, by one output over 54.
- The loss curve and behavioral metric DIRECTIONALLY AGREE; they are not independent signals
  (same dev task, same distribution).
- Checkpoint 54 had NO behavioral role in the model floor: the corrected floor is
  planner-independent. Any claim that checkpoint 54 made the floor conservative is withdrawn.
- Checkpoint 54 has the highest functionality but the lowest conditional compliance; the
  checkpoints trade off along different axes on 48 rows of one task.
