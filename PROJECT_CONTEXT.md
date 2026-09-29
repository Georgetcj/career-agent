# 秋招求职 Agent 项目上下文

## 1. 项目背景

本项目旨在构建一个面向秋招用户的全流程智能求职系统，重点服务技术类岗位，包括但不限于后端开发、前端开发、客户端、算法工程、AI 应用、数据开发、云原生与安全方向。

传统求职工具通常只覆盖简历制作或职位搜索中的单一环节。本项目希望通过多 Agent、RAG、Skills、MCP 与可靠工作流，将用户从职业定位、简历准备、岗位匹配、技术学习、笔试训练、模拟面试、投递管理到 Offer 决策串成完整闭环。

系统必须以用户真实经历为基础，不能伪造学历、项目、实习、奖项、技术能力或面试结果。

---

## 2. 目标用户

- 计算机、AI、数据等相关专业的应届生。
- 有实习或项目经历，希望提升简历和面试表现的技术候选人。
- 转码、跨专业或跨岗位方向求职者。
- 需要管理多岗位投递与多个面试流程的求职者。
- 希望获得系统化技术学习、算法训练和项目深挖帮助的用户。

---

## 3. 核心业务需求

### 3.1 用户画像与求职策略

系统应支持用户上传简历、填写教育背景、项目经历、实习经历、技术栈、意向岗位、意向城市、薪资期望和求职时间安排。

系统需要：

- 提取结构化候选人画像。
- 分析用户的岗位竞争力与能力短板。
- 推荐保底、主申、冲刺三个层级的岗位策略。
- 基于秋招时间线生成周计划、每日任务与提醒。
- 根据投递和面试结果动态调整策略。

### 3.2 简历与求职材料

系统需要：

- 支持 PDF、Word、Markdown、LaTex 简历导入与解析。
- 支持简历质量诊断，包括量化程度、表达质量、重复表述、技术真实性风险和 ATS 关键词。
- 针对不同 JD 生成定制版简历。
- 支持简历版本管理、对比、导出和关联投递记录。
- 生成自我介绍、项目介绍、求职信、内推私信、网申问答和英文材料。
- 对任何可能涉及新增指标或经历的内容标记为“待用户确认”。

### 3.3 岗位发现与 JD 匹配

系统需要：

- 汇总公开岗位、企业招聘官网和用户导入岗位信息。
- 解析 JD 的岗位职责、硬性要求、加分项、技术栈、业务方向和潜在面试重点。
- 根据用户画像、简历与 JD 计算可解释的匹配度。
- 给出能力缺口、简历优化建议和投递优先级。
- 管理岗位订阅、截止日期、投递状态和流程节点。

### 3.4 技术学习与笔试训练

系统需要覆盖：

- 编程语言：Python、Java、Go、C++、JavaScript/TypeScript 等。
- 数据结构与算法。
- 操作系统、计算机网络、数据库、Linux。
- 后端与分布式系统。
- 前端与工程化。
- AI、LLM、RAG、Agent、MLOps。
- 数据工程、数仓、实时计算。
- 云原生、容器、Kubernetes、CI/CD、可观测性。
- 安全与认证授权。

系统应支持：

- 能力图谱和技术知识树。
- 根据 JD 和目标岗位生成学习路径。
- 算法题训练、代码评测、错题本、模拟笔试。
- 按掌握程度安排复习和间隔重复训练。
- 为每个主题提供面试题、追问路径、动手实验与项目增强建议。

### 3.5 模拟面试与项目深挖

系统需要支持：

- 算法面、基础技术面、系统设计面、项目深挖、AI 面、数据面、HR 面和终面模拟。
- 基于用户简历、项目资料和目标 JD 定制问题。
- 多轮追问，而非孤立题库问答。
- 从正确性、技术深度、工程性、表达能力、项目真实性和岗位匹配度进行评分。
- 输出面试复盘、薄弱点、改进建议和后续学习任务。
- 对项目进行背景、架构、技术选型、难点、性能、故障、优化与复盘的完整深挖。

### 3.6 投递与 Offer 管理

