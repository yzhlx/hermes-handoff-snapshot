# Hermes AI 提供商配置指南

## 适用范围

本指南对应本地 Hermes Learning OS 的“设置 > AI 配置”。服务只在本机回环地址上运行；AI 请求由本地 Python 服务发起，浏览器不会保存 API 密钥。

支持两种协议：

- `chat_completions`：OpenAI 兼容 Chat Completions。
- `responses`：OpenAI Responses 风格接口。

图像快速录入目前只支持 `chat_completions`，且仍取决于所选服务实际提供视觉能力。

## 配置字段

| 字段 | 说明 |
| --- | --- |
| AI 服务地址 | 必须是无查询参数、无片段的 HTTPS 地址。可填写服务根地址、`/v1` 或对应协议的端点。 |
| 协议 | 必须与服务端实现匹配；不要把 Chat Completions URL 与 Responses 协议混用。 |
| 模型 | 使用服务商实际提供的模型 ID；应用不会替模型名做猜测或映射。 |
| 超时 | 5–120 秒，默认 30 秒。 |
| API 密钥 | 首次保存或替换时填写；勾选“清除已保存的密钥”可移除已存密钥。 |

## URL 规范化

选择 `chat_completions` 时，下列输入会被规范化为同一类目标：

| 输入形式 | 请求目标 |
| --- | --- |
| `https://provider.example` | `https://provider.example/v1/chat/completions` |
| `https://provider.example/v1` | `https://provider.example/v1/chat/completions` |
| `https://provider.example/v1/chat` | `https://provider.example/v1/chat/completions` |
| `https://provider.example/v1/chat/completions` | 保持不变 |

选择 `responses` 时，服务根地址或 `/v1` 会指向 `/v1/responses`；完整 `/v1/responses` 地址保持不变。

协议与 URL 不匹配会被拒绝。例如，在 `responses` 协议下填写 Chat Completions 终点，或反过来填写，都会返回 `AI_UNSUPPORTED_PROTOCOL`，而不是发送一个混合请求。

## 保存、测试与数据边界

1. 填写 URL、协议、模型和超时；首次使用时填写 API 密钥。
2. 点击“保存 AI 配置”。配置元数据保存在本机 SQLite；密钥只写入 Windows Credential Manager 的 `LearningOS.AI.Provider` 条目。
3. 点击“测试 AI 连接”。成功只代表该 URL、协议、模型和密钥组合能够完成最小文本请求，不代表视觉输入一定可用。
4. 需要更换密钥时填写新值并保存；需要删除时只勾选“清除已保存的密钥”。

API 密钥不会写入 SQLite、浏览器持久化存储、导出内容、截图或诊断日志。设置接口只会返回是否已配置以及受限的尾号状态。

## 常见错误

| 错误码 | 含义与首要检查项 |
| --- | --- |
| `AI_NOT_CONFIGURED` | 保存服务地址和模型。 |
| `AI_KEY_MISSING` | 在设置中保存 API 密钥。 |
| `AI_INVALID_BASE_URL` | 使用 HTTPS，移除查询参数和片段，并检查地址拼写。 |
| `AI_UNSUPPORTED_PROTOCOL` | 让协议与 URL 的终点一致。 |
| `AI_MODEL_NOT_FOUND` | 核对服务商给出的模型 ID 与最终端点。`404` 同时可能表示 URL 填错。 |
| `AI_AUTH_FAILED` | 核对 API 密钥是否有效、是否属于该服务和模型。 |
| `AI_RATE_LIMITED` | 稍后重试，或检查服务商配额。 |
| `AI_TIMEOUT` | 增加超时时间，或确认服务和网络可达。 |
| `AI_PROVIDER_UNAVAILABLE` | 检查服务状态、URL 和网络；应用不会泄露上游响应正文。 |
| `AI_INVALID_RESPONSE` / `AI_EMPTY_RESPONSE` | 上游响应不符合当前协议，或未返回有效文本。 |
| `AI_VISION_UNSUPPORTED` | 图片快速录入需要 Chat Completions 和实际可用的视觉模型。 |

如果连接测试成功但某项功能失败，先确认该功能的协议要求：聊天与错题文本分析可使用两种协议；图片快速录入只能使用 Chat Completions，且服务商需要接受 `image_url` 内容。

## 验证与发布边界

自动化测试使用确定性的 mock 提供商；真实提供商连接测试属于独立的、非破坏性冒烟验证。不要把密钥复制到测试文件、SQLite、浏览器控制台或 QA 工件中。

2026-07-21 生成的独立构建位于 `package-ai-fixed-v2/学习 OS/学习 OS.exe`。它与更早的 `package/`、`package-fixed/`、`package-fixed-v2/` 并存；维护或重新打包时应输出新的目录，不能覆盖既有工件。
