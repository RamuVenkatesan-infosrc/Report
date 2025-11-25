# ECS Deployment Script for Windows PowerShell
# Run this script step by step or all at once

$AWS_REGION = "us-east-1"
$ACCOUNT_ID = "383574875115"  # Replace with your AWS account ID if different
$ECR_REPO = "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/report-analyzer-api"
$CLUSTER_NAME = "report-analyzer-cluster"
$SERVICE_NAME = "report-analyzer-service"

Write-Host "=== Step 2: Create ECR Repository ===" -ForegroundColor Green
try {
    aws ecr create-repository `
        --repository-name report-analyzer-api `
        --region $AWS_REGION `
        --image-scanning-configuration scanOnPush=true
    Write-Host "✅ ECR repository created" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Repository might already exist (this is OK)" -ForegroundColor Yellow
}

Write-Host "`n=== Step 3: Authenticate Docker to ECR ===" -ForegroundColor Green
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

Write-Host "`n=== Step 4: Tag and Push Image ===" -ForegroundColor Green
docker tag report-analyzer-api:latest $ECR_REPO`:latest
docker push $ECR_REPO`:latest

Write-Host "`n=== Step 5: Create ECS Cluster ===" -ForegroundColor Green
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION

Write-Host "`n=== Step 6: Create IAM Roles ===" -ForegroundColor Green
# Create trust policy
$trustPolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Principal = @{
                Service = "ecs-tasks.amazonaws.com"
            }
            Action = "sts:AssumeRole"
        }
    )
} | ConvertTo-Json

# Create execution role
try {
    aws iam create-role `
        --role-name ecsTaskExecutionRole `
        --assume-role-policy-document $trustPolicy
    Write-Host "✅ Execution role created" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Execution role might already exist" -ForegroundColor Yellow
}

# Attach managed policy
aws iam attach-role-policy `
    --role-name ecsTaskExecutionRole `
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create task role
try {
    aws iam create-role `
        --role-name ecsTaskRole `
        --assume-role-policy-document $trustPolicy
    Write-Host "✅ Task role created" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Task role might already exist" -ForegroundColor Yellow
}

# Create and attach task policy
$taskPolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Action = @(
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListModels",
                "bedrock:GetModel"
            )
            Resource = "*"
        },
        @{
            Effect = "Allow"
            Action = @(
                "aws-marketplace:ViewSubscriptions"
            )
            Resource = "*"
        },
        @{
            Effect = "Allow"
            Action = @(
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:DescribeTable"
            )
            Resource = "arn:aws:dynamodb:*:*:table/*"
        },
        @{
            Effect = "Allow"
            Action = @(
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            )
            Resource = "*"
        }
    )
} | ConvertTo-Json -Depth 10

aws iam put-role-policy `
    --role-name ecsTaskRole `
    --policy-name ECSBedrockDynamoDBPolicy `
    --policy-document $taskPolicy

Write-Host "`n=== Step 7: Create Task Definition ===" -ForegroundColor Green
# Create log group
aws logs create-log-group --log-group-name /ecs/report-analyzer-api --region $AWS_REGION 2>$null

# Create task definition JSON
$taskDef = @{
    family = "report-analyzer-api"
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = "1024"
    memory = "2048"
    executionRoleArn = "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole"
    taskRoleArn = "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskRole"
    containerDefinitions = @(
        @{
            name = "report-analyzer-api"
            image = "$ECR_REPO`:latest"
            essential = $true
            portMappings = @(
                @{
                    containerPort = 8000
                    protocol = "tcp"
                }
            )
            environment = @(
                @{ name = "STAGE"; value = "dev" }
                @{ name = "LOG_LEVEL"; value = "INFO" }
                @{ name = "ENABLE_BEDROCK"; value = "true" }
                @{ name = "BEDROCK_MODEL_ID"; value = "anthropic.claude-3-5-sonnet-20240620-v1:0" }
                @{ name = "ALLOWED_ORIGINS"; value = "*" }
                @{ name = "AWS_REGION"; value = "us-east-1" }
            )
            logConfiguration = @{
                logDriver = "awslogs"
                options = @{
                    "awslogs-group" = "/ecs/report-analyzer-api"
                    "awslogs-region" = "us-east-1"
                    "awslogs-stream-prefix" = "ecs"
                }
            }
        }
    )
} | ConvertTo-Json -Depth 10

$taskDef | Out-File -FilePath task-definition.json -Encoding UTF8

aws ecs register-task-definition `
    --cli-input-json file://task-definition.json `
    --region $AWS_REGION

Write-Host "`n=== Step 8: Get VPC and Networking ===" -ForegroundColor Green
$VPC_ID = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION
$SUBNET_IDS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $AWS_REGION) -replace "`t", ","
$SECURITY_GROUP_ID = aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=default" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION

Write-Host "VPC ID: $VPC_ID"
Write-Host "Subnet IDs: $SUBNET_IDS"
Write-Host "Security Group ID: $SECURITY_GROUP_ID"

# Allow port 8000
aws ec2 authorize-security-group-ingress `
    --group-id $SECURITY_GROUP_ID `
    --protocol tcp `
    --port 8000 `
    --cidr 0.0.0.0/0 `
    --region $AWS_REGION 2>$null

Write-Host "`n=== Step 9: Create ECS Service ===" -ForegroundColor Green
aws ecs create-service `
    --cluster $CLUSTER_NAME `
    --service-name $SERVICE_NAME `
    --task-definition report-analyzer-api `
    --desired-count 1 `
    --launch-type FARGATE `
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" `
    --region $AWS_REGION

Write-Host "`n=== Step 10: Get Service URL ===" -ForegroundColor Green
Write-Host "Waiting for service to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

$TASK_ARN = aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $AWS_REGION --query 'taskArns[0]' --output text

if ($TASK_ARN) {
    Write-Host "Task ARN: $TASK_ARN"
    Write-Host "`nYour service is starting! Check status with:" -ForegroundColor Green
    Write-Host "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
    Write-Host "`nTo get the public IP, run:" -ForegroundColor Green
    Write-Host "aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --region $AWS_REGION --query 'tasks[0].attachments[0].details[?name==\`networkInterfaceId\`].value' --output text | ForEach-Object { aws ec2 describe-network-interfaces --network-interface-ids `$_ --region $AWS_REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text }"
} else {
    Write-Host "Service is still starting. Wait a few minutes and check again." -ForegroundColor Yellow
}

Write-Host "`n✅ Deployment initiated! Check AWS Console for status." -ForegroundColor Green