系统需要：

- 提供待投递、已投递、笔试、面试、Offer、拒绝和归档看板。
- 记录岗位链接、简历版本、内推人、投递时间、面试安排与反馈。
- 对笔试、面试、截止日期和跟进事项进行提醒。
- 分析不同公司、岗位、轮次、题型与简历版本的转化率。
- 支持 Offer 条件对比、谈薪建议和决策辅助。

---

## 4. 系统设计原则

- Python 为主语言，核心后端、Agent、RAG、评测、任务与 MCP 服务均使用 Python。
- 使用明确的领域模型、数据模型和权限模型，避免让 LLM 成为业务真相来源。
- 核心业务能力通过受测试的 Python 函数和服务实现。
- MCP 用于连接外部工具和第三方数据源，不替代内部业务模块。
- Skills 用于沉淀可复用、可版本化、可评测的求职工作流。
- RAG 用于非结构化知识和个性化证据检索，不替代 PostgreSQL 等结构化数据系统。
- 所有外部副作用操作必须经过人工确认。
- 所有 Agent 执行必须具备可观测性、审计、失败恢复和评测机制。
- 所有用户敏感信息必须按用户隔离、最小权限访问并支持删除。

---

## 5. 总体技术架构

```text
Web / App Client
        ↓
FastAPI API Gateway + WebSocket / SSE
        ↓
LangGraph Agent Orchestrator
        ├─ Profile Agent
        ├─ Resume Agent
        ├─ Job Agent
        ├─ Project Agent
        ├─ Interview Agent
        ├─ Learning Agent
        └─ Analytics Agent
        ↓
Python Tools / RAG / Skill Registry / MCP Gateway
        ↓
PostgreSQL + pgvector + Redis + Object Storage
        ↓
Temporal Durable Workflows + Workers
        ↓
External MCP Servers / Calendar / Email / Drive / GitHub / Browser
```

---

## 6. Agent 编排方案

### 6.1 技术选型

- 主 Agent 编排：LangGraph。
- 长时可靠工作流：Temporal Python SDK。
- API 服务：FastAPI。
- 模型调用：OpenAI Python SDK；必要时可在特定节点接入 OpenAI Agents SDK。
- 状态持久化：PostgreSQL。
- 缓存、限流、短任务：Redis。
- 可观测性：OpenTelemetry、Langfuse、Sentry。
- 异步消息或事件：初期 Redis/Celery；规模扩大后可引入 Kafka。

### 6.2 编排原则

- 采用“中心编排器 + 专职 Agent 节点”模式。
- Agent 之间不得无限制自由对话。
- 编排器负责意图识别、任务拆解、状态管理、路由、重试、审批和最终汇总。
- 每个 Agent 只能访问获授权的工具与数据。
- 高风险动作进入人工审核节点。
- Agent 状态、工具调用、检索结果、模型版本和成本必须可追踪。

### 6.3 Agent 列表

| Agent | 职责 |
|---|---|
| Orchestrator | 请求分类、任务拆解、Agent 路由、状态与审批管理 |
| Profile Agent | 构建和维护候选人画像、求职偏好与长期记忆 |
| Resume Agent | 简历解析、诊断、定制、材料生成与真实性校验 |
| Job Agent | JD 解析、岗位匹配、岗位排序、投递建议 |
| Project Agent | 项目架构梳理、项目深挖、面试追问与作品集建议 |
| Interview Agent | 多轮模拟面试、动态追问、评分与复盘 |
| Learning Agent | 技能缺口分析、学习计划、题目推荐与复习调度 |
| Analytics Agent | 投递漏斗、面试表现、策略归因与持续优化 |

---

## 7. RAG 设计

### 7.1 RAG 的作用

RAG 是系统的个性化知识与证据层，用于让 Agent 基于用户真实资料、岗位 JD、技术文档和历史面试记录输出有来源的建议。

### 7.2 适合进入 RAG 的资料

- 用户简历、项目文档、作品集、学习笔记。
- 用户历史面试记录、错题、复盘与反馈。
- 招聘 JD、公司公开资料和岗位技术要求。
- 技术文档、系统设计资料、题库、评分标准。
- 简历规范、面试方法论和求职策略资料。

