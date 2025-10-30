// Environment configuration
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:4723',
  appName: import.meta.env.VITE_APP_NAME || 'API Performance Analyzer',
  appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
} as const;

export default config;
