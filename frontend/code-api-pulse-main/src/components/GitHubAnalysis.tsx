import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Github, GitBranch, Code2, AlertCircle, CheckCircle2, ExternalLink, Eye, FileText, LayoutTemplate, ArrowRight, Zap, Loader2 } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Toggle } from '@/components/ui/toggle';
import { AnalysisResult, apiService } from '@/services/api';
import DiffViewer from './DiffViewer';

interface GitHubAnalysisProps {
  issuesApis?: AnalysisResult[];
  onAnalysisComplete?: (results: any) => void;
}

const GitHubAnalysis = ({ issuesApis = [], onAnalysisComplete }: GitHubAnalysisProps) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [token, setToken] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [viewMode, setViewMode] = useState<'side-by-side' | 'text-diff' | 'one-by-one'>('side-by-side');
  const [selectedSuggestion, setSelectedSuggestion] = useState(0);
  const [analysisResults, setAnalysisResults] = useState<any[]>([]);
  const [matchedApis, setMatchedApis] = useState<any[]>([]);
  const [unmatchedApis, setUnmatchedApis] = useState<any[]>([]);
  const [branches, setBranches] = useState<string[]>([]);
  const [detailedComparison, setDetailedComparison] = useState<any>(null);
  const [diffAnalysis, setDiffAnalysis] = useState<any[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<any>(null);
  const [isLoadingBranches, setIsLoadingBranches] = useState(false);
  const [branchError, setBranchError] = useState<string>('');
  const [repositoryInfo, setRepositoryInfo] = useState<any>(null);

  // Helper function to generate diff text
  const generateDiff = (oldCode: string, newCode: string): string => {
    if (!oldCode && !newCode) return 'No code to compare';
    if (!oldCode) return `+${newCode}`;
    if (!newCode) return `-${oldCode}`;
    
    const oldLines = oldCode.split('\n');
    const newLines = newCode.split('\n');
    let diff = '--- Current Code\n+++ Improved Code\n';
    
    const maxLines = Math.max(oldLines.length, newLines.length);
    let hasChanges = false;
    
    for (let i = 0; i < maxLines; i++) {
      const oldLine = oldLines[i] || '';
      const newLine = newLines[i] || '';
      
      if (oldLine !== newLine) {
        hasChanges = true;
        if (oldLine && newLine) {
          // Modified line
          diff += `@@ -${i + 1},1 +${i + 1},1 @@\n`;
          diff += `-${oldLine}\n`;
          diff += `+${newLine}\n`;
        } else if (oldLine) {
          // Deleted line
          diff += `@@ -${i + 1},1 +${i + 1},0 @@\n`;
          diff += `-${oldLine}\n`;
        } else if (newLine) {
          // Added line
          diff += `@@ -${i + 1},0 +${i + 1},1 @@\n`;
          diff += `+${newLine}\n`;
        }
      } else if (oldLine) {
        // Unchanged line
        diff += ` ${oldLine}\n`;
      }
    }
    
    return hasChanges ? diff : 'No differences found';
  };

  const handleConnect = async () => {
    if (!repoUrl || !token) {
      alert('Please provide both repository URL and token');
      return;
    }

    setIsLoadingBranches(true);
    setBranchError('');
    setBranches([]);
    setSelectedBranch('');

    try {
      // First configure the GitHub token
      await apiService.configureGitHubToken(token);
      
      // Then fetch repository information and branches
      const repoInfo = await apiService.getRepositoryInfo(repoUrl);
      
      setRepositoryInfo(repoInfo.repository);
      setBranches(repoInfo.branches.map((branch: any) => branch.name));
      
      // Auto-select default branch if available
      if (repoInfo.default_branch) {
        setSelectedBranch(repoInfo.default_branch);
      }
      
      setIsConnected(true);
    } catch (error: any) {
      console.error('Failed to connect to repository:', error);
      setBranchError(error.message || 'Failed to fetch repository information');
      setIsConnected(false);
    } finally {
      setIsLoadingBranches(false);
    }
  };

  const handleAnalyze = async () => {
    if (!repoUrl || !token || !selectedBranch) {
      alert('Please provide repository URL, token, and select a branch');
      return;
    }

    if (issuesApis.length === 0) {
      alert('No Issues APIs available for analysis. Please run report analysis first.');
      return;
    }

    setIsAnalyzing(true);
    
    try {
      // Call the enhanced backend API to analyze Issues APIs against GitHub source code
      const analysisResults = await apiService.analyzeGitHubWithCodeSuggestions(
        issuesApis,
        repoUrl,
        selectedBranch
      );
      
      // Process the enhanced results - the backend returns a new structure
      const data = analysisResults.data || analysisResults;
      
      // Check if this is a warning response (no APIs found)
      if (analysisResults.status === 'warning') {
        console.warn('GitHub Analysis Warning:', analysisResults.message);
        console.warn('Suggestions:', analysisResults.suggestions);
        
        // Set empty results for warning case
        setMatchedApis([]);
        setUnmatchedApis([]);
        setAnalysisResults([]);
        setDetailedComparison({
          status: "warning",
          matched_apis: [],
          unmatched_performance_apis: [],
          unmatched_source_apis: []
        });
        setDiffAnalysis([]);
        setAnalysisComplete(true);
        
        // Show warning message to user
        alert(`GitHub Analysis Warning: ${analysisResults.message}\n\nSuggestions:\n${analysisResults.suggestions.join('\n')}`);
        return;
      }
      
      // Validate response structure
      if (!data) {
        throw new Error('Invalid response structure from backend');
      }
      
      // Extract matched APIs with detailed information
      const matchedApis = data.detailed_matches || [];
      const discoveredApis = data.discovered_apis || [];
      const codeSuggestions = data.code_suggestions || [];
      const unmatchedApis = []; // Will be populated from performance analysis
      
      // Extract diff analysis
      const diffAnalysis = data.diff_analysis || [];
      
      // Create matching analysis structure
      const matchingAnalysis = {
        status: "completed",
        matched_apis: matchedApis,
        unmatched_performance_apis: [],
        unmatched_source_apis: []
      };
      
      console.log('Enhanced GitHub Analysis Results:', {
        matchedApis: matchedApis.length,
        discoveredApis: discoveredApis.length,
        codeSuggestions: codeSuggestions.length,
        diffAnalysis: diffAnalysis.length,
        summary: data.summary,
        repositoryInfo: data.repository_info,
        fullResponse: analysisResults
      });
      
      setMatchedApis(matchedApis);
      setUnmatchedApis(unmatchedApis);
      setAnalysisResults(discoveredApis);
      setCodeImprovements(codeSuggestions);
      setDetailedComparison(matchingAnalysis);
      setDiffAnalysis(diffAnalysis);
      setAnalysisComplete(true);
      
      if (onAnalysisComplete) {
        onAnalysisComplete({
          matched: matchedApis,
          unmatched: unmatchedApis,
          discovered: discoveredApis,
          analysis: analysisResults,
          matchingAnalysis: matchingAnalysis
        });
      }
    } catch (error: any) {
      console.error('Analysis failed:', error);
      alert(`Analysis failed: ${error.message || 'Please try again.'}`);
    } finally {
      setIsAnalyzing(false);
    }
  };


  
  const [codeImprovements, setCodeImprovements] = useState<any[]>([]);
  
  const renderCodeView = () => {
    if (codeImprovements.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <p>No code improvements available</p>
          <p className="text-sm">This could mean:</p>
          <ul className="text-sm text-left mt-2 space-y-1">
            <li>• No APIs were found in the repository</li>
            <li>• No performance issues were detected</li>
            <li>• Repository is private and no GitHub token is provided</li>
            <li>• Analysis is still in progress</li>
          </ul>
          <p className="text-sm mt-4">
            <strong>Suggestions:</strong> Try analyzing a different repository or ensure the repository contains API code.
          </p>
        </div>
      );
    }
    
    const improvement = codeImprovements[selectedSuggestion];
    
    switch (viewMode) {
      case 'side-by-side':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <h5 className="font-medium mb-2 text-sm flex items-center">
                <AlertCircle className="w-4 h-4 mr-2 text-destructive" />
                Current Code (Problematic)
              </h5>
              <div className="bg-code-bg border border-code-border rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                <pre className="text-destructive whitespace-pre-wrap">{improvement.beforeCode}</pre>
              </div>
            </div>
            <div>
              <h5 className="font-medium mb-2 text-sm flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-2 text-success" />
                Improved Code
              </h5>
              <div className="bg-code-bg border border-code-border rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                <pre className="text-success whitespace-pre-wrap">{improvement.afterCode}</pre>
              </div>
            </div>
          </div>
        );
        
      case 'text-diff':
        return (
          <div>
            <h5 className="font-medium mb-2 text-sm">Unified Diff View</h5>
            <div className="bg-code-bg border border-code-border rounded p-3 text-sm font-mono max-h-96 overflow-y-auto">
              <div className="text-muted-foreground mb-2">@@ -{improvement.file} @@</div>
              {improvement.beforeCode.split('\n').map((line, i) => (
                <div key={`before-${i}`} className="text-destructive">- {line}</div>
              ))}
              {improvement.afterCode.split('\n').map((line, i) => (
                <div key={`after-${i}`} className="text-success">+ {line}</div>
              ))}
            </div>
          </div>
        );
        
      case 'one-by-one':
        return (
          <div className="space-y-4">
            <div>
              <h5 className="font-medium mb-2 text-sm flex items-center">
                <AlertCircle className="w-4 h-4 mr-2 text-destructive" />
                Current Code (Problematic)
              </h5>
              <div className="bg-code-bg border border-code-border rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                <pre className="text-destructive whitespace-pre-wrap">{improvement.beforeCode}</pre>
              </div>
            </div>
            
            <div className="flex items-center justify-center">
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <Separator className="w-8" />
                <span>Improved to</span>
                <Separator className="w-8" />
              </div>
            </div>
            
            <div>
              <h5 className="font-medium mb-2 text-sm flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-2 text-success" />
                Improved Code
              </h5>
              <div className="bg-code-bg border border-code-border rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                <pre className="text-success whitespace-pre-wrap">{improvement.afterCode}</pre>
              </div>
            </div>
          </div>
        );
        
      default:
        return null;
    }
  };
  
  return (
    <div className="space-y-8">
      {/* Repository Connection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Github className="h-5 w-5" />
            <span>Repository Connection</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="repo-url">Repository URL</Label>
              <Input
                id="repo-url"
                placeholder="https://github.com/username/repository"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="github-token">GitHub Token</Label>
              <Input
                id="github-token"
                type="password"
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <Button 
              onClick={handleConnect} 
              disabled={!repoUrl || !token || isConnected || isLoadingBranches}
            >
              {isLoadingBranches ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Connecting...
                </>
              ) : isConnected ? (
                'Connected'
              ) : (
                'Connect Repository'
              )}
            </Button>
            {isConnected && (
              <Badge variant="secondary" className="bg-success/20 text-success">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                Repository Connected
              </Badge>
            )}
          </div>
          
          {branchError && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <p className="text-sm text-destructive">{branchError}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Issues APIs from Report Analysis */}
      {issuesApis.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <span>Issues APIs from Report Analysis</span>
              <Badge variant="destructive">{issuesApis.length} APIs</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                These APIs will be analyzed against the source code to find matches and improvement suggestions.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {issuesApis.map((api, index) => (
                  <div key={index} className="p-3 bg-destructive/10 rounded-lg border border-destructive/20">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-destructive">{api.endpoint}</p>
                        <p className="text-sm text-muted-foreground">
                          {api.avg_response_time_ms?.toFixed(0)}ms • {api.error_rate_percent?.toFixed(1)}% error
                        </p>
                      </div>
                      <Badge variant="destructive" className="text-xs">
                        Issue
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Branch Selection */}
      {isConnected && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <GitBranch className="h-5 w-5" />
              <span>Branch Analysis</span>
              {repositoryInfo && (
                <Badge variant="outline" className="ml-2">
                  {repositoryInfo.full_name}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="branch-select">Select Branch</Label>
                  <Select value={selectedBranch} onValueChange={setSelectedBranch}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a branch" />
                    </SelectTrigger>
                    <SelectContent>
                      {isLoadingBranches ? (
                        <SelectItem value="loading" disabled>
                          <div className="flex items-center space-x-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Loading branches...</span>
                          </div>
                        </SelectItem>
                      ) : branches.length === 0 ? (
                        <SelectItem value="no-branches" disabled>
                          No branches available
                        </SelectItem>
                      ) : (
                        branches.map((branch) => (
                          <SelectItem key={branch} value={branch}>
                            <div className="flex items-center space-x-2">
                              <GitBranch className="w-3 h-3" />
                              <span>{branch}</span>
                              {branch === repositoryInfo?.default_branch && (
                                <Badge variant="secondary" className="text-xs">default</Badge>
                              )}
                            </div>
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  {branches.length > 0 && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Found {branches.length} branch{branches.length !== 1 ? 'es' : ''}
                    </p>
                  )}
                </div>
                <div className="flex items-end">
                  <Button 
                    onClick={handleAnalyze} 
                    disabled={!selectedBranch || isAnalyzing || isLoadingBranches}
                    className="w-full"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Analyzing Source Code...
                      </>
                    ) : (
                      'Analyze Source Code'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Debug Information */}
      {analysisComplete && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5" />
              <span>Analysis Debug Info</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <p><strong>Discovered APIs:</strong> {analysisResults.length}</p>
              <p><strong>Matched APIs:</strong> {matchedApis.length}</p>
              <p><strong>Unmatched APIs:</strong> {unmatchedApis.length}</p>
              <p><strong>Repository:</strong> {repositoryInfo?.full_name || 'Unknown'}</p>
              <p><strong>Branch:</strong> {selectedBranch}</p>
              <details className="mt-4">
                <summary className="cursor-pointer font-medium">Sample API Data</summary>
                <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-h-40">
                  {JSON.stringify(analysisResults.slice(0, 2), null, 2)}
                </pre>
              </details>
              <details className="mt-2">
                <summary className="cursor-pointer font-medium">Full Response Data</summary>
                <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-h-40">
                  {JSON.stringify(analysisResults, null, 2)}
                </pre>
              </details>
            </div>
          </CardContent>
        </Card>
      )}

      {/* API Endpoints Analysis */}
      {analysisComplete && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center space-x-2">
                  <Code2 className="h-5 w-5" />
                  <span>API Endpoints Found in Source Code</span>
                </span>
                <Badge variant="outline">{analysisResults.length} endpoints</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analysisResults.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>No API endpoints found in source code</p>
                    <p className="text-sm">This could mean:</p>
                    <ul className="text-sm text-left mt-2 space-y-1">
                      <li>• Repository is private and no GitHub token is provided</li>
                      <li>• Repository doesn't contain API code</li>
                      <li>• API patterns are not recognized</li>
                      <li>• GitHub API rate limiting</li>
                    </ul>
                    <p className="text-sm mt-4">
                      <strong>Suggestions:</strong> Try a different repository, provide a GitHub token, or check if the repository contains API code.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Search and Filter Bar */}
                    <div className="flex items-center space-x-4">
                      <div className="relative flex-1">
                        <input
                          type="text"
                          placeholder="Search APIs..."
                          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                        </div>
                      </div>
                      <button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                        <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.207A1 1 0 013 6.5V4z" />
                        </svg>
                        <span>All Methods</span>
                      </button>
                    </div>

                    {/* API Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left py-3 px-4 font-medium text-gray-700">Method</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-700">Endpoint</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-700">File</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-700">Line</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {analysisResults.map((api, index) => {
                            const endpoint = api.endpoint || '';
                            
                            // Extract method from the endpoint or use default
                            let method = 'GET';
                            let cleanEndpoint = endpoint;
                            
                            if (endpoint.startsWith('POST ')) {
                              method = 'POST';
                              cleanEndpoint = endpoint.replace(/^POST\s+/, '');
                            } else if (endpoint.startsWith('GET ')) {
                              method = 'GET';
                              cleanEndpoint = endpoint.replace(/^GET\s+/, '');
                            } else if (endpoint.startsWith('PUT ')) {
                              method = 'PUT';
                              cleanEndpoint = endpoint.replace(/^PUT\s+/, '');
                            } else if (endpoint.startsWith('DELETE ')) {
                              method = 'DELETE';
                              cleanEndpoint = endpoint.replace(/^DELETE\s+/, '');
                            } else if (endpoint.startsWith('PATCH ')) {
                              method = 'PATCH';
                              cleanEndpoint = endpoint.replace(/^PATCH\s+/, '');
                            } else {
                              // If no method prefix, try to determine from the function name or context
                              const functionName = api.function_name || '';
                              if (functionName.toLowerCase().includes('post') || functionName.toLowerCase().includes('create') || functionName.toLowerCase().includes('update')) {
                                method = 'POST';
                              } else if (functionName.toLowerCase().includes('delete') || functionName.toLowerCase().includes('remove')) {
                                method = 'DELETE';
                              } else if (functionName.toLowerCase().includes('put') || functionName.toLowerCase().includes('modify')) {
                                method = 'PUT';
                              }
                              cleanEndpoint = endpoint;
                            }
                            
                            // Get line number from the backend (now properly provided)
                            const lineNumber = api.line_number || 'N/A';
                            
                            // Debug: Log the first few APIs to see their structure
                            if (index < 3) {
                              console.log(`API ${index}:`, {
                                endpoint: api.endpoint,
                                line_number: api.line_number,
                                file_path: api.file_path,
                                function_name: api.function_name
                              });
                            }
                            
                            return (
                              <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="py-3 px-4">
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                    method === 'GET' ? 'bg-blue-100 text-blue-800' :
                                    method === 'POST' ? 'bg-green-100 text-green-800' :
                                    method === 'PUT' ? 'bg-orange-100 text-orange-800' :
                                    method === 'DELETE' ? 'bg-red-100 text-red-800' :
                                    method === 'PATCH' ? 'bg-purple-100 text-purple-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {method}
                                  </span>
                                </td>
                                <td className="py-3 px-4 font-mono text-sm">{cleanEndpoint}</td>
                                <td className="py-3 px-4 text-sm text-gray-600">{api.file_path || 'Unknown'}</td>
                                <td className="py-3 px-4 text-sm text-gray-600">{lineNumber}</td>
                                <td className="py-3 px-4">
                                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    Detected
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Detailed Comparison Results */}
          {analysisComplete && detailedComparison && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Code2 className="h-5 w-5" />
                  <span>Detailed API Comparison & Improvements</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Summary Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {detailedComparison.summary?.total_matches || 0}
                      </div>
                      <div className="text-sm text-green-700">Matches Found</div>
                    </div>
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {detailedComparison.summary?.unmatched_performance || 0}
                      </div>
                      <div className="text-sm text-blue-700">Unmatched Performance APIs</div>
                    </div>
                    <div className="bg-orange-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {detailedComparison.summary?.unmatched_source || 0}
                      </div>
                      <div className="text-sm text-orange-700">Unmatched Source APIs</div>
                    </div>
                    <div className="bg-purple-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {Math.round((detailedComparison.summary?.match_rate || 0) * 100)}%
                      </div>
                      <div className="text-sm text-purple-700">Match Rate</div>
                    </div>
                  </div>

                  {/* Matched APIs with Detailed Analysis */}
                  {detailedComparison.matches && detailedComparison.matches.length > 0 && (
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold flex items-center space-x-2">
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                        <span>Matched APIs with Improvements</span>
                      </h3>
                      
                      <div className="space-y-4">
                        {detailedComparison.matches.map((match: any, index: number) => (
                          <Card key={index} className="border-l-4 border-l-green-500">
                            <CardHeader>
                              <div className="flex justify-between items-start">
                                <div>
                                  <CardTitle className="text-lg">
                                    {match.performance_api?.endpoint || 'Unknown API'}
                                  </CardTitle>
                                  <p className="text-sm text-muted-foreground">
                                    Matched with {match.source_api?.endpoint} 
                                    <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                                      {Math.round(match.match_confidence * 100)}% confidence
                                    </span>
                                  </p>
                                </div>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => setSelectedMatch(selectedMatch === match ? null : match)}
                                >
                                  {selectedMatch === match ? 'Hide Details' : 'Show Details'}
                                </Button>
                              </div>
                            </CardHeader>
                            
                            {selectedMatch === match && (
                              <CardContent className="space-y-4">
                                {/* Performance Analysis */}
                                {match.performance_analysis && (
                                  <div className="bg-red-50 p-4 rounded-lg">
                                    <h4 className="font-semibold text-red-800 mb-2">Performance Issues</h4>
                                    <div className="space-y-2">
                                      {match.performance_analysis.issues?.map((issue: any, idx: number) => (
                                        <div key={idx} className="flex items-start space-x-2">
                                          <AlertCircle className="h-4 w-4 text-red-500 mt-0.5" />
                                          <div>
                                            <p className="text-sm font-medium text-red-800">{issue.description}</p>
                                            <p className="text-xs text-red-600">Impact: {issue.impact}</p>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* Code Improvements */}
                                {match.improvements && match.improvements.length > 0 && (
                                  <div className="bg-blue-50 p-4 rounded-lg">
                                    <h4 className="font-semibold text-blue-800 mb-2">Recommended Improvements</h4>
                                    <div className="space-y-3">
                                      {match.improvements.map((improvement: any, idx: number) => (
                                        <div key={idx} className="border border-blue-200 rounded-lg p-3">
                                          <div className="flex items-center justify-between mb-2">
                                            <h5 className="font-medium text-blue-800">{improvement.title}</h5>
                                            <Badge variant={improvement.priority === 'HIGH' ? 'destructive' : 'secondary'}>
                                              {improvement.priority}
                                            </Badge>
                                          </div>
                                          <p className="text-sm text-blue-700 mb-2">{improvement.description}</p>
                                          <p className="text-xs text-blue-600 mb-2">
                                            <strong>Implementation:</strong> {improvement.implementation}
                                          </p>
                                          {improvement.code_example && (
                                            <details className="mt-2">
                                              <summary className="cursor-pointer text-xs font-medium text-blue-600">
                                                Show Code Example
                                              </summary>
                                              <pre className="mt-2 p-2 bg-blue-100 rounded text-xs overflow-auto">
                                                {improvement.code_example}
                                              </pre>
                                            </details>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* Code Suggestions */}
                                {match.code_suggestions && match.code_suggestions.length > 0 && (
                                  <div className="bg-yellow-50 p-4 rounded-lg">
                                    <h4 className="font-semibold text-yellow-800 mb-2">Code Suggestions</h4>
                                    <ul className="space-y-1">
                                      {match.code_suggestions.map((suggestion: string, idx: number) => (
                                        <li key={idx} className="text-sm text-yellow-700 flex items-start space-x-2">
                                          <span className="text-yellow-500">•</span>
                                          <span>{suggestion}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Recommended Actions */}
                                {match.recommended_actions && match.recommended_actions.length > 0 && (
                                  <div className="bg-green-50 p-4 rounded-lg">
                                    <h4 className="font-semibold text-green-800 mb-2">Recommended Actions</h4>
                                    <ul className="space-y-1">
                                      {match.recommended_actions.map((action: string, idx: number) => (
                                        <li key={idx} className="text-sm text-green-700 flex items-start space-x-2">
                                          <span className="text-green-500">✓</span>
                                          <span>{action}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Source Code Details */}
                                <div className="bg-gray-50 p-4 rounded-lg">
                                  <h4 className="font-semibold text-gray-800 mb-2">Source Code Details</h4>
                                  <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                      <span className="font-medium">File:</span> {match.source_code_info?.file_path || match.file_path}
                                    </div>
                                    <div>
                                      <span className="font-medium">Function:</span> {match.source_code_info?.function_name || match.function_name}
                                    </div>
                                    <div>
                                      <span className="font-medium">Line:</span> {match.source_code_info?.line_number || match.line_number}
                                    </div>
                                    <div>
                                      <span className="font-medium">Framework:</span> {match.source_code_info?.framework || match.framework}
                                    </div>
                                  </div>
                                  {(match.source_code_info?.code_snippet || match.code_snippet) && (
                                    <details className="mt-3">
                                      <summary className="cursor-pointer text-sm font-medium text-gray-600">
                                        Show Code Snippet
                                      </summary>
                                      <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto">
                                        {match.source_code_info?.code_snippet || match.code_snippet}
                                      </pre>
                                    </details>
                                  )}
                                </div>
                              </CardContent>
                            )}
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Analysis Results */}
          {analysisComplete && (
            <div className="space-y-6">

            </div>
          )}

          {/* Code Improvements */}
          {analysisComplete && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Generated Code Improvements</span>
                  <Badge variant="outline">{codeImprovements.length} suggestions</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* View Mode Toggle */}
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium">View Mode:</span>
                      <div className="flex items-center space-x-1">
                        <Toggle
                          pressed={viewMode === 'side-by-side'}
                          onPressedChange={() => setViewMode('side-by-side')}
                          aria-label="Side by side view"
                          size="sm"
                        >
                          <LayoutTemplate className="w-4 h-4 mr-1" />
                          Side by Side
                        </Toggle>
                        <Toggle
                          pressed={viewMode === 'text-diff'}
                          onPressedChange={() => setViewMode('text-diff')}
                          aria-label="Text diff view"
                          size="sm"
                        >
                          <FileText className="w-4 h-4 mr-1" />
                          Text Diff
                        </Toggle>
                        <Toggle
                          pressed={viewMode === 'one-by-one'}
                          onPressedChange={() => setViewMode('one-by-one')}
                          aria-label="One by one view"
                          size="sm"
                        >
                          <Eye className="w-4 h-4 mr-1" />
                          One by One
                        </Toggle>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium">Suggestion:</span>
                      <Select value={selectedSuggestion.toString()} onValueChange={(value) => setSelectedSuggestion(parseInt(value))}>
                        <SelectTrigger className="w-48">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {codeImprovements.map((improvement, index) => (
                            <SelectItem key={index} value={index.toString()}>
                              {improvement.title || `Improvement ${index + 1}`}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Code Improvements Display */}
                  {codeImprovements.length > 0 ? (
                    <div className="space-y-6">
                      {codeImprovements.map((improvement, index) => (
                        <div key={index} className={`${selectedSuggestion === index ? 'block' : 'hidden'}`}>
                          <div className="p-6 bg-card rounded-lg border">
                            {/* Improvement Header */}
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex-1">
                                <h4 className="text-lg font-semibold mb-2">
                                  {improvement.title || `Code Improvement ${index + 1}`}
                                </h4>
                                <p className="text-sm text-muted-foreground mb-3">
                                  {improvement.description || 'No description available'}
                                </p>
                                
                                {/* Improvement Metadata */}
                                <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                                  {improvement.priority && (
                                    <Badge variant="outline" className="text-xs">
                                      {improvement.priority} Priority
                                    </Badge>
                                  )}
                                  {improvement.category && (
                                    <Badge variant="secondary" className="text-xs">
                                      {improvement.category}
                                    </Badge>
                                  )}
                                  {improvement.implementation_effort && (
                                    <span>Effort: {improvement.implementation_effort}</span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Code Comparison Based on View Mode */}
                            {improvement.current_code && improvement.improved_code && (
                              <div className="space-y-4">
                                {viewMode === 'side-by-side' && (
                                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                    {/* Current Code */}
                                    <div className="space-y-2">
                                      <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                                        <h5 className="font-medium text-sm">Current Code (Issues)</h5>
                                      </div>
                                      <div className="bg-red-50 border border-red-200 rounded-lg overflow-hidden">
                                        <div className="bg-red-100 px-3 py-2 text-xs font-medium text-red-800">
                                          Issues Found
                                        </div>
                                        <pre className="p-4 text-xs overflow-x-auto bg-white">
                                          <code className="text-red-800">{improvement.current_code}</code>
                                        </pre>
                                      </div>
                                    </div>

                                    {/* Improved Code */}
                                    <div className="space-y-2">
                                      <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                        <h5 className="font-medium text-sm">Improved Code (Solution)</h5>
                                      </div>
                                      <div className="bg-green-50 border border-green-200 rounded-lg overflow-hidden">
                                        <div className="bg-green-100 px-3 py-2 text-xs font-medium text-green-800">
                                          Optimized Solution
                                        </div>
                                        <pre className="p-4 text-xs overflow-x-auto bg-white">
                                          <code className="text-green-800">{improvement.improved_code}</code>
                                        </pre>
                                      </div>
                                    </div>
                                  </div>
                                )}

                                {viewMode === 'text-diff' && (
                                  <div className="space-y-4">
                                    <div className="bg-gray-50 border border-gray-200 rounded-lg overflow-hidden">
                                      <div className="bg-gray-100 px-3 py-2 text-xs font-medium text-gray-800">
                                        Unified Diff View
                                      </div>
                                      <div className="p-4 bg-white">
                                        <div className="text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                                          {(() => {
                                            const diffText = improvement.diff || generateDiff(improvement.current_code || '', improvement.improved_code || '');
                                            console.log('Diff text:', diffText);
                                            console.log('Current code:', improvement.current_code);
                                            console.log('Improved code:', improvement.improved_code);
                                            return diffText;
                                          })().split('\n').map((line, index) => {
                                            if (line.startsWith('---') || line.startsWith('+++')) {
                                              return (
                                                <div key={index} className="text-blue-600 font-semibold bg-blue-50 px-2 py-1 my-1 rounded">
                                                  {line}
                                                </div>
                                              );
                                            } else if (line.startsWith('@@')) {
                                              return (
                                                <div key={index} className="text-purple-600 font-semibold bg-purple-50 px-2 py-1 my-1 rounded">
                                                  {line}
                                                </div>
                                              );
                                            } else if (line.startsWith('-')) {
                                              return (
                                                <div key={index} className="text-red-800 bg-red-50 px-2 py-1 my-1 rounded border-l-4 border-red-400">
                                                  {line}
                                                </div>
                                              );
                                            } else if (line.startsWith('+')) {
                                              return (
                                                <div key={index} className="text-green-800 bg-green-50 px-2 py-1 my-1 rounded border-l-4 border-green-400">
                                                  {line}
                                                </div>
                                              );
                                            } else {
                                              return (
                                                <div key={index} className="text-gray-700 px-2 py-1 my-1">
                                                  {line}
                                                </div>
                                              );
                                            }
                                          })}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )}

                                {viewMode === 'one-by-one' && (
                                  <div className="space-y-6">
                                    {/* Current Code */}
                                    <div className="space-y-2">
                                      <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                                        <h5 className="font-medium text-sm text-red-700">Current Code (Issues)</h5>
                                      </div>
                                      <div className="bg-red-50 border-l-4 border-red-500 rounded-r-lg overflow-hidden">
                                        <div className="bg-red-100 px-4 py-2 text-sm font-medium text-red-800">
                                          Problems Identified
                                        </div>
                                        <pre className="p-4 text-sm overflow-x-auto bg-white">
                                          <code className="text-red-800">{improvement.current_code}</code>
                                        </pre>
                                      </div>
                                    </div>

                                    {/* Arrow pointing down */}
                                    <div className="flex justify-center">
                                      <ArrowRight className="w-6 h-6 text-muted-foreground rotate-90" />
                                    </div>

                                    {/* Improved Code */}
                                    <div className="space-y-2">
                                      <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                        <h5 className="font-medium text-sm text-green-700">Improved Code (Solution)</h5>
                                      </div>
                                      <div className="bg-green-50 border-l-4 border-green-500 rounded-r-lg overflow-hidden">
                                        <div className="bg-green-100 px-4 py-2 text-sm font-medium text-green-800">
                                          Optimized Solution
                                        </div>
                                        <pre className="p-4 text-sm overflow-x-auto bg-white">
                                          <code className="text-green-800">{improvement.improved_code}</code>
                                        </pre>
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Expected Improvement */}
                            {improvement.expected_improvement && (
                              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                <h5 className="font-medium text-sm text-blue-800 mb-2">Expected Improvement</h5>
                                <p className="text-sm text-blue-700">{improvement.expected_improvement}</p>
                              </div>
                            )}

                            {/* Implementation Details */}
                            {improvement.implementation_effort && (
                              <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                                <span>Implementation Effort: <strong>{improvement.implementation_effort}</strong></span>
                                {improvement.priority && (
                                  <span>Priority: <strong>{improvement.priority}</strong></span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <Code2 className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
                      <p className="text-lg font-medium mb-2">No Code Improvements Generated</p>
                      <p className="text-sm mb-4">This could mean:</p>
                      <ul className="text-sm text-left max-w-md mx-auto space-y-1">
                        <li>• No APIs were found in the repository</li>
                        <li>• No performance issues were detected</li>
                        <li>• Repository is private and no GitHub token is provided</li>
                        <li>• Analysis is still in progress</li>
                      </ul>
                      <p className="text-sm mt-4">
                        <strong>Suggestions:</strong> Try analyzing a different repository or ensure the repository contains API code.
                      </p>
                    </div>
                  )}

                  {/* Action Buttons */}
                  {codeImprovements.length > 0 && (
                    <>
                      <Separator />
                      <div className="flex justify-center space-x-4">
                        <Button variant="outline" className="flex items-center space-x-2">
                          <ExternalLink className="w-4 h-4" />
                          <span>Create Individual PRs</span>
                        </Button>
                        <Button className="flex items-center space-x-2">
                          <Github className="w-4 h-4" />
                          <span>Create Combined PR</span>
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default GitHubAnalysis;