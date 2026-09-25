# CloudWatch alarms for App Runner (proposal UC-15 — failure alerts)

resource "aws_sns_topic" "ops_alerts" {
  count = var.enable_cloudwatch_alarms ? 1 : 0
  name  = "${var.project_name}-ops-alerts"
}

resource "aws_cloudwatch_metric_alarm" "backend_5xx" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-backend-5xx"
  alarm_description   = "App Runner backend returned too many 5xx responses"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5xxStatusCodeCount"
  namespace           = "AWS/AppRunner"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = aws_apprunner_service.backend.service_name
  }

  alarm_actions = [aws_sns_topic.ops_alerts[0].arn]
}

resource "aws_cloudwatch_metric_alarm" "backend_health_check" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-backend-unhealthy"
  alarm_description   = "App Runner backend health check failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HealthCheckFailed"
  namespace           = "AWS/AppRunner"
  period              = 60
  statistic           = "Sum"
  threshold           = 3
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = aws_apprunner_service.backend.service_name
  }

  alarm_actions = [aws_sns_topic.ops_alerts[0].arn]
}
