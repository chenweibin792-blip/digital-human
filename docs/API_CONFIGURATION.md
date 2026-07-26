# OpenAI 兼容 API 配置

在 `.env` 中填写，不要修改 Python、HTML 或 JavaScript：

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://provider.example/v1
LLM_API_KEY=replace-with-your-secret
LLM_MODEL=provider-model-name
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
LLM_TEMPERATURE=0.7
LLM_MAX_HISTORY_TURNS=10
LLM_STREAM=true
SYSTEM_PROMPT=你是一名简洁、自然、友好的AI数字人助手。
```

`LLM_BASE_URL` 应指向包含 `/v1` 的兼容根地址，后端调用
`/chat/completions`，并在服务器侧通过 `Authorization: Bearer` 传递密钥。
浏览器不会读取密钥。

每个 WebRTC `sessionid` 有独立历史，清空仅作用于当前会话。回答在送入 TTS
前会移除代码块、Markdown 装饰和 URL。

阶段4使用本地 Mock 验证了流式/非流式、多轮、401、404、429、超时、空响应、
非 JSON 和流中断。没有提供真实 API Key，因此没有把任何线上供应商标记为
已经通过。更换供应商后请先用短消息验证模型名、计费和流式兼容性。

