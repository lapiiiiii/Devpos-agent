from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AgentContext:
    session_id: str
    user_input: str
    intent: Optional[str] = None
    task_decomposition: Optional[Dict[str, Any]] = None
    executed_steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    max_retries: int = 3
    retry_delay: float = 1.0
    execution_timeout: int = 300
    enable_reflection: bool = True
    enable_memory: bool = True
    enable_rag: bool = True


class AgentState:
    def __init__(self):
        self.status = AgentStatus.IDLE
        self.context: Optional[AgentContext] = None
        self.history: List[AgentContext] = []

    def set_context(self, context: AgentContext):
        self.context = context
        self.history.append(context)

    def update_status(self, status: AgentStatus):
        self.status = status
        if self.context:
            self.context.metadata["status"] = status.value

    def get_summary(self) -> Dict[str, Any]:
        if not self.context:
            return {"status": "no_context"}
        return {
            "session_id": self.context.session_id,
            "intent": self.context.intent,
            "status": self.status.value,
            "current_step": self.context.current_step,
            "executed_steps": len(self.context.executed_steps),
            "retry_count": self.context.retry_count,
        }


class AgentCore:
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.state = AgentState()
        self._intention_recognizer = None
        self._task_decomposer = None
        self._executor = None
        self._reflector = None
        self._memory_manager = None

    def set_components(
        self,
        intention_recognizer,
        task_decomposer,
        executor,
        reflector,
        memory_manager=None,
    ):
        self._intention_recognizer = intention_recognizer
        self._task_decomposer = task_decomposer
        self._executor = executor
        self._reflector = reflector
        self._memory_manager = memory_manager

    async def run(self, user_input: str, session_id: str) -> Dict[str, Any]:
        context = AgentContext(session_id=session_id, user_input=user_input)
        self.state.set_context(context)
        self.state.update_status(AgentStatus.RUNNING)

        try:
            logger.info(f"Agent starting for session {session_id}")

            intent = await self._recognize_intent(user_input)
            context.intent = intent
            logger.info(f"Recognized intent: {intent}")

            task_plan = await self._decompose_task(user_input, intent)
            context.task_decomposition = task_plan
            logger.info(f"Task decomposed: {len(task_plan.get('subtasks', []))} subtasks")

            result = await self._execute_plan(task_plan, context)

            if self.config.enable_reflection:
                result = await self._reflect_and_correct(result, context)

            context.result = result
            self.state.update_status(AgentStatus.SUCCESS)
            logger.info(f"Agent completed successfully for session {session_id}")

            return {
                "success": True,
                "intent": intent,
                "result": result,
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Agent failed: {str(e)}")
            context.error = str(e)
            self.state.update_status(AgentStatus.FAILED)
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
            }

    async def _recognize_intent(self, user_input: str) -> str:
        if self._intention_recognizer:
            return await self._intention_recognizer.recognize(user_input)
        return "unknown"

    async def _decompose_task(self, user_input: str, intent: str) -> Dict[str, Any]:
        if self._task_decomposer:
            return await self._task_decomposer.decompose(user_input, intent)
        return {
            "main_task": user_input,
            "subtasks": [
                {
                    "id": 1,
                    "description": user_input,
                    "tool": "default_tool",
                    "depends_on": [],
                    "can_parallel": False,
                }
            ],
        }

    async def _execute_plan(
        self, task_plan: Dict[str, Any], context: AgentContext
    ) -> Any:
        if not self._executor:
            return {"message": "Executor not configured", "task_plan": task_plan}

        results = []
        for step in task_plan.get("subtasks", []):
            context.current_step = step["id"]
            context.executed_steps.append(
                {"step_id": step["id"], "started_at": datetime.utcnow().isoformat()}
            )

            step_result = await self._executor.execute(step, context)
            results.append(step_result)

            context.executed_steps[-1]["completed_at"] = datetime.utcnow().isoformat()
            context.executed_steps[-1]["result"] = step_result

        return {"step_results": results, "total_steps": len(results)}

    async def _reflect_and_correct(
        self, result: Any, context: AgentContext
    ) -> Any:
        if self._reflector and self.config.enable_reflection:
            validation = await self._reflector.validate(result, context)
            if not validation["is_valid"]:
                logger.info(f"Reflection detected issues: {validation['issues']}")
                if context.retry_count < self.config.max_retries:
                    context.retry_count += 1
                    self.state.update_status(AgentStatus.RETRYING)
                    corrected_result = await self._reflector.correct(
                        result, validation, context
                    )
                    return corrected_result
        return result
