# Stitch Ideate 现状约束 Brief

## 1. 这份文档的用途

这不是新 PRD，也不是纯视觉需求单。

目的只有一个：把当前产品里已经存在的功能、状态机、接口前提和未实现边界说清楚，方便 Stitch 在 ideate / redesign 时只重做视觉与信息组织，不把现有后端约束打散。

## 2. 当前产品一句话定义

Miro 当前是一个“跨文化商务沟通 rehearsal 产品原型”。

核心链路不是翻译，而是：

`会前 setup -> 生成策略 -> live rehearsal -> 结束后 review -> 累积长期 memory`

产品重点是语言与语用信号，不是表情识别，不是硬件端 AI，不是完整支付系统。

## 3. 当前信息架构

| 路由 | 是否需要登录 | 当前作用 | 数据来源现状 |
| --- | --- | --- | --- |
| `home` | 否 | 品牌入口、能力概览、跳转 live/review | 本地状态 |
| `live` | 是 | 会前配置 + live rehearsal 主链路 | 已接后端，支持本地 fallback |
| `hardware` | 是 | 设备状态、同步记录、日志入口 | 前端本地假数据，后端未实现 |
| `review` | 是 | 查看 rehearsal/review 结果 | 已接后端，支持本地 fallback |
| `pricing` | 否 | 方案卡片、余额展示、top up 按钮 | 前端本地模拟，后端未实现 |
| `settings` | 是 | 账号摘要、语言切换、credits 入口 | 账号信息部分接后端，设置本身本地模拟 |

当前只有 `home` 和 `pricing` 是公开路由。

## 4. 页面级功能清单

### 4.1 Home

- 作用：作为品牌主页，同时把用户导向 `Live Simulation` 和 `Review Center`
- 主要内容：
- Hero + CTA
- User Twin 高频问题摘要
- Testimonials
- CQ score / tracked signals / repeated risks 数字摘要
- 关键交互：
- `Start new simulation` 进入 live
- `Open Review Center` 进入 review
- 如果未登录，进入受保护页面前会先弹 auth modal

### 4.2 Live Simulation

这是当前唯一真正串到核心后端逻辑的主模块，必须按“两阶段”理解。

#### A. Setup 阶段

- 用户可编辑字段：
- `country`
- `meetingType`
- `goal`
- `voiceStyle`
- `voiceProfileId`
- `duration`
- `constraints`
- `files`
- 用户可执行动作：
- `Generate strategy`
- `Start simulation`
- 关键行为：
- 切换 `country` 会重置默认 `meetingType`、`goal`、`voiceStyle`，并清空当前 `voiceProfileId`
- `voiceProfileId` 是启动前置条件之一
- setup 改动会触发新的 `setupRevision`
- 一旦 setup 变了，旧 strategy 会失效
- 当前 setup 状态分三种：
- `draft`
- `ready_for_strategy`
- `strategy_ready`

#### B. Session 阶段

- 用户可执行动作：
- 输入文本练习回答
- `Evaluate language`
- 收起/展开右侧 drawer
- `Back to setup`
- `End session & analyze`
- 当前 session 右侧 drawer 包含：
- metrics summary
- alerts / reminders
- latest translation
- transcript
- 当前并没有真实语音对话 UI 逻辑，`Mic` 只是提示文案
- 当前真实输入模式仍以文本为主

### 4.3 Review Center

- 作用：查看已生成的 review snapshot
- 当前真实能力：
- 拉取 review list
- 进入单个 review detail
- 展示 summary / next step / metrics / repeated issues / line-by-line transcript
- 当前前端没有真正做出的能力：
- 没有 source filter UI
- 没有 compare 视图
- 没有跨记录对比
- 当前后端 review 来源主要是 `realtime session bridge`，不是任意自由生成

### 4.4 Hardware Devices

- 当前页面承担“演示硬件状态展示 + review 入口”
- 当前前端可见内容：
- 连接状态
- transfer health
- battery
- captured sessions
- vibration logs
- sync records
- 从日志跳 review
- 当前交互应被理解为 demo 状态模拟，而不是真设备能力：
- connect
- disconnect
- sync
- upload / download 动画可由前端演示层模拟
- 不计划做蓝牙、芯片、固件、真实设备接入
- 后端需要的只是一个很薄的 demo 状态层，而不是硬件协议栈