### 7.3 不应只依赖 RAG 的数据

- 用户账号、权限、投递状态、面试时间、提醒任务。
- 岗位筛选、排序、统计报表和能力评分。
- 邮件发送、日历创建、投递等外部操作。
- 高精度筛选条件，例如城市、毕业年份、岗位发布时间。

这些数据优先使用 PostgreSQL、全文检索、规则引擎和工作流系统。

### 7.4 RAG 流程

```text
文档上传 / JD 采集 / 技术资料导入
        ↓
解析、清洗、脱敏、去重、切块
        ↓
元数据存储 + Embedding 生成
        ↓
PostgreSQL Full-Text Search + pgvector 混合检索
        ↓
重排序、权限过滤、来源构建
        ↓
Agent 获取上下文并输出引用依据
```

### 7.5 RAG 基础要求

- 所有检索结果必须进行用户权限过滤。
- 用户私有资料不得被其他用户检索。
- 关键建议应提供来源、资料标题或引用片段。
- Embedding、切块与索引策略必须版本化。
- RAG 需要独立评测召回率、引用正确率、答案忠实度、幻觉率、延迟与成本。

---

## 8. MCP 设计

### 8.1 MCP 的作用

MCP 是外部工具和数据源的接入标准，用于让系统连接日历、邮箱、云盘、GitHub、浏览器与其他第三方服务。

### 8.2 优先 MCP 能力

| MCP 服务 | 主要用途 | 风险控制 |
|---|---|---|
| Calendar | 面试安排、学习计划、截止日期提醒 | 写入前人工确认 |
| Email | 读取招聘通知、生成邮件草稿 | 默认不发送，发送需确认 |
| Drive | 导入和导出简历、作品集、面试资料 | 仅访问授权目录 |
| GitHub | 读取项目资料、辅助项目深挖与作品集生成 | 默认只读 |
| Browser | 公开岗位检索、JD 收集、技术资料检索 | 限速并遵守站点政策 |
| 自建 Career MCP | 对外暴露岗位搜索、画像分析和面试报告能力 | 强鉴权、审计、幂等 |

### 8.3 MCP 安全要求

- MCP 返回的网页、邮件、JD 和文档内容均视为不可信输入。
- 所有工具参数必须使用 Pydantic 或 JSON Schema 验证。
- 必须设置超时、重试、限流、熔断和幂等键。
- 所有外部写操作必须经过审批。
- OAuth Token 与密钥不能写入日志或长期明文数据库。
- 必须记录工具调用人、时间、参数摘要、结果和审批记录。

---

## 9. Skills 设计

Skills 是系统内部可复用的求职工作流包。每个 Skill 应具备明确输入、输出、工具权限、版本、评测集和说明文档。

推荐首批 Skills：

- `resume_tailoring`：基于真实经历和 JD 定制简历。
- `job_match_analysis`：解析 JD、计算匹配度并提出能力补足建议。
- `project_deep_dive`：将真实项目转化为面试可讲述的技术故事与追问树。
- `backend_interview`：后端基础、数据库、缓存、消息队列、分布式系统面试。
- `algorithm_mock_exam`：算法模拟笔试、代码评测与错题复习。
- `ai_interview`：机器学习、LLM、RAG、Agent、MLOps 面试。
- `offer_negotiation`：Offer 对比、谈薪与沟通材料生成。
- `post_interview_review`：面试记录整理、问题归类、能力缺口与后续计划。

每个 Skill 的基础结构：

```text
skill_name/
├─ skill.yaml
├─ instructions.md
├─ prompts/
├─ rubrics/
├─ references/
├─ tests/
└─ assets/
```

---

## 10. 数据与安全要求

### 10.1 核心数据

- 用户与身份信息。
- 候选人画像、偏好和能力图谱。
- 简历及其版本。
- 项目经历和项目资料。
- 岗位、公司、JD 和匹配结果。
- 投递、笔试、面试、Offer 与反馈。
- 学习计划、题目记录、错题和掌握度。
- Agent 执行记录、检索记录、审批记录和评测结果。

