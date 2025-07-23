import time
import psutil
import threading
from datetime import datetime
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)  # {metric_name: [values]}
        self.errors = []  # [(timestamp, type, details)]
        self.lock = threading.Lock()
        self.start_resource_monitor()

    def log_response_time(self, label, ms):
        with self.lock:
            self.metrics[f"response_time_{label}"].append((datetime.now(), ms))

    def log_error(self, error_type, details):
        with self.lock:
            self.errors.append((datetime.now(), error_type, details))

    def log_event(self, event_type, value=1):
        with self.lock:
            self.metrics[event_type].append((datetime.now(), value))

    def log_button(self, button_id, user_id=None, success=True, error=None):
        with self.lock:
            self.metrics[f"button_{button_id}_clicks"].append((datetime.now(), user_id, success))
            if not success and error:
                self.errors.append((datetime.now(), f"button_{button_id}_error", error))

    def log_platform(self, platform, event_type, user_id=None, success=True, error=None):
        with self.lock:
            self.metrics[f"platform_{platform}_{event_type}"].append((datetime.now(), user_id, success))
            if not success and error:
                self.errors.append((datetime.now(), f"platform_{platform}_{event_type}_error", error))

    def get_stats(self, last_minutes=60):
        now = datetime.now()
        stats = {}
        with self.lock:
            for key, values in self.metrics.items():
                filtered = [v for t, v in values if (now-t).total_seconds() < last_minutes*60]
                if filtered:
                    stats[key] = {
                        'count': len(filtered),
                        'avg': sum(filtered)/len(filtered) if filtered else 0,
                        'max': max(filtered),
                        'min': min(filtered)
                    }
            recent_errors = [e for e in self.errors if (now-e[0]).total_seconds() < last_minutes*60]
            stats['errors'] = recent_errors
        return stats

    def start_resource_monitor(self):
        def monitor():
            while True:
                mem = psutil.virtual_memory().used / (1024*1024)
                cpu = psutil.cpu_percent(interval=1)
                with self.lock:
                    self.metrics['memory_mb'].append((datetime.now(), mem))
                    self.metrics['cpu_percent'].append((datetime.now(), cpu))
                time.sleep(10)
        t = threading.Thread(target=monitor, daemon=True)
        t.start()

performance_monitor = PerformanceMonitor()
