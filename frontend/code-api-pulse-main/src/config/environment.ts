// Environment configuration
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://report-analyzer-lb-676990092.us-east-1.elb.amazonaws.com',
  appName: import.meta.env.VITE_APP_NAME || 'API Performance Analyzer',
  appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
} as const;

export default config;
