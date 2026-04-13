# 智慧水务信息源 Hub 落地方案（Vibe Coding 版）

## 1. 项目目标

建设一个面向智慧水务行业情报的轻量化信息 Hub，形成从信息采集、过滤、结构化、分析到周报输出的闭环。

一期目标：

- 监听和过滤法规、标准发布动态
- 跟踪竞品公司公开信息并做事件级分析
- 自动生成每周推送报告，且每条信息保留消息出处

二期目标：

- 接入招投标情报，补充国家、项目、金额、技术路线、中标方维度分析

## 2. 适合 Vibe Coding 的落地原则

该系统不建议一开始就做成重型情报平台，而是采用“小闭环、强结构、可扩展”的方式推进。

设计原则：

- 先做少量高价值数据源，验证周报价值，再扩源
- 先保存原始信息，再做 AI 抽取，避免后续无法回溯
- 每条结论都必须绑定来源 URL、抓取时间、来源类型，支持定量分析
- 把“抓取”和“分析”解耦，防止某个站点波动拖垮整体流程
- 招投标作为二期能力，目录、表结构和任务接口先预留

## 3. 推荐系统架构

```text
数据源（法规 / 标准 / 竞品 / 招投标）
        ↓
采集层（RSS / API / requests / Playwright）
        ↓
原始层（raw_documents）
        ↓
解析层（规则抽取 + LLM 抽取 + 分类）
        ↓
事件层（normalized_events）
        ↓
分析层（打分 / 聚类 / 趋势 / 周报生成）
        ↓
输出层（Markdown 周报 / 邮件 / 企业微信）
```

相比直接建三张业务表，一期更建议采用“原始文档 + 统一事件 + 领域扩展字段”的模式。这样后续新增站点和新增分析口径的成本更低。

## 4. 一期与二期范围

### 4.1 一期必须完成

- 法规与标准动态监听
- 竞品情报采集与分析
- 周报自动生成
- 事件评分、来源追踪、去重、标签化
- 基础 Dashboard 所需字段预留

### 4.2 二期预留但暂不实现

- 招投标站点接入
- 招投标事件抽取与技术路线分析
- 国家维度技术偏好统计
- 中标方竞争格局变化分析

## 5. 技术路线

## 5.1 推荐技术栈

- 语言：Python 3.11+
- 抓取：requests、feedparser、Playwright
- 后端：FastAPI
- 任务调度：APScheduler 或 cron
- 数据库：PostgreSQL
- 向量检索：pgvector
- ORM：SQLAlchemy 2.x
- 消息/队列：一期可不引入，后续可加 Redis 或 RabbitMQ
- LLM：DeepSeek 或 OpenAI 兼容接口
- 周报模板：Jinja2 + Markdown
- 推送：SMTP 邮件、企业微信机器人、飞书机器人三选一

## 5.2 为什么这样选

- Python 适合快速拼装抓取、NLP、LLM 调用、报表输出
- PostgreSQL 足够支撑结构化事件、来源记录、周报归档
- pgvector 适合做相似新闻去重、主题聚类、相关标准召回
- Playwright 只处理动态站点，避免所有站点都走浏览器导致维护成本过高

## 6. 核心数据模型

建议至少分为五层表。

### 6.1 原始文档表 raw_documents

用途：保存抓到的原始信息，便于复算和审计。

关键字段：

- id
- source_id
- source_name
- source_type：official / media / social / tender
- source_url
- title
- published_at
- fetched_at
- language
- raw_text
- raw_html_path
- content_hash
- status

### 6.2 事件表 normalized_events

用途：统一承载结构化后的事件。

关键字段：

- id
- domain：standard / competitor / tender
- event_type
- entity_name
- event_title
- summary
- region
- country
- technologies：JSONB
- tags：JSONB
- importance_score
- signal_strength
- confidence
- published_at
- first_seen_at
- last_seen_at
- dedupe_key
- embedding

