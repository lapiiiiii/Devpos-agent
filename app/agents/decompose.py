from typing import Dict, List, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class TaskDecomposer:
    def __init__(self, llm=None):
        self.llm = llm
        self._intent_to_tools = {
            "bug统计": ["jira_get_bugs", "github_get_issues"],
            "缺陷分析": ["jira_get_bugs", "jira_get_issue", "github_get_commits"],
            "缺陷详情": ["jira_get_issue"],
            "代码评审": ["github_get_pulls", "github_get_commits"],
            "构建查询": ["cicd_get_build_history"],
            "构建分析": ["cicd_get_build_history", "cicd_get_workflow_logs"],
            "效能指标": ["cicd_get_metrics"],
            "触发构建": ["cicd_trigger_workflow"],
            "效能报表": ["cicd_get_metrics", "github_get_commits", "github_get_pulls"],
            "交付周期": ["jira_get_issues", "cicd_get_metrics"],
            "贡献统计": ["github_get_commits"],
            "知识问答": ["retrieval_search"],
            "故障排查": ["jira_get_issues", "cicd_get_build_history"],
            "任务创建": ["jira_create_issue"],
            "状态更新": ["jira_update_issue"],
        }

    async def decompose(self, user_input: str, intent: str) -> Dict[str, Any]:
        if self._intent_to_tools.get(intent):
            return self._structured_decompose(user_input, intent)

        if self.llm:
            try:
                return await self._llm_decompose(user_input, intent)
            except Exception as e:
                logger.warning(f"LLM decompose failed: {e}")

        return self._simple_decompose(user_input)

    def _structured_decompose(self, user_input: str, intent: str) -> Dict[str, Any]:
        tools = self._intent_to_tools.get(intent, [])

        subtasks = []
        for i, tool in enumerate(tools, 1):
            subtask = {
                "id": i,
                "description": f"使用{tool}获取数据",
                "tool": tool,
                "depends_on": [],
                "can_parallel": False,
                "complexity": "low",
            }
            subtasks.append(subtask)

        parallel_groups = self._identify_parallel_tasks(subtasks)
        execution_plan = self._generate_execution_plan(parallel_groups)

        return {
            "main_task": user_input,
            "intent": intent,
            "subtasks": subtasks,
            "parallel_groups": parallel_groups,
            "execution_plan": execution_plan,
        }

    def _identify_parallel_tasks(self, subtasks: List[Dict]) -> List[List[int]]:
        parallel_groups = []
        current_group = []

        for task in subtasks:
            if task.get("can_parallel") and current_group:
                parallel_groups.append([t["id"] for t in current_group])
                current_group = []
            current_group.append(task)

        if current_group:
            parallel_groups.append([t["id"] for t in current_group])

        return parallel_groups

    def _generate_execution_plan(self, parallel_groups: List[List[int]]) -> str:
        if len(parallel_groups) == 1:
            return f"并行执行任务组: {parallel_groups[0]}"
        plan = "串行执行各任务组:\n"
        for i, group in enumerate(parallel_groups, 1):
            plan += f"  阶段{i}: {'并行' if len(group) > 1 else '单独'}执行 {group}\n"
        return plan

    async def _llm_decompose(self, user_input: str, intent: str) -> Dict[str, Any]:
        prompt = f"""将以下任务拆分为可执行的子任务。

任务：{user_input}
识别到的意图：{intent}

请以JSON格式输出：
{{
    "main_task": "主任务描述",
    "subtasks": [
        {{
            "id": 1,
            "description": "子任务描述",
            "tool": "需要的工具名称",
            "depends_on": [],
            "can_parallel": false,
            "complexity": "low/medium/high"
        }}
    ],
    "execution_plan": "执行计划说明"
}}
"""

        response = await self.llm.agenerate([prompt])
        if response and response.generations:
            result_text = response.generations[0][0].text.strip()
            try:
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                return json.loads(result_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {result_text}")
        return self._simple_decompose(user_input)

    def _simple_decompose(self, user_input: str) -> Dict[str, Any]:
        return {
            "main_task": user_input,
            "subtasks": [
                {
                    "id": 1,
                    "description": user_input,
                    "tool": "default_tool",
                    "depends_on": [],
                    "can_parallel": False,
                    "complexity": "medium",
                }
            ],
            "execution_plan": "单一任务执行",
        }
