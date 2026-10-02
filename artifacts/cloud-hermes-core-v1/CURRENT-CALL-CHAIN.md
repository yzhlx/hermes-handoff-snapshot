# CURRENT-CALL-CHAIN.md

Verified current (pre-Cloud-Hermes) call chain. Source evidence in parentheses.

```
[Browser / Windows WebView] learning-os-app.js
   API = http://127.0.0.1:4174/api/v2            (learning-os-app.js:1)
   POST /api/v2/chats                                 (learning-os-app.js:292)
   POST /api/v2/chats/{id}/messages  {role,content}  (learning-os-app.js:293)
        |
        v
[Local Python] learning-os-api.py  (BaseHTTPRequestHandler, loopback 127.0.0.1)
   /api/v2/chats/{id}/messages
     -> service.ai.answer_chat(service.core.list_chat_messages(chat_id))  (api.py:1100)
     -> service.core.add_chat_message(chat_id, {role:assistant, content}) (api.py:1101)
        |
        v
[Local Python] learning-os-ai.py  AIGateway
   answer_chat(messages) -> generate_text(messages, max_tokens)         (ai.py:332,289)
     -> validate_config(): reads base_url/model/timeout from core settings
        + api_key from WindowsCredentialStore (local OS credential manager) (ai.py:238-249)
     -> _request(protocol, base_url, headers{Authorization: Bearer <local key>}, payload)
        -> urllib POST to Provider /v1/chat/completions                   (ai.py:274-287)
        |
        v
[External] OpenAI-compatible Provider (deepkey.top / cctq.ai)
        |
        v
[Local SQLite] chat_messages  (learning-os-store.py Core store)
```

## Properties of the current chain

- AI request never passes through Hermes Gateway / Runtime / Profile / Memory / Skill /
  Tool Router / Event Store / Master / Critic / Execution Node.
- Provider API key lives in the **local Windows Credential Manager** and is attached by the
  local service; it is never sent to the browser.
- No `hermes_run_id`, no event append, no memory retrieval, no cloud persistence.
- Single-device: the Windows service must be running for AI to work. If the PC is off, the
  tablet/phone web UI cannot reach AI (it proxies to 127.0.0.1:4174 which is down).
- `HERMES_SYSTEM_INSTRUCTIONS` (ai.py:21) is the only "Hermes" substance — a system prompt.

## What the target chain must change (see TARGET-CALL-CHAIN.md)

Replace the `Local Python -> Provider` hop with `Client -> Cloud Hermes Gateway -> Master
-> Context/Memory/Event -> Provider -> Event/Memory writeback`, so the PC is optional.
