# Career Agent

面向技术类秋招用户的可信智能求职系统。项目以用户确认的真实经历为事实来源，支持简历解析、JD 匹配、定制简历、项目深挖与模拟面试。

## 本地基础服务

本项目使用 Docker Compose 启动开发依赖：

| 服务 | 用途 | 本机地址 |
| --- | --- | --- |
| PostgreSQL + pgvector | 业务数据与向量检索 | `localhost:5432` |
| Redis | 缓存和短期任务状态 | `localhost:6379` |
| MinIO | 简历与项目资料等对象文件 | API：`http://localhost:9000`；控制台：`http://localhost:9001` |

MinIO 使用 Quay 上的固定镜像摘要，以避免 Docker Hub 上该历史公开镜像的访问限制。

首次使用时复制环境变量模板并填入本机开发密码：

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
```

首次启动完成后，可验证三项服务与 pgvector 扩展：

```powershell
docker compose exec postgres psql -U career_agent -d career_agent -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose exec redis redis-cli ping
Invoke-WebRequest http://localhost:9000/minio/health/live
```

预期结果分别为 `vector`、`PONG` 与 HTTP `200`。

停止服务：

```powershell
docker compose down
```

服务数据由 Docker Volumes 保存；`docker compose down` 不会删除数据。仅在明确需要清空本地开发数据时使用 `docker compose down -v`。

## 初始目录

```text
src/career_agent/     Python 应用包
tests/                自动化测试
```

## API 健康检查

在激活 `career-agent` Conda 环境后启动 API：

```powershell
fastapi dev src/career_agent/api/main.py
```

另开一个终端窗口，访问健康检查接口：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

当 API 能连接 PostgreSQL 时，预期结果为：

```text
status database
------ --------
ok     available
```

## 第二阶段：核心数据模型与迁移

项目已使用 Alembic 管理业务表的结构演进。首次迁移会创建 `users`、`candidate_profiles`、`preferences`、`resumes`、`resume_versions` 和 `resume_sources`。

```powershell
alembic upgrade head
alembic current
```

当前最小 API 支持创建和读取用户、候选人画像、求职偏好、简历及简历版本元数据。启动 API 后可访问交互式文档：

```text
http://127.0.0.1:8000/docs
```

## 第三阶段：MinIO 简历文件存储

简历原文件保存在 MinIO 的 `career-agent-files` Bucket 中；PostgreSQL 的 `resume_sources`
只保存对象路径、原文件名、文件大小和 SHA-256 等元数据。上传接口只接受不超过 10 MB 的
PDF 或 DOCX 文件：

```text
POST /users/{user_id}/resumes/upload
```

它使用 `multipart/form-data`，字段为 `file`、可选 `title` 与可选 `is_primary`。文件先写入
MinIO，再以单个 PostgreSQL 事务创建简历、版本和来源记录；若写库失败，接口会删除刚上传的
对象作为补偿。下载时使用以下接口，服务会先检查简历归属，再签发 5 分钟有效的 MinIO URL：

```text
GET /users/{user_id}/resume-versions/{resume_version_id}/download-url
```

启动 API 后可在 `http://127.0.0.1:8000/docs` 试用接口。配置项见 `.env.example`，包括
`MINIO_BUCKET`、预签名 URL 的有效期与文件大小上限。

## 第四阶段：简历解析与 RAG 基础

对已经上传的 PDF/DOCX 简历，用户可显式触发解析与索引：原文件从 MinIO 读取，提取的原文保存到
`resume_versions.content_text`，随后按段落分块、调用 Embedding 服务，并将向量与来源信息写入
`document_chunks`。数据库使用 pgvector 的 HNSW 余弦索引加速检索；检索始终按 `user_id` 过滤，且仅返回
当前简历版本的已索引文本块。

在 `.env` 中配置 OpenAI 官方服务或 OpenAI 兼容服务。密钥绝不能提交到 Git：

```dotenv
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_KEY=your-provider-key
EMBEDDING_BASE_URL=https://your-provider.example/v1
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

安装新增依赖并执行迁移后，使用下面两个接口。索引接口会将简历文本发送给配置的 Embedding 服务，只有在
用户明确调用它时才会产生外部 API 请求：

```text
POST /users/{user_id}/resume-versions/{resume_version_id}/index
POST /users/{user_id}/knowledge/search
```
