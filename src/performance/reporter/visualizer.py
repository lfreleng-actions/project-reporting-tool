# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Visualization and export of performance metrics.

Contains the visualizer that renders metrics as ASCII charts and exports
performance reports as standalone HTML documents.
"""

import logging
from datetime import datetime
from pathlib import Path

from .models import AlertSeverity, Metric, PerformanceReport


logger = logging.getLogger(__name__)


class MetricsVisualizer:
    """Visualizes performance metrics."""

    def __init__(self):
        """Initialize metrics visualizer."""
        pass

    def create_ascii_chart(
        self,
        values: list[float],
        width: int = 60,
        height: int = 10,  # noqa: ARG002
        title: str = "",
    ) -> str:
        """
        Create ASCII bar chart.

        Args:
            values: Values to chart
            width: Chart width
            height: Chart height
            title: Chart title

        Returns:
            ASCII chart string
        """
        if not values:
            return "No data"

        lines = []

        if title:
            lines.append(title)
            lines.append("-" * width)

        max_val = max(values)
        min_val = min(values)
        range_val = max_val - min_val if max_val != min_val else 1

        for i, value in enumerate(values):
            normalized = (value - min_val) / range_val
            bar_length = int(normalized * (width - 20))
            bar = "█" * bar_length
            lines.append(f"{i:3d} | {bar} {value:.2f}")

        return "\n".join(lines)

    def create_trend_chart(
        self,
        metrics: list[Metric],
        width: int = 60,
        height: int = 10,
    ) -> str:
        """
        Create ASCII trend chart.

        Args:
            metrics: Metrics to chart
            width: Chart width
            height: Chart height

        Returns:
            ASCII chart string
        """
        if not metrics:
            return "No data"

        values = [m.value for m in metrics]
        return self.create_ascii_chart(values, width, height, f"Trend: {metrics[0].name}")

    def export_html(
        self,
        report: PerformanceReport,
        output_path: str | Path,
    ) -> None:
        """
        Export report as HTML.

        Args:
            report: Performance report
            output_path: Output file path
        """
        output_path = Path(output_path)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Performance Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .metric {{
            background-color: #f9f9f9;
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid #4CAF50;
        }}
        .alert {{
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid #ff9800;
            background-color: #fff3cd;
        }}
        .alert.error {{
            border-left-color: #f44336;
            background-color: #ffebee;
        }}
        .trend {{
            padding: 10px;
            margin: 5px 0;
            background-color: #e3f2fd;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #2196F3;
        }}
        .timestamp {{
            color: #777;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Performance Report</h1>
        <p class="timestamp">Generated: {datetime.fromtimestamp(report.generated_at).strftime("%Y-%m-%d %H:%M:%S")}</p>

        <h2>Summary</h2>
        <div class="summary">
"""

        for key, value in report.summary.items():
            html += f"""
            <div class="summary-card">
                <strong>{key}</strong><br>
                {value}
            </div>
"""

        html += """
        </div>

        <h2>Alerts</h2>
"""

        if report.alerts:
            for alert in report.alerts:
                alert_class = (
                    "error"
                    if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]
                    else ""
                )
                html += f"""
        <div class="alert {alert_class}">
            <strong>{alert.severity.value.upper()}</strong>: {alert.message}
        </div>
"""
        else:
            html += "<p>No alerts</p>"

        html += """
        <h2>Trends</h2>
"""

        if report.trends:
            for trend in report.trends:
                html += f"""
        <div class="trend">
            {trend.format()}
        </div>
"""
        else:
            html += "<p>No trends available</p>"

        html += """
        <h2>Metrics</h2>
"""

        for metric in report.metrics:
            unit_str = f" {metric.unit}" if metric.unit else ""
            html += f"""
        <div class="metric">
            <strong>{metric.name}</strong>: {metric.value:.2f}{unit_str}
            <span style="color: #777; font-size: 0.9em;">({metric.metric_type.value})</span>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""

        output_path.write_text(html)
        logger.info(f"HTML report saved to {output_path}")
