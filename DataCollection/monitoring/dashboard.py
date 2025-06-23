"""
Monitoring Dashboard API
FastAPI dashboard for monitoring data collection pipeline health and performance
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio

from monitoring.quality_control import DataQualityMonitor, quick_quality_check
from monitoring.performance import PerformanceMonitor
from monitoring.alerts import AlertSystem, AlertLevel, AlertType, create_manual_alert
from config.logging_config import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DXB Events Data Collection Monitor",
    description="Monitoring dashboard for the Dubai Events data collection pipeline",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve basic HTML dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DXB Events Data Collection Monitor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .status-good { color: #28a745; }
            .status-warning { color: #ffc107; }
            .status-error { color: #dc3545; }
            h1, h2 { color: #333; }
            .refresh-btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .refresh-btn:hover { background: #0056b3; }
        </style>
        <script>
            async function refreshData() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    updateHealthDisplay(data);
                } catch (error) {
                    console.error('Error fetching health data:', error);
                }
            }
            
            function updateHealthDisplay(data) {
                document.getElementById('health-status').innerHTML = 
                    `<span class="status-${data.status === 'healthy' ? 'good' : data.status === 'degraded' ? 'warning' : 'error'}">${data.status.toUpperCase()}</span>`;
                document.getElementById('last-updated').textContent = new Date(data.last_updated).toLocaleString();
            }
            
            setInterval(refreshData, 30000);
            window.onload = refreshData;
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🏙️ DXB Events Data Collection Monitor</h1>
            
            <div class="card">
                <h2>System Health</h2>
                <p>Status: <span id="health-status">Loading...</span></p>
                <p>Last Updated: <span id="last-updated">-</span></p>
                <button class="refresh-btn" onclick="refreshData()">Refresh Now</button>
            </div>
            
            <div class="card">
                <h2>Quick Links</h2>
                <ul>
                    <li><a href="/health">System Health Summary</a></li>
                    <li><a href="/metrics/performance">Performance Metrics</a></li>
                    <li><a href="/metrics/quality">Quality Report</a></li>
                    <li><a href="/alerts/active">Active Alerts</a></li>
                    <li><a href="/docs">API Documentation</a></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


@app.get("/health")
async def health_check():
    """Get overall system health status"""
    try:
        async with PerformanceMonitor() as perf_monitor:
            summary = await perf_monitor.get_performance_summary()
            
        async with AlertSystem() as alert_system:
            active_alerts = await alert_system.get_active_alerts(hours=24)
            
        async with DataQualityMonitor() as quality_monitor:
            quality_summary = await quality_monitor.get_quality_summary()
        
        # Determine overall status
        health_score = summary.get('overall_health_score', 0)
        critical_alerts = len([a for a in active_alerts if a.get('level') == 'critical'])
        
        if critical_alerts > 0:
            status = "critical"
        elif health_score >= 75:
            status = "healthy"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "health_score": health_score,
            "active_alerts_count": len(active_alerts),
            "critical_alerts_count": critical_alerts,
            "uptime_hours": summary.get('uptime_hours', 0),
            "quality_percentage": quality_summary.get('estimated_quality_percentage', 0),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "error",
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }


@app.get("/metrics/performance")
async def get_performance_metrics():
    """Get comprehensive performance metrics"""
    try:
        async with PerformanceMonitor() as perf_monitor:
            return await perf_monitor.get_performance_summary()
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/quality")
async def get_quality_metrics(hours: int = 24):
    """Get data quality metrics and report"""
    try:
        async with DataQualityMonitor() as quality_monitor:
            return await quality_monitor.generate_quality_report(hours=hours)
    except Exception as e:
        logger.error(f"Error fetching quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/active")
async def get_active_alerts(hours: int = 24):
    """Get all active (unresolved) alerts"""
    try:
        async with AlertSystem() as alert_system:
            alerts = await alert_system.get_active_alerts(hours=hours)
            
        return {
            "alerts": alerts,
            "count": len(alerts),
            "by_level": {
                "critical": len([a for a in alerts if a.get('level') == 'critical']),
                "error": len([a for a in alerts if a.get('level') == 'error']),
                "warning": len([a for a in alerts if a.get('level') == 'warning']),
                "info": len([a for a in alerts if a.get('level') == 'info'])
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/run-checks")
async def run_alert_checks(background_tasks: BackgroundTasks):
    """Manually trigger alert checks"""
    try:
        async def run_checks():
            async with AlertSystem() as alert_system:
                alerts = await alert_system.run_all_checks()
                logger.info(f"Alert check completed. Found {len(alerts)} alerts")
        
        background_tasks.add_task(run_checks)
        
        return {
            "success": True,
            "message": "Alert checks triggered in background"
        }
        
    except Exception as e:
        logger.error(f"Error triggering alert checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ping")
async def ping():
    """Simple ping endpoint for external monitoring"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 