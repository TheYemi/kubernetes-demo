resource "aws_secretsmanager_secret" "grafana_password" {
  name        = "${var.project_name}-grafana-admin-password"
  description = "Grafana admin password for ${var.project_name} cluster"
  
  tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = "shared"
  }
}

resource "aws_secretsmanager_secret_version" "grafana_password" {
  secret_id     = aws_secretsmanager_secret.grafana_password.id
  secret_string = var.grafana_admin_password
}

resource "aws_secretsmanager_secret" "redis_password" {
  name        = "${var.project_name}-redis-password"
  description = "Redis password for ${var.project_name} applications"
  
  tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = "shared"
  }
}

resource "aws_secretsmanager_secret_version" "redis_password" {
  secret_id     = aws_secretsmanager_secret.redis_password.id
  secret_string = var.redis_password
}

resource "aws_secretsmanager_secret" "alertmanager_config" {
  name        = "${var.project_name}-alertmanager-config"
  description = "Alertmanager configuration with Slack webhook"
  
  tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = "shared"
  }
}

resource "aws_secretsmanager_secret_version" "alertmanager_config" {
  secret_id     = aws_secretsmanager_secret.alertmanager_config.id
  secret_string = file("${path.module}/alertmanager.yml")
}

resource "aws_iam_policy" "external_secrets" {
  name        = "${var.project_name}-external-secrets-policy"
  description = "Policy for External Secrets Operator to read secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.grafana_password.arn,
          aws_secretsmanager_secret.redis_password.arn,
          aws_secretsmanager_secret.alertmanager_config.arn
        ]
      }
    ]
  })

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

resource "aws_iam_role_policy_attachment" "external_secrets_to_nodes" {
  role       = aws_iam_role.k8s_node_role.name
  policy_arn = aws_iam_policy.external_secrets.arn
}

output "secrets_manager_arns" {
  description = "ARNs of secrets in AWS Secrets Manager"
  value = {
    grafana_password = aws_secretsmanager_secret.grafana_password.arn
    redis_password   = aws_secretsmanager_secret.redis_password.arn
    alertmanager_config   = aws_secretsmanager_secret.alertmanager_config.arn
  }
}

output "external_secrets_policy_arn" {
  description = "ARN of IAM policy for External Secrets Operator"
  value       = aws_iam_policy.external_secrets.arn
}