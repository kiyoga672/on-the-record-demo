# On the Record：开发与 Demo 实施计划

更新日期：2026-10-16，Australia/Sydney。以下按验收顺序推进；原 brief 中冲突的 13:00/13:30 截止时间不作为交付承诺。


## 当前交付快照（本轮开发后，以本节覆盖早期状态表）

- Amplify发布准备：已创建独立deploy/amplify-20261016副本（Next15.5.28/Node22，PostCSS8.5.30override），不改原Next16本地demo。生产构建/15项前端测试/真实推荐搜索回归/health/OG均通过，审计0漏洞。已推送私有仓库https://github.com/kiyoga672/on-the-record-demo，含amplify.yml和白名单SSR配置生成器。AWS登录尚未完成，未创建Amplify应用或公网地址，不能称部署完成。

- 新增F1/F3/F4/F5本地实现；F2收藏原生Workflow、严格验证、幂等保存、受保护管理和删除已完成真实API测试。完整提醒Workflow已注册valid但禁用，需邮件connector和明确发送授权后验收。自动审批拒绝邮件工作流试运行，未发送邮件。验收细节以FEATURE_BACKLOG.md为准。

- 2026-10-16历史回填已启动：源目录从2025年起共众议院100个、参议院83个议事日文件。首批预算新增6000条，以完整议事日为单位、两院按日期交错推进。backfill.py已增加原子保存进度、并发锁、完成日跳过和中断日稳定ID重放；3项解析/恢复测试通过。实时数量以ES和.local/coverage.json为准，不能沿用下面初始542条作为当前总量。

- ML 节点已存在；ELSER 和 Elastic Rerank 最小推理均通过。BM25+ELSER→RRF→Rerank 实测约0.34秒；Bedrock直连成功。
- 已创建四索引、6个检索/分析工具、3个Workflow工具及On the Record Agent。
- 已注册4个Workflow：find_my_mp、follow_topic、export_factsheet、daily_hansard。查找、导出、真实单条源记录入库重放均有completed执行。follow未代用户创建订阅，未发送邮件。
- 已入库226名成员和2026-10-15两院542条发言，21条身份不明记录隔离。覆盖仅一天，complete=false。
- Next.js 14.2.35审计存在未修复critical漏洞，因此升级为16.4.2；Tailwind4、Recharts3。依赖审计0漏洞。生产构建、TypeScript、逐字校验/统计测试与XML身份映射测试通过。最终生产构建和5组JS测试均已通过，Python XML测试通过；运行时依赖审计0项漏洞。
- 本地预览 http://127.0.0.1:3000 。真实时间线返回2条已验证引文，约13.7秒；真实导出经Workflow生成候选、再调用verify_quote及原文复核，约14秒，产生可用markdown。
- 带全部工具的同步Agent调用曾循环空参数；现在使用流式API和仅verify_quote的工具覆盖。导出Workflow中Agent只产生候选，服务端在交付前强制验证。
- 语义相似可能产生无关引文，现增加保守的主题词证据门槛：常见主题同义词OR、未知多词主题AND；可能漏掉隐含讨论，不声称零语义关联。Attention与月图复用此口径。
- 已有15道临时评估题。上一轮正例9/10返回有验证引文的答案，最终展示10/10条引文源文本匹配；修复后的5个负例全部返回incomplete_coverage，无引文。不能称为全量Hansard的5/5精确拒答。历史失败run均保留。
- eval_runs已写入真实结果；Kibana仪表板on-the-record-reliability使用实时ES|QL，保留完整覆盖拒答指标为空，另列索引范围负例指标与正例成功率。LLM judge尚未运行。
- 未完成：全量回填与覆盖审查、邮编映射、daily定时触发/分类/匹配/邮件、SES/Guardrails、Amplify及公网访问控制、两次完整排练。
- 当前 daily_hansard 是worker提交标准化batch后由Workflow逐条入库；daily.py会在配置了Workflow ID时走这条路径。没有把批次入库演示称作完整自动digest。

## 1. 初始实测状态（配置前历史记录）

基础访问凭据已足够开始开发，但云端配置尚未全部就绪，产品尚未完成。