### 6.3 事件来源映射表 event_sources

用途：一个事件可能对应多个来源，必须保留出处，便于定量分析和可信度加权。

关键字段：

- id
- event_id
- raw_document_id
- source_url
- source_name
- source_type
- quote_text
- extraction_confidence

### 6.4 领域扩展表

一期可建，便于以后精细查询。

standard_events：

- event_id
- standard_no
- standard_name
- standard_scope
- action_type：new / update / withdrawn
- organization

competitor_events：

- event_id
- company_name
- market
- strategic_intent
- impact_analysis

tender_events：

- event_id
- project_name
- award_company
- amount
- currency
- procurement_org

### 6.5 周报表 weekly_reports

关键字段：

- id
- report_week
- report_title
- generated_at
- report_markdown
- report_json
- status

可再补一张 weekly_report_items 保存每条周报引用了哪些 event_id。

## 7. 信息源设计

## 7.1 法规、标准监听

### 目标

监控与智慧水务、计量、通信协议、仪表标准相关的新增与修订。

### 优先信息源

- 国家标准化管理委员会及相关国家标准平台
- OIML
- IEC
- 欧洲标准组织相关公开页面
- 行业协会标准公告页

### 采集方式建议

- 列表页稳定：requests + BeautifulSoup
- 有 RSS：优先 RSS
- 动态渲染：Playwright
- PDF 公告：先抓元数据，再做 PDF 文本抽取

### 一期过滤规则

先做规则过滤，再做 AI 分类，不要直接把所有文本送给 LLM。

关键词白名单：

- water meter
- smart water
- metering
- measurement
- NB-IoT
- LoRaWAN
- M-Bus
- wM-Bus
- AMI
- communication protocol

关键词黑名单：

- 与食品、医疗、建筑材料等明显无关的标准

### 标准事件抽取字段

- 标准编号
- 标准名称
- 发布机构
- 适用对象
- 事件类型：新增 / 修订 / 废止
- 地区 / 国家
- 发布时间
- 原文链接
- 与水务关联度

### AI 抽取策略

第一步：规则抽取编号、日期、机构名。

第二步：LLM 输出结构化 JSON。

第三步：分类器判断是否属于以下主题：

- 水表
- 电表
- 燃气表
- 通信协议
- 计量与校准

### 重要性评分建议

标准类 importance_score 可按以下维度加权：

- 发布机构权威性
- 是否为正式发布而非征求意见
- 是否涉及通信或计量核心标准
- 是否直接影响水表、远传、AMI 系统

## 7.2 竞品信息发布与分析

### 目标

跟踪重点竞品在产品、市场、认证、合作、中标、技术路线方面的动作。

### 首批监控对象

- Itron
- Arad
- Diehl Metering
- Kumstrup
- sagemcon
- B Meter
- Axioma
- Maddalena

### 信息源优先级

优先级从高到低建议如下：

- 官网新闻中心
- 官方新闻稿 / Investor Relations
- 行业媒体
- 官方 YouTube / Webinar 页面
- LinkedIn

### 关于 LinkedIn 的现实建议

LinkedIn 抓取的稳定性和合规性都较差，一期不要把它作为主来源。可以采用以下策略：

- 先只抓官网和媒体
- LinkedIn 仅作为补充人工校验源
- 若后续必须做，可引入第三方监测服务或半自动导入

### 竞品事件类型体系

- 新产品发布
- 市场拓展
- 获得认证
- 项目中标
- 技术升级
- 战略合作
- 渠道合作
- 并购投资

### 抽取字段

- 公司名
- 事件类型
- 标题
- 国家 / 市场
- 涉及技术
- 涉及产品
- 事件时间
- 来源 URL
- 可能的战略意图
- 对行业影响

### 竞品分析建议

不要只抽事实，还要补两类分析字段：

- strategic_intent：例如扩张某区域、强化某通信路线、绑定公用事业客户
- impact_analysis：这条消息是否改变竞争格局、是否释放明确趋势信号

