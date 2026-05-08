#!/bin/bash
# Cleanup script for AWS Secrets Manager secrets scheduled for deletion

PROJECT_NAME="k8s-demo"
REGION="us-east-1"

echo "🔍 Finding secrets scheduled for deletion for project: $PROJECT_NAME"
echo ""

SECRETS=$(aws secretsmanager list-secrets \
  --region $REGION \
  --filters Key=name,Values=${PROJECT_NAME}- \
  --query 'SecretList[?DeletedDate!=null].[Name,ARN]' \
  --output text)

if [ -z "$SECRETS" ]; then
  echo "No secrets scheduled for deletion found"
  exit 0
fi

echo "Found secrets scheduled for deletion:"
echo "$SECRETS" | awk '{print "  - " $1}'
echo ""

read -p "Force delete these secrets? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancelled"
  exit 1
fi

echo ""
echo "Deleting secrets..."
echo ""

while IFS=$'\t' read -r SECRET_NAME SECRET_ARN; do
  echo "Deleting: $SECRET_NAME"
  
  aws secretsmanager delete-secret \
    --secret-id "$SECRET_NAME" \
    --region $REGION \
    --force-delete-without-recovery \
    --output text > /dev/null 2>&1
  
  if [ $? -eq 0 ]; then
    echo "Deleted successfully"
  else
    echo "Failed or already deleted"
  fi
done <<< "$SECRETS"

echo ""
echo "Cleanup complete!"