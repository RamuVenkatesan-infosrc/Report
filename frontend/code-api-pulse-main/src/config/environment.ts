// Environment configuration
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:4723',
  // Lambda Function URL for long-running endpoints (supports up to 900 seconds vs API Gateway's 30 seconds)
  // Use this for endpoints that might take longer than 30 seconds
  functionUrl: import.meta.env.VITE_LAMBDA_FUNCTION_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:4723',
  appName: import.meta.env.VITE_APP_NAME || 'API Performance Analyzer',
  appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
} as const;

export default config;
