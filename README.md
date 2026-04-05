# 研发效能AI Agent平台

## 项目概述
面向研发效能领域的AI Agent平台，实现缺陷分析、代码评审、CI/CD监控等场景的智能化辅助。

## 技术栈
Python / FastAPI / LangChain / ChromaDB / SQLite / GitHub API

## 核心能力（已全部实现）

### 1. Agent核心执行闭环
实现"意图识别 → 任务拆解 → 工具执行 → 反思纠错"的完整闭环，支持串行/并行/条件分支执行策略。

### 2. 多系统交互
封装GitHub Issues/PRs/Actions API，支持Jira、飞书等企业系统扩展。

### 3. RAG检索增强
基于ChromaDB向量检索+BM25关键词检索，采用RRF算法混合排序，上下文字符级别压缩优化。

### 4. 全链路可观测性
集成Prometheus metrics，实现执行Trace追踪与多维归因分析。

### 5. 自动化评测体系
20+测试用例覆盖核心意图场景，支持效果回测与版本对比。

### 6. 高并发优化
基于asyncio异步处理，支持工具并行执行与超时控制。

### 7. 记忆管理与推理
Context级别压缩优化，LRU淘汰策略，支持多轮对话上下文记忆。

### 8. Context工程
Prompt模板版本化管理，变量校验与渲染，支持动态注入。

### 9. 安全防护
集成输入安全校验、Prompt注入检测、敏感词过滤机制。

### 10. 多智能体编排
专用单Agent协同调度，支持跨场景复杂任务自动分解。

### 11. 版本化管理
任务执行结果版本化记录，支持历史回溯与效果对比。

### 12. 工具编排
动态工具注册与调用，支持条件分支与循环执行。

### 13. 监控日志
全链路日志追踪，Prometheus+Grafana可视化监控。

## 已接入数据源
- GitHub Issues（缺陷管理）
- GitHub Pull Requests（代码评审）
- GitHub Actions（CI/CD监控）

## 快速启动
```bash
pip install -r requirements.txt
cp .env.example .env  # 填入GitHub Token
python -m uvicorn app.main:app --port 8000
```
