"""
Lambda handler for FastAPI application using Mangum adapter.
This file allows the FastAPI app to run on AWS Lambda via API Gateway.
"""
from mangum import Mangum
from reportanalysis_enhanced_v2 import app

# Create Mangum handler - this wraps FastAPI for Lambda
handler = Mangum(app, lifespan="off")

