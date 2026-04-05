# 研发效能AI Agent平台

## 项目简介
个人简历向研发效能领域专属AI Agent平台，核心聚焦Agent全栈技术能力。

## 技术栈
- **后端**: Python 3.10+ / FastAPI / Uvicorn
- **AI框架**: LangChain
- **向量库**: ChromaDB
- **存储**: SQLite + Redis
- **监控**: Prometheus + Grafana

## 快速启动

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入你的API密钥
```

### 3. 启动服务
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. 访问API文档
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构
```
devops-agent/
├── app/
│   ├── main.py           # FastAPI入口
│   ├── config.py         # 配置管理
│   ├── agents/           # Agent核心模块
│   ├── tools/             # 工具调用
│   ├── memory/            # 记忆管理
│   ├── retrieval/         # 检索增强
│   ├── evaluation/        # 评测体系
│   └── observation/       # 观测体系
├── tests/                # 测试用例
└── data/                 # 数据存储
```

## 核心能力
1. Agent核心执行闭环
2. 多系统交互
3. 意图识别
4. 任务拆解
5. 反思纠错
6. 记忆管理
7. 上下文优化
8. RAG检索
9. 推理策略
10. 工具编排
11. 安全防护
12. 全链路观测
13. 多智能体协同

## License
MIT
