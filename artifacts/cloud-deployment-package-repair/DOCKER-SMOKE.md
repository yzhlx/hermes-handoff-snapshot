# DOCKER-SMOKE — Isolated Package-Repair Smoke (real Docker, temp resources)

## How it ran (§8.2, §9)

Because the local Docker daemon is unavailable on the Windows agent host, the smoke was executed
over SSH to the candidate cloud host, using **only throwaway `/tmp` resources** (never the
production defaults `/opt/hermes-cloud`, `/var/lib/hermes-cloud`, `/var/backups/hermes-cloud`,
and never ports 80/443 or the public network).

```
host:    ubuntu@129.211.0.213
docker:  sudo -E docker  (server=29.6.2)   # -E preserves the exported HERMES_* vars for compose
python:  python3 (3.12.3)
script:  DOCKER="sudo -E docker" PYTHON=python3 bash scripts/rollback_smoke.sh
```

The script is self-contained: it builds a unique project (`hermes-package-repair-<ts>`), uses a
random temp `HERMES_DATA_DIR`/`BACKUP_DIR`, isolates to a high loopback port `18080`, bootstraps
a **test-only** admin, runs a Mock chat + a marker task, then tears everything down via `trap`
(removes only this run's container/network/image/temp dir).

## Result: ALL CHECKS PASSED

```
===== CLOUD HERMES PACKAGE-REPAIR SMOKE =====
started:      2026-07-23T04:53:51Z
host:         VM-0-15-ubuntu
docker:       server=29.6.2
project:      hermes-package-repair-20260723-125351
test port:    18080 (loopback only)
health url:   http://127.0.0.1:18080/api/hermes/v1/health

[1]  building image........................... PASS: image built
[2]  bootstrapping test admin................ PASS: admin bootstrapped
[3]  starting container...................... (up -d)
[4]  healthy + loopback health............... PASS: container healthy
                                                 PASS: loopback health OK at http://127.0.0.1:18080/.../health
[5]  loopback-only bind (no 0.0.0.0)......... PASS: port bound to 127.0.0.1 (127.0.0.1:8080)
                                                 PASS: no 0.0.0.0 listener on 18080 (local bind=127.0.0.1:18080)
[6]  login (bearer)......................... PASS: login OK (token issued)
[7]  mock chat + marker task................ PASS: chat OK (hermes_run_id=run_1d510c47f99b490886d4f6689994d90d)
                                                 PASS: task created (id=task_a16a23c79c8b4b518fb6a705f4f5c32a)
[8]  read endpoints......................... PASS: conversations 200 / tasks 200 / execution-nodes 200 / run 200
[9]  DB file present in temp host data dir.. PASS: DB at <tmp>/data/hermes_cloud.db (204800 bytes)
[10] stop + restart, marker persists....... PASS: marker task persisted across restart
[11] rollback safe backup + verification.... backup written
                                                 PASS: backup exists (204800 bytes)
                                                 PASS: backup integrity=ok
                                                 PASS: backup contains marker data
                                                 PASS: original DB integrity=ok (not dropped)
                                                 PASS: original DB still contains marker data
                                                 PASS: original DB file still present
[12] post-rollback bring-up health......... PASS: service healthy after rollback bring-up
[13] unauthenticated access rejected (401). PASS: unauth -> 401

===== SMOKE RESULT =====
ALL CHECKS PASSED
finished: 2026-07-23T04:54:38Z
```

## What each check proves

- **[1]–[2]:** the image builds and the one-shot `--bootstrap-admin` (fixed in `main.py`) works.
- **[4]:** compose loopback ingress + container health both succeed (gates #1, #3).
- **[5]:** the published port binds **only** `127.0.0.1` (gate #1); no `0.0.0.0` listener.
- **[6]–[8]:** auth (bearer), chat (Mock Provider), and all read endpoints function over loopback.
- **[9]–[10]:** the unified `HERMES_DATA_DIR` volume persists the SQLite DB across a stop/restart
  (gate #2).
- **[11]:** rollback's **non-destructive** online SQLite backup is correct — backup is valid and
  contains the marker, and the **original DB is never dropped** (gate #4 safety).
- **[12]–[13]:** service recovers after a rollback bring-up; unauthenticated calls are rejected
  with 401.

## Cleanup

The `trap EXIT` removed only this run's container, network, image, and temp directory. No
production resources, secrets, or public listeners were created or left behind.
