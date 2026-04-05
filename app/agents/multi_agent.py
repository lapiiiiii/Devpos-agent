from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    BUG_ANALYZER = "bug_analyzer"
    CODE_REVIEWER = "code_reviewer"
    CI_CD_MONITOR = "ci_cd_monitor"
    EFFICIENCY_REPORTER = "efficiency_reporter"
    GENERAL = "general"


@dataclass
class AgentSpec:
    agent_type: AgentType
    name: str
    description: str
    capabilities: List[str]
    tools: List[str]
    specialized_intents: List[str]


class SingleAgent:
    def __init__(
        self,
        agent_spec: AgentSpec,
        agent_core,
        memory_manager=None,
    ):
        self.spec = agent_spec
        self.agent_core = agent_core
        self.memory_manager = memory_manager
        self._is_busy = False

    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self._is_busy = True
        try:
            result = await self.agent_core.run(
                user_input=task.get("user_input", ""),
                session_id=task.get("session_id", ""),
            )
            return {
                "agent_type": self.spec.agent_type.value,
                "agent_name": self.spec.name,
                "success": result.get("success", False),
                "result": result.get("result"),
                "intent": result.get("intent"),
            }
        except Exception as e:
            logger.error(f"Agent {self.spec.name} execution error: {e}")
            return {
                "agent_type": self.spec.agent_type.value,
                "agent_name": self.spec.name,
                "success": False,
                "error": str(e),
            }
        finally:
            self._is_busy = False

    def can_handle(self, intent: str) -> bool:
        return intent in self.spec.specialized_intents

    @property
    def is_busy(self) -> bool:
        return self._is_busy


class MultiAgentOrchestrator:
    def __init__(self):
        self._agents: Dict[AgentType, SingleAgent] = {}
        self._agent_registry: Dict[str, AgentType] = {}

    def register_agent(self, agent: SingleAgent):
        self._agents[agent.spec.agent_type] = agent
        for intent in agent.spec.specialized_intents:
            self._agent_registry[intent] = agent.spec.agent_type
        logger.info(f"Registered agent: {agent.spec.name} for intents: {agent.spec.specialized_intents}")

    def get_agent_for_intent(self, intent: str) -> Optional[SingleAgent]:
        agent_type = self._agent_registry.get(intent)
        if agent_type:
            return self._agents.get(agent_type)
        return None

    def get_all_agents(self) -> List[SingleAgent]:
        return list(self._agents.values())

    async def orchestrate_single(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        intent = task.get("intent", "")
        agent = self.get_agent_for_intent(intent)

        if not agent:
            logger.warning(f"No specialized agent found for intent: {intent}, using general agent")
            general_agent = self._agents.get(AgentType.GENERAL)
            if general_agent:
                agent = general_agent
            else:
                return {"success": False, "error": "No agent available for this intent"}

        return await agent.execute(task, context)

    async def orchestrate_multi(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        sub_tasks = task.get("sub_tasks", [])
        if not sub_tasks:
            return await self.orchestrate_single(task, context)

        results = []
        for sub_task in sub_tasks:
            agent = self.get_agent_for_intent(sub_task.get("intent", ""))
            if agent:
                result = await agent.execute(sub_task, context)
                results.append(result)

        return {
            "success": all(r.get("success", False) for r in results),
            "results": results,
            "total_agents_used": len(set(r.get("agent_type") for r in results)),
        }

    async def orchestrate_parallel(
        self, tasks: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        async def execute_task(task):
            return await self.orchestrate_single(task, context)

        results = await asyncio.gather(
            *[execute_task(t) for t in tasks],
            return_exceptions=True
        )

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "task": tasks[i],
                    "success": False,
                    "error": str(result),
                })
            else:
                processed_results.append(result)

        return {
            "success": all(r.get("success", False) for r in processed_results),
            "results": processed_results,
            "total_tasks": len(tasks),
            "succeeded": sum(1 for r in processed_results if r.get("success")),
        }


def create_default_agents(agent_core_factory) -> List[SingleAgent]:
    agent_specs = [
        AgentSpec(
            agent_type=AgentType.BUG_ANALYZER,
            name="Bug分析Agent",
            description="专门处理缺陷分析、Bug统计相关任务",
            capabilities=["缺陷分析", "Bug统计", "根因定位"],
            tools=["jira_get_bugs", "jira_get_issue", "github_get_issues"],
            specialized_intents=["bug统计", "缺陷分析", "缺陷详情"],
        ),
        AgentSpec(
            agent_type=AgentType.CODE_REVIEWER,
            name="代码评审Agent",
            description="专门处理代码评审、PR分析相关任务",
            capabilities=["CodeReview", "PR分析", "代码质量评估"],
            tools=["github_get_pulls", "github_get_commits"],
            specialized_intents=["代码评审", "PR列表", "PR详情"],
        ),
        AgentSpec(
            agent_type=AgentType.CI_CD_MONITOR,
            name="CI/CD监控Agent",
            description="专门处理CI/CD构建监控、异常排查任务",
            capabilities=["构建监控", "失败分析", "效能指标"],
            tools=["cicd_get_build_history", "cicd_get_workflow_logs", "cicd_get_metrics"],
            specialized_intents=["构建查询", "构建分析", "效能指标", "触发构建"],
        ),
        AgentSpec(
            agent_type=AgentType.EFFICIENCY_REPORTER,
            name="效能报表Agent",
            description="专门处理研发效能报表生成任务",
            capabilities=["效能分析", "报表生成", "数据统计"],
            tools=["cicd_get_metrics", "github_get_commits", "github_get_pulls"],
            specialized_intents=["效能报表", "交付周期", "贡献统计"],
        ),
        AgentSpec(
            agent_type=AgentType.GENERAL,
            name="通用Agent",
            description="处理通用任务的默认Agent",
            capabilities=["通用问答", "知识查询", "任务协作"],
            tools=["retrieval_search"],
            specialized_intents=["知识问答", "故障排查", "任务创建", "状态更新"],
        ),
    ]

    agents = []
    for spec in agent_specs:
        agent_core = agent_core_factory()
        agent = SingleAgent(agent_spec=spec, agent_core=agent_core)
        agents.append(agent)

    return agents
