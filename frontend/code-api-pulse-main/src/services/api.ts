// API service for backend communication
import config from '@/config/environment';

const API_BASE_URL = config.apiBaseUrl;

export interface AnalysisConfig {
  response_time_good_threshold?: number;
  response_time_bad_threshold?: number;
  error_rate_good_threshold?: number;
  error_rate_bad_threshold?: number;
  throughput_good_threshold?: number;
  throughput_bad_threshold?: number;
  percentile_95_latency_good_threshold?: number;
  percentile_95_latency_bad_threshold?: number;
}

export interface AnalysisResult {
  endpoint: string;
  avg_response_time_ms: number;
  error_rate_percent: number;
  throughput_rps: number;
  percentile_95_latency_ms: number;
  is_good_response_time?: boolean;
  is_bad_response_time?: boolean;
  is_good_error_rate?: boolean;
  is_bad_error_rate?: boolean;
  is_good_throughput?: boolean;
  is_bad_throughput?: boolean;
  is_good_percentile_95_latency?: boolean;
  is_bad_percentile_95_latency?: boolean;
}

export interface PerformanceAnalysis {
  best_api: AnalysisResult[];
  worst_api: AnalysisResult[];
  details: AnalysisResult[];
  overall_percentile_95_latency_ms: number;
  insights?: {
    summary: string;
    recommendations: string[];
    key_metrics: {
      total_apis: number;
      best_performing: number;
      worst_performing: number;
      moderate_performing: number;
      unmatched_conditions: number;
      avg_response_time_ms: number;
      avg_error_rate_percent: number;
      avg_throughput_rps: number;
      overall_95th_percentile_ms: number;
    };
    trends: {
      response_time_consistency: string;
      error_rate_stability: string;
      throughput_efficiency: string;
    };
    unmatched_conditions?: {
      endpoint: string;
      response_time_ms: number;
      error_rate_percent: number;
      throughput_rps: number;
      percentile_95_latency_ms: number;
      reason: string;
    }[];
  };
}

export interface AnalysisResponse {
  status: string;
  analysis: PerformanceAnalysis;
  summary: string;
  processed_files: string[];
  skipped_files: string[];
  thresholds_used?: AnalysisConfig;
}