### 4.5 Pricing

- 当前页面是视觉和信息占位，不是真实结算流
- 当前前端可见能力：
- plan card selection
- credits 展示
- top up 按钮
- 当前行为：
- plan selection 只改本地 `pricingSelection`
- top up 只给本地 balance 加数
- 没有真实 checkout、invoice、payment provider

### 4.6 Settings

- 当前作用：
- 展示账号摘要
- 语言切换
- credits 入口
- plan/renewal 摘要
- logout
- 当前真实行为：
- 登录态来自 Supabase + 后端 `/auth/session`
- 语言切换目前只写本地状态
- `zh` 文案并未完全本地化，很多仍是英文 fallback

## 5. 当前核心交互链路

### 5.1 Auth 链路

- 入口：
- 顶部导航 `Register / Log In`
- 点击受保护路由时自动拉起登录
- 真实流程：
- 前端用 Supabase email/password 登录
- 登录成功后调用 `GET /api/v1/auth/session`
- 后端校验 Supabase token 并返回业务态用户信息
- 登录后如果之前有 pending route，会自动跳转回去
- 登出后会清掉 protected workspace 状态，并回到 `home`

### 5.2 Live 主链路

真实后端链路必须按下面顺序理解：

1. 保存/更新 simulation setup
2. 生成 strategy
3. 运行 precheck
4. 创建 realtime session
5. start realtime session
6. respond turn
7. end realtime session
8. bridge 到 review

这条链路里任何一步都不是纯展示状态。

### 5.3 Setup Revision 规则

- `simulation` 不是一次性表单，它有持久化的 `setupRevision`
- 修改 setup 会 bump revision
- strategy 绑定到某个 revision
- 如果 revision 变化，旧 strategy 会立刻失效
- realtime session 也绑定当时的 `setupRevision` 和 `strategyForSetupRevision`
- 所以 redesign 不能把 strategy 当成“纯静态说明卡片”

### 5.4 Realtime Session 恢复逻辑

当前 live 页面除了 setup/session 两个主视图，还有 recovery notice：

- 有 active session 但当前不在 session 画面
- 有 pending session 还没完全开始
- 上一场 session 已 ended
- review bridge 失败，可重试 bridge
- voice profile 加载失败
- simulation hydrate 失败
- session hydrate 失败

这说明 redesign 不能只考虑 happy path，必须给“恢复、继续、重试”保留信息层级。

### 5.5 Review Bridge 规则

- review 不是用户在前端随手生成的 note
- review 是在 realtime session `ended` 或 `failed` 后，由 `/reviews/from-realtime/{sessionId}` 生成的 snapshot
- bridge 成功后才会在 review list 里出现
- bridge 是幂等的，同一 session 不会重复生成多个 review

## 6. 后端已落地的硬约束

### 6.1 Live 相关状态枚举

`simulation.status`

- `draft`
- `ready_for_strategy`
- `strategy_ready`

`realtime.status`

- `pending`
- `active`
- `ended`
- `failed`

`review.overallAssessment`

- `needs_work`
- `mixed`
- `promising`

### 6.2 Live setup 的关键字段

后端当前把下面字段视为正式输入：

- `countryKey`
- `meetingType`
- `goal`
- `durationMinutes`
- `voiceStyle`
- `voiceProfileId`
- `constraints`

其中 `voiceProfileId` 是强约束。

如果没有 voice profile：

- strategy 无法生成
- realtime session 无法创建

### 6.3 当前后端枚举值

`meetingType`

- `first_introduction`
- `commercial_alignment`
- `relationship_building`

`goal`

- `establish_trust_before_pricing`
- `clarify_process_and_risk_ownership`
- `build_rapport_before_scope_depth`

`voiceStyle`

- `formal_measured`
- `direct_structured`
- `warm_relational`

新的 UI 可以改标签文案，但不要随意改掉这组业务语义。

### 6.4 Precheck 约束

后端当前存在正式 precheck：

- `ready`
- `learning_required`
- `learning_outdated`
- `country_not_supported`

