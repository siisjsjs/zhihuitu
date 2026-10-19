# zhihuitu · 智绘图平台

> 面向工业工程（IE）的 AI 智能绘图平台：用自然语言或表单生成专业图表，在线编辑、保存与导出。

![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![Vue3](https://img.shields.io/badge/frontend-Vue3-42b883)
![Vite](https://img.shields.io/badge/build-Vite-646cff)
![Docker](https://img.shields.io/badge/deploy-Docker%20Compose-2496ed)

智绘图是一套前后端分离的工业工程图表平台：内置 40+ 工业工程专业模板，支持 AI 生成、在线编辑、图表持久化、图片/Excel 导出，并可与知识库门户（[kg-qa-ie](https://github.com/siisjsjs/kg-qa-ie)）通过 SSO 单点登录打通。

## 功能特性

- **模板库**：方法研究、生产管理、质量控制、六西格玛、库存管理、可靠性分析、常用统计图七大类，40+ 模板（鱼骨图、双手作业分析、动素分析、价值流图、OEE、X-bar R / X-MR / P / C 控制图、甘特图、学习曲线、EOQ/EPQ、雷达图、热力图等）。
- **AI 生成图表**：给定数据与需求，由大模型选择模板、生成图表配置并渲染。
- **在线编辑器**：生成后进入编辑器实时修改，保存到「我的图表」。
- **导出**：图表图片与 Excel 数据导出。
- **用户与权限**：用户表 + 角色（admin / user），支持从知识库门户同步身份。
- **SSO**：以知识库门户为唯一用户源，`POST /api/v1/auth/sso` 服务端校验 token 后 find-or-create 本地用户。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python · FastAPI · SQLAlchemy(async) · Alembic · Pydantic |
| 数据库 | MySQL 8.4（生产） / SQLite（本地开发） |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · ECharts · Pinia |
| 部署 | Docker Compose（nginx 托管前端 + FastAPI + MySQL） |

## 目录结构

```
.
├── backend/                     FastAPI 后端
│   ├── app/
│   │   ├── api/v1/              REST 路由（auth / charts / templates / users / files ...）
│   │   ├── core/                配置、安全、数据库、依赖
│   │   ├── models/              SQLAlchemy 模型
│   │   ├── services/            图表生成、模板同步、导出等业务逻辑
│   │   └── main.py
│   ├── alembic/                 数据库迁移
│   ├── tests/                   pytest 测试
│   ├── Dockerfile               完整镜像构建
│   ├── Dockerfile.incr          增量构建（基于已有镜像，仅 COPY 改动文件）
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    Vue3 + Vite 前端
│   ├── src/
│   │   ├── views/               模板库、编辑器、我的图表、登录、管理后台
│   │   ├── components/
│   │   ├── api/                 接口封装
│   │   └── router/
│   ├── public/
│   ├── Dockerfile
│   └── .env.example
├── chart-templates/             图表模板（每个模板一个目录 + preview.png）
├── docker-compose.yml
└── .dockerignore
```

## 快速开始

### Docker Compose（推荐）

```bash
cp backend/.env.example backend/.env          # 按需填写
```

编辑 `docker-compose.yml`，把所有 `CHANGE_ME` 换成自己的值（MySQL 密码、`DATABASE_URL` 中的密码、`SECRET_KEY`、初始管理员密码），然后：

```bash
docker compose up -d --build
```

- 前端：<http://localhost/>
- API 文档：<http://localhost:8000/docs>
- 首次启动自动建表，并把 `chart-templates/` 同步进数据库。

### 本地开发

```bash
# 后端
cd backend
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd frontend
npm install
npm run dev                                       # 默认 http://localhost:5173
```

前端 `vite.config.ts` 已将 `/api` 代理到 `http://127.0.0.1:8000`，本地开发无需额外处理跨域。

## 配置（环境变量）

| 变量 | 说明 | 示例 |
|---|---|---|
| `DATABASE_URL` | 数据库连接串 | `mysql+aiomysql://user:pass@mysql:3306/zhihuitu` |
| `SECRET_KEY` | JWT 签名密钥（HS256，token 7 天） | 随机长字符串 |
| `CHART_TEMPLATES_DIR` | 模板目录 | `/app/chart-templates` |
| `ANNOUNCEMENT_UPLOAD_DIR` | 公告图片上传目录 | `/app/backend/uploads/announcements` |
| `CORS_ORIGINS` | 允许的前端来源，英文逗号分隔 | `http://localhost,http://127.0.0.1` |
| `BOOTSTRAP_USER_USERNAME` / `BOOTSTRAP_USER_PASSWORD` / `BOOTSTRAP_USER_ROLE` | 空库时的初始管理员 | `admin` / 强密码 / `admin` |
| `BACKEND_AUTO_CREATE_TABLES` | 启动自动建表 | `true` |
| `BACKEND_SYNC_TEMPLATES_ON_STARTUP` | 启动同步模板 | `true` |
| `KGQA_BASE_URL` | 知识库门户地址，用于 SSO token 校验 | `https://kb.example.com` |

## 与知识库门户（kg-qa-ie）的 SSO 对接

1. 用户在知识库门户登录后点击「进入绘图工具」；
2. 门户前端把 access token 以 `POST` 表单提交到 `https://<本平台>/api/v1/auth/sso`（token 放在 body，不落 URL）；
3. 本平台后端用 `KGQA_BASE_URL` 服务端调用门户 `GET /api/v1/auth/me` 校验 token；
4. 按用户名 find-or-create 本地用户，同步 role / is_active（以门户为准）；
5. 签发本平台 token，写入前端 storage 后跳转 `/templates`。

不共享 JWT 密钥，靠门户的 `/me` 服务端校验实现解耦。

## 部署建议

- 生产上避免全量 `docker compose build`（build cache 丢失会重跑 apt/pip 依赖，耗时且易失败）。推荐用 `backend/Dockerfile.incr`：先把当前容器 `docker commit` 成 base 镜像，再只 `COPY` 改动文件做增量构建。
- 前端一般在本地 `npm run build` 出 `dist`，由 nginx 托管，不在服务器上装 Node 构建。
- 反向代理需放行较大文件上传（`client_max_body_size`），并为 `/api/` 保持长超时以支持流式响应。

## 说明

本仓库是智绘图平台生产部署版本的源码快照。生产环境的真实配置、数据库、TLS 证书与凭据不在仓库内；`docker-compose.yml`、`.env.example` 中的敏感值均已用 `CHANGE_ME` 或环境变量替代，`create_admin.py` 从环境变量读取管理员密码。

## 许可证

[MIT](LICENSE) © 2026 siisjsjs
