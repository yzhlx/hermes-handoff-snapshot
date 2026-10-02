# TAG-REPORT — Hermes Cloud Core V1 RC1

**Date:** 2026-07-22.

---

## 1. Tag created (local)

```bash
git tag -a cloud-hermes-core-v1-rc1 \
  -m "Hermes Cloud Core V1 RC1: local integration verified, public cloud deployment pending"
```

- Tag name: **`cloud-hermes-core-v1-rc1`** (annotated).
- Points to: `b76d18e23e9bb7f77870b9ff2ad91f9ff7928328` (final integration commit).
- Message clearly states public-cloud deployment is **pending**.

## 2. Why RC1 (not v1.0.0)

Per `AGENTS.md` and the task mandate, a formal release tag (`v1.0.0` / `cloud-hermes-core-v1.0.0`)
is withheld until:

- real public-cloud deployment is completed,
- public HTTPS domain acceptance passes,
- Windows-PC-powered-off tablet acceptance passes.

Until then only `rcN` tags are used. If a future commit requires a new tag, use the next
increment (`cloud-hermes-core-v1-rc2`, …); never force-move an existing tag.

## 3. Push status

Tag push is **BLOCKED** (see PUSH-REPORT.md) — it requires the remote + auth that are not
available here. Once the remote exists, `git push origin cloud-hermes-core-v1-rc1` publishes it.

## 4. Verification (local)

```
git rev-list -n1 cloud-hermes-core-v1-rc1   # b76d18e...
git cat-file -t cloud-hermes-core-v1-rc1     # tag (annotated)
git tag -l | grep rc1                        # cloud-hermes-core-v1-rc1
```