### 10.2 隐私与真实性

- 简历、联系方式、面试记录、录音等敏感信息加密存储。
- 数据通过 `tenant_id`、`user_id` 和权限策略进行隔离。
- 用户可查看、修正、导出和删除自身数据。
- 不将用户数据直接用于模型训练。
- 不生成或强化虚构经历。
- 对“用户未确认的数字或事实”明确标记为待确认。

---

## 11. 可进化机制

系统进化必须基于受控评测和反馈闭环，而不是让 Agent 自动修改自身规则后直接上线。

### 11.1 需要版本化的内容

- Prompt。
- 模型与模型参数。
- Agent 图与路由逻辑。
- Skill 定义。
- RAG 切块、Embedding、检索与重排序策略。
- 评分标准与评测集。
- MCP 工具定义和权限策略。

### 11.2 评测能力

- 简历定制真实性与质量评测。
- JD 匹配准确性与可解释性评测。
- RAG 召回率、引用正确率与忠实度评测。
- 模拟面试技术正确性、追问质量与评分一致性评测。
- 安全评测：提示注入、越权、隐私泄露、虚构经历。
- 成本、延迟、失败率与用户满意度分析。

### 11.3 发布机制

```text
新 Prompt / 新模型 / 新 RAG 策略
        ↓
离线评测
        ↓
人工审核
        ↓
灰度发布 / A-B 测试
        ↓
线上监控与用户反馈
        ↓
正式发布或回滚
```

---

## 12. 项目目录结构

