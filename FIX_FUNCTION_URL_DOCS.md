# Fix for Function URL Docs Not Loading

## Problem
When accessing FastAPI docs at Function URL:
- ❌ `https://67z7tlitf2i5qf2etx7ndslyey0eicxc.lambda-url.us-east-1.on.aws/docs`
- Error: `Failed to load API definition. Not Found /dev/openapi.json`

But API Gateway works fine:
- ✅ `https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev/docs`

## Root Cause
- **API Gateway** includes stage prefix in path: `/dev/docs`, `/dev/openapi.json`
- **Function URL** has no stage prefix: `/docs`, `/openapi.json`
- FastAPI was hardcoded with `root_path="/dev"` which caused OpenAPI schema to look for `/dev/openapi.json` even when accessed via Function URL

## Solution Applied

### 1. Dynamic Root Path
Changed from hardcoded `root_path="/dev"` to dynamic detection:
```python
STAGE = os.getenv("STAGE", "")
root_path = f"/{STAGE}" if STAGE else ""
```

### 2. Custom OpenAPI and Docs Routes
Added custom handlers for `/openapi.json`, `/docs`, and `/redoc` that dynamically adjust root_path based on the request source:
```python
@app.get("/openapi.json", include_in_schema=False)
async def custom_openapi(request: Request):
    # Uses request.scope["root_path"] which is set correctly by Mangum
    actual_root_path = request.scope.get("root_path", "").rstrip("/")
    # Updates OpenAPI schema servers accordingly

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    # Constructs openapi_url using actual root_path from request
    actual_root_path = request.scope.get("root_path", "").rstrip("/")
    openapi_url = f"{actual_root_path}/openapi.json"
    # Returns Swagger UI with correct openapi_url
```

### 3. Root Path Configuration
Set `root_path_in_servers=False` to let FastAPI auto-detect from request scope instead of using the app's default root_path.

## Testing

After deploying, both should work:

### API Gateway (with /dev prefix):
```
https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev/docs
https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev/openapi.json
```

### Function URL (no prefix):
```
https://67z7tlitf2i5qf2etx7ndslyey0eicxc.lambda-url.us-east-1.on.aws/docs
https://67z7tlitf2i5qf2etx7ndslyey0eicxc.lambda-url.us-east-1.on.aws/openapi.json
```

## Deployment

1. **Redeploy backend:**
   ```bash
   cd backend
   serverless deploy
   ```

2. **Test Function URL docs:**
   - Visit: `https://67z7tlitf2i5qf2etx7ndslyey0eicxc.lambda-url.us-east-1.on.aws/docs`
   - Should load without errors

3. **Test API Gateway docs (should still work):**
   - Visit: `https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev/docs`
   - Should still work as before

## How It Works

1. **Mangum** (the ASGI adapter) sets `request.scope["root_path"]` correctly:
   - API Gateway requests: `root_path = "/dev"`
   - Function URL requests: `root_path = ""`

2. **Custom OpenAPI route** reads the root_path from request scope and updates the OpenAPI schema servers array accordingly.

3. **Swagger UI** uses the correct OpenAPI URL based on the request source.

## Notes

- Both API Gateway and Function URL work simultaneously
- The same Lambda function handles both
- No environment variable changes needed
- Backward compatible - existing API Gateway URLs still work