| 项目 | 结果 | 影响 |
| --- | --- | --- |
| 本地环境 | Python 3.11.9、Node 24.14.1、npm 11.11.0；.venv 已安装依赖 | Python 语法与 pip check 已通过，前端尚未建立 |
| ES / Kibana | AWS Sydney Hosted 9.5.5，连接成功 | 地址与 key 已保存在根目录 .env |
| ES 权限 | monitor/manage_inference；四个项目索引 create_index/read/write/view_index_metadata 均为 true | 可以开发安装脚本；Kibana 写权限仍需实测 |
| Agent Builder | 37 个内置工具可读取 | 自定义工具和推理尚未验证 |
| Workflow | GET /api/workflows/schema?loose=true 成功 | 部署实际 schema 已保存，按它验证 YAML |
| OpenAustralia key | getRepresentatives 返回 150 条成员记录 | key 有效；person_id/member_id/name/constituency/party/image 字段已确认 |
| 发言搜索 API | person 查询 getDebates、关键词 getHansard 返回 HTTP 500 | 不依赖源站搜索完成检索，建立自己的 ES 索引 |
| 日期 API | 2026-09-17 返回 21 个 entry/subs 顶层项 | 返回议程/标题目录，不能当作完整发言；需要继续按 gid 展开 |
| XML 备用 | HTTPS 目录可访问；最新众议院文件名 2026-10-15.xml；样例含 247 个 speech | 可用作 brief 允许的备用路径，需映射 speakerid→person_id |
| 邮编查询 | getRepresentative(postcode=2204) 返回参数错误；官方只支持 id/division | 原 brief 的邮编解析方案需修正 |
| ML 容量 | 当前 0 个 ml role 节点 | 默认 ELSER/Rerank endpoint 存在，但运行条件尚未满足 |
| 模型服务 | 用户完成活动工具后，已查到14个service=amazonbedrock端点，region=ap-southeast-2 | bedrock-sonnet-4-5-chat已记录为BEDROCK_INFERENCE_ID；Agent实际推理路径仍待验证 |
| Email | 已有 elastic-cloud-email 预配置 connector | 尚未试发，不能等同于 SES 已配置 |

可复核脚本：elastic/preflight.py、elastic/readiness.py。报告和 schema 位于 Git 忽略的 .local/，不含 API key。尚无检索、前端或端到端测试通过结果。

## 2. 交付目标

核心路径：查找议员 → 真实主题 → 混合检索 → Agent 选取引文并调用验证工具 → 服务端原文逐字校验 → 时间线/源链接 → 统计 → Workflow 关注/导出 → 可靠性面板。

定位文案：**LLM for reasoning, Elastic for truth.**

必须交付：

- Agent Builder 实际负责工具调用和引文选择，trace 可见。
- Elastic Workflows 实际编排关注写入、导出和每日处理，至少两种工作流真实完成。
- BM25 + ELSER semantic_text 经 RRF 合并，再用 Elastic/Jina rerank。
- UI、下载和邮件共用校验规则，逐字、说话者、日期、议院、源链接一致。
- 姓名/选区入口、主题 chips、timeline、attention gauge/月图、空状态、关注、导出。
- 15 道真实评估、eval_runs、Kibana 可靠性展示，只报告实测值。

延后：Compare mode、They Vote For You、额外 AWS 服务和装饰动画。邮编仍是完整产品目标，但姓名入口先完成可用闭环；不能用硬编码答案掩盖邮编缺失。

## 3. 还需收尾的环境配置

### 必要项

1. Cloud → MES → Edit deployment → Machine Learning：配置至少 4 GB ML 容量及 autoscaling，核对可选规格和费用后再应用。本次未扩容部署。
2. 已完成：按活动 PDF 创建14个Bedrock端点，服务类型/地区通过REST核验。保留结果于.local/bedrock-check.json。
3. 检查实际创建的 inference endpoints/connectors，记录 service/model/region；测试最小推理，并通过 converse 证明 Agent 选中了该模型。
4. 9.5 ai.agent 可使用 inference-id；实际 ID 单独记录，不把 inference endpoint ID 混填为 BEDROCK_CONNECTOR_ID。若仍需原生 Bedrock connector，再配置并验证。
5. 分别 warm-up ELSER 和 rerank。端点列表存在不算运行通过。无 ML 时可以调查已有托管 Elastic/Jina 模型，但不能静默改变 brief 的 Hosted ML 固定要求。

