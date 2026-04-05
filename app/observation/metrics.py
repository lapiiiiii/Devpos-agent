from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)

    def increment(self, metric: str, value: float = 1.0, tags: Optional[Dict] = None):
        key = self._make_key(metric, tags)
        self._counters[key] += value

    def gauge(self, metric: str, value: float, tags: Optional[Dict] = None):
        key = self._make_key(metric, tags)
        self._gauges[key] = value

    def histogram(self, metric: str, value: float, tags: Optional[Dict] = None):
        key = self._make_key(metric, tags)
        self._histograms[key].append(value)

    def timer(self, metric: str, duration_ms: float, tags: Optional[Dict] = None):
        key = self._make_key(metric, tags)
        self._timers[key].append(duration_ms)

    def _make_key(self, metric: str, tags: Optional[Dict] = None) -> str:
        if not tags:
            return metric
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric}[{tag_str}]"

    def get_counter(self, metric: str, tags: Optional[Dict] = None) -> float:
        key = self._make_key(metric, tags)
        return self._counters.get(key, 0)

    def get_gauge(self, metric: str, tags: Optional[Dict] = None) -> Optional[float]:
        key = self._make_key(metric, tags)
        return self._gauges.get(key)

    def get_histogram_stats(self, metric: str, tags: Optional[Dict] = None) -> Dict[str, float]:
        key = self._make_key(metric, tags)
        values = self._histograms.get(key, [])

        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }

    def _percentile(self, values: List[float], p: int) -> float:
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_all_metrics(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: self.get_histogram_stats(k) for k in self._histograms.keys()
            },
            "timers": {
                k: self.get_histogram_stats(k) for k in self._timers.keys()
            },
        }

    def reset(self):
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()


metrics_collector = MetricsCollector()


class PrometheusExporter:
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector

    def generate_metrics_text(self) -> str:
        lines = []

        for metric, value in self.metrics_collector._counters.items():
            lines.append(f'# TYPE {metric} counter')
            lines.append(f'{metric} {value}')

        for metric, value in self.metrics_collector._gauges.items():
            lines.append(f'# TYPE {metric} gauge')
            lines.append(f'{metric} {value}')

        for metric in self.metrics_collector._histograms.keys():
            stats = self.metrics_collector.get_histogram_stats(metric)
            lines.append(f'# TYPE {metric} histogram')
            for suffix, value in stats.items():
                if suffix != "count":
                    lines.append(f'{metric}_{suffix} {value}')

        return "\n".join(lines)
