from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    CHAIN_OF_THOUGHT = "cot"
    SELF_CONSISTENCY = "self_consistency"
    TREE_OF_THOUGHT = "tree_of_thought"
    DIRECT = "direct"


class ReasoningEngine:
    def __init__(self, llm=None):
        self.llm = llm
        self._reasoning_templates = {
            ReasoningType.CHAIN_OF_THOUGHT: self._cot_template,
            ReasoningType.SELF_CONSISTENCY: self._self_consistency_template,
            ReasoningType.TREE_OF_THOUGHT: self._tree_of_thought_template,
        }

    async def reason(
        self,
        problem: str,
        reasoning_type: ReasoningType = ReasoningType.CHAIN_OF_THOUGHT,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        template_func = self._reasoning_templates.get(
            reasoning_type, self._direct_reasoning
        )

        result = await template_func(problem, context or {})

        return {
            "reasoning_type": reasoning_type.value,
            "problem": problem,
            "result": result,
            "steps": result.get("steps", []),
            "conclusion": result.get("conclusion", ""),
        }

    async def _cot_template(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        steps = []

        step1 = {
            "step": 1,
            "thought": "理解问题",
            "action": f"分析用户需求: {problem}",
            "reasoning": "首先明确用户想要什么，这有助于后续分解任务",
        }
        steps.append(step1)

        step2 = {
            "step": 2,
            "thought": "任务分解",
            "action": "将复杂任务拆分为子任务",
            "reasoning": "分而治之可以更高效地处理复杂问题",
        }
        steps.append(step2)

        step3 = {
            "step": 3,
            "thought": "执行验证",
            "action": "执行每个子任务并验证结果",
            "reasoning": "确保每一步都正确执行",
        }
        steps.append(step3)

        step4 = {
            "step": 4,
            "thought": "整合结果",
            "action": "汇总所有子任务结果",
            "reasoning": "提供完整的答案给用户",
        }
        steps.append(step4)

        return {
            "steps": steps,
            "conclusion": f"通过Chain of Thought推理完成: {problem}",
        }

    async def _self_consistency_template(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        reasoning_paths = []

        for i in range(3):
            path = {
                "path_id": i + 1,
                "reasoning": f"推理路径 {i + 1}: 先理解问题，再分解任务，最后执行",
                "answer": f"基于路径 {i + 1} 的答案",
            }
            reasoning_paths.append(path)

        consensus = self._find_consensus([p["answer"] for p in reasoning_paths])

        return {
            "steps": reasoning_paths,
            "conclusion": consensus,
            "consistency_score": 0.85,
        }

    async def _tree_of_thought_template(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        branches = [
            {
                "branch": "分支A",
                "thought": "从缺陷分析角度出发",
                "action": "查询Jira缺陷数据",
            },
            {
                "branch": "分支B",
                "thought": "从代码变更角度出发",
                "action": "查询Git提交记录",
            },
            {
                "branch": "分支C",
                "thought": "从CI/CD角度出发",
                "action": "查询构建历史",
            },
        ]

        return {
            "steps": branches,
            "conclusion": f"通过Tree of Thought展开多个推理分支分析: {problem}",
        }

    async def _direct_reasoning(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "steps": [{"step": 1, "thought": "直接推理", "action": problem}],
            "conclusion": problem,
        }

    def _find_consensus(self, answers: List[str]) -> str:
        from collections import Counter
        counter = Counter(answers)
        return counter.most_common(1)[0][0]


class ToolOrchestrator:
    def __init__(self, executor=None):
        self.executor = executor
        self._orchestration_strategies = {
            "sequential": self._sequential_execute,
            "parallel": self._parallel_execute,
            "conditional": self._conditional_execute,
            "pipeline": self._pipeline_execute,
        }

    async def orchestrate(
        self,
        tasks: List[Dict[str, Any]],
        strategy: str = "sequential",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        strategy_func = self._orchestration_strategies.get(
            strategy, self._sequential_execute
        )

        return await strategy_func(tasks, context or {})

    async def _sequential_execute(
        self, tasks: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        results = []
        for task in tasks:
            result = await self.executor.execute(task, context)
            results.append(result)
            if not result.get("success", False):
                logger.warning(f"Task {task.get('id')} failed, continuing...")

        return {
            "strategy": "sequential",
            "results": results,
            "total_tasks": len(tasks),
            "successful": sum(1 for r in results if r.get("success")),
        }

    async def _parallel_execute(
        self, tasks: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        import asyncio

        coroutines = [self.executor.execute(task, context) for task in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {"task_id": tasks[i].get("id"), "success": False, "error": str(result)}
                )
            else:
                processed_results.append(result)

        return {
            "strategy": "parallel",
            "results": processed_results,
            "total_tasks": len(tasks),
            "successful": sum(1 for r in processed_results if r.get("success")),
        }

    async def _conditional_execute(
        self, tasks: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        results = []
        condition_results = {}

        for task in tasks:
            condition = task.get("condition")
            if condition:
                condition_met = self._evaluate_condition(condition, condition_results)
                if not condition_met:
                    results.append(
                        {
                            "task_id": task.get("id"),
                            "skipped": True,
                            "reason": "Condition not met",
                        }
                    )
                    continue

            result = await self.executor.execute(task, context)
            results.append(result)
            condition_results[task.get("id")] = result

        return {
            "strategy": "conditional",
            "results": results,
            "total_tasks": len(tasks),
            "executed": sum(1 for r in results if not r.get("skipped")),
        }

    async def _pipeline_execute(
        self, tasks: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        results = []
        pipeline_context = {}

        for task in tasks:
            task_with_context = {**task, "pipeline_context": pipeline_context}
            result = await self.executor.execute(task_with_context, context)

            if result.get("success"):
                pipeline_context[task.get("id")] = result.get("result")

            results.append(result)

        return {
            "strategy": "pipeline",
            "results": results,
            "pipeline_context": pipeline_context,
            "total_tasks": len(tasks),
            "successful": sum(1 for r in results if r.get("success")),
        }

    def _evaluate_condition(
        self, condition: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        condition_type = condition.get("type")
        if condition_type == "success_of":
            task_id = condition.get("task_id")
            if task_id in context:
                return context[task_id].get("success", False)
        return True
