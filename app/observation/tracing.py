from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TraceStatus(Enum):
    STARTED = "started"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Span:
    span_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "started"
    error: Optional[str] = None

    def finish(self, status: str = "success", error: Optional[str] = None):
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        if error:
            self.error = error


@dataclass
class Trace:
    trace_id: str
    session_id: str
    user_input: str
    intent: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "started"
    spans: List[Span] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None

    def finish(self, status: str = "success", result: Any = None, error: Optional[str] = None):
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        if result:
            self.result = result
        if error:
            self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_input": self.user_input,
            "intent": self.intent,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "spans": [
                {
                    "span_id": s.span_id,
                    "operation_name": s.operation_name,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_ms": s.duration_ms,
                    "attributes": s.attributes,
                    "status": s.status,
                    "error": s.error,
                }
                for s in self.spans
            ],
            "attributes": self.attributes,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
        }


class TraceManager:
    def __init__(self, max_traces: int = 1000):
        self.max_traces = max_traces
        self._traces: Dict[str, Trace] = {}
        self._trace_by_session: Dict[str, List[str]] = {}

    def create_trace(self, trace_id: str, session_id: str, user_input: str) -> Trace:
        trace = Trace(trace_id=trace_id, session_id=session_id, user_input=user_input)
        self._traces[trace_id] = trace

        if session_id not in self._trace_by_session:
            self._trace_by_session[session_id] = []
        self._trace_by_session[session_id].append(trace_id)

        self._cleanup_old_traces()

        logger.debug(f"Created trace: {trace_id}")
        return trace

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self._traces.get(trace_id)

    def get_traces_by_session(self, session_id: str) -> List[Trace]:
        trace_ids = self._trace_by_session.get(session_id, [])
        return [self._traces[tid] for tid in trace_ids if tid in self._traces]

    def add_span(self, trace_id: str, span: Span) -> bool:
        trace = self._traces.get(trace_id)
        if trace:
            trace.spans.append(span)
            return True
        return False

    def _cleanup_old_traces(self):
        if len(self._traces) > self.max_traces:
            sorted_traces = sorted(
                self._traces.items(),
                key=lambda x: x[1].start_time,
                reverse=True
            )
            for trace_id, _ in sorted_traces[self.max_traces:]:
                del self._traces[trace_id]

    def get_stats(self) -> Dict[str, Any]:
        total_traces = len(self._traces)
        status_counts = {}

        for trace in self._traces.values():
            status = trace.status
            status_counts[status] = status_counts.get(status, 0) + 1

        durations = [
            t.duration_ms for t in self._traces.values()
            if t.duration_ms is not None
        ]

        return {
            "total_traces": total_traces,
            "status_counts": status_counts,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
        }


class AgentTracer:
    def __init__(self, trace_manager: TraceManager):
        self.trace_manager = trace_manager
        self._current_trace: Optional[Trace] = None
        self._current_span: Optional[Span] = None

    def start_trace(
        self, trace_id: str, session_id: str, user_input: str
    ) -> Trace:
        self._current_trace = self.trace_manager.create_trace(
            trace_id, session_id, user_input
        )
        return self._current_trace

    def end_trace(self, status: str = "success", result: Any = None, error: Optional[str] = None):
        if self._current_trace:
            self._current_trace.finish(status=status, result=result, error=error)
            self._current_trace = None

    def start_span(self, span_id: str, operation_name: str, attributes: Optional[Dict] = None) -> Span:
        span = Span(
            span_id=span_id,
            operation_name=operation_name,
            start_time=datetime.utcnow(),
            attributes=attributes or {},
        )

        if self._current_trace:
            self.trace_manager.add_span(self._current_trace.trace_id, span)

        self._current_span = span
        return span

    def end_span(self, status: str = "success", error: Optional[str] = None):
        if self._current_span:
            self._current_span.finish(status=status, error=error)
            self._current_span = None

    def record_exception(self, exception: Exception):
        if self._current_span:
            self._current_span.error = str(exception)

    def get_current_trace(self) -> Optional[Trace]:
        return self._current_trace


trace_manager = TraceManager()
agent_tracer = AgentTracer(trace_manager)
