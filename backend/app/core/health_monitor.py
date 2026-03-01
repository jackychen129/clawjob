"""
Health Monitoring System for Agent Arena

Provides comprehensive monitoring of agent performance, system health,
and autonomous recovery capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.models.agent import Agent
from app.models.task import Task
from app.schemas.health import HealthStatus, AgentHealthMetrics

logger = logging.getLogger(__name__)

class HealthSeverity(Enum):
    """Health severity levels"""
    CRITICAL = "critical"
    WARNING = "warning" 
    INFO = "info"
    OK = "ok"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthSeverity
    message: str
    metrics: Dict[str, Any]
    timestamp: datetime

class HealthMonitor:
    """Main health monitoring class"""
    
    def __init__(self):
        self.db_session = next(get_db_session())
        self.health_checks: List[HealthCheckResult] = []
        self.anomaly_detector = AnomalyDetector()
        self.recovery_manager = RecoveryManager()
        
    async def run_health_check(self) -> HealthStatus:
        """Run comprehensive health check"""
        logger.info("Starting comprehensive health check")
        
        # Run all health checks concurrently
        tasks = [
            self._check_database_health(),
            self._check_agent_performance(),
            self._check_system_resources(),
            self._check_task_queue_health(),
            self._check_external_dependencies()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                continue
            valid_results.append(result)
            
        self.health_checks.extend(valid_results)
        
        # Detect anomalies
        anomalies = await self.anomaly_detector.detect_anomalies(valid_results)
        
        # Handle recovery if needed
        if anomalies:
            await self.recovery_manager.handle_anomalies(anomalies)
            
        # Create health status
        overall_status = self._determine_overall_status(valid_results)
        health_status = HealthStatus(
            overall_status=overall_status.value,
            components=[r.component for r in valid_results],
            metrics={r.component: r.metrics for r in valid_results},
            anomalies=[a.dict() for a in anomalies],
            last_check=datetime.utcnow()
        )
        
        logger.info(f"Health check completed. Status: {overall_status.value}")
        return health_status
        
    async def _check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        try:
            # Test connection
            start_time = datetime.utcnow()
            self.db_session.execute("SELECT 1")
            end_time = datetime.utcnow()
            
            query_time = (end_time - start_time).total_seconds()
            
            metrics = {
                "query_time_seconds": query_time,
                "connection_active": True
            }
            
            if query_time > 1.0:
                return HealthCheckResult(
                    component="database",
                    status=HealthSeverity.WARNING,
                    message=f"Database query slow: {query_time:.2f}s",
                    metrics=metrics,
                    timestamp=end_time
                )
                
            return HealthCheckResult(
                component="database", 
                status=HealthSeverity.OK,
                message="Database healthy",
                metrics=metrics,
                timestamp=end_time
            )
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthCheckResult(
                component="database",
                status=HealthSeverity.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                metrics={"connection_active": False},
                timestamp=datetime.utcnow()
            )
            
    async def _check_agent_performance(self) -> HealthCheckResult:
        """Check agent performance metrics"""
        try:
            # Get agent performance data from last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            agents = self.db_session.query(Agent).all()
            tasks = self.db_session.query(Task).filter(
                Task.created_at >= one_hour_ago
            ).all()
            
            if not agents:
                return HealthCheckResult(
                    component="agents",
                    status=HealthSeverity.WARNING,
                    message="No agents registered",
                    metrics={"agent_count": 0, "task_count": 0},
                    timestamp=datetime.utcnow()
                )
                
            successful_tasks = [t for t in tasks if t.status == "completed"]
            failed_tasks = [t for t in tasks if t.status == "failed"]
            
            success_rate = len(successful_tasks) / len(tasks) if tasks else 0
            
            metrics = {
                "agent_count": len(agents),
                "task_count": len(tasks),
                "success_rate": success_rate,
                "failed_tasks": len(failed_tasks)
            }
            
            if success_rate < 0.8:
                return HealthCheckResult(
                    component="agents",
                    status=HealthSeverity.WARNING,
                    message=f"Low success rate: {success_rate:.2%}",
                    metrics=metrics,
                    timestamp=datetime.utcnow()
                )
                
            if success_rate < 0.5:
                return HealthCheckResult(
                    component="agents", 
                    status=HealthSeverity.CRITICAL,
                    message=f"Critical success rate: {success_rate:.2%}",
                    metrics=metrics,
                    timestamp=datetime.utcnow()
                )
                
            return HealthCheckResult(
                component="agents",
                status=HealthSeverity.OK,
                message=f"Agents performing well. Success rate: {success_rate:.2%}",
                metrics=metrics,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Agent performance check failed: {e}")
            return HealthCheckResult(
                component="agents",
                status=HealthSeverity.CRITICAL,
                message=f"Agent performance check failed: {str(e)}",
                metrics={"agent_count": 0, "task_count": 0},
                timestamp=datetime.utcnow()
            )
            
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100,
                "available_memory_gb": memory.available / (1024**3)
            }
            
            status = HealthSeverity.OK
            message = "System resources healthy"
            
            if cpu_percent > 90 or memory.percent > 90:
                status = HealthSeverity.CRITICAL
                message = f"Critical resource usage: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%"
            elif cpu_percent > 70 or memory.percent > 70:
                status = HealthSeverity.WARNING
                message = f"High resource usage: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%"
                
            return HealthCheckResult(
                component="system_resources",
                status=status,
                message=message,
                metrics=metrics,
                timestamp=datetime.utcnow()
            )
            
        except ImportError:
            # psutil not available, skip this check
            return HealthCheckResult(
                component="system_resources",
                status=HealthSeverity.INFO,
                message="System resource monitoring not available",
                metrics={},
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return HealthCheckResult(
                component="system_resources",
                status=HealthSeverity.WARNING,
                message=f"System resource check failed: {str(e)}",
                metrics={},
                timestamp=datetime.utcnow()
            )
            
    async def _check_task_queue_health(self) -> HealthCheckResult:
        """Check task queue health and processing"""
        try:
            from app.services.task_queue import get_task_queue
            
            queue = get_task_queue()
            queue_size = await queue.get_size()
            processing_rate = await queue.get_processing_rate()
            
            metrics = {
                "queue_size": queue_size,
                "processing_rate_per_minute": processing_rate
            }
            
            if queue_size > 1000:
                return HealthCheckResult(
                    component="task_queue",
                    status=HealthSeverity.WARNING,
                    message=f"Large task queue: {queue_size} tasks",
                    metrics=metrics,
                    timestamp=datetime.utcnow()
                )
                
            if processing_rate < 10:
                return HealthCheckResult(
                    component="task_queue",
                    status=HealthSeverity.WARNING,
                    message=f"Slow processing rate: {processing_rate}/min",
                    metrics=metrics,
                    timestamp=datetime.utcnow()
                )
                
            return HealthCheckResult(
                component="task_queue",
                status=HealthSeverity.OK,
                message=f"Task queue healthy. Size: {queue_size}, Rate: {processing_rate}/min",
                metrics=metrics,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Task queue health check failed: {e}")
            return HealthCheckResult(
                component="task_queue",
                status=HealthSeverity.WARNING,
                message=f"Task queue health check failed: {str(e)}",
                metrics={"queue_size": 0, "processing_rate_per_minute": 0},
                timestamp=datetime.utcnow()
            )
            
    async def _check_external_dependencies(self) -> HealthCheckResult:
        """Check external service dependencies"""
        try:
            # Check Redis connectivity
            from app.database.redis_client import get_redis_client
            
            redis_client = get_redis_client()
            await redis_client.ping()
            redis_healthy = True
            
            metrics = {"redis_healthy": redis_healthy}
            message = "External dependencies healthy"
            status = HealthSeverity.OK
            
            if not redis_healthy:
                status = HealthSeverity.CRITICAL
                message = "Redis connection failed"
                metrics["redis_healthy"] = False
                
            return HealthCheckResult(
                component="external_dependencies",
                status=status,
                message=message,
                metrics=metrics,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"External dependencies check failed: {e}")
            return HealthCheckResult(
                component="external_dependencies",
                status=HealthSeverity.CRITICAL,
                message=f"External dependencies check failed: {str(e)}",
                metrics={"redis_healthy": False},
                timestamp=datetime.utcnow()
            )
            
    def _determine_overall_status(self, results: List[HealthCheckResult]) -> HealthSeverity:
        """Determine overall health status from individual results"""
        severities = [r.status for r in results]
        
        if HealthSeverity.CRITICAL in severities:
            return HealthSeverity.CRITICAL
        elif HealthSeverity.WARNING in severities:
            return HealthSeverity.WARNING
        else:
            return HealthSeverity.OK
            
    async def start_continuous_monitoring(self, background_tasks: BackgroundTasks):
        """Start continuous health monitoring"""
        background_tasks.add_task(self._continuous_monitoring_loop)
        
    async def _continuous_monitoring_loop(self):
        """Continuous monitoring loop"""
        while True:
            try:
                await self.run_health_check()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Continuous monitoring error: {e}")
                await asyncio.sleep(60)

class AnomalyDetector:
    """Detects anomalies in system behavior"""
    
    async def detect_anomalies(self, results: List[HealthCheckResult]) -> List[Dict[str, Any]]:
        """Detect anomalies in health check results"""
        anomalies = []
        
        for result in results:
            if result.status in [HealthSeverity.CRITICAL, HealthSeverity.WARNING]:
                anomalies.append({
                    "component": result.component,
                    "severity": result.status.value,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat()
                })
                
        return anomalies

class RecoveryManager:
    """Manages automatic recovery from anomalies"""
    
    async def handle_anomalies(self, anomalies: List[Dict[str, Any]]):
        """Handle detected anomalies with automatic recovery"""
        for anomaly in anomalies:
            component = anomaly["component"]
            severity = anomaly["severity"]
            
            if severity == "critical":
                await self._handle_critical_anomaly(component)
            elif severity == "warning":
                await self._handle_warning_anomaly(component)
                
    async def _handle_critical_anomaly(self, component: str):
        """Handle critical anomalies"""
        logger.critical(f"Handling critical anomaly in {component}")
        
        if component == "database":
            # Attempt database connection recovery
            await self._recover_database_connection()
        elif component == "agents":
            # Restart agent services
            await self._restart_agent_services()
        elif component == "task_queue":
            # Clear and restart task queue
            await self._recover_task_queue()
            
    async def _handle_warning_anomaly(self, component: str):
        """Handle warning anomalies"""
        logger.warning(f"Handling warning anomaly in {component}")
        # Log warning and monitor, no immediate action needed
        
    async def _recover_database_connection(self):
        """Attempt to recover database connection"""
        logger.info("Attempting database connection recovery")
        # Implementation would depend on specific database setup
        
    async def _restart_agent_services(self):
        """Restart agent services"""
        logger.info("Restarting agent services")
        # Implementation would restart agent processes
        
    async def _recover_task_queue(self):
        """Recover task queue"""
        logger.info("Recovering task queue")
        # Implementation would clear stuck tasks and restart queue

# Global health monitor instance
health_monitor = HealthMonitor()

async def get_health_status() -> HealthStatus:
    """Get current health status"""
    return await health_monitor.run_health_check()

async def start_health_monitoring(background_tasks: BackgroundTasks):
    """Start health monitoring"""
    await health_monitor.start_continuous_monitoring(background_tasks)