### signal_strength 计算建议

可按以下规则给 0 到 1 的分值：

- 官方新闻稿高于媒体转载
- 产品发布高于普通市场活动
- 涉及水务主航道高于跨行业泛化内容
- 同一事件被多个来源交叉验证时提高分数

## 7.3 招投标信息追踪（二期预留）

### 二期目标

跟踪谁中标、在哪个国家、采用何种技术、金额多大，并形成技术路线趋势判断。

### 建议优先信息源

- TED
- 各国政府采购网
- 大型公用事业采购公告页

### 二期抽取字段

- 项目名称
- 国家
- 招标方
- 中标方
- 技术类型
- 金额
- 币种
- 发布时间
- 公告链接

### 二期分析输出

- 国家偏好的技术路线变化
- NB-IoT、LoRaWAN、wM-Bus 项目占比变化
- 竞品中标频次与区域分布

## 8. 处理流水线设计

## 8.1 每日任务链路

建议拆成五步，便于排错。

1. crawl_sources
2. normalize_documents
3. classify_and_extract
4. dedupe_and_score
5. persist_events

## 8.2 周任务链路

1. aggregate_weekly_events
2. cluster_topics
3. generate_weekly_report
4. review_and_publish

## 8.3 去重策略

建议三层去重：

- URL 去重：同一来源重复抓取
- 标题哈希去重：标题完全相同
- 语义去重：embedding 相似度阈值，例如 0.92 以上视为同事件

## 8.4 可信度策略

confidence 建议来自以下因子：

- 来源类型权重：official > tender > media > social
- 抽取字段完整度
- 是否多源交叉印证
- LLM 输出结构校验是否通过

## 9. 周报产品形态

## 9.1 报告标题

2026 年第 X 周｜全球智慧水务行业情报周报

## 9.2 报告结构

### 一、本周关键结论

- 2 到 5 条机器生成摘要
- 每条结论必须由多个事件支撑，不能凭单条新闻臆断

### 二、标准与法规动态

- 按重要性排序
- 每条包含：事件摘要、标准编号、影响判断、来源链接

### 三、竞品动态

- 按公司分组或按事件重要性排序
- 每条包含：事实、技术、市场、分析、来源

### 四、招投标动态

- 一期可显示“模块预留，暂未上线”
- 二期上线后按国家和技术路线输出

### 五、技术趋势观察

- 本周技术词频变化
- 高信号路线变化
- 值得关注的区域变化

### 六、附录

- 全量事件清单
- 事件来源列表
- 统计口径说明

## 9.3 周报每条记录必须包含字段

- summary
- source_url
- source_name
- source_type
- published_at
- confidence
- signal_strength

## 9.4 周报生成方式

建议采用“先筛选、再聚类、后生成”的模式：

- 先取一周内高于阈值的事件
- 再按主题聚类，减少重复表述
- 最后由 LLM 生成 Markdown

这样可避免周报只是新闻堆砌。

## 10. 建议 Prompt 设计

## 10.1 标准抽取 Prompt

目标：从公告或新闻中抽取标准事件。

输出要求：

- 严格 JSON
- 缺失字段返回 null
- 不允许编造日期和编号

字段：

- standard_name
- standard_no
- device_type
- action_type
- organization
- region
- published_at
- source_url
- relevance_reason

## 10.2 竞品分析 Prompt

目标：从竞品新闻中抽取事实并给出简短分析。

字段：

- company_name
- event_type
- technologies
- market
- strategic_intent
- impact_analysis
- signal_strength

## 10.3 周报生成 Prompt

要求：

- 按重要性排序
- 输出 Markdown
- 每条信息保留来源名称和来源 URL
- 结论必须基于输入数据，不得生成无依据判断

## 11. 建议工程目录结构

一期就把二期目录预留出来，后续扩展会顺很多。

