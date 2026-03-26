window.MIRO_DATA = {};
MIRO_DATA.ISSUE_LIBRARY = {
  soft_refusal_missed: {
    en: { title: "Soft refusal missed", short: "Soft refusal", detail: "The partner signalled hesitation indirectly. Slow down and offer a lighter next step." },
    zh: { title: "错过委婉拒绝", short: "委婉拒绝", detail: "对方用高语境方式表达了犹豫。你需要降速，并给出更柔和的下一步。" }
  },
  price_pressure: {
    en: { title: "Price pressure too early", short: "Price pressure", detail: "You pushed for commitment or price closure before trust was established." },
    zh: { title: "过早施加价格压力", short: "价格压力", detail: "你在信任尚未建立前就推进报价或成交承诺。" }
  },
  repetition_loop: {
    en: { title: "Repetition loop detected", short: "Repetition", detail: "The same pressure cue appeared again, which can sound rigid or anxious." },
    zh: { title: "检测到重复施压", short: "重复表达", detail: "同一类施压表达再次出现，容易显得僵硬或焦虑。" }
  },
  taboo_wording: {
    en: { title: "Taboo wording risk", short: "Taboo cue", detail: "A low-value or face-threatening phrase was detected for this country." },
    zh: { title: "禁忌措辞风险", short: "禁忌表达", detail: "检测到在当前国家语境中带有贬值或伤害面子的用词。" }
  },
  pause_control: {
    en: { title: "No pause window", short: "Pause control", detail: "The response packed too many asks into one turn and gave no breathing room." },
    zh: { title: "缺少停顿窗口", short: "停顿控制", detail: "一轮回应塞入过多要求，没有给对方留出反应空间。" }
  },
  metaphor_risk: {
    en: { title: "Metaphor did not travel", short: "Metaphor", detail: "Culture-specific idioms or metaphors can reduce clarity in high-stakes meetings." },
    zh: { title: "隐喻迁移失败", short: "隐喻风险", detail: "文化特定的成语或隐喻在高风险商务场景中可能削弱清晰度。" }
  },
  intensity_spike: {
    en: { title: "Intensity too high", short: "Intensity", detail: "The phrase sounded more forceful than the current trust level supports." },
    zh: { title: "语气强度过高", short: "强度过高", detail: "当前话语强度超出了现有信任程度可以承受的范围。" }
  },
  underdeveloped_answer: {
    en: { title: "Answer is too thin", short: "Thin answer", detail: "The response is too short to move the conversation forward." },
    zh: { title: "回答过薄", short: "回答过薄", detail: "这段回应太短，难以推动对话继续向前。" }
  },
  premature_pricing_push: {
    en: { title: "Price pressure is too early", short: "Early pricing push", detail: "This opening risks pushing pricing before trust is established." },
    zh: { title: "过早推进价格", short: "过早价格推进", detail: "这段开场在信任建立前就推进价格，风险过高。" }
  },
  overclaiming: {
    en: { title: "Claim sounds too absolute", short: "Overclaiming", detail: "The wording may sound overconfident or hard to defend." },
    zh: { title: "表达过于绝对", short: "绝对化表达", detail: "这段措辞显得过于绝对，后续很难支撑。" }
  }
};
MIRO_DATA.COUNTRY_LIBRARY = {
  Japan: {
    label: { en: "Japan", zh: "日本" },
    defaultMeeting: "First Introduction",
    defaultGoal: "Establish trust before pricing",
    localOpening: "本日はお時間をいただきありがとうございます。まずは相互理解から始められればと思います。",
    openingEn: "Thank you for making time today. I hope we can begin by understanding each other first.",
    openingZh: "感谢今天拨冗会面。希望我们先从彼此了解开始。",
    tabooPatterns: [/cheap/i, /final offer/i, /why not/i, /no problem/i],
    strongPatterns: [/must/i, /need your answer/i, /today/i, /immediately/i, /final/i],
    pricePatterns: [/price/i, /discount/i, /commit/i, /final/i],
    metaphorPatterns: [/home run/i, /slam dunk/i, /kill two birds/i, /move the needle/i],
    softeners: [/would/i, /could/i, /appreciate/i, /perhaps/i, /may/i],
    strategies: [
      { tag: { en: "High-context", zh: "高语境" }, title: { en: "Treat hesitation as signal", zh: "把犹豫视为信号" }, bullets: { en: ["If the client says they need to think carefully, do not push for instant closure.", "Offer a lighter next step such as a memo, sample pack, or follow-up note."], zh: ["如果客户表示需要认真考虑，不要继续追问立刻定案。", "改用更轻的下一步，例如补充备忘录、样品包或后续说明。"] } },
      { tag: { en: "Face management", zh: "面子管理" }, title: { en: "Keep value language elevated", zh: "保持价值表达的高度" }, bullets: { en: ["Avoid low-value words like cheap or bargain during first trust-building meetings.", "Use quality, reliability, continuity, and fit instead."], zh: ["在第一次建立信任的会面中，避免 cheap 或 bargain 这类低价值词。", "改用 quality、reliability、continuity 和 fit 这类表达。"] } },
      { tag: { en: "Pacing", zh: "节奏控制" }, title: { en: "Leave room after a key ask", zh: "关键请求后给对方留出停顿" }, bullets: { en: ["Do not stack price, timeline, and commitment in one sentence.", "Make one ask, pause, and let the partner respond at their own pace."], zh: ["不要把价格、时间表和承诺请求堆在同一句里。", "每次只提出一个请求，停一下，让对方按自己的节奏回应。"] } }
    ],
    partnerResponses: {
      low: { local: "そうですね、前向きに検討できそうです。", en: "That sounds workable. We can continue this positively.", zh: "这个方向可以继续积极推进。" },
      medium: { local: "少し社内で相談したいと思います。", en: "I would like to consult internally first.", zh: "我想先在内部再讨论一下。" },
      high: { local: "慎重に考えさせていただければと思います。", en: "We would appreciate time to consider this carefully.", zh: "我们希望先谨慎考虑一下。" }
    }
  },
  Germany: {
    label: { en: "Germany", zh: "德国" },
    defaultMeeting: "Commercial Alignment",
    defaultGoal: "Clarify process and risk ownership",
    localOpening: "Danke fur Ihre Zeit. Lassen Sie uns die Anforderungen sauber strukturieren.",
    openingEn: "Thank you for your time. Let us structure the requirements clearly.",
    openingZh: "感谢您的时间。让我们把需求清晰地结构化。",
    tabooPatterns: [/trust me/i, /no risk/i],
    strongPatterns: [/must/i, /right now/i, /final/i],
    pricePatterns: [/price/i, /cost/i, /budget/i],
    metaphorPatterns: [/home run/i, /slam dunk/i],
    softeners: [/would/i, /could/i, /please/i, /propose/i],
    strategies: [
      { tag: { en: "Clarity", zh: "清晰度" }, title: { en: "Be explicit about assumptions", zh: "明确表达假设条件" }, bullets: { en: ["State dependencies, dates, and responsibilities directly.", "Do not hide uncertainty behind vague optimism."], zh: ["直接说明依赖项、时间点和责任归属。", "不要用模糊乐观来掩盖不确定性。"] } },
      { tag: { en: "Process", zh: "流程" }, title: { en: "Sequence before persuasion", zh: "先给流程，再给说服" }, bullets: { en: ["Anchor the meeting with process, then discuss commercial upside.", "Use structured bullets instead of idiomatic persuasion."], zh: ["先用流程框架锚定会议，再讨论商业收益。", "优先用结构化要点，而不是习语式说服。"] } },
      { tag: { en: "Risk", zh: "风险" }, title: { en: "Name risk without drama", zh: "冷静说明风险" }, bullets: { en: ["Describe mitigation steps instead of emotional urgency.", "Stay factual and concise."], zh: ["说明缓解步骤，而不是制造情绪化紧迫感。", "保持事实导向和简洁。"] } }
    ],
    partnerResponses: {
      low: { local: "Das ist nachvollziehbar. Bitte senden Sie die Spezifikation.", en: "That is understandable. Please send the specification.", zh: "这个说法合理。请发送规格说明。" },
      medium: { local: "Wir mussen die Annahmen noch prufen.", en: "We still need to validate the assumptions.", zh: "我们还需要验证这些假设。" },
      high: { local: "So konnen wir derzeit nicht zusagen.", en: "We cannot commit under these terms at the moment.", zh: "在这些条件下，我们目前无法承诺。" }
    }
  }
};
MIRO_DATA.COUNTRY_LIBRARY.UAE = {
  label: { en: "UAE", zh: "阿联酋" },
  defaultMeeting: "Relationship Building",
  defaultGoal: "Build rapport before scope depth",
  localOpening: "Thank you for joining us today. It is a pleasure to begin the relationship.",
  openingEn: "Thank you for joining us today. It is a pleasure to begin the relationship.",
  openingZh: "感谢今天会面。很高兴开始建立这段合作关系。",
  tabooPatterns: [/cheap/i, /take it or leave it/i],
  strongPatterns: [/must/i, /immediately/i, /deadline today/i],
  pricePatterns: [/price/i, /discount/i],
  metaphorPatterns: [/slam dunk/i, /kill two birds/i],
  softeners: [/appreciate/i, /would/i, /honor/i, /may/i],
  strategies: [
    { tag: { en: "Relationship", zh: "关系" }, title: { en: "Respect before detail", zh: "先尊重关系，再进入细节" }, bullets: { en: ["Open with respect and mutual intent before pushing operational asks.", "Do not make the first turn purely transactional."], zh: ["先表达尊重和合作意图，再提出操作层面的要求。", "第一次发言不要完全交易化。"] } },
    { tag: { en: "Directness", zh: "直接度" }, title: { en: "Keep firmness warm", zh: "保持坚定，但语气温暖" }, bullets: { en: ["Firm structure is acceptable, but keep the tone warm and respectful.", "Use appreciation before escalation."], zh: ["可以有明确结构，但语气要温和且尊重。", "在升级要求前，先表达感谢与重视。"] } },
    { tag: { en: "Timing", zh: "时机" }, title: { en: "Do not rush closure in the opening", zh: "开场阶段不要急于收口" }, bullets: { en: ["Trust and hierarchy cues need room before price closure.", "Signal patience as well as competence."], zh: ["在价格收口前，需要给信任和层级线索留出空间。", "既要表现能力，也要传达耐心。"] } }
  ],
  partnerResponses: {
    low: { local: "This direction is promising. Let us continue the conversation.", en: "This direction is promising. Let us continue the conversation.", zh: "这个方向有希望。我们继续推进。" },
    medium: { local: "We would prefer to reflect on this with the broader team.", en: "We would prefer to reflect on this with the broader team.", zh: "我们希望先和更大的团队一起再讨论一下。" },
    high: { local: "We are not ready to move on this structure yet.", en: "We are not ready to move on this structure yet.", zh: "我们目前还不能按这个结构推进。" }
  }
};
MIRO_DATA.TESTIMONIALS = [
  { name: "Isabella Chen", company: "Atlas Supply", role: "VP Partnerships", initials: "IC", quote: { en: "Miro caught the exact moment we became too direct in Japanese distributor calls. Our team now rehearses softer next steps before every visit.", zh: "Miro 能抓到我们在日本分销商通话里变得过于直接的那个瞬间。现在团队每次拜访前都会先演练更柔和的下一步。" } },
  { name: "Rafael Mendez", company: "Northframe Commerce", role: "Regional GM", initials: "RM", quote: { en: "The value is not translation. The value is repeated coaching on the same pragmatic mistakes until the team stops making them.", zh: "价值不在翻译本身，而在于系统会持续追踪同一类语用失误，直到团队不再重复犯错。" } },
  { name: "Yuki Sato", company: "Mercury Retail", role: "Strategy Lead", initials: "YS", quote: { en: "The Review Center helped us compare simulation language with real client visit records from the pin. That closed the coaching loop.", zh: "复盘中心让我们能把模拟训练的话术和别针同步回来的真实客户会谈记录放在一起比较，真正闭环了。" } },
  { name: "Taha Hossain", company: "Daybreak Global", role: "Founder", initials: "TH", quote: { en: "The pause and repetition cues are surprisingly useful. We discovered our reps were not impolite, they were just not leaving room.", zh: "停顿和重复提醒非常有用。我们发现销售并不是不礼貌，而是没有给对方留出空间。" } },
  { name: "Haerin Song", company: "Visa", role: "Product Ops", initials: "HS", quote: { en: "It is the first prototype I have seen that treats high-context rejection as a learnable signal, not a translation bug.", zh: "这是我见过第一个把高语境拒绝当成可学习信号而不是翻译错误来处理的原型。" } },
  { name: "John Bai", company: "Plaid", role: "Design Engineering", initials: "JB", quote: { en: "The UI feels enterprise-grade, but the real win is the memory layer. Miro remembers what your team keeps repeating.", zh: "UI 很企业化，但真正的亮点是记忆层。Miro 会记住你的团队一直在重复什么错误。" } }
];
MIRO_DATA.seedState = function seedState() {
  return {
    lang: "en",
    activeRoute: "home",
    loggedIn: false,
    authOpen: false,
    authMode: "login",
    pendingRoute: null,
    drawerCollapsed: false,
    insightsOn: true,
    reviewFilter: "all",
    selectedReviewId: "review-sim-1",
    toast: null,
    user: { name: "Alex Morgan", role: "Director, Global Partnerships", company: "North River Commerce", email: "alex@northriver.com", plan: "Free", balance: 0, renewal: null, cqScore: 78, cqDimensions: [82, 74, 70, 80, 84] },
    pricingSelection: "free",
    userTwin: [
      { id: "tw-1", issueKey: "soft_refusal_missed", count: 3, risk: "High", country: "Japan", lastContext: { en: "Tokyo distributor introduction", zh: "东京分销商初次会面" }, coach: { en: "When the partner says they need to think carefully, stop pushing for closure and offer a summary note instead.", zh: "当对方说需要谨慎考虑时，不要继续收口，改为提供会后摘要和更轻的下一步。" } },
      { id: "tw-2", issueKey: "price_pressure", count: 2, risk: "Medium", country: "Japan", lastContext: { en: "Kyoto retail expansion call", zh: "京都零售扩张电话会" }, coach: { en: "Hold pricing until you receive an explicit invitation to discuss commercial terms.", zh: "在对方明确邀请进入商务条款前，先不要主动推进价格。" } },
      { id: "tw-3", issueKey: "repetition_loop", count: 2, risk: "Medium", country: "Germany", lastContext: { en: "Berlin commercial alignment", zh: "柏林商务对齐会议" }, coach: { en: "Do not restate urgency in each turn. Summarize once, then wait for the partner to process.", zh: "不要每一轮都重复强调紧迫感。总结一次，然后给对方时间处理。" } }
    ],
    reviews: [
      { id: "review-sim-1", source: "simulation", title: { en: "Japan / First Distributor Introduction", zh: "日本 / 分销商初次介绍" }, country: "Japan", date: "2026-03-08T09:10:00.000Z", score: 72, modules: [74, 68, 76, 70], repeatedIssues: ["soft_refusal_missed", "price_pressure"], summary: { en: "You introduced price pressure before the buyer signalled readiness, and you missed a polite hesitation cue.", zh: "你在买方尚未释放准备信号时就推进价格，同时错过了礼貌性的犹豫提示。" }, lines: [{ speaker: "Partner", sourceText: "本日はまず背景を伺えればと思います。", translation: { en: "Today I would first like to understand your background.", zh: "今天我更希望先了解你们的背景。" }, tags: ["High-context", "Trust-building"], issueKey: null, advice: null }, { speaker: "User", sourceText: "We can lock the final price today if you move quickly.", translation: { en: "We can lock the final price today if you move quickly.", zh: "如果你们尽快决定，我们今天就能锁定最终价格。" }, tags: ["Price", "Directness"], issueKey: "price_pressure", advice: { en: "Replace price closure with a lighter trust step such as sharing case studies or a written follow-up.", zh: "把价格收口改为更轻的信任动作，例如分享案例或发送会后书面说明。" } }, { speaker: "Partner", sourceText: "社内でもう少し検討したいと思います。", translation: { en: "I would like to think about this internally a little more.", zh: "我想在公司内部再稍微讨论一下。" }, tags: ["Soft refusal", "Indirectness"], issueKey: null, advice: null }, { speaker: "User", sourceText: "Why not decide now? It is the best offer.", translation: { en: "Why not decide now? It is the best offer.", zh: "为什么不现在就决定？这已经是最好的报价了。" }, tags: ["Pressure", "Taboo cue"], issueKey: "soft_refusal_missed", advice: { en: "Acknowledge the hesitation, slow down, and propose a non-threatening next step.", zh: "先确认对方的犹豫，放慢节奏，再提出没有压迫感的下一步。" } }] },
      { id: "review-device-1", source: "device", title: { en: "Tokyo buyer visit / Pin sync", zh: "东京客户拜访 / 别针同步" }, country: "Japan", date: "2026-03-06T11:45:00.000Z", score: 68, modules: [70, 64, 73, 65], repeatedIssues: ["repetition_loop"], summary: { en: "The wearable pin logged two vibration alerts when pricing urgency was repeated after a hesitation cue.", zh: "可穿戴别针在客户出现犹豫信号后记录了两次因重复价格紧迫表达而触发的震动提醒。" }, lines: [{ speaker: "Device note", sourceText: "Vibration triggered after repeated urgency cue.", translation: { en: "Vibration triggered after repeated urgency cue.", zh: "在重复强调紧迫性后触发震动。" }, tags: ["Wearable", "Urgency"], issueKey: "repetition_loop", advice: { en: "Once urgency is stated, shift to listening instead of restating the same pressure line.", zh: "紧迫性表达一次即可，之后要转向倾听，而不是重复施压。" } }] }
    ],
    hardware: {
      deviceName: "Miro Pin 01",
      connected: true,
      transferHealth: "Healthy",
      firmware: "1.4.2",
      versionPath: "1.3.8 -> 1.4.2",
      battery: 84,
      lastSync: new Date().toISOString(),
      capturedSessions: 14,
      vibrationEvents: 9,
      logs: [
        { id: "log-1", time: "2026-03-06T11:42:00.000Z", title: { en: "Vibration: urgency repeated after hesitation cue", zh: "震动：在犹豫信号后重复强调紧迫性" }, detail: { en: "Triggered when the same price urgency cue appeared twice within 32 seconds.", zh: "在 32 秒内同一类价格紧迫表达出现两次时触发。" }, reviewId: "review-device-1" },
        { id: "log-2", time: "2026-03-05T09:28:00.000Z", title: { en: "Transfer complete / 18 language events uploaded", zh: "传输完成 / 18 条语言事件已上传" }, detail: { en: "Device session metadata arrived successfully in the review pipeline.", zh: "设备会话元数据已成功进入复盘流水线。" }, reviewId: "review-device-1" }
      ],
      syncRecords: [
        { id: "sync-1", time: "2026-03-06T11:48:00.000Z", title: { en: "Tokyo buyer visit / upload successful", zh: "东京客户拜访 / 上传成功" }, detail: { en: "Transcript summary, vibration events, and metadata were stored without packet loss.", zh: "对话摘要、震动事件和元数据已无丢包写入。" }, status: "healthy" },
        { id: "sync-2", time: "2026-03-04T08:15:00.000Z", title: { en: "Firmware 1.4.2 deployed", zh: "固件 1.4.2 已部署" }, detail: { en: "Pause-signal vibration thresholds updated for the Japan package.", zh: "针对日本国家包更新了停顿信号的震动阈值。" }, status: "warn" }
      ]
    },
    currentSimulation: {
      country: "Japan",
      meetingType: "First Introduction",
      goal: "Establish trust before pricing",
      duration: 10,
      voiceStyle: "Formal / measured",
      voiceProfileId: null,
      constraint: "The client is traditional and risk-sensitive. Keep language conservative.",
      files: [],
      simulationId: null,
      simulationStatus: "draft",
      setupRevision: 0,
      strategyForSetupRevision: null,
      strategies: [],
      strategySummary: null,
      sessionId: null,
      realtimeStatus: null,
      recentReviewId: null,
      recentCompletedSessionId: null,
      lastCompletionStatus: null,
      transcript: [],
      alerts: [],
      sessionSummary: null,
      liveStarted: false,
      practiceText: "",
      metrics: { wording: "Calibrated", pauses: "Needs room", repetition: "Low", taboo: "Clear", intensity: "Measured", metaphor: "Concrete" },
      issueCounts: {},
      countdown: 600
    }
  };
};
