#!/bin/bash
# Run script for ECS - sets environment variables and starts uvicorn

# Set default environment variables if not set
export STAGE=${STAGE:-dev}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export ENABLE_BEDROCK=${ENABLE_BEDROCK:-true}
export BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-anthropic.claude-3-5-sonnet-20240620-v1:0}
export ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-*}

# Start uvicorn server
exec uvicorn reportanalysis_enhanced_v2:app --host 0.0.0.0 --port 8000

