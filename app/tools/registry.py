from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolType(Enum):
    JIRA = "jira"
    GITHUB = "github"
    CICD = "cicd"
    RETRIEVAL = "retrieval"
    CUSTOM = "custom"


@dataclass
class ToolDefinition:
    name: str
    description: str
    tool_type: ToolType
    parameters: Dict[str, Any] = field(default_factory=dict)
    function: Optional[Callable] = None


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._intent_mappings: Dict[str, List[str]] = {}

    def register(
        self,
        name: str,
        description: str,
        tool_type: ToolType,
        parameters: Optional[Dict[str, Any]] = None,
        function: Optional[Callable] = None,
    ):
        tool_def = ToolDefinition(
            name=name,
            description=description,
            tool_type=tool_type,
            parameters=parameters or {},
            function=function,
        )
        self._tools[name] = tool_def
        logger.info(f"Registered tool: {name} ({tool_type.value})")

    def register_intent_mapping(self, intent: str, tools: List[str]):
        self._intent_mappings[intent] = tools
        logger.debug(f"Mapped intent '{intent}' to tools: {tools}")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def get_tools_for_intent(self, intent: str) -> List[ToolDefinition]:
        tool_names = self._intent_mappings.get(intent, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def list_intents(self) -> List[str]:
        return list(self._intent_mappings.keys())


tool_registry = ToolRegistry()


def register_default_tools():
    tool_registry.register(
        name="github_get_issues",
        description="Get GitHub issues with optional state filter (open/closed/all)",
        tool_type=ToolType.GITHUB,
        parameters={"state": "open", "limit": 50},
    )

    tool_registry.register(
        name="github_get_commits",
        description="Get recent commits from GitHub repository",
        tool_type=ToolType.GITHUB,
        parameters={"limit": 50},
    )

    tool_registry.register(
        name="github_get_pulls",
        description="Get GitHub pull requests with optional state filter",
        tool_type=ToolType.GITHUB,
        parameters={"state": "open", "limit": 50},
    )

    tool_registry.register(
        name="github_get_workflow_runs",
        description="Get GitHub Actions workflow runs",
        tool_type=ToolType.GITHUB,
        parameters={"limit": 30},
    )

    tool_registry.register(
        name="jira_get_issues",
        description="Get Jira issues with optional project and status filters",
        tool_type=ToolType.JIRA,
        parameters={"project": None, "status": None, "limit": 50},
    )

    tool_registry.register(
        name="jira_get_bugs",
        description="Get Jira bugs, optionally filtered by project",
        tool_type=ToolType.JIRA,
        parameters={"project": None, "limit": 50},
    )

    tool_registry.register(
        name="jira_get_issue",
        description="Get a specific Jira issue by key (e.g., PROJ-101)",
        tool_type=ToolType.JIRA,
        parameters={"key": "required"},
    )

    tool_registry.register(
        name="cicd_get_build_history",
        description="Get CI/CD build history with optional branch filter",
        tool_type=ToolType.CICD,
        parameters={"branch": None, "limit": 30},
    )

    tool_registry.register(
        name="cicd_get_workflow_logs",
        description="Get detailed logs for a specific CI/CD workflow run",
        tool_type=ToolType.CICD,
        parameters={"run_id": "required"},
    )

    tool_registry.register(
        name="cicd_get_metrics",
        description="Get CI/CD build metrics for the past N days",
        tool_type=ToolType.CICD,
        parameters={"days": 7},
    )

    tool_registry.register_intent_mapping("bug统计", ["jira_get_bugs", "github_get_issues"])
    tool_registry.register_intent_mapping("代码评审", ["github_get_pulls"])
    tool_registry.register_intent_mapping("构建查询", ["cicd_get_build_history", "cicd_get_metrics"])
    tool_registry.register_intent_mapping("缺陷分析", ["jira_get_bugs", "jira_get_issue"])
    tool_registry.register_intent_mapping("效能报表", ["cicd_get_metrics", "github_get_commits"])

    logger.info("Default tools registered successfully")


register_default_tools()
