# SECRET-SCAN — Hermes Cloud Core V1

**Date:** 2026-07-22. Scope: all tracked files, all untracked-but-not-ignored files in the
integration worktree, and the loose artifact directory
`learning os-worktrees/artifacts/cloud-hermes-core-v1/`.

---

## 1. Patterns searched

```
api_key, apikey, api-key, authorization, bearer, password, passwd, secret, token, cookie,
private_key, BEGIN PRIVATE KEY, BEGIN RSA PRIVATE KEY, BEGIN OPENSSH PRIVATE KEY,
deepkey, openai, credential, session_secret, jwt_secret, admin_password, bootstrap_admin,
sk-[A-Za-z0-9]{20,}   (OpenAI-style provider key shape)
```

## 2. Method

- `grep -rniE` over `*.py *.js *.html *.json *.yml *.yaml *.sh *.ps1 *.env* *.md *.txt`.
- Match lines with an assignment shape were **masked** (`"***"`) before review so no value
  could leak into logs.
- `.gitignore` excluded binaries/DBs; `work/` runtime files were scanned separately and are
  not committed.

## 3. Results — REAL secrets

**0 real secrets found.**

## 4. Matches and their disposition (all benign)

| File | Match | Disposition |
|------|-------|-------------|
| `docker-compose.yml` | `PROVIDER_API_KEY: "${PROVIDER_API_KEY}"` etc. | **Safe** — `${...}` env-var reference, no literal. Committed. |
| `scripts/smoke_local.sh` | `SECRET="smoke-secret-key-local-only-$(date +%s)"`, `ADMIN_TOKEN="init-token-smoke"`, `ADMIN_PASS="Smoke!Pass#2026"` | **Safe** — runtime-generated / obviously-fake local smoke values. Committed (script is a deploy aid; generates its own secret at runtime). |
| `tests/cloud_hermes/helpers.py` | `secret="test-secret"`, `provider_api_key="sk-FAKE_PROVIDER_KEY_DO_NOT_LEAK"` | **Safe** — explicit fake placeholder, never used (MockProvider injected), asserted not-in-DB/responses by tests. Committed. |
| `work/presentations/learning-os-ui/tmp/test_learning_os_api.py` | `secret="***"` (test fixture) | **Safe** — fake test value; inside `work/` which is git-ignored and NOT committed. |

## 5. Negative checks (all clean)

- No `sk-` provider keys (real shape) anywhere.
- No `BEGIN ... PRIVATE KEY` blocks anywhere.
- No `.env` files present (only `.env.example` with `replace-me` placeholders was added).
- No token/cookie in committed Markdown reports (verified by the masked scan returning nothing
  for the `artifacts/cloud-hermes-core-v1/*.md` set).

## 6. Tokens that WERE found but correctly excluded

`api-results/login.json` and `logs/deploy-smoke.log` contain real **session** `access_token`
values from the local smoke run. These are runtime outputs, not source. They were **excluded**
from the repo (see PRIVATE-DATA-SCAN.md). No provider key, password, or private key appears in
them.

## 7. Conclusion

No secret enters version control. Provider key remains env/secret-manager only, exactly as the
Cloud Hermes design requires (SECURITY-REVIEW.md). Safe to publish the committed set.