```text
waterinfohub/
├─ apps/
│  ├─ api/
│  └─ worker/
├─ configs/
│  ├─ sources/
│  │  ├─ standards.yaml
│  │  ├─ competitors.yaml
│  │  └─ tenders.yaml
│  ├─ prompts/
│  │  ├─ standard_extract.md
│  │  ├─ competitor_analysis.md
│  │  ├─ tender_analysis.md
│  │  └─ weekly_report.md
│  └─ scoring/
│     └─ rules.yaml
├─ data/
│  ├─ raw/
│  ├─ parsed/
│  └─ reports/
├─ docs/
│  └─ waterinfohub-implementation-plan.md
├─ infra/
│  ├─ docker/
│  └─ sql/
│     ├─ 001_init.sql
│     ├─ 002_events.sql
│     ├─ 003_reports.sql
│     └─ 004_tender_reserve.sql
├─ src/
│  ├─ collectors/
│  │  ├─ base.py
│  │  ├─ standards/
│  │  ├─ competitors/
│  │  └─ tenders/
│  ├─ parsers/
│  │  ├─ rule_based/
│  │  └─ llm/
│  ├─ pipelines/
│  │  ├─ ingest.py
│  │  ├─ classify.py
│  │  ├─ dedupe.py
│  │  ├─ score.py
│  │  └─ weekly_report.py
│  ├─ models/
│  │  ├─ raw_document.py
│  │  ├─ event.py
│  │  ├─ standard_event.py
│  │  ├─ competitor_event.py
│  │  ├─ tender_event.py
│  │  └─ weekly_report.py
│  ├─ services/
│  │  ├─ embeddings.py
│  │  ├─ llm_client.py
│  │  ├─ notifier.py
│  │  └─ report_renderer.py
│  └─ utils/
├─ tests/
│  ├─ collectors/
│  ├─ parsers/
│  └─ pipelines/
└─ README.md
```

## 12. 最小可行版本（MVP）建议

建议 3 周内做出可演示版本。

### 第 1 周

- 建库和表结构
- 接入 3 个标准源
- 接入 3 个竞品官网新闻源
- 保存 raw_documents

### 第 2 周

- 完成规则过滤和 LLM 抽取
- 事件去重、打标签、评分
- 输出结构化事件列表

### 第 3 周

- 周报 Markdown 生成
- 邮件或企业微信推送
- 增加简单查询接口或管理页

## 13. 关键风险与规避建议

### 风险 1：站点结构频繁变化

建议：

- 每个采集器独立实现
- 把 CSS 选择器和 URL 模板配置化
- 抓取失败不影响其他任务继续执行

### 风险 2：LLM 输出不稳定

建议：

- 强制 JSON schema 校验
- 对重要字段做二次规则兜底
- 保留原文片段 quote_text 便于复核

### 风险 3：周报变成信息堆砌

建议：

- 引入 importance_score 和 signal_strength
- 低分事件进入附录，不进入正文
- 聚类后生成，避免同主题多条重复输出

### 风险 4：LinkedIn 与部分媒体采集不稳定

建议：

- 一期弱化依赖
- 用官方新闻源做主骨架
- 媒体只作为补充和交叉验证

## 14. 推荐实施结论

如果目标是尽快做出一个能持续产出周报的智慧水务情报系统，一期最优路径不是先做复杂前端，而是先打通下面这条链路：

法规标准源 + 竞品官网源 → 原始文档存储 → AI 结构化抽取 → 事件去重评分 → 周报生成与推送。

招投标模块放到二期是合理的，但表结构、目录、Prompt 和调度入口现在就应预留。这样一期不会被拖慢，同时也不会在二期重构底座。

对这个项目而言，真正决定成败的不是爬虫数量，而是三个能力：

- 是否能稳定保留消息出处
- 是否能把噪音过滤掉
- 是否能把一周的碎片信息组织成可读的结论

只要这三个环节设计正确，这个 Hub 就具备持续演进成行业情报产品的基础。