### 后续项，不阻塞核心代码开发

- 邮件：确定演示收件人，实测现有 connector。SES 是 brief 的目标配置，不能把未经核实的 Cloud SMTP 称作 SES。
- AWS：Lambda/S3/Amplify 部署账号和权限在核心跑通后配置，可先本地演示。
- Jina key 可选，不默认索要。

## 4. 数据策略与覆盖范围

### 第一个完整数据批次

1. 获取众议员/参议员，区分 person_id/member_id；修正相对图片 URL；Senate constituency 对应州时明确转换。
2. 获取最新完整 sitting day 的两个议院。日期 API 是标题目录，需继续按 gid 展开；源搜索 API 500 时优先解析完整 XML。
3. 用成员 XML 或经过核验的 API 建立 speakerid→person_id 映射，不按同名猜测身份。无法唯一映射的发言隔离并记录。
4. 保留标题层级、稳定 speech_id、日期、chamber、原文、来源链接；heading 不入 hansard。
5. 先归档原始来源，再标准化并索引；保存源 URL、抓取时间、hash、解析器版本。S3 配置后使用版本化/保留策略，普通覆盖上传不能称作 immutable。

### 回填与完整性

- 从源目录发现 sitting days，从新到旧 bulk 100；初始上限 6,000 条。完整目标是 2025-01-01 起至来源最新日期，不预设总量。
- 本地 coverage manifest 记录 house/date/hash/parse status/indexed count/失败原因，不改变四个核心索引约定。
- bulk 逐条检查错误，重试失败项；稳定 speech_id 作为 _id，同一天重跑不重复。
- refresh 后核对源发言数、标准化数、已入库数、隔离数，不只看 HTTP 状态。
- 源站错误、缺文件、非 sitting day 和部分回填必须区分。
- 当前议员名单不包含全部历史发言者；保留历史 speaker 身份，不能用今日党派/选区覆盖当时的元数据。

### 邮编修正

- 第一条可用路径是姓名/选区搜索 members，处理同名和多候选。
- 邮编目标采用有来源和版本的 postcode→federal electorate→state 映射，再通过 division/id 找议员。
- 一个邮编跨多个选区时保留选择；映射未核实前 UI 明示暂不可用并提供姓名入口。
- 不硬编码 2204 结果，不在日志/分析中保存邮编；只有显式关注可按要求持久化。

## 5. 服务端架构与 API 契约

Next.js API routes 持有 ES/Kibana/OpenAustralia 凭据；Python 负责安装、采集、评估、Lambda。检索/验证集中实现，UI、export、digest 和 eval 使用同一规则。

| 路由 | 契约 |
| --- | --- |
| GET /api/health | 最小就绪状态，不泄露配置、key 或 email |
| GET /api/members?q= | 姓名/选区候选 |
| GET /api/mp?postcode= | 映射完成后启用，返回全部候选及适用州参议员 |
| GET /api/topics?speaker_id= | ES|QL 计数，明确区分分类主题与辩论标题 |
| POST /api/timeline | 参数校验、RRF/rerank、Agent、逐条验证，返回结构化 items 和状态 |
| GET /api/attention | score/monthly/原始计数/coverage/eligible_speakers |
| POST /api/follow | 显式订阅提交后运行 Workflow，返回 execution id/status |
| POST /api/export | Workflow 完成后返回已验证 markdown；邮件为显式选项 |
| GET /api/workflows/executions/[id] | 仅允许读取当前应用/会话发起的执行，不开放任意日志查询 |

Timeline 顶层字段：status（verified/no_matches/incomplete_coverage/unavailable）、items、topics、coverage、attribution、脱敏 agent_trace、timing。

每条 item：speech_id、speaker_id、speaker_name、date、house、debate_title、quote、url、verified=true。元数据以 fresh _source 为准。

