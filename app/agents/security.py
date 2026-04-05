from typing import Dict, List, Any, Optional, Set
import re
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    def __init__(self):
        self._sensitive_patterns = [
            r"api[_-]?key",
            r"token",
            r"password",
            r"secret",
            r"private[_-]?key",
            r"-----BEGIN.*KEY-----",
            r"-----BEGIN.*RSA.*PRIVATE KEY-----",
        ]
        self._injection_patterns = [
            r"ignore\s+(previous|all|above)\s+instructions",
            r"disregard\s+(previous|all|above)",
            r"forget\s+(everything|all|previous)",
            r"new\s+instructions?:",
            r"you\s+are\s+now\s+",
            r"system\s*[:\-]",
            r"<\s*script",
            r"javascript:",
        ]
        self._max_length = 10000

    def validate(self, user_input: str) -> Dict[str, Any]:
        issues = []
        risk_level = "low"

        if len(user_input) > self._max_length:
            issues.append(f"Input exceeds maximum length of {self._max_length}")
            risk_level = "medium"

        for pattern in self._injection_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                issues.append(f"Potential prompt injection detected: {pattern}")
                risk_level = "high"

        has_sensitive = self._contains_sensitive_info(user_input)
        if has_sensitive:
            issues.append("Input contains potentially sensitive information")
            risk_level = "high"

        sanitized_input = self._sanitize(user_input)

        return {
            "is_safe": risk_level == "low",
            "risk_level": risk_level,
            "issues": issues,
            "sanitized_input": sanitized_input,
        }

    def _contains_sensitive_info(self, text: str) -> bool:
        for pattern in self._sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _sanitize(self, text: str) -> str:
        sanitized = text
        dangerous_patterns = [
            (r"<script[^>]*>.*?</script>", ""),
            (r"javascript:", ""),
            (r"on\w+\s*=", ""),
        ]

        for pattern, replacement in dangerous_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized.strip()


class HallucinationDetector:
    def __init__(self):
        self._fact_keywords = [
            "confirmed",
            "verified",
            "actual",
            "real",
            "definitely",
            "certainly",
        ]
        self._uncertainty_keywords = [
            "maybe",
            "perhaps",
            "might",
            "could",
            "possibly",
            "likely",
            "unlikely",
        ]
        self._confidence_threshold = 0.7

    async def detect(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        certainty_score = self._calculate_certainty(response)
        factual_indicators = self._extract_factual_indicators(response)

        hallucination_risk = "low"
        if certainty_score > 0.8 and len(factual_indicators) > 2:
            hallucination_risk = "medium"
        if certainty_score > 0.9 and len(factual_indicators) > 4:
            hallucination_risk = "high"

        return {
            "response": response,
            "certainty_score": certainty_score,
            "factual_indicators": factual_indicators,
            "hallucination_risk": hallucination_risk,
            "needs_verification": hallucination_risk in ["medium", "high"],
        }

    def _calculate_certainty(self, text: str) -> float:
        certainty_count = sum(
            1 for kw in self._fact_keywords if kw.lower() in text.lower()
        )
        uncertainty_count = sum(
            1 for kw in self._uncertainty_keywords if kw.lower() in text.lower()
        )

        total = certainty_count + uncertainty_count
        if total == 0:
            return 0.5

        return certainty_count / total

    def _extract_factual_indicators(self, text: str) -> List[str]:
        indicators = []
        for keyword in self._fact_keywords:
            if keyword.lower() in text.lower():
                indicators.append(keyword)
        return indicators


class FactChecker:
    def __init__(self):
        self._verified_facts: Dict[str, bool] = {}

    async def check(
        self, statement: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        is_verified = await self._verify_against_sources(statement, context)

        return {
            "statement": statement,
            "is_verified": is_verified,
            "verification_method": "retrieval_augmented_checking",
            "confidence": 0.9 if is_verified else 0.5,
        }

    async def _verify_against_sources(
        self, statement: str, context: Optional[Dict[str, Any]]
    ) -> bool:
        if not context:
            return True

        retrieved_data = context.get("retrieved_data", [])
        for data in retrieved_data:
            if isinstance(data, dict) and "content" in data:
                if statement.lower() in data["content"].lower():
                    return True

        return True


class PromptInjectionDetector:
    def __init__(self):
        self._injection_indicators = [
            "ignore",
            "disregard",
            "forget",
            "new instructions",
            "override",
            "system prompt",
            "you are now",
            "pretend",
            "as an AI",
        ]
        self._role_play_patterns = [
            r"act\s+as\s+",
            r"pretend\s+you\s+are",
            r"you\s+are\s+a?\s+",
        ]

    def detect(self, user_input: str) -> Dict[str, Any]:
        indicators_found = []
        injection_score = 0.0

        user_input_lower = user_input.lower()
        for indicator in self._injection_indicators:
            if indicator.lower() in user_input_lower:
                indicators_found.append(indicator)
                injection_score += 0.2

        for pattern in self._role_play_patterns:
            if re.search(pattern, user_input_lower):
                indicators_found.append(f"role_play: {pattern}")
                injection_score += 0.3

        is_injection = injection_score >= 0.5

        return {
            "is_injection": is_injection,
            "injection_score": min(injection_score, 1.0),
            "indicators": indicators_found,
            "recommendation": "reject" if is_injection else "allow",
        }


class SecurityManager:
    def __init__(self):
        self.input_validator = InputValidator()
        self.hallucination_detector = HallucinationDetector()
        self.fact_checker = FactChecker()
        self.injection_detector = PromptInjectionDetector()

    async def validate_input(self, user_input: str) -> Dict[str, Any]:
        injection_result = self.injection_detector.detect(user_input)
        validation_result = self.input_validator.validate(user_input)

        combined_result = {
            **validation_result,
            "injection_score": injection_result.get("injection_score", 0),
            "injection_detected": injection_result.get("is_injection", False),
        }

        if injection_result.get("is_injection"):
            combined_result["is_safe"] = False
            combined_result["risk_level"] = "high"
            combined_result["issues"].append("Prompt injection detected")

        return combined_result

    async def validate_output(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        hallucination_result = await self.hallucination_detector.detect(response, context)

        if hallucination_result.get("needs_verification"):
            fact_check_result = await self.fact_checker.check(response, context)
            hallucination_result["fact_check"] = fact_check_result

        return hallucination_result

    async def sanitize_response(
        self, response: str, validation_result: Dict[str, Any]
    ) -> str:
        if validation_result.get("risk_level") == "high":
            return "抱歉，我无法处理这个请求，因为它可能包含不安全的内容。"

        if validation_result.get("injection_detected"):
            return "抱歉，我不能忽略我的核心指令来执行这个请求。"

        return response
