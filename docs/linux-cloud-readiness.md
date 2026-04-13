# WaterInfoHub Linux 云部署评估与待办

## 1. 当前状态评估

你现在已经具备这些基础：

- 项目骨架完成
- 核心配置目录完成（sources、prompts、scoring）
- PostgreSQL 初始化 SQL 与 Alembic 迁移已就绪
- API 与 worker 入口已建立

当前已补的数据库增强：

- 二版迁移新增 source_host，便于按站点来源追踪与统计
- 二版迁移新增 search_text，便于全文检索和后续周报召回
- 已补 JSONB、全文检索、向量检索相关索引

当前已补的业务链路：

- 每日 ingest 可写入 raw_documents
- normalize 可把 raw_documents 写入 normalized_events 和 event_sources
- weekly report 可从事件层生成 Markdown 并归档到 weekly_reports

距离 Linux 云服务器可稳定运行，还需要补齐“运行时、交付、运维、安全、可观测”五块能力。

## 2. 上云前必须完成（P0）

## 2.1 运行时与依赖

- 固化 Python 依赖版本，避免线上与本地行为漂移
- 为 Playwright 增加 Linux 运行依赖安装步骤
- 将 .env 配置拆分为 dev 与 prod

验收标准：

- 新机器拉代码后，30 分钟内可完成依赖安装并成功启动 API 与 worker

## 2.2 数据库与迁移

- 正式启用 Alembic（本仓库已补基础配置）
- 新 schema 变更只走 Alembic revision，不再直接改线上 SQL
- 建立备份策略（每日全量 + 事务日志或至少每日快照）

验收标准：

- 任意版本可回滚
- 新环境可一键初始化到当前 schema

## 2.3 任务调度与进程托管

- 每日抓取任务和每周周报任务使用 systemd timer 或容器定时器
- API/worker 使用 systemd 或容器编排守护
- 进程异常退出可自动拉起

验收标准：

- 强制 kill 进程后，60 秒内自动恢复

## 2.4 配置与密钥管理

- API Key 不允许写入代码或镜像
- 使用环境变量或云厂商 Secret Manager
- 对外通知 webhook 做最小权限管理

验收标准：

- 仓库内无真实密钥
- 线上密钥可轮换且不重发镜像

## 2.5 基础可观测

- 增加结构化日志（JSON）
- 关键任务写入执行状态和耗时
- 失败任务支持告警（邮件/企业微信）

验收标准：

- 任意一次失败可定位到 source_id 和失败阶段

## 3. 建议尽快完成（P1）

- 增加限流和重试策略（站点抓取）
- 增加数据质量规则（空 summary、空 source_url 拦截）
- 建立事件去重命中率、周报覆盖率指标
- 接入 Sentry 或等效错误追踪

## 4. 生产部署推荐形态

推荐优先采用单机 Docker Compose 方案（先快跑），后续再迁移 Kubernetes。

单机组成：

- waterinfohub-api
- waterinfohub-worker
- postgres（含 pgvector）
- 可选：redis（后续队列化时启用）

## 5. Linux 服务器准备清单

系统层：

- Ubuntu 22.04 LTS 或 Debian 12
- 时区统一为 UTC（报表展示再转本地）
- 开放端口最小化（建议仅 22、80、443、应用端口）

软件层：

- Docker + Compose
- Nginx（反向代理与 TLS）
- Fail2ban（可选）

数据层：

- PostgreSQL 16+
- pgvector 扩展

## 6. 成本与容量初始建议

对于 MVP，建议起步资源：

- 2 vCPU
- 4 GB RAM
- 80 GB SSD

当 Playwright 任务增多时建议升级至 4 vCPU / 8 GB RAM。

## 7. 你下一步最该做的事情

1. 先完成容器化和一键启动（本仓库已补模板）
2. 接入日志和失败告警，确保周报任务可运营
3. 完成周报候选查询与全文检索接口，真正用上二版索引
4. 用 LLM 替换当前规则版摘要与分析，提升周报质量