```text
career-agent/
├─ README.md
├─ pyproject.toml                  # Python 依赖、Ruff、Pyright、pytest 配置
├─ uv.lock                         # 使用 uv 管理依赖
├─ .env.example
├─ .gitignore
├─ Makefile
├─ docker-compose.yml              # 本地：API、Worker、Postgres、Redis、MinIO
├─ AGENTS.md                       # 给开发 Agent 的项目协作规范
│
├─ apps/
│  ├─ api/
│  │  ├─ main.py                   # FastAPI 启动入口
│  │  ├─ dependencies.py           # 鉴权、数据库、当前用户等依赖注入
│  │  ├─ middleware.py             # CORS、请求 ID、限流、审计
│  │  ├─ routers/
│  │  │  ├─ auth.py
│  │  │  ├─ profiles.py
│  │  │  ├─ resumes.py
│  │  │  ├─ jobs.py
│  │  │  ├─ applications.py
│  │  │  ├─ interviews.py
│  │  │  ├─ learning.py
│  │  │  ├─ chat.py
│  │  │  ├─ files.py
│  │  │  ├─ integrations.py        # MCP 授权、连接状态、回调
│  │  │  └─ admin.py
│  │  └─ websocket/
│  │     ├─ interview_session.py   # 实时模拟面试
│  │     └─ agent_events.py        # Agent 执行进度流
│  │
│  ├─ worker/
│  │  ├─ celery_app.py             # 或 Temporal Worker 入口
│  │  ├─ tasks/
│  │  │  ├─ parse_resume.py
│  │  │  ├─ crawl_jobs.py
│  │  │  ├─ index_documents.py
│  │  │  ├─ generate_embeddings.py
│  │  │  ├─ send_reminders.py
│  │  │  └─ run_evaluations.py
│  │  └─ schedules.py
│  │
│  └─ mcp_server/
│     ├─ server.py                 # 自建 Career Agent MCP Server
│     ├─ tools/
│     │  ├─ search_jobs.py
│     │  ├─ get_candidate_profile.py
│     │  ├─ analyze_resume.py
│     │  ├─ create_learning_plan.py
│     │  ├─ get_application_status.py
│     │  └─ create_interview_report.py
│     ├─ resources/
│     │  └─ candidate_context.py
│     └─ policies.py
│
├─ src/
│  └─ career_agent/
│     ├─ core/                     # 与业务无关的基础能力
│     │  ├─ config.py              # pydantic-settings
│     │  ├─ constants.py
│     │  ├─ errors.py
│     │  ├─ logging.py
│     │  ├─ security.py
│     │  ├─ telemetry.py            # OpenTelemetry / Langfuse
│     │  ├─ idempotency.py
│     │  └─ types.py
│     │
│     ├─ domain/                   # 核心领域模型与业务规则
│     │  ├─ identity/
│     │  │  ├─ entities.py
│     │  │  ├─ schemas.py
│     │  │  └─ services.py
│     │  ├─ profile/
│     │  │  ├─ entities.py          # CandidateProfile、Skill、Preference
│     │  │  ├─ schemas.py
│     │  │  ├─ repository.py
│     │  │  └─ services.py
│     │  ├─ resume/
│     │  │  ├─ entities.py          # Resume、ResumeVersion、Experience
│     │  │  ├─ parser.py
│     │  │  ├─ scoring.py
│     │  │  ├─ tailoring.py
│     │  │  └─ repository.py
│     │  ├─ job/
│     │  │  ├─ entities.py          # Job、Company、JDRequirement
│     │  │  ├─ jd_parser.py
│     │  │  ├─ matcher.py
│     │  │  ├─ ranking.py
│     │  │  └─ repository.py
│     │  ├─ application/
│     │  │  ├─ entities.py          # Application、Stage、Offer
│     │  │  ├─ funnel.py
│     │  │  ├─ reminders.py
│     │  │  └─ repository.py
│     │  ├─ interview/
│     │  │  ├─ entities.py          # Session、Question、Answer、Feedback
│     │  │  ├─ rubric.py
│     │  │  ├─ scoring.py
│     │  │  ├─ followup_tree.py
│     │  │  └─ repository.py
│     │  ├─ learning/
│     │  │  ├─ entities.py          # SkillMap、LearningPlan、PracticeRecord
│     │  │  ├─ knowledge_graph.py
│     │  │  ├─ planner.py
│     │  │  ├─ spaced_repetition.py
│     │  │  └─ repository.py
│     │  └─ project/
│     │     ├─ entities.py
│     │     ├─ architecture_analysis.py
│     │     ├─ deep_dive.py
│     │     └─ repository.py
│     │
│     ├─ agents/                   # 多 Agent：决策、协作、状态
│     │  ├─ orchestrator/
│     │  │  ├─ agent.py
│     │  │  ├─ router.py            # 请求分类、任务拆解、Agent 路由
│     │  │  ├─ state.py             # 可持久化运行状态
│     │  │  ├─ handoff.py
│     │  │  └─ approval.py          # 人工确认节点
│     │  ├─ profile_agent/
│     │  │  ├─ agent.py
│     │  │  ├─ prompts.py
│     │  │  └─ tools.py
│     │  ├─ resume_agent/
│     │  │  ├─ agent.py
│     │  │  ├─ prompts.py
│     │  │  └─ tools.py
│     │  ├─ job_agent/
│     │  │  ├─ agent.py
│     │  │  ├─ prompts.py
│     │  │  └─ tools.py
│     │  ├─ interview_agent/
│     │  │  ├─ agent.py
│     │  │  ├─ prompts.py
│     │  │  ├─ question_generator.py
│     │  │  └─ tools.py
│     │  ├─ learning_agent/
│     │  │  ├─ agent.py
│     │  │  ├─ prompts.py
│     │  │  └─ tools.py
│     │  ├─ project_agent/
│     │  │  ├─ agent.py
│     │  │  ├─ prompts.py
│     │  │  └─ tools.py
│     │  ├─ analytics_agent/
│     │  │  ├─ agent.py
│     │  │  ├─ prompts.py
│     │  │  └─ tools.py
│     │  └─ common/
│     │     ├─ base.py              # BaseAgent
│     │     ├─ context.py           # AgentContext
│     │     ├─ result.py            # AgentResult
│     │     ├─ guardrails.py
│     │     ├─ tool_registry.py
│     │     └─ model_router.py
│     │
│     ├─ skills/                    # 自定义 Skill Registry 与执行器
│     │  ├─ registry.py
│     │  ├─ loader.py
│     │  ├─ executor.py
│     │  ├─ contracts.py
│     │  ├─ resume_tailoring/
│     │  │  ├─ skill.yaml
│     │  │  ├─ instructions.md
│     │  │  ├─ rubrics/
│     │  │  └─ tests/
│     │  ├─ backend_interview/
│     │  │  ├─ skill.yaml
│     │  │  ├─ instructions.md
│     │  │  ├─ question_templates/
│     │  │  ├─ rubrics/
│     │  │  └─ tests/
│     │  ├─ algorithm_mock_exam/
│     │  ├─ project_deep_dive/
│     │  ├─ job_match_analysis/
│     │  └─ offer_negotiation/
│     │
│     ├─ rag/                       # 检索增强生成
│     │  ├─ ingestion/
│     │  │  ├─ resume_loader.py
│     │  │  ├─ jd_loader.py
│     │  │  ├─ project_loader.py
│     │  │  ├─ interview_note_loader.py
│     │  │  └─ tech_doc_loader.py
│     │  ├─ processing/
│     │  │  ├─ cleaner.py
│     │  │  ├─ pii_redactor.py
│     │  │  ├─ chunker.py
│     │  │  ├─ metadata.py
│     │  │  └─ deduplicator.py
│     │  ├─ retrieval/
│     │  │  ├─ vector_search.py
│     │  │  ├─ keyword_search.py
│     │  │  ├─ hybrid_search.py
│     │  │  ├─ reranker.py
│     │  │  ├─ permission_filter.py
│     │  │  └─ citation_builder.py
│     │  ├─ embeddings/
│     │  │  ├─ provider.py
│     │  │  ├─ indexer.py
│     │  │  └─ versioning.py
│     │  └─ evaluation/
│     │     ├─ retrieval_metrics.py
│     │     └─ faithfulness.py
│     │
│     ├─ integrations/              # 外部系统适配器
│     │  ├─ mcp/
│     │  │  ├─ client.py
│     │  │  ├─ registry.py
│     │  │  ├─ policy.py
│     │  │  ├─ approval.py
│     │  │  └─ adapters/
│     │  │     ├─ calendar.py
│     │  │     ├─ email.py
│     │  │     ├─ drive.py
│     │  │     ├─ github.py
│     │  │     └─ browser.py
│     │  ├─ llm/
│     │  │  ├─ openai_provider.py
│     │  │  ├─ fallback_provider.py
│     │  │  ├─ prompt_registry.py
│     │  │  └─ cost_tracker.py
│     │  ├─ storage/
│     │  │  ├─ object_storage.py
│     │  │  └─ file_repository.py
│     │  ├─ notifications/
│     │  │  ├─ email.py
│     │  │  ├─ webhook.py
│     │  │  └─ in_app.py
│     │  └─ crawlers/
│     │     ├─ base.py
│     │     ├─ company_career_site.py
│     │     └─ public_job_sources.py
│     │
│     ├─ infrastructure/            # 技术实现，不放业务逻辑
│     │  ├─ database/
│     │  │  ├─ session.py
│     │  │  ├─ models/
│     │  │  ├─ repositories/
│     │  │  └─ migrations/
│     │  ├─ cache/
│     │  │  └─ redis.py
│     │  ├─ queue/
│     │  │  ├─ celery.py
│     │  │  └─ events.py
│     │  ├─ observability/
│     │  │  ├─ tracing.py
│     │  │  ├─ metrics.py
│     │  │  └─ error_reporting.py
│     │  └─ auth/
│     │     ├─ jwt.py
│     │     ├─ oauth.py
│     │     └─ rbac.py
│     │
│     ├─ workflows/                 # 可恢复的长时任务
│     │  ├─ resume_to_application.py
│     │  ├─ job_discovery.py
│     │  ├─ interview_simulation.py
│     │  ├─ weekly_learning_plan.py
│     │  ├─ post_interview_review.py
│     │  └─ external_action_approval.py
│     │
│     ├─ policies/                  # 统一治理规则
│     │  ├─ resume_truthfulness.py  # 禁止编造学历、项目、数据
│     │  ├─ privacy.py
│     │  ├─ prompt_injection.py
│     │  ├─ tool_permissions.py
│     │  ├─ content_safety.py
│     │  └─ human_in_the_loop.py
│     │
│     └─ evals/                     # 让系统“可进化”的基础
│        ├─ datasets/
│        │  ├─ resume_cases.jsonl
│        │  ├─ jd_match_cases.jsonl
│        │  ├─ interview_cases.jsonl
│        │  └─ rag_retrieval_cases.jsonl
│        ├─ graders/
│        │  ├─ rubric_grader.py
│        │  ├─ citation_grader.py
│        │  ├─ safety_grader.py
│        │  └─ truthfulness_grader.py
│        ├─ experiments/
│        │  ├─ prompt_ab_test.py
│        │  ├─ model_comparison.py
│        │  └─ retrieval_comparison.py
│        └─ reports/
│
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ contract/                     # MCP、LLM、第三方服务接口契约测试
│  ├─ e2e/
│  ├─ security/
│  ├─ fixtures/
│  └─ conftest.py
│
├─ docs/
│  ├─ architecture.md
│  ├─ api.md
│  ├─ agent-design.md
│  ├─ rag-design.md
│  ├─ mcp-design.md
│  ├─ skill-authoring-guide.md
│  ├─ data-model.md
│  ├─ security-and-privacy.md
│  ├─ evaluation-framework.md
│  └─ runbooks/
│     ├─ incident-response.md
│     ├─ model-fallback.md
│     └─ mcp-outage.md
│
├─ infra/
│  ├─ docker/
│  │  ├─ api.Dockerfile
│  │  ├─ worker.Dockerfile
│  │  └─ mcp.Dockerfile
│  ├─ kubernetes/
│  │  ├─ base/
│  │  └─ overlays/
│  │     ├─ staging/
│  │     └─ production/
│  ├─ terraform/
│  ├─ monitoring/
│  │  ├─ prometheus.yml
│  │  └─ grafana-dashboards/
│  └─ scripts/
│     ├─ bootstrap.ps1
│     ├─ seed_data.py
│     ├─ reindex_documents.py
│     └─ run_evals.py
│
├─ data/
│  ├─ seed/
│  ├─ schemas/
│  └─ samples/                      # 脱敏示例简历、JD、面试记录
│
└─ web/                             # 可选：React/Next.js 前端
   ├─ app/
   ├─ components/
   ├─ lib/
   ├─ package.json
   └─ playwright/
```

