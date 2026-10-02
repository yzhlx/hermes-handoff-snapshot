# ROLLBACK-SMOKE — Rollback Safety Verification

The deployment-package-repair mandate required proving that a rollback is **safe** (non-
destructive) before relying on `scripts/rollback.sh` in production. The full git-code rollback
(`git checkout <stable>`) is intentionally performed only by `rollback.sh` on a real deployment
host; the isolated smoke validates the critical property — the **online SQLite backup** — without
disturbing any git working tree.

## Property under test

Given a live DB containing identifiable marker data (a marker task written during the smoke):

1. `rollback.sh` takes an online backup via `sqlite3.connect(src).backup(dst)` to
   `${BACKUP_DIR}/pre-rollback-<ts>.db` **before** any destructive step.
2. The backup must be (a) present and non-zero, (b) pass `PRAGMA integrity_check` (`ok`),
   (c) contain the marker data, and (d) the **original** DB must remain intact (not dropped,
   integrity ok, marker still present, file still on disk).
3. The service must come back healthy after the rollback bring-up.

## Result (from DOCKER-SMOKE step [11]–[12])

```
[11] rollback safe backup + verification.... backup written
                                                 PASS: backup exists (204800 bytes)
                                                 PASS: backup integrity=ok
                                                 PASS: backup contains marker data
                                                 PASS: original DB integrity=ok (not dropped)
                                                 PASS: original DB still contains marker data
                                                 PASS: original DB file still present
[12] post-rollback bring-up health......... PASS: service healthy after rollback bring-up
```

## Why this is the critical property

A deployment rollback that drops or corrupts the live DB would be catastrophic. `rollback.sh`
was rewritten so that:

- The backup is taken **online** (`sqlite3` `backup()`) — no service downtime needed to snapshot.
- Verification (existence + `integrity_check` + marker presence) gates any subsequent
  `git checkout`. If verification fails, the script stops rather than proceeding.
- The original DB file is **never** removed by the script; the git checkout swaps code, not data.

## Scope honesty

The isolated smoke does **not** execute the actual `git checkout <stable>` (that is a real
deployment-host operation). It verifies the backup+restart guarantee, which is the part that
must never lose user data. The `git checkout` path in `rollback.sh` is reviewed (not executed
here) and is guarded by the backup verification above.
