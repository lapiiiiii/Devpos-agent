from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    test_case_id: str
    test_case_name: str
    intent: str
    input_text: str
    expected_intent: str
    expected_tools: List[str]
    expected_result_pattern: Optional[str] = None


class EvaluationMetrics:
    def __init__(self):
        self.intent_accuracy: float = 0.0
        self.task_completion_rate: float = 0.0
        self.hallucination_rate: float = 0.0
        self.avg_response_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "intent_accuracy": self.intent_accuracy,
            "task_completion_rate": self.task_completion_rate,
            "hallucination_rate": self.hallucination_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
        }


class Evaluator:
    def __init__(self):
        self._test_cases: List[TestCase] = []
        self._results: List[Dict[str, Any]] = []

    def add_test_case(self, test_case: TestCase):
        self._test_cases.append(test_case)

    def add_test_cases(self, test_cases: List[TestCase]):
        self._test_cases.extend(test_cases)

    async def evaluate(self, agent_response: Dict[str, Any], test_case: TestCase) -> Dict[str, Any]:
        result = {
            "test_case_id": test_case.test_case_id,
            "test_case_name": test_case.test_case_name,
            "intent": agent_response.get("intent"),
            "expected_intent": test_case.expected_intent,
            "success": agent_response.get("intent") == test_case.expected_intent,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if agent_response.get("intent") == test_case.expected_intent:
            result["intent_match"] = True
        else:
            result["intent_match"] = False

        if agent_response.get("tools_used"):
            expected_set = set(test_case.expected_tools)
            actual_set = set(agent_response.get("tools_used", []))
            result["tools_match"] = expected_set == actual_set
            result["tools_precision"] = len(expected_set & actual_set) / len(actual_set) if actual_set else 0
        else:
            result["tools_match"] = False
            result["tools_precision"] = 0

        result["hallucination_detected"] = agent_response.get("hallucination_detected", False)

        self._results.append(result)
        return result

    def get_metrics(self) -> EvaluationMetrics:
        if not self._results:
            return EvaluationMetrics()

        total = len(self._results)
        intent_matches = sum(1 for r in self._results if r.get("intent_match"))
        hallucination_count = sum(1 for r in self._results if r.get("hallucination_detected"))

        metrics = EvaluationMetrics()
        metrics.intent_accuracy = intent_matches / total if total > 0 else 0
        metrics.hallucination_rate = hallucination_count / total if total > 0 else 0

        return metrics

    def get_results_summary(self) -> Dict[str, Any]:
        metrics = self.get_metrics()
        return {
            "total_tests": len(self._results),
            "metrics": metrics.to_dict(),
            "passed": sum(1 for r in self._results if r.get("success")),
            "failed": sum(1 for r in self._results if not r.get("success")),
        }


class TestCaseLibrary:
    def __init__(self):
        self._test_cases: Dict[str, TestCase] = {}
        self._register_default_test_cases()

    def _register_default_test_cases(self):
        test_cases = [
            TestCase(
                test_case_id="tc001",
                test_case_name="Bug统计查询",
                intent="bug统计",
                input_text="本周新增了多少Bug？",
                expected_intent="bug统计",
                expected_tools=["jira_get_bugs"],
            ),
            TestCase(
                test_case_id="tc002",
                test_case_name="缺陷分析",
                intent="缺陷分析",
                input_text="分析最近Bug的根因",
                expected_intent="缺陷分析",
                expected_tools=["jira_get_bugs", "jira_get_issue"],
            ),
            TestCase(
                test_case_id="tc003",
                test_case_name="缺陷详情",
                intent="缺陷详情",
                input_text="查看PROJ-101的详细信息",
                expected_intent="缺陷详情",
                expected_tools=["jira_get_issue"],
            ),
            TestCase(
                test_case_id="tc004",
                test_case_name="代码评审",
                intent="代码评审",
                input_text="有哪些PR需要评审？",
                expected_intent="代码评审",
                expected_tools=["github_get_pulls"],
            ),
            TestCase(
                test_case_id="tc005",
                test_case_name="构建历史查询",
                intent="构建查询",
                input_text="最近构建成功了吗？",
                expected_intent="构建查询",
                expected_tools=["cicd_get_build_history"],
            ),
            TestCase(
                test_case_id="tc006",
                test_case_name="构建分析",
                intent="构建分析",
                input_text="为什么构建失败了？",
                expected_intent="构建分析",
                expected_tools=["cicd_get_build_history", "cicd_get_workflow_logs"],
            ),
            TestCase(
                test_case_id="tc007",
                test_case_name="效能指标",
                intent="效能指标",
                input_text="这周的构建成功率是多少？",
                expected_intent="效能指标",
                expected_tools=["cicd_get_metrics"],
            ),
            TestCase(
                test_case_id="tc008",
                test_case_name="效能报表",
                intent="效能报表",
                input_text="生成本周研发效能报表",
                expected_intent="效能报表",
                expected_tools=["cicd_get_metrics", "github_get_commits"],
            ),
            TestCase(
                test_case_id="tc009",
                test_case_name="交付周期",
                intent="交付周期",
                input_text="平均交付周期是多久？",
                expected_intent="交付周期",
                expected_tools=["jira_get_issues"],
            ),
            TestCase(
                test_case_id="tc010",
                test_case_name="贡献统计",
                intent="贡献统计",
                input_text="这周谁贡献了最多代码？",
                expected_intent="贡献统计",
                expected_tools=["github_get_commits"],
            ),
        ]

        for tc in test_cases:
            self._test_cases[tc.test_case_id] = tc

    def get_test_case(self, test_case_id: str) -> Optional[TestCase]:
        return self._test_cases.get(test_case_id)

    def get_all_test_cases(self) -> List[TestCase]:
        return list(self._test_cases.values())

    def get_test_cases_by_intent(self, intent: str) -> List[TestCase]:
        return [tc for tc in self._test_cases.values() if tc.intent == intent]

    def add_test_case(self, test_case: TestCase):
        self._test_cases[test_case.test_case_id] = test_case


class BacktestRunner:
    def __init__(self, evaluator: Evaluator, agent):
        self.evaluator = evaluator
        self.agent = agent
        self._test_results: List[Dict[str, Any]] = []

    async def run_backtest(
        self,
        test_cases: List[TestCase],
        parallel: bool = True,
    ) -> Dict[str, Any]:
        results = []

        if parallel:
            import asyncio
            tasks = [
                self._run_single_test(tc)
                for tc in test_cases
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for tc in test_cases:
                result = await self._run_single_test(tc)
                results.append(result)

        self._test_results.extend([r for r in results if not isinstance(r, Exception)])

        return self._generate_report()

    async def _run_single_test(self, test_case: TestCase) -> Dict[str, Any]:
        try:
            response = await self.agent.run(
                test_case.input_text,
                session_id=f"backtest_{test_case.test_case_id}"
            )

            result = await self.evaluator.evaluate(response, test_case)
            result["response"] = response
            return result

        except Exception as e:
            return {
                "test_case_id": test_case.test_case_id,
                "test_case_name": test_case.test_case_name,
                "success": False,
                "error": str(e),
            }

    def _generate_report(self) -> Dict[str, Any]:
        metrics = self.evaluator.get_metrics()
        summary = self.evaluator.get_results_summary()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_tests": len(self._test_results),
            "passed": summary["passed"],
            "failed": summary["failed"],
            "pass_rate": summary["passed"] / len(self._test_results) if self._test_results else 0,
            "metrics": metrics.to_dict(),
            "failed_tests": [
                {
                    "test_case_id": r.get("test_case_id"),
                    "reason": r.get("error") or "Intent mismatch",
                }
                for r in self._test_results
                if not r.get("success")
            ],
        }
