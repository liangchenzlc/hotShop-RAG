# HotSpot RAG

热点新闻聚合与 GraphRAG 智能问答系统。自动采集多源新闻，通过 GraphRAG 管线构建知识图谱，支持语义搜索与智能问答。

## 架构概览

```
                   采集管线
  NewsAPI → 调度器 → 文章采集 → MySQL(元数据) + Redis(全文内容)
                              │
                              ▼ doc_id 关联
  索引管线
  POST /index/rebuild → MiniRAG.insert()
    → 分块 + 嵌入 → FAISS (chunks_vdb)
    → LLM 提取实体/关系 → 嵌入 → FAISS (entities_vdb / relationships_vdb)
    → 图存储 (NetworkX)

  检索管线
  POST /qa/ask  → MiniRAG.query(mode="hybrid")
    → 关键词提取 → 实体/关系/文本块 多路搜索 → 上下文构建 → LLM 生成
  POST /search  → MiniRAG.query(mode="naive") 纯向量搜索

  存储: MySQL + Redis + FAISS + NetworkX 图
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| GraphRAG | MiniRAG (LangGraph-based) |
| 向量数据库 | FAISS (本地文件) |
| 关系数据库 | MySQL (SQLAlchemy 2.0) |
| KV 缓存 | Redis |
| 图存储 | NetworkX |
| LLM | DashScope 通义千问 / OpenAI 兼容接口 |
| 调度器 | APScheduler |
| 数据源 | NewsAPI |

## 项目结构

```
backend/
├── app/
│   ├── agent/               # LLM + GraphRAG 核心
│   │   ├── chat_router.py   # 聊天/意图识别路由
│   │   ├── minirag_lang/    # GraphRAG 引擎
│   │   │   ├── rag.py       # 插入/查询入口
│   │   │   ├── graph.py     # LangGraph 管线定义
│   │   │   ├── nodes/       # 插入/查询节点
│   │   │   ├── storage/     # FAISS/Graph/KV 存储
│   │   │   └── retrieval/   # 检索逻辑
│   │   ├── prompts.py       # 提示词模板
│   │   └── embedding_router.py
│   ├── api/routes/          # API 路由
│   ├── core/                # 配置
│   ├── db/                  # 数据库模型 + Session
│   ├── domain/schemas.py    # Pydantic 模型
│   ├── infra/
│   │   ├── graphrag/        # MiniRAGAdapter (桥接)
│   │   ├── storage/         # Redis 客户端
│   │   └── converter/       # 内容转换
│   ├── services/            # 业务逻辑层
│   ├── sources/             # 数据源 (NewsAPI)
│   └── scheduler/           # 定时任务
├── test/                    # 测试 (75 tests)
├── scripts/                 # 工具脚本
└── API_DOCS.md              # 完整 API 文档
```

## 快速开始

### 1. 环境要求

- Python 3.12+
- MySQL 8.0+
- Redis 7+

### 2. 安装

```bash
# 创建虚拟环境
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
```

### 3. 配置

编辑 `.env` 文件，配置以下关键参数：

```ini
# 数据库
MYSQL_URL=mysql+pymysql://root:password@localhost:3306/hotspot_rag

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM (DashScope/阿里云通义千问)
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CHAT_MODEL=qwen-plus
EMBEDDING_MODEL=text-embedding-v4

# NewsAPI
NEWSAPI_API_KEY=your-newsapi-key
```

### 4. 启动

```bash
# 创建数据库表
python -m scripts.init_db

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 5. 使用

```bash
# 1. 创建数据源
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"name":"newsapi_hot","source_type":"newsapi","keywords":["AI","technology"]}'

# 2. 触发采集
curl -X POST http://localhost:8000/sources/collect-all

# 3. 重建索引
curl -X POST http://localhost:8000/index/rebuild -H "Content-Type: application/json" -d '{}'

# 4. 语义搜索
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"AI agent","top_k":5}'

# 5. 问答
curl -X POST http://localhost:8000/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","use_retrieval":true}'
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/sources` | 创建数据源 |
| GET | `/sources` | 数据源列表 |
| GET | `/sources/{id}` | 数据源详情 |
| PATCH | `/sources/{id}` | 更新数据源 |
| DELETE | `/sources/{id}` | 删除数据源 |
| POST | `/sources/collect-all` | 全量采集 |
| POST | `/sources/{id}/collect` | 单源采集 |
| GET | `/knowledge/stats` | 知识库统计 |
| GET | `/knowledge/articles` | 文章列表 |
| GET | `/knowledge/articles/{id}` | 文章详情 |
| DELETE | `/knowledge/articles/{id}` | 删除文章 |
| POST | `/knowledge/articles/batch-delete` | 批量删除 |
| POST | `/index/rebuild` | 重建 GraphRAG 索引 |
| POST | `/search` | 语义搜索 (naive) |
| POST | `/qa/ask` | 问答 (非流式) |
| POST | `/qa/ask/stream` | 问答 (流式 SSE) |
| GET | `/chat/sessions` | 会话列表 |
| POST | `/chat/sessions` | 创建会话 |
| DELETE | `/chat/sessions/{id}` | 删除会话 |
| GET | `/chat/sessions/{id}/messages` | 消息历史 |

详细文档见 [API_DOCS.md](API_DOCS.md)。

## 测试

```bash
# 运行全部测试
pytest test/ -v

# 运行特定模块
pytest test/test_source_management_api.py -v
```

## 数据流

### 采集 → 索引 → 问答

```
NewsAPI → 文章采集 → MySQL + Redis
                         ↓
                  /index/rebuild
                         ↓
              MiniRAG 索引管线
            ┌─ 分块 → FAISS(chunks)
            ├─ 实体提取 → FAISS(entities) + Graph
            └─ 关系提取 → FAISS(relationships) + Graph
                         ↓
                  /qa/ask (hybrid 检索)
            ┌─ 关键词提取 (LLM)
            ├─ local: 实体向量 → 图邻居遍历
            ├─ global: 关系向量 → 图查找
            ├─ naive: 文本块向量搜索
            └─ 合并 → 上下文构建 → LLM 生成
```
