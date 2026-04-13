# WaterInfoHub 阿里云 ECS 部署指南

本文档面向单机 Docker Compose 生产部署，适合当前 MVP 阶段。

## 1. 推荐规格

- ECS：`2 vCPU / 4 GB RAM / 80 GB ESSD`
- 系统：`Ubuntu 22.04 LTS`
- 安全组：
  - 入站开放 `22`
  - 若 API 直连，开放 `8000`
  - 若走 Nginx，开放 `80` 和 `443`
- 磁盘：
  - 系统盘建议 `40 GB+`
  - 数据盘建议单独挂载给 Docker 数据目录或 PostgreSQL 卷

## 2. 服务器初始化

登录 ECS 后执行：

```bash
sudo timedatectl set-timezone UTC
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

说明：

- 生产上建议统一使用 `UTC`，周报展示时再转本地时区。
- 如果后面要接域名，建议同时安装 `nginx` 和 `certbot`。

## 3. 拉取代码与准备目录

```bash
git clone <your-repo-url> /opt/waterinfohub
cd /opt/waterinfohub
mkdir -p data/reports logs
cp .env.prod.example .env.prod
```

然后编辑 `.env.prod`：

```bash
vim .env.prod
```

至少修改这些值：

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `LLM_API_KEY`

注意：

- `DATABASE_URL` 中的用户名、密码、库名要和 `POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB` 保持一致。
- 容器内数据库主机名固定写 `postgres`，不要写 `localhost`。

## 4. 构建镜像

在项目根目录执行：

```bash
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml build
```

## 5. 初始化数据库迁移

首次部署先执行迁移：

```bash
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml --profile ops run --rm migrate
```

如果后续代码升级带来 schema 变化，重复执行同一条命令即可。

## 6. 启动生产服务

```bash
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml up -d postgres api worker
```

查看状态：

```bash
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml ps
```

查看日志：

```bash
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml logs -f api
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml logs -f worker
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml logs -f postgres
```

## 7. 验证服务

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

手动触发一次流水线：

```bash
curl -X POST http://127.0.0.1:8000/jobs/pipeline/run
```

手动触发一次周报：

```bash
curl -X POST http://127.0.0.1:8000/jobs/weekly-report/run
```

周报文件输出目录：

- 宿主机：`/opt/waterinfohub/data/reports`
- 容器内：`/app/data/reports`

日志目录：

- 宿主机：`/opt/waterinfohub/logs`
- 容器内：`/app/logs`

## 8. 发布与升级命令

代码更新后建议执行：

```bash
git pull
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml build
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml --profile ops run --rm migrate
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml up -d postgres api worker
```

## 9. 生产建议

- 不要把 `8000` 直接暴露公网太久，建议用 `nginx` 反向代理。
- `.env.prod` 不要入库。
- `POSTGRES_PASSWORD` 和 `LLM_API_KEY` 建议使用高强度随机值。
- 至少开启云盘快照，最好再补数据库备份策略。
- 若采集站点逐步增多，建议升级到 `4 vCPU / 8 GB RAM`。

## 10. 常用回滚与排障

回滚到上一个提交：

```bash
git log --oneline -n 5
git checkout <previous_commit>
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml build
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml up -d postgres api worker
```

仅重启 worker：

```bash
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml restart worker
```

重新执行迁移：

```bash
docker compose --env-file .env.prod -f infra/docker/docker-compose.prod.yml --profile ops run --rm migrate
```

如果 API 无法连接数据库，优先检查：

- `docker compose ... ps`
- `docker compose ... logs postgres`
- `.env.prod` 中 `DATABASE_URL`
- 安全组、云防火墙、宿主机磁盘是否满
