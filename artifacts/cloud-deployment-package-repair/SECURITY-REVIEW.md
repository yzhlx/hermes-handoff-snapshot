# SECURITY-REVIEW — Deployment Package Repair

Static security scan of the changed files, the diff, shell scripts, compose, and artifacts.
No dynamic penetration testing; the goal is to confirm **no real secrets, keys, databases, or
user data** are introduced or referenced by the repair.

## Checks performed (§10)

### [A] Tracked sensitive files
`git ls-files` filtered for `.env`, `.db`, `.sqlite`, `.pem`, `.key`, `secrets`:
**none tracked.** No `.env`, `.db`, `.pem`, or key file is committed.

### [B] Stray `.env`
Only `.env.example` exists; no populated `.env` in the tree.

### [C] Real secret-key patterns
`git grep` for `sk-…`, `AKIA…`, `ghp_…`, `xox…`, and `-----BEGIN … PRIVATE KEY-----`
across source (excluding tests + the clearly-marked test-only helpers/smoke):
**no matches.** No real provider keys, AWS/GitHub/Slack tokens, or private keys.

### [D] `.env.example` content
All values are placeholders/defaults: `HERMES_SECRET_KEY=replace-me`,
`PROVIDER_API_KEY=replace-me`, `ADMIN_INIT_TOKEN=replace-me`,
`PROVIDER_BASE_URL=https://your-provider.example.com/v1`, `HERMES_DB_PATH=/data/hermes_cloud.db`.
No real credentials.

### [E] Hardcoded runtime secrets in scripts/compose
Grep for `https://127.0.0.1`, `password="…"`, `secret_key="…"`, `token="…{8,}"`,
`api_key="…"` in `deploy.sh`/`rollback.sh`/`rollback_smoke.sh`/`docker-compose.yml`:
the only `https://127` occurrence is a **comment** in `rollback.sh` ("never https://127.0.0.1").
No hardcoded passwords/secret/token/api_key values.

### [F] Public ingress
Compose has **no** `8080:8080` or `0.0.0.0:8080` mapping. The only host publish is
`127.0.0.1:8080:8080` (loopback). `HERMES_BIND_HOST=0.0.0.0` is container-internal only.
No public 80/443/8080 listener is created.

### [G] Loopback ingress present
`grep '127.0.0.1:8080' docker-compose.yml` → confirmed.

### [H] Artifacts cleanliness
`find artifacts` for `*.db/*.sqlite/*.env/*.pem/*secret*` → **none** in the repair artifacts.

### [I] rollback.sh hygiene
Uses `HEALTH_URL` (http loopback) and `HERMES_DATA_DIR`; the `https://127` reference is
comment-only. DB read path matches compose (gate #2/#4).

## Log sanitization

`deploy.sh` redacts `Authorization`/key/token lines from any diagnostic log dump via `sed`,
so secret **names** may appear in logs but secret **values** are not echoed.

## Conclusion

The repair introduces **no** real secrets, keys, databases, or user data, and reduces attack
surface by removing the hardcoded `https://127.0.0.1` and the public `0.0.0.0:8080` mapping.
Security scan passes.
