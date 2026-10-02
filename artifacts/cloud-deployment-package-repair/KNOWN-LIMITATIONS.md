# KNOWN-LIMITATIONS — Deployment Package Repair

Honest enumeration of what this repair does **not** do and what remains out of scope.

## Out of scope (by mandate)

1. **No real production deployment.** The Docker smoke used temp `/tmp` resources on the
   candidate cloud host only. No service was deployed to the production paths
   (`/opt/hermes-cloud`, `/var/lib/hermes-cloud`, `/var/backups/hermes-cloud`).
2. **No TLS / HTTPS / DNS / nginx changes.** `nginx.conf` upstream stays
   `http://127.0.0.1:8080` and was not touched. Public HTTPS termination (443 → loopback) is a
   separate, later deployment stage and is explicitly out of scope here.
3. **No real Provider integration.** All tests and the smoke use `HERMES_MOCK_PROVIDER=1`
   (deterministic Mock Provider). A real Provider key/network smoke was not executed (no real
   key in this environment), consistent with the original task §18.
4. **No PR #1 merge / Ready, no Release / Tag.** The integration PR stays Draft; no tags or
   releases were created.
5. **No UI integration started.** `ui/hermes-ui-2-program` was not edited and the UI → Cloud
   Core integration was not begun. This repair only unblocks the UI Integration gate #2.

## Residual risks / notes

- **`sudo -E docker` requirement.** The cloud host grants passwordless `sudo` for docker, and
  compose needs the operator's `HERMES_*` env vars, hence `sudo -E`. On a host where `docker`
  is usable without sudo (user in the `docker` group), simply set `DOCKER=docker`. The smoke
  script handles both via the unquoted `$DOCKER` prefix.
- **Docker userland-proxy / ss output.** The loopback bind is confirmed authoritatively by
  `docker port` (shows `127.0.0.1:8080`). The `ss` corroboration now inspects only the local
  address column to avoid a prior false positive on the peer-address column.
- **One-shot bootstrap.** `main.py --bootstrap-admin` now returns `0` instead of falling through
  to `app.start()`. If any caller relied on the old (buggy) behavior of starting the server after
  a bootstrap, it must be updated — none in this repo do.
- **Windows CRLF.** Committed files are stored with CRLF on this Windows checkout (git's
  `autocrlf` behavior), consistent with prior commits in this worktree. No functional impact.
- **Cloud host is a verification target, not a deployment target.** `129.211.0.213` was used
  solely to exercise real Docker. No persistent resources, images, or listeners were left there
  by the smoke (trap cleanup removed this run's artifacts).

## What the next agent must still do

- Run the *Hermes Cloud UI Integration V1* gate #1–#6 (gate #2 should now resolve to
  `CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS`).
- Perform the actual production deployment + real-Provider smoke on a properly provisioned host
  (with real secrets supplied via the secret manager / env, never committed).
