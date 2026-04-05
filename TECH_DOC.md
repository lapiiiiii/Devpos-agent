# 研发效能AI Agent平台 - 技术文档

## 一、项目概述

### 1.1 项目定位
个人简历向研发效能领域专属AI Agent平台，核心聚焦Agent全栈技术能力。

### 1.2 核心目标
- 4周完成MVP版本，6周完成完整版本
- 可本地运行、可演示、可写进简历
- 覆盖13项Agent核心技术点

## 二、技术架构

### 2.1 技术栈
| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI + Uvicorn | 异步高性能API |
| Agent框架 | LangChain | Agent抽象与编排 |
| 大模型 | OpenAI/豆包/通义 | 可切换 |
| 向量数据库 | ChromaDB | 本地轻量RAG |
| 全文检索 | BM25 | 关键词召回 |
| 数据库 | SQLite | 免部署 |
| 缓存 | Redis | 记忆/队列 |
| 监控 | Prometheus + Grafana | 可观测性 |

### 2.2 系统架构
```
用户 -> FastAPI -> Agent Core Engine -> 工具层
                                    -> 检索层
                                    -> 记忆层
                                    -> 观测层
```

## 三、核心模块

### 3.1 Agent核心引擎
- **意图识别**: 基于规则+LLM的混合识别
- **任务拆解**: 结构化任务分解与规划
- **执行引擎**: 工具动态调度与并行执行
- **反思纠错**: 结果校验与自愈机制

### 3.2 工具系统
- **Jira客户端**: 缺陷数据拉取
- **GitHub客户端**: 代码、PR、提交查询
- **CI/CD客户端**: 构建历史与日志

### 3.3 检索增强
- **向量检索**: ChromaDB + Embedding
- **BM25检索**: 关键词精准召回
- **混合搜索**: RRF重排序

### 3.4 记忆管理
- **短期记忆**: 对话上下文窗口
- **长期记忆**: 项目知识持久化

### 3.5 安全模块
- **输入校验**: Prompt注入检测
- **幻觉防护**: 检索增强+事实校验
- **敏感信息过滤**: API密钥等保护

## 四、13项核心技术点

| # | 核心技术点 | 实现模块 | 技术细节 |
|---|-----------|----------|----------|
| 1 | Agent核心闭环 | agents/core.py | 意图-拆解-执行-反思 |
| 2 | 多系统交互 | tools/*.py | Jira/GitHub/CICD SDK |
| 3 | 意图识别 | agents/intention.py | 规则+LLM混合 |
| 4 | 任务拆解 | agents/decompose.py | 结构化分解 |
| 5 | 反思纠错 | agents/reflect.py | 校验+重试 |
| 6 | 记忆管理 | memory/manager.py | 短期+长期 |
| 7 | 上下文优化 | memory/context.py | 压缩+注入 |
| 8 | RAG检索 | retrieval/*.py | 向量+BM25 |
| 9 | 推理策略 | agents/reasoning.py | CoT+自洽 |
| 10 | 工具编排 | agents/reasoning.py | 串行/并行/条件 |
| 11 | 安全防护 | agents/security.py | 注入+幻觉 |
| 12 | 全链路观测 | observation/*.py | Trace+Metrics |
| 13 | 多智能体 | agents/multi_agent.py | 专用Agent调度 |

## 五、API接口

### 5.1 聊天接口
```
POST /api/v1/chat
{
    "message": "本周新增了多少Bug？",
    "session_id": "optional-session-id"
}
```

### 5.2 意图列表
```
GET /api/v1/intents
```

### 5.3 工具列表
```
GET /api/v1/tools
```

## 六、部署说明

### 6.1 环境要求
- Python 3.10+
- Windows/Linux/macOS

### 6.2 启动方式
```bash
# 方式1: 使用启动脚本 (Windows)
start.bat

# 方式2: 命令行
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 6.3 访问地址
- API服务: http://localhost:8000
- Swagger文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc

## 七、效果指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 意图识别准确率 | ≥90% | 核心意图正确识别 |
| 幻觉率 | ≤5% | 大模型虚假输出 |
| 任务完成率 | ≥85% | 成功完成用户任务 |

## 八、面试亮点

1. **Agent全栈能力**: 从意图识别到执行闭环的完整链路
2. **RAG检索增强**: 混合搜索+重排序提升召回质量
3. **反思自愈机制**: 结果校验+智能重试提升准确性
4. **多智能体协作**: 专用Agent分工+协同处理复杂任务
5. **全链路可观测**: Trace+Metrics+归因分析
6. **工程化落地**: FastAPI异步+工具编排+安全防护