这意味着 live launch 在后端并不是“只要点了 Start 就能进”。

### 6.5 Review 的真实来源

当前 review detail 会带这些业务字段：

- `countryKey`
- `meetingType`
- `goal`
- `durationMinutes`
- `voiceStyle`
- `voiceProfileId`
- `setupRevision`
- `strategyForSetupRevision`
- `metrics`
- `lines`

所以 redesign 时，review 不能被改成一个和 live setup 完全脱钩的内容卡片系统。

## 7. 现阶段前后端不一致点

这些点最好直接告诉 Stitch，不然很容易设计出“看上去合理、实际上接不住”的方案。

### 7.1 Precheck 弹窗允许 `Continue anyway`，但后端仍会拦截 launch

- 前端现在会在 `learning_required / learning_outdated` 时弹窗
- 文案允许用户继续
- 但后端 `create realtime session` 仍然要求 precheck ready
- 也就是说，当前真实后端并不支持跳过 learning 直接开始 live

这不是视觉问题，是业务规则未对齐。

### 7.2 前端没有 Learning 页面，但后端已经有 Learning / Progress / Complete API

- 后端已有 learning country / progress / complete
- 前端没有对应页面入口
- 所以 precheck 失败时，用户实际上没有完整的前端闭环可走

### 7.3 Review Center 文档里提过 filter，但当前前端没有 filter UI

- 现在只能 list + select detail
- 没有 `all / simulation / device` 的实际筛选交互

### 7.4 Hardware 和 Billing 目前还是占位模块

- 页面存在
- 交互不存在
- 后端接口还是 placeholder

### 7.5 中文并未完全本地化

- `zh` 只是部分 fallback
- redesign 不要假设当前已经有完整中英双语内容系统

## 8. 设计时可自由调整的部分

- Home 的内容组织、视觉风格、信息密度
- Live setup 的布局、层次、表单编排
- Session 阶段的视觉表现、drawer 结构、指标表达方式
- Review 的视觉呈现、摘要层级、阅读效率
- Settings / Pricing / Hardware 的视觉统一性

## 9. 设计时不要改掉的业务骨架

- Live 必须保留 `setup` 和 `session` 两阶段
- Strategy 必须和 setup revision 强绑定
- Start simulation 不能绕开 setup completeness 和 voice profile
- Review 必须来自已完成 session 的 bridge
- Auth 仍然是 protected route gating 的前提
- Hardware / Billing 当前不要被设计成“已完成产品能力”
- 如果要引入 Learning，应该作为新模块补齐，而不是偷偷塞进现有弹窗假装已经可用

## 10. 给 Stitch 的建议提问方向

- 如何让 Live setup 更清晰地表达“已完成哪些前置条件、还缺什么”
- 如何把 `strategy / precheck / session launch` 做成更顺滑但不丢状态感的体验
- 如何让 Review 更像长期成长闭环，而不是一次性报告页
- 如何在不夸大能力的前提下处理 Hardware / Pricing 这两个仍在占位期的模块
- 如何把 Home 到 Live 到 Review 的叙事关系做得更连续

## 11. 可以直接贴给 Stitch 的输入

请基于以下产品现状做一版 redesign，重点优化信息架构、视觉层级和交互清晰度，不要改动底层业务骨架：

- 产品核心链路是 `setup -> strategy -> precheck -> live session -> review`
- `Live Simulation` 是主流程，必须保留 setup 和 session 两阶段
- strategy 和 `setupRevision` 强绑定，setup 改动后 strategy 会失效
- 启动 live 需要完整 setup，尤其需要 `voiceProfileId`
- review 不是自由笔记，而是结束后的 session snapshot
- `hardware` 和 `pricing` 目前还是展示/占位，不要设计成完整可交易/可连接能力
- 当前有 auth gating，只有 `home` 和 `pricing` 是公开页面
- 如果你建议加入 learning flow，请把它作为新增模块明确提出，不要默认系统已经有完整学习页面

优先解决的问题：

- Live setup 目前状态很多，但表达不够清晰
- Review 和 Home 之间的长期成长关系不够强
- 现有页面视觉统一性不够，模块成熟度也没有被区分开
