# TEST-REPORT — Local Unit/Integration Tests & Static Checks

All checks executed on the local Windows checkout (managed Python 3.13.12).

## 1. Full test suite (§7.1)

Command:
```
cd cloud-hermes-core-v1
python -m unittest discover -s tests/cloud_hermes -p "test_*.py"
```

Result:
```
Ran 38 tests in 35.987s

OK
```

This is a complete, clean run. No errors, no failures, no skips.

### Note on the prior `WinError 10053` race

Earlier runs intermittently failed with `ConnectionAbortedError: [WinError 10053]` (count grew
1→3 across runs). Root cause: the shared test harness reused a keep-alive connection across
requests; when `tearDown()` shut the server while an idle socket lingered, the next reused
request aborted. Fixed in `tests/cloud_hermes/helpers.py` by (a) a `TestHandler` with
`protocol_version = "HTTP/1.0"` forcing `Connection: close` per response, and (b) a
`TestHTTPServer` with `daemon_threads = False` and a graceful `shutdown()` that joins the serve
thread. After the fix the full 38-test suite passes deterministically.

## 2. Compile checks (§7.2)

```
python -m compileall -q cloud_hermes     -> exit 0
python -m py_compile scripts/*.py        -> exit 0
python -m py_compile cloud_hermes/main.py -> exit 0
```

## 3. Compose render check (§7.3)

```
HERMES_DATA_DIR=/tmp/verify-data HERMES_MOCK_PROVIDER=1 COMPOSE_PROJECT_NAME=hermes-cloud \
  docker compose -f docker-compose.yml config
```

Relevant resolved output (sanitised):
```
services:
  hermes-cloud:
    environment:
      HERMES_BIND_HOST: 0.0.0.0
      HERMES_DB_PATH: /data/hermes_cloud.db
      HERMES_MOCK_PROVIDER: "1"
    expose:
      - "8080"
    ports:
      - mode: ingress
        host_ip: 127.0.0.1
        target: 8080
        published: "8080"
    volumes:
      - source: /tmp/verify-data
        target: /data
```

Confirms:
- **Gate #1:** host publishes only `127.0.0.1:8080` (no `0.0.0.0`).
- **Gate #2:** volume maps the unified `HERMES_DATA_DIR` → `/data`; container DB path `/data/hermes_cloud.db`.
- No public `0.0.0.0` ingress; `expose` keeps the container-internal port available for the healthcheck.

## Conclusion

Local static + dynamic verification is fully green and supports `CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS`.
