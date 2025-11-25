# Deploy ECS using Serverless Framework
# This script builds Docker image, pushes to ECR, then deploys with serverless

param(
    [string]$Stage = "dev",
    [string]$Region = "us-east-1"
)

Write-Host "=== Deploying ECS with Serverless Framework ===" -ForegroundColor Green

# Get AWS Account ID
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text --region $Region
if (-not $ACCOUNT_ID) {
    Write-Host "❌ Error: Could not get AWS Account ID. Make sure AWS credentials are configured." -ForegroundColor Red
    exit 1
}

Write-Host "`nAWS Account ID: $ACCOUNT_ID" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host "Stage: $Stage" -ForegroundColor Cyan

# Set variables
$ECR_REPO = "report-analyzer-api"
$IMAGE_TAG = "$Stage-latest"
$ECR_URI = "$ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/$ECR_REPO`:$IMAGE_TAG"

Write-Host "`n=== Step 1: Build Docker Image ===" -ForegroundColor Green
docker build -t $ECR_REPO`:$IMAGE_TAG .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 2: Login to ECR ===" -ForegroundColor Green
$ECR_REGISTRY = "$ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com"
$ECR_PASSWORD = aws ecr get-login-password --region $Region 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to get ECR password!" -ForegroundColor Red
    Write-Host $ECR_PASSWORD -ForegroundColor Red
    exit 1
}

# Use PowerShell's proper way to pipe password
$ECR_PASSWORD | docker login --username AWS --password-stdin $ECR_REGISTRY

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ECR login failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Logged in to ECR: $ECR_REGISTRY" -ForegroundColor Green

Write-Host "`n=== Step 3: Tag Image ===" -ForegroundColor Green
docker tag $ECR_REPO`:$IMAGE_TAG $ECR_URI

Write-Host "`n=== Step 4: Push to ECR ===" -ForegroundColor Green
docker push $ECR_URI

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker push failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 5: Deploy with Serverless ===" -ForegroundColor Green
$env:AWS_ACCOUNT_ID = $ACCOUNT_ID
serverless deploy --stage $Stage --region $Region

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Serverless deployment failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 6: Get Service URL ===" -ForegroundColor Green
$STACK_NAME = "report-analyzer-api-$Stage"
$ALB_URL = aws cloudformation describe-stacks `
    --stack-name $STACK_NAME `
    --query 'Stacks[0].Outputs[?OutputKey==`PublicURL`].OutputValue' `
    --output text `
    --region $Region

if ($ALB_URL) {
    Write-Host "`n✅ Deployment Complete!" -ForegroundColor Green
    Write-Host "`n🌐 Your ECS Service URL: $ALB_URL" -ForegroundColor Cyan
    Write-Host "`nUpdate your frontend .env file:" -ForegroundColor Yellow
    Write-Host "VITE_API_BASE_URL=$ALB_URL" -ForegroundColor White
} else {
    Write-Host "`n⚠️ Could not retrieve ALB URL. Check CloudFormation console." -ForegroundColor Yellow
}

Write-Host "`n=== Done ===" -ForegroundColor Green

