# ROLLBACK-PLAN.md

## Goal
Return to the verified stable build WITHOUT deleting new cloud data and WITHOUT overwriting
the user's local DB.

## Triggers
- Integration tests fail on the candidate.
- Health check red after deploy.
- Data corruption detected in the cloud DB.

## Steps
1. **Stop** the candidate cloud service (keep the DB volume mounted, read-only).
2. **Do not drop** the cloud DB. Tag it `pre-rollback-<ts>` and keep for forensics.
3. **Restore** the prior stable service image / commit (the old `learning-os` local build is
   untouched; cloud mode is a toggle, not a replacement).
4. **Revert client** to local-provider mode via the rollback switch
   (`HERMES_CLOUD_MODE=0`); old provider code is retained for exactly this purpose.
5. **Verify** local non-AI features (tasks, wrong-answers, Canvas, exit) still work on the
   Windows app.
6. **Keep** cloud data: rollback switches the active path, it does not delete
   conversations/messages/runs/events/memory created in the cloud.

## Automated
- `scripts/rollback.sh <stable_commit>` performs steps 1-4 against the local/docker deploy and
  prints the exact commit + schema version restored. Real public-cloud rollback is
  `BLOCKED_CLOUD_ACCESS` (no cloud host) but the script is written to be cloud-ready.

## Guards
- Rollback never runs `DROP DATABASE` or `rm -rf` on user data.
- Rollback never writes the Provider key to disk or logs.
- Rollback is演练-tested locally (rollback smoke test) and recorded in DEPLOYMENT-REPORT.md;
  the public-cloud演练 is marked UNEXECUTED for lack of cloud access.
