# Option 1: Comment out resources that already exist manually
# Option 2: Use CloudFormation resource import

# Since you created ECS manually, you likely also have:
# - ECR repository (report-analyzer-api)
# - IAM roles (ecsTaskExecutionRole, ecsTaskRole)
# - VPC (probably default VPC)
# - Log group (/ecs/report-analyzer-task)

# SOLUTION: Comment out existing resources and reference them by name/ARN

# To check what exists, run:
# aws ecs describe-clusters --clusters report-analyzer-cluster --region us-east-1
# aws ecr describe-repositories --repository-names report-analyzer-api --region us-east-1
# aws iam get-role --role-name ecsTaskExecutionRole --region us-east-1
# aws iam get-role --role-name ecsTaskRole --region us-east-1

# Then update serverless.yml to reference existing resources instead of creating them.