---

## 13. 模块依赖规则

```text
API / Worker
    ↓
Agents / Workflows
    ↓
Domain / Skills / RAG / Integrations
    ↓
Infrastructure
```

- `domain/` 不依赖 FastAPI、Celery、Temporal、LLM、MCP 或数据库具体实现。
- `agents/` 不直接读写数据库，应通过领域服务和受控工具访问数据。
- `rag/` 只处理非结构化知识、检索、引用与评测。
- `integrations/mcp/` 是外部系统边界，不承载核心业务规则。
- `workflows/` 处理长任务、重试、补偿、审批和恢复。
- `evals/` 必须独立运行，不依赖线上真实用户数据。

---

## 14. MVP 范围

第一阶段优先实现：

1. 用户画像与简历导入解析。
2. JD 解析、岗位匹配与可解释评分。
3. 基于真实经历的简历定制。
4. 项目深挖与后端/算法模拟面试。
5. 基础 RAG：用户资料、JD 与技术知识检索。
6. 投递与面试看板。
7. LangGraph 状态编排、人工审批和基础观测。
8. PostgreSQL、pgvector、Redis、MinIO、Docker Compose 本地部署。

后续阶段再实现：

- MCP 日历、邮箱、云盘、GitHub 与浏览器接入。
- 语音模拟面试。
- 完整算法判题沙箱。
- 自动化岗位订阅与抓取。
- Temporal 长时任务编排。
- 更复杂的评测、灰度与持续优化体系。
- Offer 决策、谈薪和多端产品体验。
