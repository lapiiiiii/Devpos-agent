from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ResultValidator:
    def __init__(self):
        self._validators = {
            "completeness": self._check_completeness,
            "accuracy": self._check_accuracy,
            "relevance": self._check_relevance,
            "format": self._check_format,
        }

    async def validate(
        self, result: Any, expected: Optional[Any] = None
    ) -> Dict[str, Any]:
        issues = []
        severity = "low"

        for check_name, check_func in self._validators.items():
            check_result = await check_func(result)
            if not check_result["passed"]:
                issues.append(f"{check_name}: {check_result['message']}")
                if check_result.get("severity") == "high":
                    severity = "high"
                elif check_result.get("severity") == "medium" and severity != "high":
                    severity = "medium"

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "severity": severity,
            "suggestion": self._generate_suggestion(issues) if issues else None,
        }

    async def _check_completeness(self, result: Any) -> Dict[str, Any]:
        if isinstance(result, dict):
            if "error" in result and result["error"]:
                return {"passed": False, "message": "Result contains error", "severity": "high"}
            if "result" in result and result["result"] is None:
                return {"passed": False, "message": "Result is None", "severity": "medium"}
        return {"passed": True}

    async def _check_accuracy(self, result: Any) -> Dict[str, Any]:
        if isinstance(result, dict) and "mock" in result:
            return {"passed": False, "message": "Result is mock data", "severity": "medium"}
        return {"passed": True}

    async def _check_relevance(self, result: Any) -> Dict[str, Any]:
        return {"passed": True}

    async def _check_format(self, result: Any) -> Dict[str, Any]:
        if result is None:
            return {"passed": False, "message": "Result is None", "severity": "high"}
        return {"passed": True}

    def _generate_suggestion(self, issues: List[str]) -> str:
        if any("completeness" in issue for issue in issues):
            return "请补充缺失的信息或重新执行查询"
        if any("accuracy" in issue for issue in issues):
            return "数据可能不准确，请检查数据源或重新获取"
        if any("mock" in issue for issue in issues):
            return "正在使用模拟数据，请配置真实API"
        return "请检查执行结果并重试"


class DeviationDetector:
    def __init__(self):
        self._deviation_keywords = [
            "unexpected", "wrong", "incorrect", "mistake",
            "error", "fail", "missing", "incomplete"
        ]

    async def detect(
        self, result: Any, user_intent: str, task_description: str
    ) -> Dict[str, Any]:
        deviations = []

        if self._check_result_empty(result):
            deviations.append({
                "type": "empty_result",
                "description": "结果为空，可能偏离了预期",
                "severity": "medium"
            })

        if self._check_result_irrelevant(result, task_description):
            deviations.append({
                "type": "irrelevant_result",
                "description": "结果与任务不相关",
                "severity": "high"
            })

        return {
            "has_deviation": len(deviations) > 0,
            "deviations": deviations,
            "confidence": 1.0 - (len(deviations) * 0.2)
        }

    def _check_result_empty(self, result: Any) -> bool:
        if result is None:
            return True
        if isinstance(result, (list, dict)) and len(result) == 0:
            return True
        return False

    def _check_result_irrelevant(self, result: Any, task_description: str) -> bool:
        return False


class RetryPlanner:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._retry_strategies = {
            "change_tool": self._strategy_change_tool,
            "adjust_params": self._strategy_adjust_params,
            "simplify_task": self._strategy_simplify_task,
            "decompose_task": self._strategy_decompose_task,
        }

    async def plan_retry(
        self,
        error: str,
        failed_task: Dict[str, Any],
        available_tools: List[str]
    ) -> Dict[str, Any]:
        error_type = self._classify_error(error)

        if error_type == "network":
            strategy = "retry_later"
        elif error_type == "auth":
            strategy = "change_tool"
        elif error_type == "data":
            strategy = "adjust_params"
        else:
            strategy = "simplify_task"

        strategy_func = self._retry_strategies.get(strategy, self._strategy_default)

        return await strategy_func(error, failed_task, available_tools)

    def _classify_error(self, error: str) -> str:
        error_lower = error.lower()
        if any(keyword in error_lower for keyword in ["timeout", "connection", "network"]):
            return "network"
        if any(keyword in error_lower for keyword in ["auth", "token", "permission"]):
            return "auth"
        if any(keyword in error_lower for keyword in ["data", "not found", "invalid"]):
            return "data"
        return "unknown"

    async def _strategy_change_tool(
        self, error: str, task: Dict, tools: List[str]
    ) -> Dict[str, Any]:
        alternative_tools = [t for t in tools if t != task.get("tool")]
        return {
            "strategy": "change_tool",
            "recommended_tool": alternative_tools[0] if alternative_tools else None,
            "reason": f"原工具失败: {error}",
        }

    async def _strategy_adjust_params(
        self, error: str, task: Dict, tools: List[str]
    ) -> Dict[str, Any]:
        return {
            "strategy": "adjust_params",
            "adjusted_params": {"limit": 10, "simplified": True},
            "reason": "调整参数简化查询",
        }

    async def _strategy_simplify_task(
        self, error: str, task: Dict, tools: List[str]
    ) -> Dict[str, Any]:
        return {
            "strategy": "simplify_task",
            "simplified_description": f"获取基本信息: {task.get('description', '')[:50]}",
            "reason": "简化任务复杂度",
        }

    async def _strategy_decompose_task(
        self, error: str, task: Dict, tools: List[str]
    ) -> Dict[str, Any]:
        return {
            "strategy": "decompose_task",
            "sub_tasks": [
                {**task, "id": 1, "complexity": "low"},
                {**task, "id": 2, "complexity": "low"},
            ],
            "reason": "分解任务为更小的子任务",
        }

    async def _strategy_default(
        self, error: str, task: Dict, tools: List[str]
    ) -> Dict[str, Any]:
        return {
            "strategy": "retry",
            "reason": f"默认重试策略: {error}",
        }


class Reflector:
    def __init__(self, llm=None, max_retries: int = 3):
        self.validator = ResultValidator()
        self.deviation_detector = DeviationDetector()
        self.retry_planner = RetryPlanner(max_retries)
        self.llm = llm

    async def validate(self, result: Any, context: Any) -> Dict[str, Any]:
        return await self.validator.validate(result)

    async def detect_deviation(
        self, result: Any, user_intent: str, task_description: str
    ) -> Dict[str, Any]:
        return await self.deviation_detector.detect(result, user_intent, task_description)

    async def plan_retry(
        self, error: str, failed_task: Dict, available_tools: List[str]
    ) -> Dict[str, Any]:
        return await self.retry_planner.plan_retry(error, failed_task, available_tools)

    async def correct(
        self, result: Any, validation: Dict, context: Any
    ) -> Any:
        suggestion = validation.get("suggestion", "请重试")
        logger.info(f"Applying correction: {suggestion}")
        return {"corrected": True, "original_result": result, "suggestion": suggestion}
