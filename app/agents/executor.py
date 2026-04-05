from typing import Dict, List, Any, Optional, Callable
import asyncio
import logging
from datetime import datetime

from app.tools.registry import tool_registry, ToolDefinition
from app.tools.github_client import GitHubClient
from app.tools.jira_client import JiraClient
from app.tools.cicd_client import CICDClient

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._github_client: Optional[GitHubClient] = None
        self._jira_client: Optional[JiraClient] = None
        self._cicd_client: Optional[CICDClient] = None
        self._initialize_tools()

    def _initialize_tools(self):
        self._tools["jira_get_issues"] = self._jira_get_issues
        self._tools["jira_get_bugs"] = self._jira_get_bugs
        self._tools["jira_get_issue"] = self._jira_get_issue
        self._tools["github_get_issues"] = self._github_get_issues
        self._tools["github_get_commits"] = self._github_get_commits
        self._tools["github_get_pulls"] = self._github_get_pulls
        self._tools["github_get_workflow_runs"] = self._github_get_workflow_runs
        self._tools["github_scan_pr_security"] = self._github_scan_pr_security
        self._tools["github_get_pr_diff"] = self._github_get_pr_diff
        self._tools["cicd_get_build_history"] = self._cicd_get_build_history
        self._tools["cicd_get_workflow_logs"] = self._cicd_get_workflow_logs
        self._tools["cicd_get_metrics"] = self._cicd_get_metrics
        self._tools["cicd_trigger_workflow"] = self._cicd_trigger_workflow
        logger.info(f"Initialized {len(self._tools)} tools")

    def set_clients(
        self,
        github_client: GitHubClient,
        jira_client: JiraClient,
        cicd_client: CICDClient,
    ):
        self._github_client = github_client
        self._jira_client = jira_client
        self._cicd_client = cicd_client

    async def execute(self, task: Dict[str, Any], context: Any) -> Dict[str, Any]:
        tool_name = task.get("tool", "unknown")
        task_id = task.get("id", 0)
        description = task.get("description", "")

        logger.info(f"Executing task {task_id}: {description} using {tool_name}")

        start_time = datetime.utcnow()
        try:
            if tool_name in self._tools:
                result = await self._execute_tool(tool_name, task)
            else:
                result = await self._execute_default(task)

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Task {task_id} completed in {duration:.2f}s")

            return {
                "task_id": task_id,
                "tool": tool_name,
                "success": True,
                "result": result,
                "duration_seconds": duration,
            }

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Task {task_id} failed: {str(e)}")
            return {
                "task_id": task_id,
                "tool": tool_name,
                "success": False,
                "error": str(e),
                "duration_seconds": duration,
            }

    async def _execute_tool(self, tool_name: str, task: Dict[str, Any]) -> Any:
        tool_func = self._tools.get(tool_name)
        if tool_func:
            return await tool_func(task)
        return {"error": f"Tool {tool_name} not implemented"}

    async def _execute_default(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "message": "Default execution",
            "task": task.get("description"),
            "status": "simulated",
        }

    async def _jira_get_issues(self, task: Dict[str, Any]) -> List[Dict]:
        if self._jira_client:
            return await self._jira_client.get_issues(
                project=task.get("params", {}).get("project"),
                status=task.get("params", {}).get("status"),
                limit=task.get("params", {}).get("limit", 50),
            )
        return [{"mock": "jira issues data"}]

    async def _jira_get_bugs(self, task: Dict[str, Any]) -> List[Dict]:
        if self._jira_client:
            return await self._jira_client.get_bugs(
                project=task.get("params", {}).get("project"),
                limit=task.get("params", {}).get("limit", 50),
            )
        return [{"mock": "jira bugs data"}]

    async def _jira_get_issue(self, task: Dict[str, Any]) -> Optional[Dict]:
        if self._jira_client:
            key = task.get("params", {}).get("key", "PROJ-101")
            return await self._jira_client.get_issue_by_key(key)
        return {"mock": "jira issue detail"}

    async def _github_get_issues(self, task: Dict[str, Any]) -> List[Dict]:
        if self._github_client:
            return await self._github_client.get_issues(
                state=task.get("params", {}).get("state", "all"),
                limit=task.get("params", {}).get("limit", 50),
            )
        return [{"mock": "github issues data"}]

    async def _github_get_commits(self, task: Dict[str, Any]) -> List[Dict]:
        if self._github_client:
            return await self._github_client.get_commits(
                limit=task.get("params", {}).get("limit", 50),
            )
        return [{"mock": "github commits data"}]

    async def _github_get_pulls(self, task: Dict[str, Any]) -> List[Dict]:
        if self._github_client:
            return await self._github_client.get_pulls(
                state=task.get("params", {}).get("state", "open"),
                limit=task.get("params", {}).get("limit", 50),
            )
        return [{"mock": "github pulls data"}]

    async def _github_get_workflow_runs(self, task: Dict[str, Any]) -> List[Dict]:
        if self._github_client:
            return await self._github_client.get_workflow_runs(
                limit=task.get("params", {}).get("limit", 30),
            )
        return [{"mock": "github workflow runs data"}]

    async def _github_scan_pr_security(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if self._github_client:
            pr_number = task.get("params", {}).get("pr_number", 1)
            return await self._github_client.scan_pr_security(pr_number)
        return {
            "pr_number": 1,
            "total_findings": 3,
            "risk_level": "high",
            "findings": [
                {"type": "API_Token", "matched": "sk-1234567890abcdef", "context": "...API_KEY = \"sk-1234567890abcdef\"..."},
                {"type": "密码", "matched": "password123", "context": "...password = \"admin123\"..."},
                {"type": "手机号", "matched": "13800138000", "context": "...phone = \"13800138000\"..."},
            ],
        }

    async def _github_get_pr_diff(self, task: Dict[str, Any]) -> str:
        if self._github_client:
            pr_number = task.get("params", {}).get("pr_number", 1)
            return await self._github_client.get_pr_diff(pr_number)
        return "Mock PR diff content..."

    async def _cicd_get_build_history(self, task: Dict[str, Any]) -> List[Dict]:
        if self._cicd_client:
            return await self._cicd_client.get_build_history(
                repo=task.get("params", {}).get("repo", "default"),
                branch=task.get("params", {}).get("branch"),
                limit=task.get("params", {}).get("limit", 30),
            )
        return [{"mock": "ci/cd build history data"}]

    async def _cicd_get_workflow_logs(self, task: Dict[str, Any]) -> str:
        if self._cicd_client:
            run_id = task.get("params", {}).get("run_id", 0)
            repo = task.get("params", {}).get("repo", "default")
            return await self._cicd_client.get_workflow_logs(repo, run_id)
        return "Mock workflow logs..."

    async def _cicd_get_metrics(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if self._cicd_client:
            return await self._cicd_client.get_build_metrics(
                repo=task.get("params", {}).get("repo", "default"),
                days=task.get("params", {}).get("days", 7),
            )
        return {"mock": "ci/cd metrics data"}

    async def _cicd_trigger_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if self._cicd_client:
            return await self._cicd_client.trigger_workflow(
                repo=task.get("params", {}).get("repo", "default"),
                workflow_name=task.get("params", {}).get("workflow_name", "CI"),
                inputs=task.get("params", {}).get("inputs"),
            )
        return {"mock": "workflow triggered"}


class ParallelExecutor:
    @staticmethod
    async def execute_parallel(tasks: List[Dict[str, Any]], executor: ToolExecutor, context: Any) -> List[Dict[str, Any]]:
        task_coroutines = [executor.execute(task, context) for task in tasks]
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "task_id": tasks[i].get("id", i),
                    "tool": tasks[i].get("tool", "unknown"),
                    "success": False,
                    "error": str(result),
                })
            else:
                processed_results.append(result)

        return processed_results