export interface HealthResponse {
  status: string;
  service: string;
  features: string[];
  github_token_status: string;
  github_rate_limit: string;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  async analyzeReport(file: File, config: AnalysisConfig = {}): Promise<AnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Add configuration parameters
    Object.entries(config).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, value.toString());
      }
    });

    const response = await fetch(`${this.baseUrl}/analyze-report/`, {
      method: 'POST',
      body: formData,
    });

    return this.handleResponse<AnalysisResponse>(response);
  }

  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    return this.handleResponse<HealthResponse>(response);
  }

  async configureGitHubToken(token: string): Promise<{ status: string; message: string; token_valid: boolean }> {
    const response = await fetch(`${this.baseUrl}/github/configure-token?token=${encodeURIComponent(token)}`, {
      method: 'POST',
    });
    return this.handleResponse(response);
  }

  async getGitHubTokenStatus(): Promise<{ has_token: boolean; token_valid: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/github/token-status`);
    return this.handleResponse(response);
  }

  async searchRepositories(query: string, language?: string): Promise<{ status: string; repositories: any[]; total_found: number }> {
    const params = new URLSearchParams({ query });
    if (language) params.append('language', language);
    
    const response = await fetch(`${this.baseUrl}/github/repositories?${params}`);
    return this.handleResponse(response);
  }

  async analyzeWithGitHub(file: File, githubRepo: string, config: AnalysisConfig = {}): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('github_repo', githubRepo);

    // Add configuration parameters
    Object.entries(config).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, value.toString());
      }
    });

    const response = await fetch(`${this.baseUrl}/analyze-with-github/`, {
      method: 'POST',
      body: formData,
    });

    return this.handleResponse(response);
  }

  // getRepositoryInfo is implemented later with optional token support


  async analyzeGitHubWithCodeSuggestions(worstApis: AnalysisResult[], githubRepo: string, branch?: string): Promise<any> {
    // Normalize GitHub repository URL
    let normalizedRepo = githubRepo;
    if (githubRepo.startsWith('https://github.com/') || githubRepo.startsWith('http://github.com/')) {
      normalizedRepo = githubRepo.replace('https://github.com/', '').replace('http://github.com/', '');
    }

    const params = new URLSearchParams({ github_repo: normalizedRepo });
    if (branch) {
      params.append('branch', branch);
    }

    const response = await fetch(`${this.baseUrl}/analyze-github-with-code-suggestions/?${params}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ worst_apis: worstApis }),
    });

    return this.handleResponse(response);
  }


  async analyzeGitHubRepository(githubRepo: string, branch?: string): Promise<any> {
    // Normalize GitHub repository URL
    let normalizedRepo = githubRepo;
    if (githubRepo.startsWith('https://github.com/') || githubRepo.startsWith('http://github.com/')) {
      normalizedRepo = githubRepo.replace('https://github.com/', '').replace('http://github.com/', '');
    }

    const params = new URLSearchParams({ github_repo: normalizedRepo });
    if (branch) {
      params.append('branch', branch);
    }

    const response = await fetch(`${this.baseUrl}/analyze-github-repository/?${params}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return this.handleResponse(response);
  }

  async analyzeFullRepository(githubRepo: string, branch?: string, token?: string): Promise<any> {
    // Normalize GitHub repository URL
    let normalizedRepo = githubRepo;
    if (githubRepo.startsWith('https://github.com/') || githubRepo.startsWith('http://github.com/')) {
      normalizedRepo = githubRepo.replace('https://github.com/', '').replace('http://github.com/', '');
    }

    const params = new URLSearchParams({ github_repo: normalizedRepo });
    if (branch) {
      params.append('branch', branch);
    }
    if (token) {
      params.append('token', token);
    }

    const response = await fetch(`${this.baseUrl}/analyze-full-repository/?${params}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return this.handleResponse(response);
  }

  async analyzeWorstApisWithGitHub(worstApis: any[], githubRepo: string, branch?: string, token?: string): Promise<any> {
    // Normalize GitHub repository URL
    let normalizedRepo = githubRepo;
    if (githubRepo.startsWith('https://github.com/') || githubRepo.startsWith('http://github.com/')) {
      normalizedRepo = githubRepo.replace('https://github.com/', '').replace('http://github.com/', '');
    }

    const params = new URLSearchParams({ github_repo: normalizedRepo });
    if (branch) {
      params.append('branch', branch);
    }
    if (token) {
      params.append('token', token);
    }

    const response = await fetch(`${this.baseUrl}/analyze-worst-apis-with-github/?${params}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ worst_apis: worstApis }),
    });

    return this.handleResponse(response);
  }

  // GitHub connection methods
  async getRepositoryInfo(githubRepo: string, token?: string): Promise<any> {
    // Normalize GitHub repository URL
    let normalizedRepo = githubRepo;
    if (githubRepo.startsWith('https://github.com/') || githubRepo.startsWith('http://github.com/')) {
      normalizedRepo = githubRepo.replace('https://github.com/', '').replace('http://github.com/', '');
    }

    const params = new URLSearchParams({ github_repo: normalizedRepo });
    if (token) {
      params.append('token', token);
    }

    const response = await fetch(`${this.baseUrl}/repository-info/${encodeURIComponent(normalizedRepo)}?${params}`);
    return this.handleResponse(response);
  }

  async getRepositoryBranches(githubRepo: string, token?: string): Promise<string[]> {
    // Normalize GitHub repository URL
    let normalizedRepo = githubRepo;
    if (githubRepo.startsWith('https://github.com/') || githubRepo.startsWith('http://github.com/')) {
      normalizedRepo = githubRepo.replace('https://github.com/', '').replace('http://github.com/', '');
    }

    const params = new URLSearchParams({ github_repo: normalizedRepo });
    if (token) {
      params.append('token', token);
    }

    const response = await fetch(`${this.baseUrl}/repository-branches/${encodeURIComponent(normalizedRepo)}?${params}`);
    const data = await this.handleResponse<{ branches: string[] }>(response);
    return data.branches || [];
  }

  async getLatestPerformanceAnalysis(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/latest-performance-analysis/`);
    return this.handleResponse(response);
  }

  async clearAnalysis(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/clear-analysis/`, {
      method: 'POST',
    });
    return this.handleResponse(response);
  }
}

export const apiService = new ApiService();
export default apiService;
