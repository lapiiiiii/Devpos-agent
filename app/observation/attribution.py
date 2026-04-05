from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AttributionDimension(Enum):
    INTENT = "intent"
    RETRIEVAL = "retrieval"
    MODEL = "model"
    TOOL = "tool"
    CONTEXT = "context"


class RootCauseAnalyzer:
    def __init__(self):
        self._rules: Dict[AttributionDimension, List[Callable]] = {
            dim: [] for dim in AttributionDimension
        }
        self._register_default_rules()

    def _register_default_rules(self):
        self.register_rule(
            AttributionDimension.INTENT,
            lambda ctx: self._analyze_intent_issues(ctx)
        )
        self.register_rule(
            AttributionDimension.RETRIEVAL,
            lambda ctx: self._analyze_retrieval_issues(ctx)
        )
        self.register_rule(
            AttributionDimension.MODEL,
            lambda ctx: self._analyze_model_issues(ctx)
        )
        self.register_rule(
            AttributionDimension.TOOL,
            lambda ctx: self._analyze_tool_issues(ctx)
        )

    def register_rule(self, dimension: AttributionDimension, rule_func: Callable):
        self._rules[dimension].append(rule_func)

    async def analyze(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        root_causes = []
        dimension_scores = {}

        for dimension in AttributionDimension:
            score = 0.0
            issues = []

            for rule in self._rules.get(dimension, []):
                try:
                    result = await rule(context)
                    if result.get("score", 0) > 0:
                        score += result["score"]
                        issues.extend(result.get("issues", []))
                except Exception as e:
                    logger.error(f"Error in rule for {dimension}: {e}")

            if issues:
                dimension_scores[dimension.value] = {
                    "score": score,
                    "issues": issues,
                }
                root_causes.append({
                    "dimension": dimension.value,
                    "score": score,
                    "issues": issues,
                })

        root_causes.sort(key=lambda x: x["score"], reverse=True)

        return {
            "error_type": error_type,
            "error_message": error_message,
            "root_causes": root_causes[:3],
            "dimension_scores": dimension_scores,
            "recommendation": self._generate_recommendation(root_causes, error_type),
        }

    def _analyze_intent_issues(self, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        score = 0.0

        if context.get("intent") == "unknown":
            issues.append("无法识别用户意图")
            score += 0.5

        if context.get("intent_confidence", 1.0) < 0.7:
            issues.append(f"意图置信度低: {context.get('intent_confidence')}")
            score += 0.3

        return {"score": score, "issues": issues}

    def _analyze_retrieval_issues(self, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        score = 0.0

        retrieval_results = context.get("retrieval_results", [])
        if len(retrieval_results) == 0:
            issues.append("检索结果为空")
            score += 0.4

        retrieval_scores = [r.get("score", 0) for r in retrieval_results]
        if retrieval_scores and max(retrieval_scores) < 0.5:
            issues.append(f"检索质量差，最高得分: {max(retrieval_scores):.2f}")
            score += 0.3

        return {"score": score, "issues": issues}

    def _analyze_model_issues(self, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        score = 0.0

        if context.get("model_latency_ms", 0) > 5000:
            issues.append(f"模型响应慢: {context.get('model_latency_ms')}ms")
            score += 0.2

        if context.get("hallucination_detected"):
            issues.append("检测到幻觉")
            score += 0.5

        if context.get("context_overflow"):
            issues.append("上下文溢出")
            score += 0.3

        return {"score": score, "issues": issues}

    def _analyze_tool_issues(self, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        score = 0.0

        failed_tools = context.get("failed_tools", [])
        for tool in failed_tools:
            issues.append(f"工具 {tool.get('name')} 执行失败: {tool.get('error')}")
            score += 0.4

        if context.get("tool_timeout"):
            issues.append("工具执行超时")
            score += 0.2

        return {"score": score, "issues": issues}

    def _generate_recommendation(
        self, root_causes: List[Dict], error_type: str
    ) -> str:
        if not root_causes:
            return "无法确定根本原因，建议检查系统日志"

        top_cause = root_causes[0]
        dimension = top_cause.get("dimension")

        recommendations = {
            "intent": "建议优化意图识别Prompt或提供更多上下文",
            "retrieval": "建议优化向量库或调整检索策略",
            "model": "建议检查模型配置或增加重试机制",
            "tool": "建议检查工具配置或增加错误处理",
            "context": "建议优化上下文压缩或增加记忆管理",
        }

        return recommendations.get(dimension, "建议进行进一步调查")


class AlertManager:
    def __init__(self):
        self._alert_rules: List[Dict[str, Any]] = []
        self._active_alerts: List[Dict[str, Any]] = []
        self._register_default_rules()

    def _register_default_rules(self):
        self.add_rule(
            name="high_hallucination_rate",
            condition=lambda ctx: ctx.get("hallucination_rate", 0) > 0.05,
            severity="high",
            message="幻觉率超过5%阈值",
        )

        self.add_rule(
            name="low_intent_accuracy",
            condition=lambda ctx: ctx.get("intent_accuracy", 1.0) < 0.9,
            severity="medium",
            message="意图识别准确率低于90%",
        )

        self.add_rule(
            name="high_failure_rate",
            condition=lambda ctx: ctx.get("failure_rate", 0) > 0.15,
            severity="high",
            message="任务失败率超过15%",
        )

        self.add_rule(
            name="slow_response",
            condition=lambda ctx: ctx.get("avg_response_time", 0) > 10000,
            severity="medium",
            message="平均响应时间超过10秒",
        )

    def add_rule(
        self,
        name: str,
        condition: Callable,
        severity: str,
        message: str,
    ):
        self._alert_rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "message": message,
        })

    async def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered_alerts = []

        for rule in self._alert_rules:
            try:
                if rule["condition"](metrics):
                    alert = {
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "triggered_at": datetime.utcnow().isoformat(),
                    }
                    triggered_alerts.append(alert)

                    if alert not in self._active_alerts:
                        self._active_alerts.append(alert)

            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")

        return triggered_alerts

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return self._active_alerts

    def clear_alert(self, alert_name: str) -> bool:
        for alert in self._active_alerts:
            if alert["name"] == alert_name:
                self._active_alerts.remove(alert)
                return True
        return False