不直接渲染 agent 自由文本；页面只输出已验证结构化引文和固定中立文案，原始答复只用于受控调试/评估。

## 6. 检索与不可绕过的逐字校验

### 检索

1. 两个检索分支均固定 speaker_id 和 date>=2025-01-01。
2. BM25 + semantic_text/ELSER → RRF → rerank → 最多8条候选，保留原文。
3. 使用明确的小型同义词表，例如 HECS/HELP/indexation；扩词不等于推断立场。
4. Agent 调用工具参与检索/选取，候选绝不提前渲染。
5. index_search 不天然等价于应用的 RRF/rerank 查询。通过受支持工具/Workflow 接入同一查询，或提供应用混合候选给 Agent；trace/README 如实解释职责，不声称两套查询相同。

### 每条引文验证

- 调用 verify_quote 工具；MATCH_PHRASE 只定位候选，不是最终逐字证明。
- 按 speech_id 回读索引，检查 speaker_id、日期范围、连续字符串包含关系。
- 使用固定 HTML→text 规则，保留措辞、标点和大小写，不用词袋 AND 代替精确验证。
- <=60词，只允许首尾省略，禁止中间拼接。
- 日期/chamber/URL 来自通过验证的源记录；链接限制在可信来源。
- 错人、错日期/URL、原文读取失败、缺少工具调用、未出现的引文全部丢弃并记录原因。
- “show more”也只展示回读的原文；ai.agent JSON schema 输出不能替代验证。
- Hansard 资料不是指令，不执行其中要求跳过校验或泄露配置的内容。

### 拒答边界

覆盖完整且成功搜索没有记录时，使用 byte-exact 模板：

`No recorded statements by <name> on <topic> in Hansard since 1 Jan 2025.`

- 只回填了部分数据：显示当前索引范围未找到，并列覆盖范围，不声称检查了全部 Hansard。
- 服务故障：显示不可用/重试，不变成拒答。
- 有候选但都验证失败：显示未能验证，不推断从未说过。
- 空状态给出其他已查到的话题/辩论标题。
- 零关键词命中不能证明零语义关联；负例评估还要固定 coverage 和检索口径。

## 7. Attention 统计口径

- 同议院、同时间窗、同覆盖范围；每人 total>=5 才进入比较集合。
- on_topic 是匹配主题的发言条数，不是词频；月图用同一主题规则。
- ES|QL 计算 total/on_topic/share；优先验证条件聚合 `STATS on_topic=COUNT(*) WHERE MATCH(text, ?topic)`，不照搬未经测试的 EVAL MATCH。
- 中位数包含合格说话者的零值 share；必须读取完整统计集合，避免默认行数截断。
- median>0：score=clamp(50*share/median,0,100)，50是中位水平。
- median=0、本人低样本、同院样本不足或覆盖不完整：显示数据不足/基准为零和原始计数，不编造分数。
- caption 明确仅说明提到主题的频率，不说明立场；不做诚信、一致性、情绪评分。

## 8. Agent Builder 与 Workflows

### 安装与工具

setup.py 顺序：mappings→模型检查→Workflows→tools→agent。固定资源 ID，可重复检查/更新，不删除已有数据，不把部分安装当成功。

工具目标：search_speeches(index_search)、verify_quote(esql)、speaker_topics(esql)、topic_timeline(esql)、topic_attention(esql)、topic_by_party(esql)、find_my_mp(workflow)、follow_topic(workflow)、export_factsheet(workflow)。可选参数给默认值，ES|QL 参数化，限制输入长度。

find_my_mp 先接已验证的 division/id 解析；postcode 仅在映射完成后启用。若某 tool 类型不支持，记录明确的兼容路径和赛道缺项。

### 工作流职责

| Workflow | 必须实际完成 | 验收证据 |
| --- | --- | --- |
| find_my_mp | 输入检查、选区/身份解析、多候选输出 | 与人工核验一致的 person_id |
| follow_topic | 明确订阅 email/speaker/topic，稳定 watch ID 写入 watches | completed execution + 文档；重复提交不重复订阅 |
| export_factsheet | 检索/Agent/校验编排，输出已验证 markdown，按需邮件 | completed execution、下载内容、源校验、邮件结果 |
| daily_hansard | 指定日期或定时采集→分类→匹配 watches→校验 digest→发信→last_sent | 条数、去重、匹配/验证数量、邮件结果及状态更新 |

