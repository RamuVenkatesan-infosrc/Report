# Async Processing for Long-Running Endpoints

## Current Problem
Your `/analyze-worst-apis-with-github/` endpoint can take 30+ seconds, causing:
- **API Gateway**: 504 Gateway Timeout (30s limit)
- **Function URL**: Works but user waits long time with no feedback

## Async Processing Solution

Instead of waiting for the entire analysis to complete, we can:
1. **Start the job** and return immediately with a job ID
2. **Process in background** (Lambda function continues)
3. **Store results** in DynamoDB
4. **Frontend polls** for status updates
5. **User sees progress** instead of waiting

## Implementation Options

### Option 1: Simple In-Process Async (Recommended for Lambda)
- Return job ID immediately
- Process in same Lambda execution
- Store results in DynamoDB
- Frontend polls `/status/{job_id}`

**Pros:**
- Simple implementation
- No additional infrastructure
- Works within Lambda timeout (900s)

**Cons:**
- Lambda still running during processing
- Costs more Lambda execution time

### Option 2: Step Functions (Better for Production)
- Return job ID immediately
- Trigger Step Functions workflow
- Each step processes part of analysis
- Store results in DynamoDB
- Frontend polls for status

**Pros:**
- Better scalability
- Can handle very long operations
- Automatic retries
- Better monitoring

**Cons:**
- More complex setup
- Additional AWS services needed

### Option 3: SQS + Separate Worker Lambda (Best for Scale)
- Return job ID immediately
- Send message to SQS queue
- Separate Lambda worker processes jobs
- Store results in DynamoDB
- Frontend polls for status

**Pros:**
- Best scalability
- Can handle thousands of jobs
- Decouples API from processing
- Better cost optimization

**Cons:**
- Most complex
- Multiple Lambda functions
- SQS setup required

## Recommended: Option 1 (Simple Async)

### Backend Changes

1. **Create job endpoint** that returns immediately:
```python
@app.post("/analyze-worst-apis-with-github-async/")
async def analyze_worst_apis_with_github_async(...):
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Store job status in DynamoDB
    dynamodb_service.create_job(job_id, status="processing", ...)
    
    # Start processing in background (async task)
    asyncio.create_task(process_analysis_async(job_id, ...))
    
    # Return immediately
    return {
        "status": "accepted",
        "job_id": job_id,
        "message": "Analysis started. Poll /status/{job_id} for updates."
    }
```

2. **Background processing function**:
```python
async def process_analysis_async(job_id: str, ...):
    try:
        # Update status
        dynamodb_service.update_job_status(job_id, "processing", progress=0)
        
        # Step 1: Discover APIs
        dynamodb_service.update_job_status(job_id, "processing", progress=25, message="Discovering APIs...")
        discovered_apis = gh.discover_apis_in_repository(...)
        
        # Step 2: Match APIs
        dynamodb_service.update_job_status(job_id, "processing", progress=50, message="Matching APIs...")
        matched_apis = api_matcher.match_apis_with_color_coding(...)
        
        # Step 3: AI Analysis
        dynamodb_service.update_job_status(job_id, "processing", progress=75, message="Generating AI analysis...")
        ai_analysis = ai_analyzer.analyze_matched_apis(...)
        
        # Step 4: Store results
        dynamodb_service.update_job_status(job_id, "completed", progress=100, result=result)
        
    except Exception as e:
        dynamodb_service.update_job_status(job_id, "failed", error=str(e))
```

3. **Status polling endpoint**:
```python
@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = dynamodb_service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return {
        "job_id": job_id,
        "status": job["status"],  # pending, processing, completed, failed
        "progress": job.get("progress", 0),  # 0-100
        "message": job.get("message", ""),
        "result": job.get("result") if job["status"] == "completed" else None,
        "error": job.get("error") if job["status"] == "failed" else None
    }
```

### Frontend Changes

1. **Call async endpoint**:
```typescript
const response = await apiService.analyzeWorstApisWithGitHubAsync(worstApis, repo, branch);
const jobId = response.job_id;

// Start polling
pollJobStatus(jobId);
```

2. **Poll for status**:
```typescript
async function pollJobStatus(jobId: string) {
  const pollInterval = 2000; // 2 seconds
  
  const poll = async () => {
    const status = await apiService.getJobStatus(jobId);
    
    // Update UI with progress
    updateProgressBar(status.progress);
    updateStatusMessage(status.message);
    
    if (status.status === "completed") {
      // Show results
      displayResults(status.result);
      return;
    }
    
    if (status.status === "failed") {
      // Show error
      showError(status.error);
      return;
    }
    
    // Continue polling
    setTimeout(poll, pollInterval);
  };
  
  poll();
}
```

## Benefits

✅ **No timeout issues** - API returns immediately
✅ **Better UX** - User sees progress instead of waiting
✅ **Handles long operations** - Can take minutes without issues
✅ **User can navigate away** - Can come back and check status
✅ **Same Lambda function** - No additional infrastructure needed

## Next Steps

1. Implement async endpoint
2. Add job status tracking to DynamoDB
3. Update frontend to use async endpoint with polling
4. Add progress indicators to UI

Would you like me to implement this async solution?

