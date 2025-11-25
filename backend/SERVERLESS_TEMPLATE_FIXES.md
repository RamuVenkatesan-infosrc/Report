# Serverless.yml Template - Fixed for Existing Manual Resources

## ✅ What Was Fixed

### 1. **Task Family Name**
- **Before**: `report-analyzer-task`
- **After**: `report-analyzer-api` (matches existing task definition)

### 2. **Log Group Name**
- **Before**: `/ecs/report-analyzer-task`
- **After**: `/ecs/report-analyzer-api` (matches existing log group)

### 3. **Commented Out Existing Resources**
- ✅ ECR Repository (already exists)
- ✅ ECS Cluster (already exists)
- ✅ IAM Roles (ecsTaskExecutionRole, ecsTaskRole already exist)
- ✅ Log Group (already exists)

### 4. **Fixed References**
- ✅ Task Definition uses ARN references for existing IAM roles
- ✅ ECS Service references existing cluster by name
- ✅ Log configuration uses existing log group name

## ⚠️ Important Notes

### VPC Issue
Your existing ECS service uses the **default VPC**, but this template creates a **new VPC** for the ALB. 

**Options:**

#### Option 1: Delete Existing Service (Recommended)
```powershell
# Delete existing service first
aws ecs delete-service `
  --cluster report-analyzer-cluster `
  --service report-analyzer-service `
  --force `
  --region us-east-1

# Wait for deletion (takes 1-2 minutes)
# Then deploy with serverless
cd backend
.\deploy-ecs-serverless.ps1
```

#### Option 2: Keep Existing Service, Create ALB Separately
- Deploy serverless (creates ALB in new VPC)
- Manually attach ALB to existing service
- Or update service manually to use new VPC

## 📋 Resources Status

### ✅ Already Exist (Commented Out)
- ECR Repository: `report-analyzer-api`
- ECS Cluster: `report-analyzer-cluster`
- IAM Role: `ecsTaskExecutionRole`
- IAM Role: `ecsTaskRole`
- Log Group: `/ecs/report-analyzer-api`
- ECS Service: `report-analyzer-service` (exists but may need update)

### 🆕 Will Be Created
- VPC (new, for ALB)
- Subnets (2 public subnets)
- Internet Gateway
- Security Groups (ALB + Service)
- ALB (Application Load Balancer)
- Target Group
- Listener
- Task Definition (new revision)
- ECS Service (updated with ALB)

## 🚀 Deployment Steps

1. **Set AWS Credentials**
   ```powershell
   $env:AWS_ACCESS_KEY_ID = "your-key"
   $env:AWS_SECRET_ACCESS_KEY = "your-secret"
   $env:AWS_SESSION_TOKEN = "your-token"  # if using temporary
   ```

2. **Deploy**
   ```powershell
   cd backend
   .\deploy-ecs-serverless.ps1
   ```

3. **If Service Update Fails**
   - Delete existing service first (see Option 1 above)
   - Then redeploy

## ✅ What This Template Does

1. Builds Docker image
2. Pushes to existing ECR repository
3. Creates/updates task definition (new revision)
4. Creates new VPC and networking
5. Creates ALB with 600s timeout
6. Updates existing ECS service to use ALB

## 📝 Next Steps

After successful deployment:
1. Get ALB URL from CloudFormation outputs
2. Update frontend `.env` with ALB URL
3. Test the application