- Timeline、导出和 digest 共用 verifier，不能信任模型自由生成的引用。
- 发信成功后才更新 last_sent；watch/date/speech_ids 作为 digest 幂等依据，避免重试重复邮件。
- dry-run 预览不发信。真正发信需要用户显式操作和确定收件人。
- demo 手动传真实 sitting day，标注“重放该日期”，不把历史数据叫作今天新发言。
- 分类只写 topic_tag，不改写原文。
- 所有 YAML 以 9.5.5 的实际 schema 验证 inputs/outputs/foreach/ES步骤；已确认 run 路径是 /api/workflows/workflow/{id}/run。

## 9. 前端体验与限制

Next.js App Router + TypeScript + Tailwind + Recharts。创建依赖清单时确认 Next.js 14 的支持/补丁和 Amplify 兼容性；如需调整版本明确记录。

视觉：中性的公共记录查询工具，米白/深蓝、醒目的日期、克制的绿色验证标记；党派颜色不用于评价。

- 首页突出姓名/选区查询；邮编是否可用明确显示；候选卡片含姓名、党派、议院、选区/州。
- Speaker 页显示覆盖范围、主题/辩论 chips、搜索框。
- 加载状态：检索中→验证中，无未经验证的候选卡。
- Timeline 新到旧，日期/chamber/context/source/Verified 清晰；context 只用标题和日期。
- Attention gauge/月图可切换，显示原始计数、样本范围，低样本不画虚假分数。
- Follow 有 email 校验、订阅对象、完成/失败状态；不在 URL 传 email。
- Export 等待完成再下载；启动成功不代表执行完成。
- 手机单列、键盘/焦点/labels、空结果/错误/超时可恢复，所有页面署名。
- 公开 demo 限制查询/发信速率和输入长度；不加用户分析，不持久化未授权邮编。

## 10. 分阶段实施与完成门槛

| 阶段 | 实现 | 门槛 |
| --- | --- | --- |
| M0 环境和样本 | ML/Bedrock、成员/一日完整发言解析、索引 schema | 模型最小推理成功；person_id 映射和两院来源正确 |
| M1 一个问题闭环 | setup、RRF/rerank、agent/tools、source verifier | 真引文通过；改词/错speaker/错URL拒绝；空结果与故障分开 |
| M2 前端 | 成员入口、speaker、topics、timeline、attention | 本地可打开，TS+生产构建通过，手机/桌面实测，无key入客户端 |
| M3 Workflows | follow/export/daily、工具注册、受控邮件 | 至少两种真实 completed；watch持久化；导出/邮件逐字 |
| M4 可靠性 | 15道题、eval_runs、Kibana dashboard | 实际run_id、分母、正例成功率、拒答率、延迟 |
| M5 冻结演示 | 回填覆盖、邮编映射、部署、两次排练 | 必需项全部明确pass或未完成，不临时塞stretch |

顺序M0→M1；M2的界面可先实现但真实卡片等M1；M3/M4共用verifier。当前单agent执行，未启动额外agents。

## 11. 测试与可靠性

- 数据：HTML/XML保持语句、heading排除、历史speaker映射、两院URL、分页/目录完整展开、去重/恢复、bulk单项失败。
- 验证：原文通过；同词乱序、改写标点/大小写、错人、跨文档拼接、中间省略、超60词、伪日期/URL、源回读失败均拒绝。
- 检索：过滤在两分支一致，实际RRF/rerank可追踪；模型故障不偷偷变为无记录。
- Attention：奇偶中位数、零基准、低样本、完整比较集合、月边界，用人工可算样本验证。
- 工作流：重复关注、验证失败、发信失败、重试去重、导出失败，不绕过校验。
- UI：输入限制、安全报错、手机布局、轮询状态、键盘操作、Verified只出现在通过校验项。

