# 研发效能AI Agent平台 - 项目架构

## 一、系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│                    (API / Chat / Dashboard)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Server                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Chat API    │  │  Agent API   │  │ Metrics API │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Agent Core Engine                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐ │
│  │ Intention │  │  Task      │  │  Execute   │  │ Reflect │ │
│  │ Recognition│  │  Decompose │  │  Engine    │  │  & Retry│ │
│  └────────────┘  └────────────┘  └────────────┘  └─────────┘ │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  Memory   │  │  Context   │  │  Tool      │               │
│  │  Manager   │  │  Manager   │  │  Registry  │               │
│  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────┘
         │                                           │
         ▼                                           ▼
┌─────────────────┐                    ┌─────────────────────────┐
│   Retrieval     │                    │   Tool Adapters         │
│  (RAG + BM25)  │                    │  ┌─────────┐ ┌────────┐ │
│  ┌───────────┐ │                    │  │  Jira   │ │ GitHub │ │
│  │ Vector DB │ │                    │  └─────────┘ └────────┘ │
│  │ (Chroma)  │ │                    │  ┌─────────┐ ┌────────┐ │
│  └───────────┘ │                    │  │  CI/CD  │ │ Custom │ │
│  ┌───────────┐ │                    │  └─────────┘ └────────┘ │
│  │  BM25     │ │                    └─────────────────────────┘
│  └───────────┘ │
└─────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Observation Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Tracing      │  │  Metrics     │  │  Logging     │          │
│  │ (Full Chain) │  │  (Prometheus)│  │  (Structured)│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                         │                                        │
│                         ▼                                        │
│                  ┌──────────────┐                                │
│                  │  Grafana     │                                │
│                  │  Dashboard   │                                │
│                  └──────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

## 二、模块职责

### 2.1 Agent Core Engine
| 模块 | 职责 | 核心技术 |
|------|------|----------|
| Intention Recognition | 意图识别与澄清 | Prompt Engineering + LLM |
| Task Decompose | 任务自动拆解 | CoT + 规划算法 |
| Execute Engine | 任务执行与工具调用 | 动态工具调度 |
| Reflect & Retry | 反思纠错与自愈 | 结果校验 + 重试机制 |

### 2.2 Memory Manager
| 模块 | 职责 | 核心技术 |
|------|------|----------|
| Short-term Memory | 对话上下文窗口 | Token管理 + 滑动窗口 |
| Long-term Memory | 项目知识持久化 | SQLite + 向量存储 |

### 2.3 Context Manager
| 模块 | 职责 | 核心技术 |
|------|------|----------|
| Context Injection | 上下文注入优化 | 重要性排序 + 压缩 |
| Context Selection | 上下文选择 | RRF + BM25混排 |

### 2.4 Tool Registry
| 模块 | 职责 | 核心技术 |
|------|------|----------|
| Tool Definition | 工具定义注册 | 标准化Schema |
| Tool Dispatch | 工具动态调度 | 串行/并行/条件 |

### 2.5 Retrieval (RAG)
| 模块 | 职责 | 核心技术 |
|------|------|----------|
| Vector Search | 向量检索 | ChromaDB + Embedding |
| BM25 Search | 关键词检索 | rank-bm25 |
| Rerank | 重排序 | RRF算法 |

## 三、数据流

```
User Input
    │
    ▼
┌─────────┐    ┌─────────────┐    ┌─────────────┐
│ Parse   │───▶│ Intention    │───▶│ Task        │
│ Intent  │    │ Recognition  │    │ Decompose   │
└─────────┘    └─────────────┘    └─────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │ Tool Selection  │
                               │ & Ordering      │
                               └─────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
             ┌────────────┐      ┌────────────┐      ┌────────────┐
             │ Execute    │      │ Execute    │      │ Execute    │
             │ Tool 1     │      │ Tool 2     │      │ Tool 3     │
             └────────────┘      └────────────┘      └────────────┘
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        ▼
                               ┌─────────────────┐
                               │ Result Merge    │
                               │ & Validation    │
                               └─────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │ Reflect         │
                               │ (Self-Correction)│
                               └─────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │ Response Gen    │
                               │ + Memory Store  │
                               └─────────────────┘
```

## 四、技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI + Uvicorn | 异步高性能 |
| Agent框架 | LangChain | Agent抽象 |
| 大模型 | OpenAI / 豆包 / 通义 | 可切换 |
| 向量数据库 | ChromaDB | 本地轻量 |
| 全文检索 | BM25 (rank-bm25) | 关键词召回 |
| 数据库 | SQLite | 免部署 |
| 缓存 | Redis | 记忆/队列 |
| 监控 | Prometheus + Grafana | 可观测性 |

## 五、13项核心技术点映射

| # | 核心技术点 | 对应模块 | 实现位置 |
|---|-----------|----------|----------|
| 1 | Agent核心执行闭环 | Agent Core | app/agents/core.py |
| 2 | 多系统交互 | Tool Adapters | app/tools/*.py |
| 3 | 意图识别与澄清 | Intention | app/agents/intention.py |
| 4 | 任务自动拆解 | Task Decompose | app/agents/decompose.py |
| 5 | 反思纠错与自愈 | Reflect | app/agents/reflect.py |
| 6 | 记忆管理 | Memory | app/memory/manager.py |
| 7 | 上下文优化 | Context | app/memory/context.py |
| 8 | RAG + 向量召回 | Retrieval | app/retrieval/*.py |
| 9 | CoT + 自洽推理 | Reasoning | app/agents/reasoning.py |
| 10 | 工具编排引擎 | Tool Registry | app/tools/registry.py |
| 11 | 安全防护 | Security | app/agents/security.py |
| 12 | 全链路观测 | Observation | app/observation/*.py |
| 13 | 多智能体协同 | Multi-Agent | app/agents/multi_agent.py |
