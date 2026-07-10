# Miro Production Readiness

更新时间：2026-07-10

## 已跑通的产品闭环

在本地后端测试环境中，以下链路已经可以连续完成：

1. 上传 TXT 或文本型 PDF。
2. 提取正文、摘要和 excerpt，并保存到当前 simulation。
3. 根据资料生成 `opening / probe / close` 面试提纲。
4. 创建 realtime session，持久化 AI 第一问。
5. 接收用户回答，按上传正文和 User Twin 检索下一轮上下文。
6. 结束面试，生成 Review 报告并保存到账号范围。
7. 从 Review 生成硬件同步记录。
8. 生成带 `schemaVersion` 和 `packetHash` 的 Review Packet，供真实硬件适配器传输。

当前证据：后端完整闭环测试 `99 passed`；最新上传检索、LLM、Doubao 客户端和端到端测试 `5 passed`。前端 TypeScript/Vite 构建和高保真静态构建均通过。

## 当前线上状态

- 前端已部署到 [miro-vert.vercel.app](https://miro-vert.vercel.app)。
- 当前 Browser Voice 版本部署为 `dpl_5gXbGo2gU34kBZLbkPmb2bauGB7w`。
- 最新硬件失败状态修复部署为 `dpl_7ht7wqGM8U9LPBmLBL9U6JZiLgBw`。
- 线上 Live 启动现在要求真实后端 session 创建成功；语音优先使用 Doubao，供应商不可用时可使用浏览器原生 Browser Voice（真实麦克风识别、后端文字回合和浏览器语音播报）。
- 生产 API 会拒绝 `speech_stub` 和 demo 硬件同步，避免测试数据进入正式账号或设备记录。
- 线上 API `https://47-238-228-236.sslip.io/api/v1` 当前健康检查超时，因此线上还不能宣称完整业务可用。
- 后端新增 `/api/v1/ready`：开发环境用于数据库连通性检查，生产环境还会检查文本模型、语音通道和硬件适配器配置，未准备好时返回 `503`。
- 生产环境不会把 API 失败静默伪装成本地面试；本地 localhost 预览才允许 fallback。

## 正式商用前必须完成

| 项目 | 当前状态 | 完成条件 |
|---|---|---|
| 后端部署 | 阻塞 | ECS 可访问，执行 migrations，`/api/v1/ready` 稳定返回 200 |
| 文本模型 | 待配置 | 设置生产 `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL`，并完成质量评测 |
| 实时语音 | 双通道 | 优先完成 Doubao `volc.speech.dialog` 授权；否则验证 Browser Voice 的浏览器识别、后端文字回合和语音播报 |
| 文件存储 | 部分完成 | 明确原文件/解析文本的保留期、删除、加密和对象存储策略 |
| 报告质量 | 待评测 | 用固定案例集验证资料引用、文化语境、评分一致性和失败降级 |
| 真实硬件 | 未完成 | 完成 BLE/USB 协议、设备认证、传输确认、断点重试和固件兼容性；生产不会再把 demo 设备标成真实同步 |
| 运营可靠性 | 未完成 | 日志、指标、告警、超时、重试、限流和数据恢复流程上线 |
| 合规与支付 | 未完成 | 隐私政策、用户授权、跨境数据处理、支付/退款/发票流程确认 |

## 需要人工提供的外部条件

1. ECS 的 SSH 或 CI/CD 发布权限，以及生产数据库连接串。
2. Doubao 控制台的 `volc.speech.dialog` 资源授权和对应 API 凭据；或者明确启用 `BROWSER_VOICE_FALLBACK_ENABLED=true` 作为语音通道。
3. 生产文本模型 API 凭据及可接受的成本/延迟限制。
4. 真实硬件协议文档、设备鉴权方式和测试设备。
5. 文件、录音、转写和报告的保存/删除规则。

没有这些外部条件时，代码可以继续本地验证，但不能把当前页面称为正式商用全链路。