指标分开报告：候选引文数、原始agent可验证率、最终展示可验证率、丢弃数、10道正例成功回答率、5道负例精确拒答率、不可用/覆盖不足数、p50/p95延迟。零引文不算100% grounded；空答不能通过正例。

入库后生成真实 golden.json，不能预编答案。Bedrock judge为额外指标，未跑标记未运行；LLM judge不能替代确定性校验。

## 12. 三分钟 Demo

| 时间 | 演示 | 预备证据 |
| --- | --- | --- |
| 0:00–0:20 | 真实议员姓名或已核验邮编→候选→topics | 固定真实speaker/topic、覆盖说明 |
| 0:20–1:00 | 查询→验证中→时间线→打开Hansard | >=3条不同日期引用，tool trace、RRF/rerank记录 |
| 1:00–1:20 | 修改一条真实引文中的一个词，验证失败 | 明示人为改写测试，不假称其他chatbot生成 |
| 1:20–1:40 | Attention与月图切换 | 同一主题规则、分母和有效median |
| 1:40–2:00 | 已审查的无记录主题→拒答→其他topics | 完整coverage负例，或明确显示索引范围 |
| 2:00–2:40 | follow+export，展示两种Workflow完成 | execution IDs、watch、下载文件；若已配置则展示实收邮件 |
| 2:40–3:00 | reliability dashboard、架构、定位文案 | 实际run_id、分母、拒答结果、延迟 |

不使用未经核实的社会统计开场。断网备用保留真实源文件、已验证结果和执行截图，注明缓存/预录与日期；不可伪装live Workflow完成。

## 13. 发布与 AWS

- 先本地运行与浏览器QA，再Amplify；验证服务端env和公开demo的最小访问控制。
- Lambda URL需认证；EventBridge Scheduler使用Australia/Sydney时区，避免夏令时偏移。
- S3保留原始源数据，版本化/保留策略实测；Secrets Manager或服务端环境保存凭据。
- Guardrails与实际模型路径关联，未配置不在架构图标成已使用。
- AWS权限、SES限制和费用在对应资源操作前明确；本计划未扩容或新建AWS资源。

## 14. 完成清单

- [x] brief/PDF、本地Python依赖、语法与pip检查。
- [x] ES/Kibana、9.5.5、Sydney、索引权限实测。
- [x] OpenAustralia key、邮编接口问题、日期目录结构核实。
- [x] Workflow schema获取、XML备用文件实际247条speech检查。
- [ ] ML模型最小推理、Bedrock和Agent实际模型路径。
- [ ] 幂等setup、四索引、真实入库与覆盖manifest。
- [ ] RRF+rerank+Agent，所有展示引文逐字验证。
- [ ] >=5自定义tools，含index_search、>=3 ES|QL、>=2 Workflow。
- [ ] 姓名/邮编、topics、timeline、attention与月图。
- [ ] 至少两种Workflow完成，导出/digest/mail不绕过verifier。
- [ ] 15道评估、eval_runs、dashboard与指标分母。
- [ ] 页面/导出/邮件署名、中立性和隐私规则。
- [ ] 构建、浏览器QA、部署、两次完整排练。

## 15. 参考

- [getRepresentative：id/division](https://www.openaustralia.org.au/api/docs/getRepresentative)
- [getDebates](https://www.openaustralia.org.au/api/docs/getDebates)
- [OpenAustralia XML](https://data.openaustralia.org.au/scrapedxml/)
- [ELSER容量要求](https://www.elastic.co/guide/en/machine-learning/current/ml-nlp-elser.html)
- [Bedrock inference API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-inference-put-amazonbedrock)
- [Workflow AI steps](https://www.elastic.co/docs/explore-analyze/workflows/steps/ai-steps)
- [Workflow run API](https://www.elastic.co/docs/api/doc/kibana/operation/operation-post-workflows-workflow-id-run)
- [ES|QL MATCH](https://www.elastic.co/docs/reference/query-languages/esql/functions-operators/search-functions/match)

沿用brief的逐字引用、署名和源链接要求；源站条款以实际官方材料为准，不把brief的法律判断当作已核实结论。
