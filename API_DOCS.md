# HotSpot RAG API 文档

Base URL: `http://localhost:8000`

## 架构概述

```
采集管线: NewsAPI → 文章 → MySQL(元数据) + Redis(全文内容)
索引管线: POST /index/rebuild → MiniRAG.insert()
          → 分块 + 嵌入 → FAISS (chunks_vdb)
          → LLM 提取实体/关系 → FAISS (entities_vdb / relationships_vdb)
          → 图存储 (NetworkX)
检索管线: POST /qa/ask  → MiniRAG.query(mode="hybrid")
          → 关键词提取 → 实体/关系/文本块 多路搜索 → 上下文构建 → LLM 生成
          POST /search  → MiniRAG.query(mode="naive") 纯向量搜索
存储:     MySQL (结构化数据) + Redis (KV 缓存) + FAISS (向量) + 图 (关系)
```

---

## 目录

1. [健康检查](#1-健康检查)
2. [数据源管理](#2-数据源管理)
3. [知识库](#3-知识库)
4. [向量搜索](#4-向量搜索)
5. [索引重建](#5-索引重建)
6. [QA 问答](#6-qa-问答)
7. [聊天记忆](#7-聊天记忆)

---

## 1. 健康检查

### GET /health

检查服务是否正常运行。

**请求参数：** 无

**响应示例：**
```json
{
  "status": "ok"
}
```

---

## 2. 数据源管理

Prefix: `/sources`

### 2.1 创建数据源

**POST /sources**

创建新的数据采集源配置。

**请求体（JSON）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | — | 数据源名称（唯一），如 `newsapi_hot` |
| `source_type` | string | 是 | — | 来源类型，当前支持 `newsapi`，未来扩展 `rss`、`twitter` 等 |
| `is_active` | bool | 否 | `true` | 是否启用 |
| `config` | object | 否 | `{}` | 来源配置（JSON），如 API key、endpoint 等 |
| `keywords` | array[string] | 否 | `[]` | 搜索关键词列表 |
| `schedule_cron` | string | 否 | `null` | 自定义调度 cron 表达式，如 `"*/30 * * * *"` |
| `max_workers` | integer | 否 | `3` | 并发 worker 上限（1-10） |

**config 示例（NewsAPI）：**
```json
{
  "api_key": "158ae2fdfcd24dd68f8ab0ab40868e73",
  "endpoint": "https://newsapi.org/v2",
  "sort_by": "popularity",
  "language": "en"
}
```

**请求示例：**
```json
{
  "name": "newsapi_hot",
  "source_type": "newsapi",
  "config": {
    "api_key": "158ae2fdfcd24dd68f8ab0ab40868e73",
    "sort_by": "popularity",
    "language": "en"
  },
  "keywords": ["technology", "AI", "climate"],
  "is_active": true
}
```

**响应（201 Created）：**
```json
{
  "id": 1,
  "name": "newsapi_hot",
  "source_type": "newsapi",
  "is_active": true,
  "config": {"api_key": "***", "sort_by": "popularity", "language": "en"},
  "keywords": ["technology", "AI", "climate"],
  "schedule_cron": null,
  "max_workers": 3,
  "last_run_at": null,
  "created_at": "2026-04-29T10:00:00Z",
  "updated_at": "2026-04-29T10:00:00Z"
}
```

**错误：** `409` — 数据源名称已存在

---

### 2.2 获取数据源列表

**GET /sources**

**请求参数：** 无

**响应：**
```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "name": "newsapi_hot",
      "source_type": "newsapi",
      "is_active": true,
      "config": {...},
      "keywords": ["technology", "AI"],
      "schedule_cron": null,
      "max_workers": 3,
      "last_run_at": "2026-04-29T10:30:00Z",
      "created_at": "2026-04-29T10:00:00Z",
      "updated_at": "2026-04-29T10:30:00Z"
    }
  ]
}
```

---

### 2.3 获取单个数据源

**GET /sources/{source_id}**

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `source_id` | integer | 数据源 ID |

**响应：** 与列表项结构相同

**错误：** `404` — 数据源不存在

---

### 2.4 更新数据源

**PATCH /sources/{source_id}**

部分更新，只传需要修改的字段。

**请求体（JSON，全部可选）：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | string | 新名称 |
| `is_active` | bool | 是否启用 |
| `config` | object | 新配置 |
| `keywords` | array[string] | 新关键词列表 |
| `schedule_cron` | string | 新 cron 表达式 |
| `max_workers` | integer | 新并发上限 |

**响应：** 更新后的数据源对象

**错误：** `404` — 数据源不存在

---

### 2.5 删除数据源

**DELETE /sources/{source_id}**

**响应：** 204 No Content

**错误：** `404` — 数据源不存在

---

### 2.6 手动触发全量采集

**POST /sources/collect-all**

对所有 active 的数据源执行一次采集。

**请求参数：** 无

**响应：**
```json
{
  "results": [
    {
      "name": "newsapi_hot",
      "status": "ok",
      "detail": {
        "job_id": 1,
        "status": "success",
        "fetched": 20,
        "new": 15,
        "dedup": 5,
        "errors": 0
      }
    }
  ]
}
```

---

### 2.7 手动触发单个数据源采集

**POST /sources/{source_id}/collect**

**响应：**
```json
{
  "name": "newsapi_hot",
  "status": "ok",
  "detail": {
    "job_id": 2,
    "status": "success",
    "fetched": 10,
    "new": 8,
    "dedup": 2,
    "errors": 0
  }
}
```

**错误：** `404` — 数据源不存在

---

## 3. 知识库

Prefix: `/knowledge`

### 3.1 获取知识库统计

**GET /knowledge/stats**

**响应：**
```json
{
  "total_articles": 150,
  "today_new": 12,
  "last_sync_time": "2026-04-29T10:30:00Z",
  "avg_hot_score": 5.2
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_articles` | integer | 文章总数 |
| `today_new` | integer | 今日新增 |
| `last_sync_time` | string or null | 最近更新时间 |
| `avg_hot_score` | float | 平均热度评分 |

---

### 3.2 获取文章列表

**GET /knowledge/articles**

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `keyword` | string | 否 | — | 标题/URL 搜索关键词 |
| `date_from` | string | 否 | — | 发布日期筛选起始，格式 `YYYY-MM-DD` |
| `date_to` | string | 否 | — | 发布日期筛选截止，格式 `YYYY-MM-DD` |
| `sort_by` | string | 否 | `"time"` | 排序字段：`"time"`(发布时间) / `"hot"`(热度) |
| `order` | string | 否 | `"desc"` | 排序方向：`"asc"` / `"desc"` |
| `page` | integer | 否 | `1` | 页码，从 1 开始 |
| `page_size` | integer | 否 | `20` | 每页条数（1-200） |

**响应：**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Ubuntu's AI roadmap revealed",
      "source_account": "TechCrunch",
      "url": "https://techcrunch.com/...",
      "published_at": "2026-04-28T10:00:00Z",
      "hot_score": 0
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `items` | array | 文章列表 |
| `items[].id` | integer | 文章 ID |
| `items[].title` | string | 标题 |
| `items[].source_account` | string | 来源名称 |
| `items[].url` | string | 原文链接 |
| `items[].published_at` | string or null | 发布时间 |
| `items[].hot_score` | integer | 热度评分 |
| `total` | integer | 总记录数 |
| `page` | integer | 当前页码 |
| `page_size` | integer | 每页大小 |

---

### 3.3 获取文章详情

**GET /knowledge/articles/{article_id}**

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `article_id` | integer | 文章 ID |

**响应：**
```json
{
  "id": 1,
  "title": "Ubuntu's AI roadmap revealed",
  "source_account": "TechCrunch",
  "url": "https://techcrunch.com/...",
  "published_at": "2026-04-28T10:00:00Z",
  "hot_score": 0,
  "summary": "A test article description...",
  "content_markdown": "# Ubuntu's AI roadmap revealed\n\nCanonical...\n\n---\nSource: https://..."
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `summary` | string or null | 文章摘要 |
| `content_markdown` | string | Markdown 格式全文 |

**错误：** `404` — 文章不存在

---

### 3.4 删除单篇文章

**DELETE /knowledge/articles/{article_id}**

同时删除文章、Redis 内容及 MiniRAG 中关联的 FAISS 向量、图节点和 KV 数据。

**响应：**
```json
{
  "deleted": true,
  "article_id": 1
}
```

**错误：** `404` — 文章不存在

---

### 3.5 批量删除文章

**POST /knowledge/articles/batch-delete**

**请求体（JSON）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `article_ids` | array[integer] | 否 | 要删除的文章 ID 列表 |

**请求示例：**
```json
{
  "article_ids": [1, 2, 3]
}
```

**响应：**
```json
{
  "deleted_count": 3
}
```

---

## 4. 向量搜索

### POST /search

对知识库进行语义向量搜索（MiniRAG naive 模式，纯 FAISS 向量检索）。

**请求体（JSON）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | 是 | — | 搜索文本 |
| `top_k` | integer | 否 | `5` | 返回结果数量 |

**请求示例：**
```json
{
  "query": "什么是RAG?",
  "top_k": 5
}
```

**响应：**
```json
{
  "hits": [
    {
      "article_id": 1,
      "title": "RAG 技术详解",
      "url": "https://example.com/rag",
      "score": 0.92,
      "chunk_no": 0,
      "snippet": "RAG 是检索增强生成...（前400字符）"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `hits[].article_id` | integer | 文章 ID |
| `hits[].title` | string | 文章标题 |
| `hits[].url` | string | 文章链接 |
| `hits[].score` | float | 相似度分数（Cosine 距离） |
| `hits[].chunk_no` | integer | 块编号 |
| `hits[].snippet` | string | 匹配文本片段（前 400 字符） |

---

## 5. 索引重建

Prefix: `/index`

### POST /index/rebuild

对文章进行 GraphRAG 索引重建（分块 → 嵌入 → 实体/关系提取 → 存入 FAISS + 图存储）。

**请求体（JSON）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `article_ids` | array[integer] | 否 | `[]` | 指定重建的文章 ID 列表，为空则重建全部 |

**请求示例：**
```json
{
  "article_ids": []
}
```

**响应：**
```json
{
  "total_articles": 150,
  "indexed_articles": 148,
  "failed_articles": 2,
  "error_samples": [
    "article_id=42 failed: empty content, cannot index"
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_articles` | integer | 待处理文章总数 |
| `indexed_articles` | integer | 成功索引数 |
| `failed_articles` | integer | 失败数 |
| `error_samples` | array[string] | 错误样例（最多 5 条） |

---

## 6. QA 问答

Prefix: `/qa`

### 6.1 非流式问答

**POST /qa/ask**

执行完整的 GraphRAG 问答流程（关键词提取 → 实体/关系/文本块多路检索 → 上下文构建 → LLM 生成）。

**请求体（JSON）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `question` | string | 是 | — | 用户问题 |
| `top_k` | integer | 否 | `5` | 检索数量 |
| `use_retrieval` | boolean | 否 | `false` | `true`=启用向量检索，`false`=纯聊天模式 |
| `session_id` | integer or null | 否 | `null` | 会话 ID（用于多轮对话上下文） |

**请求示例：**
```json
{
  "question": "什么是RAG技术？",
  "top_k": 5,
  "use_retrieval": true,
  "session_id": null
}
```

**响应：**
```json
{
  "answer": "RAG（Retrieval-Augmented Generation）是一种...",
  "citations": [
    {
      "article_id": 1,
      "url": "https://example.com/rag",
      "title": "RAG 技术详解",
      "chunk_no": 0
    }
  ],
  "intent": "qa",
  "evaluation": {
    "graphrag_mode": "hybrid"
  },
  "session_id": 42
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer` | string | 生成的回答 |
| `citations` | array | 引用的文章列表 |
| `citations[].article_id` | integer | 文章 ID |
| `citations[].url` | string | 原文链接 |
| `citations[].title` | string | 文章标题 |
| `citations[].chunk_no` | integer | 引用的块编号 |
| `intent` | string | 识别意图：`"qa"` / `"chat"` |
| `evaluation` | object | GraphRAG 元信息，如 `{"graphrag_mode": "hybrid"}` |
| `session_id` | integer or null | 会话 ID |

---

### 6.2 流式问答

**POST /qa/ask/stream**

与 `/qa/ask` 相同，但使用 SSE（Server-Sent Events）流式返回。

**请求体（JSON）：** 与 `/qa/ask` 完全一致

**响应格式：**

```
data: {"type": "token", "token": "RAG"}

data: {"type": "token", "token": "（"}

data: {"type": "token", "token": "Retrieval"}

data: {"type": "token", "token": "-Augmented"}

data: {"type": "done", "session_id": 42, "answer": "RAG（Retrieval-Augmented Generation）是一种...", "intent": "qa", "evaluation": {"streaming": true, "mode": "graphrag_hybrid"}, "citations": [...]}
```

| Event | type | 说明 |
|-------|------|------|
| `token` | 文本块 | 每次一个 token，前端逐一拼接 |
| `done` | 结束信号 | 包含完整 answer、citations、session_id |

**MediaType:** `text/event-stream`

**Headers:** `Cache-Control: no-cache`, `Connection: keep-alive`

---

## 7. 聊天记忆

Prefix: `/chat`

### 7.1 获取会话列表

**GET /chat/sessions**

**响应：**
```json
{
  "items": [
    {
      "id": 1,
      "title": "新对话",
      "message_count": 4,
      "last_preview": "RAG（Retrieval-Augmented Generation）是一种...",
      "created_at": "2026-04-29T10:00:00Z",
      "updated_at": "2026-04-29T10:05:00Z"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `items[].id` | integer | 会话 ID |
| `items[].title` | string | 会话标题（默认"新对话"） |
| `items[].message_count` | integer | 消息数量 |
| `items[].last_preview` | string or null | 最后一条消息的预览 |
| `items[].created_at` | string | 创建时间 |
| `items[].updated_at` | string | 更新时间 |

---

### 7.2 创建会话

**POST /chat/sessions**

**响应（200 OK）：**
```json
{
  "id": 2,
  "title": "新对话",
  "message_count": 0,
  "created_at": "2026-04-29T11:00:00Z",
  "updated_at": "2026-04-29T11:00:00Z"
}
```

---

### 7.3 删除会话

**DELETE /chat/sessions/{session_id}**

**响应：**
```json
{
  "ok": true
}
```

**错误：** `404` — 会话不存在

---

### 7.4 获取会话消息列表

**GET /chat/sessions/{session_id}/messages**

**响应：**
```json
{
  "items": [
    {
      "id": 1,
      "role": "user",
      "content": "什么是RAG？",
      "citations": null,
      "intent": null,
      "created_at": "2026-04-29T10:00:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "RAG（Retrieval-Augmented Generation）是一种...",
      "citations": {
        "items": [
          {
            "article_id": 1,
            "url": "https://example.com/rag",
            "title": "RAG 技术详解",
            "chunk_no": 0
          }
        ]
      },
      "intent": "qa",
      "created_at": "2026-04-29T10:00:01Z"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `items[].role` | string | `"user"` / `"assistant"` |
| `items[].content` | string | 消息内容 |
| `items[].citations` | object or null | assistant 消息的引用来源 |
| `items[].intent` | string or null | assistant 消息的意图类型 |

---

## 路由前缀总结

| Prefix | 路由文件 | 功能模块 |
|--------|----------|----------|
| `/health` | `health.py` | 健康检查 |
| `/sources` | `source_management.py` | 数据源 CRUD + 采集触发 |
| `/knowledge` | `knowledge.py` | 知识库文章管理 |
| `/search` | `search.py` | GraphRAG naive 模式语义搜索 |
| `/index` | `indexing.py` | GraphRAG 索引重建（FAISS + 图存储） |
| `/qa` | `qa.py` | GraphRAG 问答（hybrid 多路检索，流式/非流式） |
| `/chat` | `chat_memory.py` | 会话和消息管理 |
