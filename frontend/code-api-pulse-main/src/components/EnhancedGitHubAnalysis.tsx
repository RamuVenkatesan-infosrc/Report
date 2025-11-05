import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Github, Code2, AlertCircle, CheckCircle2, Loader2, FileText, Eye, ArrowRight, Link, GitBranch, CheckCircle, Brain, Search, Target, Folder } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { apiService } from '@/services/api';

const EnhancedGitHubAnalysis = () => {
  const [activeTab, setActiveTab] = useState('full-repository');
  const [repoUrl, setRepoUrl] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [availableBranches, setAvailableBranches] = useState<string[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<any>(null);
  const [worstApis, setWorstApis] = useState<any[]>([]);
  const [discoveredApis, setDiscoveredApis] = useState<any[]>([]);
  const [performanceAnalysisData, setPerformanceAnalysisData] = useState<any>(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState(0);
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'side-by-side' | 'text-diff' | 'one-by-one'>('side-by-side');
  const [expandedIndices, setExpandedIndices] = useState<Record<string, boolean>>({});

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text || '');
      alert('Copied to clipboard');
    } catch (e) {
      console.error('Copy failed', e);
    }
  };

  // GitHub-style unified diff generation
  const generateDiff = (currentCode: string, improvedCode: string): string => {
    if (!currentCode && !improvedCode) return '';
    if (!currentCode) return improvedCode.split('\n').map(line => `+ ${line}`).join('\n');
    if (!improvedCode) return currentCode.split('\n').map(line => `- ${line}`).join('\n');
    
    const currentLines = currentCode.split('\n');
    const improvedLines = improvedCode.split('\n');
    const diff: string[] = [];
    
    // Create a simple diff: compare line by line
    const maxLen = Math.max(currentLines.length, improvedLines.length);
    
    for (let i = 0; i < maxLen; i++) {
      const currentLine = i < currentLines.length ? currentLines[i] : undefined;
      const improvedLine = i < improvedLines.length ? improvedLines[i] : undefined;
      
      if (currentLine === improvedLine) {
        // Unchanged line - show with space prefix (context)
        diff.push(`  ${currentLine || ''}`);
      } else {
        // Changed line
        if (currentLine !== undefined) {
          diff.push(`- ${currentLine}`);
        }
        if (improvedLine !== undefined && improvedLine !== currentLine) {
          diff.push(`+ ${improvedLine}`);
        }
      }
    }
    
    // Format with unified diff header
    let oldLineNum = 1;
    let newLineNum = 1;
    let oldCount = 0;
    let newCount = 0;
    
    // Count lines
    for (const line of diff) {
      if (line.startsWith('- ')) {
        oldCount++;
      } else if (line.startsWith('+ ')) {
        newCount++;
      } else if (line.startsWith('  ')) {
        oldCount++;
        newCount++;
      }
    }
    
    // Add unified diff header
    const header = `@@ -${oldLineNum},${oldCount} +${newLineNum},${newCount} @@\n`;
    return header + diff.join('\n');
  };

  // Load performance analysis data on component mount
  useEffect(() => {
    loadPerformanceAnalysisData();
  }, []);

  // Load performance analysis data
  const loadPerformanceAnalysisData = async () => {
    try {
      const data = await apiService.getLatestPerformanceAnalysis();
      setPerformanceAnalysisData(data);
      
      // Backend returns worst_api as array under analysis.worst_api
      if (data.status === 'success' && data.analysis && data.analysis.worst_api) {
        setWorstApis(data.analysis.worst_api);
      } else if (data.status === 'success' && data.worst_apis) {
        // Fallback for direct worst_apis array
        setWorstApis(data.worst_apis);
      }
      
      console.log('Loaded performance analysis data:', {
        status: data.status,
        worst_apis_count: data.analysis?.worst_api?.length || data.worst_apis?.length || 0,
        best_apis_count: data.analysis?.best_api?.length || data.best_apis?.length || 0
      });
    } catch (error: any) {
      console.error('Failed to load performance analysis data:', error);
      // Don't show alert for this as it's not critical
    }
  };

  // GitHub Connection
  const handleConnectToGitHub = async () => {
    if (!repoUrl || !githubToken) {
      alert('Please enter both GitHub repository URL and token');
      return;
    }

    setIsConnecting(true);
    try {
      // Extract owner/repo from URL
      const repoMatch = repoUrl.match(/github\.com\/([^\/]+)\/([^\/]+)/);
      if (!repoMatch) {
        throw new Error('Invalid GitHub repository URL');
      }
      const [, owner, repo] = repoMatch;
      const repoPath = `${owner}/${repo}`;

      // Fetch repository info and branches
      const repoInfo = await apiService.getRepositoryInfo(repoPath, githubToken);
      const branches = await apiService.getRepositoryBranches(repoPath, githubToken);
      
      setAvailableBranches(branches);
      setIsConnected(true);
      
      // Auto-select main/master branch if available
      const defaultBranch = branches.find(b => b === 'main' || b === 'master') || branches[0];
      if (defaultBranch) {
        setSelectedBranch(defaultBranch);
      }
    } catch (error: any) {
      console.error('GitHub connection failed:', error);
      alert(`Connection failed: ${error.message || 'Please check your repository URL and token.'}`);
    } finally {
      setIsConnecting(false);
    }
  };

  // Feature 1: Full Repository Analysis
  const handleFullRepositoryAnalysis = async () => {
    if (!isConnected) {
      alert('Please connect to GitHub first');
      return;
    }

    setIsAnalyzing(true);
    try {
      // Extract owner/repo from URL
      const repoMatch = repoUrl.match(/github\.com\/([^\/]+)\/([^\/]+)/);
      if (!repoMatch) {
        throw new Error('Invalid GitHub repository URL');
      }
      const [, owner, repo] = repoMatch;
      const repoPath = `${owner}/${repo}`;

      const result = await apiService.analyzeFullRepository(repoPath, selectedBranch, githubToken);
      setAnalysisResults(result);
      // Set the first file as selected by default
      if (result?.files_with_suggestions?.length > 0) {
        setSelectedFile(result.files_with_suggestions[0]);
      }
    } catch (error: any) {
      console.error('Full repository analysis failed:', error);
      alert(`Analysis failed: ${error.message || 'Please try again.'}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Feature 2: Performance-Driven API Matching
  const handlePerformanceAnalysis = async () => {
    if (!isConnected || worstApis.length === 0) {
      alert('Please connect to GitHub first and add worst APIs');
      return;
    }

    setIsAnalyzing(true);
    try {
      // Extract owner/repo from URL
      const repoMatch = repoUrl.match(/github\.com\/([^\/]+)\/([^\/]+)/);
      if (!repoMatch) {
        throw new Error('Invalid GitHub repository URL');
      }
      const [, owner, repo] = repoMatch;
      const repoPath = `${owner}/${repo}`;

      const result = await apiService.analyzeWorstApisWithGitHub(worstApis, repoPath, selectedBranch, githubToken);
      setAnalysisResults(result);
      
      // Extract discovered APIs from the result
      if (result?.enhanced_analysis?.discovered_apis || result?.comparison_analysis?.github_source_analysis?.discovered_apis || result?.discovered_apis) {
        const apis = result?.enhanced_analysis?.discovered_apis || 
                     result?.comparison_analysis?.github_source_analysis?.discovered_apis || 
                     result?.discovered_apis || [];
        setDiscoveredApis(apis);
      }
    } catch (error: any) {
      console.error('Performance analysis failed:', error);
      alert(`Analysis failed: ${error.message || 'Please try again.'}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Add sample worst API for testing
  const addSampleWorstApi = () => {
    const sampleApi = {
      endpoint: '/api/users',
      avg_response_time_ms: 2500,
      error_rate_percent: 15,
      throughput_rps: 100,
      percentile_95_latency_ms: 3000
    };
    setWorstApis([...worstApis, sampleApi]);
  };

  // Remove worst API
  const removeWorstApi = (index: number) => {
    setWorstApis(worstApis.filter((_, i) => i !== index));
  };


  return (
    <div className="space-y-8">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Github className="h-5 w-5" />
            <span>Enhanced GitHub Analysis</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!isConnected ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="repo-url">GitHub Repository URL</Label>
                  <Input
                    id="repo-url"
                    placeholder="https://github.com/owner/repository"
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
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                  />
                </div>
              </div>
              <Button 
                onClick={handleConnectToGitHub}
                disabled={!repoUrl || !githubToken || isConnecting}
                className="w-full"
              >
                {isConnecting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Connecting to GitHub...
                  </>
                ) : (
                  <>
                    <Link className="w-4 h-4 mr-2" />
                    Connect to GitHub
                  </>
                )}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center space-x-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Connected to GitHub</span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="repo-display">Repository</Label>
                  <Input
                    id="repo-display"
                    value={repoUrl}
                    disabled
                    className="bg-muted"
                  />
                </div>
                <div>
                  <Label htmlFor="branch-select">Select Branch</Label>
                  <Select value={selectedBranch} onValueChange={setSelectedBranch}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a branch" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableBranches.map((branch) => (
                        <SelectItem key={branch} value={branch}>
                          <div className="flex items-center space-x-2">
                            <GitBranch className="w-4 h-4" />
                            <span>{branch}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <Button 
                onClick={() => {
                  setIsConnected(false);
                  setAvailableBranches([]);
                  setSelectedBranch('');
                  setAnalysisResults(null);
                }}
                variant="outline"
                className="w-full"
              >
                Disconnect
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Feature Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="full-repository">Full Repository Analysis</TabsTrigger>
          <TabsTrigger value="performance-matching">Performance API Matching</TabsTrigger>
        </TabsList>

        {/* Feature 1: Full Repository Analysis */}
        <TabsContent value="full-repository">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Code2 className="h-5 w-5" />
                <span>Full Repository Code Analysis</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Analyze the entire GitHub repository for code quality and provide improvement suggestions.
                This feature scans all code files and identifies potential improvements.
              </p>
              
              <Button 
                onClick={handleFullRepositoryAnalysis}
                disabled={!repoUrl || isAnalyzing}
                className="w-full"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing Repository...
                  </>
                ) : (
                  'Analyze Full Repository'
                )}
              </Button>

              {/* Results for Full Repository Analysis */}
              {analysisResults && analysisResults.analysis_type === 'full_repository_analysis' && (
                <div className="space-y-6">
                  <Separator />
                  
                  {/* Header Section */}
                  <div className="text-center space-y-2">
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                      Repository Analysis Complete
                    </h2>
                    <p className="text-muted-foreground">
                      AI-powered code review and improvement suggestions
                    </p>
                  </div>
                    
                    {/* Repository Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
                        <CardContent className="p-6">
                          <div className="flex items-center space-x-3">
                            <div className="p-2 bg-blue-500 rounded-lg">
                              <FileText className="h-5 w-5 text-white" />
                            </div>
                      <div>
                              <p className="text-sm font-medium text-blue-700">Repository</p>
                              <p className="text-lg font-bold text-blue-900 truncate">
                          {analysisResults.repository_info?.owner}/{analysisResults.repository_info?.repo}
                        </p>
                      </div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
                        <CardContent className="p-6">
                          <div className="flex items-center space-x-3">
                            <div className="p-2 bg-green-500 rounded-lg">
                              <Folder className="h-5 w-5 text-white" />
                      </div>
                      <div>
                              <p className="text-sm font-medium text-green-700">Files Found</p>
                              <p className="text-3xl font-bold text-green-900">
                                {analysisResults.repository_info?.total_files_found || 0}
                        </p>
                      </div>
                    </div>
                        </CardContent>
                      </Card>

                      <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
                        <CardContent className="p-6">
                          <div className="flex items-center space-x-3">
                            <div className="p-2 bg-purple-500 rounded-lg">
                              <Search className="h-5 w-5 text-white" />
                            </div>
                            <div>
                              <p className="text-sm font-medium text-purple-700">Files Analyzed</p>
                              <p className="text-3xl font-bold text-purple-900">
                                {analysisResults.repository_info?.total_files_analyzed || 0}
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
                        <CardContent className="p-6">
                          <div className="flex items-center space-x-3">
                            <div className="p-2 bg-orange-500 rounded-lg">
                              <Target className="h-5 w-5 text-white" />
                            </div>
                            <div>
                              <p className="text-sm font-medium text-orange-700">Coverage</p>
                              <p className="text-lg font-bold text-orange-900">
                                {analysisResults.summary?.analysis_coverage || 'N/A'}
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Files with Suggestions */}
                    {analysisResults.files_with_suggestions && analysisResults.files_with_suggestions.length > 0 ? (
                      <div className="space-y-6">
                        {/* Section Header */}
                        <div className="text-center space-y-2">
                          <h3 className="text-xl font-bold flex items-center justify-center space-x-2">
                            <Brain className="h-6 w-6 text-blue-600" />
                            <span>AI Code Suggestions</span>
                          </h3>
                          <p className="text-muted-foreground">
                            {analysisResults.files_with_suggestions.length} files with improvement recommendations
                          </p>
                        </div>
                        
                        {/* File List + Details */}
                        <div className="flex flex-col gap-6">
                          {/* File List Card */}
                          <Card className="h-fit shadow-lg border-2 border-blue-100">
                            <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b dark:from-slate-800 dark:to-slate-900">
                              <CardTitle className="text-lg flex items-center justify-between">
                                <div className="flex items-center space-x-2">
                                  <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                  <span className="text-blue-800 font-semibold dark:text-blue-200">Files with Suggestions</span>
                                </div>
                                <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-300">
                                  {analysisResults.files_with_suggestions.length} files
                                </Badge>
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                              <div className="max-h-96 overflow-y-auto">
                                {analysisResults.files_with_suggestions.map((file: any, index: number) => (
                                  <div
                                    key={file.file_path}
                                    className={`border-b last:border-b-0 transition-all duration-200 ${
                                      selectedFile?.file_path === file.file_path 
                                        ? 'bg-blue-50 border-l-4 border-l-blue-500 shadow-sm dark:bg-slate-800' 
                                        : 'hover:bg-gray-50 hover:border-l-4 hover:border-l-gray-300 dark:hover:bg-slate-800'
                                    }`}
                                  >
                                    <button
                                      className="w-full text-left px-4 py-4 flex items-center justify-between group"
                                      onClick={() => setSelectedFile(file)}
                                    >
                                      <div className="flex items-center space-x-3 min-w-0 flex-1">
                                        <div className={`p-2 rounded-lg transition-colors ${
                                          selectedFile?.file_path === file.file_path 
                                            ? 'bg-blue-500 text-white' 
                                            : 'bg-gray-100 text-gray-600 group-hover:bg-blue-100 group-hover:text-blue-600 dark:bg-slate-700 dark:text-slate-200'
                                        }`}>
                                          <FileText className="h-4 w-4" />
                                        </div>
                                        <div className="min-w-0 flex-1">
                                          <p className="text-sm font-semibold text-gray-900 truncate dark:text-slate-100">
                                            {file.file_path.split('/').pop()}
                                          </p>
                                          <p className="text-xs text-gray-600 truncate dark:text-slate-300">
                                            {file.file_path}
                                          </p>
                                        </div>
                                      </div>
                                      <div className="flex items-center space-x-2">
                                        <Badge 
                                          variant="secondary" 
                                          className={`${
                                            selectedFile?.file_path === file.file_path 
                                              ? 'bg-blue-200 text-blue-800' 
                                              : 'bg-gray-200 text-gray-700 group-hover:bg-blue-100 group-hover:text-blue-700 dark:bg-slate-700 dark:text-slate-200'
                                          }`}
                                        >
                                          {file.improvements?.length || file.suggestions?.length || 0}
                                        </Badge>
                                        {selectedFile?.file_path === file.file_path && (
                                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                        )}
                                      </div>
                                    </button>
                                  </div>
                                ))}
                              </div>
                            </CardContent>
                          </Card>

                          {/* Code Suggestions for Selected File */}
                          <div className="space-y-4">
                            {selectedFile ? (
                              <Card className="shadow-lg border-2 border-green-100 dark:border-emerald-900">
                                <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 border-b dark:from-slate-800 dark:to-slate-900">
                                  <CardTitle className="text-lg flex items-center justify-between">
                                    <div className="flex items-center space-x-2">
                                      <Brain className="h-5 w-5 text-green-600 dark:text-green-400" />
                                      <span className="text-green-800 font-semibold dark:text-green-200">AI Code Suggestions</span>
                                    </div>
                                    <Badge variant="outline" className="bg-green-100 text-green-700 border-green-300">
                                      {selectedFile.improvements?.length || selectedFile.suggestions?.length || 0} suggestions
                                    </Badge>
                                  </CardTitle>
                                  <div className="flex items-center space-x-2 mt-2">
                                    <span className="text-sm font-medium text-gray-700 dark:text-slate-200">For:</span>
                                    <code className="bg-green-100 text-green-800 px-3 py-1 rounded-md text-sm font-mono border dark:bg-slate-800 dark:text-slate-100">
                                      {selectedFile.file_path}
                                    </code>
                                  </div>
                                </CardHeader>
                                <CardContent className="space-y-6 p-6">
                                  {(selectedFile.improvements || selectedFile.suggestions || []).map((suggestion: any, idx: number) => (
                                    <Card key={idx} className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 shadow-md hover:shadow-lg transition-shadow">
                                      <CardContent className="p-6">
                                        <div className="space-y-4">
                                          <div className="flex items-start space-x-4">
                                            <div className="p-3 bg-blue-500 rounded-xl flex-shrink-0 shadow-md">
                                              <Brain className="h-5 w-5 text-white" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                              <div className="flex items-center space-x-2 mb-3">
                                                <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-300 text-xs">
                                                  Suggestion {idx + 1}
                                                </Badge>
                                              </div>
                                              <h6 className="font-bold text-gray-900 text-lg mb-3 leading-tight">
                                                {suggestion.title || suggestion.issue || suggestion.type || 'Code Improvement'}
                                              </h6>
                                              <p className="text-gray-700 leading-relaxed text-base">
                                                {suggestion.description || suggestion.explanation || suggestion.suggestion}
                                              </p>
                                              {suggestion.summary && (
                                                <div className="mt-4 p-4 bg-yellow-50 border-2 border-yellow-200 rounded-lg">
                                                  <div className="flex items-start space-x-2">
                                                    <div className="text-yellow-600 text-lg">💡</div>
                                                    <p className="text-yellow-800 font-semibold text-sm">
                                                      {suggestion.summary}
                                                    </p>
                                                  </div>
                                                </div>
                                              )}
                                            </div>
                                          </div>
                                        
                                        {suggestion.current_code && suggestion.improved_code && (
                                          <div className="space-y-6 mt-6">
                                            {/* View Mode Toggle */}
                                            <div className="flex items-center justify-between">
                                              <div className="flex items-center space-x-2">
                                                <span className="text-base font-semibold text-gray-800">Code Comparison</span>
                                                <Badge variant="outline" className="bg-gray-100 text-gray-700">
                                                  Before vs After
                                                </Badge>
                                              </div>
                                              <div className="flex items-center space-x-2">
                                                <Button
                                                  variant="outline"
                                                  size="sm"
                                                  className="text-xs"
                                                  onClick={() => setExpandedIndices(prev => ({...prev, [idx]: !prev[idx]}))}
                                                >
                                                  {expandedIndices[idx] ? 'Collapse' : 'Expand'}
                                                </Button>
                                                <Button
                                                  variant="outline"
                                                  size="sm"
                                                  className="text-xs"
                                                  onClick={() => copyToClipboard(`${suggestion.improved_code}`)}
                                                >
                                                  Copy Improved
                                                </Button>
                                              </div>
                                            </div>

                                            {/* Side by Side View */}
                                            {viewMode === 'side-by-side' && (
                                              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                                <Card className="border-2 border-red-200 bg-gradient-to-br from-red-50 to-red-100 shadow-md">
                                                  <CardHeader className="pb-3 bg-red-100">
                                                    <CardTitle className="text-base flex items-center space-x-2">
                                                      <div className="w-4 h-4 bg-red-500 rounded-full shadow-sm"></div>
                                                      <span className="text-red-800 font-semibold">Current Code</span>
                                                    </CardTitle>
                                                  </CardHeader>
                                                  <CardContent className="p-4">
                                                    <pre className={`text-sm text-red-900 whitespace-pre-wrap font-mono leading-relaxed overflow-x-auto bg-white/50 p-3 rounded border ${expandedIndices[idx] ? 'max-h-none' : 'max-h-80'} `}>
                                                      {suggestion.current_code}
                                                    </pre>
                                                  </CardContent>
                                                </Card>
                                                <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50 to-green-100 shadow-md">
                                                  <CardHeader className="pb-3 bg-green-100">
                                                    <CardTitle className="text-base flex items-center space-x-2">
                                                      <div className="w-4 h-4 bg-green-500 rounded-full shadow-sm"></div>
                                                      <span className="text-green-800 font-semibold">Improved Code</span>
                                                    </CardTitle>
                                                  </CardHeader>
                                                  <CardContent className="p-4">
                                                    <pre className={`text-sm text-green-900 whitespace-pre-wrap font-mono leading-relaxed overflow-x-auto bg-white/50 p-3 rounded border ${expandedIndices[idx] ? 'max-h-none' : 'max-h-80'} `}>
                                                      {suggestion.improved_code}
                                                    </pre>
                                                  </CardContent>
                                                </Card>
                                              </div>
                                            )}

                                            {/* Text Diff View */}
                                            {viewMode === 'text-diff' && (
                                              <Card className="border-2 border-gray-200 shadow-md">
                                                <CardHeader className="pb-3 bg-gray-50">
                                                  <CardTitle className="text-base flex items-center space-x-2">
                                                    <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center">
                                                      <FileText className="h-4 w-4 text-blue-600" />
                                                    </div>
                                                    <span className="text-gray-800 font-semibold">Unified Diff View</span>
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      className="ml-auto text-xs"
                                                      onClick={() => copyToClipboard(generateDiff(suggestion.current_code, suggestion.improved_code))}
                                                    >
                                                      Copy Diff
                                                    </Button>
                                                  </CardTitle>
                                                </CardHeader>
                                                <CardContent className="p-0">
                                                  <div className={`bg-gray-900 border border-gray-700 rounded-lg p-4 overflow-y-auto shadow-inner ${expandedIndices[idx] ? 'max-h-none' : 'max-h-96'}`}>
                                                    <pre className="text-sm font-mono leading-relaxed">
                                                      {generateDiff(suggestion.current_code, suggestion.improved_code).split('\n').map((line, i) => (
                                                        <div key={i} className={
                                                          line.startsWith('-') ? 'text-red-300 bg-red-900/30 px-3 py-1 rounded border-l-2 border-red-500' :
                                                          line.startsWith('+') ? 'text-green-300 bg-green-900/30 px-3 py-1 rounded border-l-2 border-green-500' :
                                                          'text-gray-300 px-3 py-1'
                                                        }>
                                                          {line}
                                                        </div>
                                                      ))}
                                                    </pre>
                                                  </div>
                                                </CardContent>
                                              </Card>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    </CardContent>
                                  </Card>
                                ))}
                              </CardContent>
                            </Card>
                            ) : (
                              <Card className="border-dashed border-2 border-gray-300 shadow-lg">
                                <CardContent className="flex flex-col items-center justify-center py-16">
                                  <div className="p-6 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full mb-6 shadow-md">
                                    <FileText className="h-12 w-12 text-gray-500" />
                                  </div>
                                  <h3 className="text-xl font-bold text-gray-800 mb-3">No File Selected</h3>
                                  <p className="text-gray-600 text-center text-base max-w-sm leading-relaxed">
                                    Choose a file from the list on the left to view AI-powered code suggestions and improvements
                                  </p>
                                  <div className="mt-4 flex items-center space-x-2 text-sm text-gray-500">
                                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                    <span>Click any file to get started</span>
                                  </div>
                                </CardContent>
                              </Card>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <Card className="border-dashed border-2 border-gray-300 shadow-lg">
                        <CardContent className="flex flex-col items-center justify-center py-20">
                          <div className="p-8 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full mb-8 shadow-md">
                            <Brain className="h-16 w-16 text-gray-500" />
                          </div>
                          <h3 className="text-2xl font-bold text-gray-800 mb-4">No Suggestions Found</h3>
                          <p className="text-gray-600 text-center max-w-lg text-base leading-relaxed mb-6">
                            The analysis completed successfully, but no code improvements were identified for this repository.
                            This could mean the code is already well-optimized or the files don't contain analyzable code patterns.
                          </p>
                          <div className="flex items-center space-x-4 text-sm text-gray-500">
                            <div className="flex items-center space-x-2">
                              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                              <span>Analysis Complete</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                              <span>Code Quality Good</span>
                            </div>
                          </div>
                          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                            <p className="text-sm text-blue-700">
                              💡 Try analyzing a different repository or check if the files contain source code files.
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {/* Fallback for old code_improvements structure */}
                    {analysisResults.code_improvements && analysisResults.code_improvements.length > 0 && (
                      <div className="space-y-4">
                        <h4 className="font-semibold">Code Improvements ({analysisResults.code_improvements.length})</h4>
                        
                        {/* View Mode Toggle */}
                        <div className="flex items-center space-x-4">
                          <span className="text-sm font-medium">View Mode:</span>
                          <div className="flex items-center space-x-2">
                            <Button
                              variant={viewMode === 'side-by-side' ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => setViewMode('side-by-side')}
                            >
                              <Eye className="w-4 h-4 mr-1" />
                              Side by Side
                            </Button>
                            <Button
                              variant={viewMode === 'text-diff' ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => setViewMode('text-diff')}
                            >
                              <FileText className="w-4 h-4 mr-1" />
                              Text Diff
                            </Button>
                            <Button
                              variant={viewMode === 'one-by-one' ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => setViewMode('one-by-one')}
                            >
                              <ArrowRight className="w-4 h-4 mr-1" />
                              One by One
                            </Button>
                          </div>
                        </div>

                        {/* Improvement Selector */}
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium">Improvement:</span>
                          <Select value={selectedSuggestion.toString()} onValueChange={(value) => setSelectedSuggestion(parseInt(value))}>
                            <SelectTrigger className="w-64">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {analysisResults.code_improvements.map((improvement: any, index: number) => (
                                <SelectItem key={index} value={index.toString()}>
                                  {improvement.issue || `Improvement ${index + 1}`}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Display Selected Improvement */}
                        {analysisResults.code_improvements[selectedSuggestion] && (
                          <div className="space-y-4">
                            {(() => {
                              const improvement = analysisResults.code_improvements[selectedSuggestion];
                              return (
                                <div className="p-6 bg-card rounded-lg border">
                                  <div className="space-y-4">
                                    <div>
                                      <h5 className="font-semibold text-lg">{improvement.issue}</h5>
                                      <p className="text-sm text-muted-foreground mt-1">{improvement.explanation}</p>
                                      {improvement.summary && (
                                        <p className="text-xs mt-2 px-2 py-1 rounded bg-yellow-50 text-yellow-800 border border-yellow-200">
                                          {improvement.summary}
                                        </p>
                                      )}
                                    </div>

                                    {/* Code Comparison */}
                                    {improvement.current_code && improvement.improved_code && (
                                      <div className="space-y-4">
                                        {viewMode === 'side-by-side' && (
                                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                            <div>
                                              <h6 className="font-medium mb-2 text-sm flex items-center">
                                                <AlertCircle className="w-4 h-4 mr-2 text-destructive" />
                                                Current Code
                                              </h6>
                                              <div className="bg-red-50 border border-red-200 rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                                                <pre className="text-red-800 whitespace-pre-wrap">{improvement.current_code}</pre>
                                              </div>
                                            </div>
                                            <div>
                                              <h6 className="font-medium mb-2 text-sm flex items-center">
                                                <CheckCircle2 className="w-4 h-4 mr-2 text-green-600" />
                                                Improved Code
                                              </h6>
                                              <div className="bg-green-50 border border-green-200 rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                                                <pre className="text-green-800 whitespace-pre-wrap">{improvement.improved_code}</pre>
                                              </div>
                                            </div>
                                          </div>
                                        )}

                                        {viewMode === 'text-diff' && (
                                          <div>
                                            <h6 className="font-medium mb-2 text-sm">Unified Diff View</h6>
                                            <div className="bg-gray-50 border border-gray-200 rounded p-3 text-sm font-mono max-h-96 overflow-y-auto">
                                              <div className="text-muted-foreground mb-2">@@ -{improvement.file} @@</div>
                                              {generateDiff(improvement.current_code, improvement.improved_code).split('\n').map((line, i) => (
                                                <div key={i} className={
                                                  line.startsWith('-') ? 'text-red-800 bg-red-50' :
                                                  line.startsWith('+') ? 'text-green-800 bg-green-50' :
                                                  'text-gray-700'
                                                }>
                                                  {line}
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}

                                        {viewMode === 'one-by-one' && (
                                          <div className="space-y-4">
                                            <div>
                                              <h6 className="font-medium mb-2 text-sm flex items-center">
                                                <AlertCircle className="w-4 h-4 mr-2 text-destructive" />
                                                Current Code
                                              </h6>
                                              <div className="bg-red-50 border border-red-200 rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                                                <pre className="text-red-800 whitespace-pre-wrap">{improvement.current_code}</pre>
                                              </div>
                                            </div>
                                            <div className="flex justify-center">
                                              <ArrowRight className="w-6 h-6 text-muted-foreground rotate-90" />
                                            </div>
                                            <div>
                                              <h6 className="font-medium mb-2 text-sm flex items-center">
                                                <CheckCircle2 className="w-4 h-4 mr-2 text-green-600" />
                                                Improved Code
                                              </h6>
                                              <div className="bg-green-50 border border-green-200 rounded p-3 text-sm font-mono max-h-64 overflow-y-auto">
                                                <pre className="text-green-800 whitespace-pre-wrap">{improvement.improved_code}</pre>
                                              </div>
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })()}
                          </div>
                        )}
                      </div>
                    )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Feature 2: Performance API Matching */}
        <TabsContent value="performance-matching">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <AlertCircle className="h-5 w-5" />
                <span>Performance-Driven API Matching</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Match worst-performing APIs from performance reports with source code and provide targeted improvements.
                APIs with performance issues will be highlighted in red.
              </p>

              {/* Performance Analysis Data */}
              {performanceAnalysisData && performanceAnalysisData.status === 'success' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="w-5 h-5 text-blue-600" />
                      <span className="text-sm font-medium text-blue-800">Performance Analysis Data Available</span>
                    </div>
                    <div className="flex items-center space-x-4 text-sm">
                      <span className="text-red-600 font-semibold">
                        {performanceAnalysisData.analysis?.worst_api?.length || performanceAnalysisData.analysis_summary?.total_worst_apis || 0} Critical
                      </span>
                      <span className="text-green-600 font-semibold">
                        {performanceAnalysisData.analysis?.best_api?.length || performanceAnalysisData.analysis_summary?.total_best_apis || 0} Good
                      </span>
                      <span className="text-blue-600 font-semibold">
                        {(performanceAnalysisData.analysis?.worst_api?.length || 0) + (performanceAnalysisData.analysis?.best_api?.length || 0) || performanceAnalysisData.total_apis || 0} Total
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Worst APIs Input */}
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900">Performance Issues ({worstApis.length})</h4>
                    <p className="text-sm text-gray-500 mt-1">APIs with critical performance problems that need attention</p>
                  </div>
                  <div className="flex space-x-2">
                    <Button onClick={loadPerformanceAnalysisData} variant="outline" size="sm" className="text-blue-600 border-blue-200 hover:bg-blue-50">
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Refresh Data
                    </Button>
                    <Button onClick={addSampleWorstApi} variant="outline" size="sm" className="text-gray-600 border-gray-200 hover:bg-gray-50">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      Add Sample
                    </Button>
                  </div>
                </div>

                {worstApis.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>No worst APIs available</p>
                    <p className="text-sm">
                      {performanceAnalysisData?.status === 'no_data' 
                        ? 'Run report analysis first to get performance data'
                        : 'Click "Refresh Data" to load from report analysis or "Add Sample API" to test'
                      }
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {worstApis.map((api, index) => (
                      <Card key={index} className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200">
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1 min-w-0">
                              <h3 className="text-sm font-semibold text-red-600 truncate">
                                {api.endpoint}
                              </h3>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Badge variant="destructive" className="text-xs px-2 py-1">
                                Issue
                              </Badge>
                              <Button
                                onClick={() => removeWorstApi(index)}
                                variant="ghost"
                                size="sm"
                                className="text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full w-6 h-6 p-0"
                              >
                                ×
                              </Button>
                            </div>
                          </div>
                          
                          <div className="space-y-2">
                            <div className="text-xs text-gray-600">
                              {Math.round(api.avg_response_time_ms)}ms • {api.error_rate_percent}% error
                            </div>
                            <div className="text-xs text-gray-500">
                              {Math.round(api.throughput_rps)} RPS
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>

              <Button 
                onClick={handlePerformanceAnalysis}
                disabled={!repoUrl || worstApis.length === 0 || isAnalyzing}
                className="w-full"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing Performance APIs...
                  </>
                ) : (
                  'Analyze Performance APIs'
                )}
              </Button>

              {/* Results for Performance Analysis - Matched APIs */}
              {analysisResults && analysisResults.analysis_type === 'worst_apis_github_comparison_with_colors' && (
                <div className="space-y-6">
                  <Separator />
                    
                  {/* Section 1: Summary Cards */}
                    {analysisResults.enhanced_analysis?.color_summary && (
                    <div className="grid grid-cols-3 gap-4">
                      <Card className="bg-gradient-to-br from-red-50 to-red-100 border-red-200">
                        <CardContent className="p-6 text-center">
                          <div className="text-3xl font-bold text-red-600">
                            {analysisResults.enhanced_analysis.color_summary.red_apis}
                          </div>
                          <div className="text-sm font-medium text-red-700 mt-1">🔴 Critical APIs</div>
                        </CardContent>
                      </Card>
                      <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
                        <CardContent className="p-6 text-center">
                          <div className="text-3xl font-bold text-green-600">
                            {analysisResults.enhanced_analysis.color_summary.green_apis}
                          </div>
                          <div className="text-sm font-medium text-green-700 mt-1">🟢 Good APIs</div>
                        </CardContent>
                      </Card>
                      <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
                        <CardContent className="p-6 text-center">
                          <div className="text-3xl font-bold text-blue-600">
                            {analysisResults.enhanced_analysis.color_summary.total_matched}
                          </div>
                          <div className="text-sm font-medium text-blue-700 mt-1">📊 Total Matched</div>
                        </CardContent>
                      </Card>
                      </div>
                    )}

                    {/* Section 2: Discovered APIs in Source Code */}
                    <Card className="border-2 border-blue-200">
                      <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b">
                        <CardTitle className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Search className="h-5 w-5 text-blue-600" />
                            <span className="text-blue-800 font-semibold">APIs Found in Source Code</span>
                          </div>
                          <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-300 font-semibold">
                            {(analysisResults.enhanced_analysis?.discovered_apis || analysisResults.comparison_analysis?.github_source_analysis?.discovered_apis || analysisResults.discovered_apis).length || 0}
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="p-0">

                    {/* Debug Info */}
                    {process.env.NODE_ENV === 'development' && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4 mx-4 mt-4">
                        <h5 className="text-sm font-medium text-yellow-800 mb-2">Debug Info:</h5>
                        <div className="text-xs text-yellow-700 space-y-1">
                          <div>Enhanced Analysis: {analysisResults.enhanced_analysis ? 'Yes' : 'No'}</div>
                          <div>Comparison Analysis: {analysisResults.comparison_analysis ? 'Yes' : 'No'}</div>
                          <div>Discovered APIs (enhanced): {analysisResults.enhanced_analysis?.discovered_apis?.length || 0}</div>
                          <div>Discovered APIs (comparison): {analysisResults.comparison_analysis?.github_source_analysis?.discovered_apis?.length || 0}</div>
                          <div>Discovered APIs (direct): {analysisResults.discovered_apis?.length || 0}</div>
                          <div>Matched APIs: {analysisResults.enhanced_analysis?.matched_apis_with_colors?.length || 0}</div>
                        </div>
                      </div>
                    )}

                    {/* Source Code APIs */}
                    {(analysisResults.enhanced_analysis?.discovered_apis || analysisResults.comparison_analysis?.github_source_analysis?.discovered_apis || analysisResults.discovered_apis) && (
                      <div className="px-4 pb-4">
                        <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b-2 border-blue-200">
                                <tr>
                                  <th className="px-4 py-3 text-left font-semibold text-gray-800">API Endpoint</th>
                                  <th className="px-4 py-3 text-left font-semibold text-gray-800">File</th>
                                  <th className="px-4 py-3 text-left font-semibold text-gray-800">Function</th>
                                  <th className="px-4 py-3 text-left font-semibold text-gray-800">Framework</th>
                                  <th className="px-4 py-3 text-left font-semibold text-gray-800">Status</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-100">
                                {(analysisResults.enhanced_analysis?.discovered_apis || analysisResults.comparison_analysis?.github_source_analysis?.discovered_apis || analysisResults.discovered_apis).map((api: any, index: number) => {
                                  // Check if this API is matched with performance issues
                                  const isMatched = analysisResults.enhanced_analysis?.matched_apis_with_colors?.some((matched: any) => 
                                    matched.api_endpoint === api.endpoint && matched.color_indicator === 'red'
                                  );
                                  
                                  return (
                                    <tr key={index} className={`hover:bg-blue-50 transition-colors duration-200 ${isMatched ? 'bg-red-50 border-l-4 border-l-red-500 shadow-sm' : 'hover:shadow-sm'}`}>
                                      <td className="px-4 py-3 font-mono text-sm">
                                        <div className="flex items-center space-x-2">
                                          {isMatched && <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>}
                                          <span className={`font-medium ${isMatched ? 'text-red-800 font-bold' : 'text-gray-800'}`}>
                                            {api.endpoint}
                                          </span>
                                        </div>
                                      </td>
                                      <td className="px-4 py-3 text-sm text-gray-700 font-medium">{api.file_path}</td>
                                      <td className="px-4 py-3 text-sm text-gray-700 font-medium">{api.function_name}</td>
                                      <td className="px-4 py-3 text-sm text-gray-700 font-medium">{api.framework}</td>
                                      <td className="px-4 py-3">
                                        <Badge 
                                          variant={isMatched ? 'destructive' : 'default'} 
                                          className={`text-xs font-semibold px-3 py-1 ${
                                            isMatched 
                                              ? 'bg-red-100 text-red-800 border-red-200 hover:bg-red-200' 
                                              : 'bg-green-100 text-green-800 border-green-200 hover:bg-green-200'
                                          }`}
                                        >
                                          {isMatched ? '🔴 Issues Found' : '✅ Discovered'}
                                        </Badge>
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* No APIs Found Message */}
                    {!analysisResults.enhanced_analysis?.discovered_apis && !analysisResults.comparison_analysis?.github_source_analysis?.discovered_apis && !analysisResults.discovered_apis && (
                      <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-200 rounded-lg p-6 shadow-sm">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center">
                            <span className="text-yellow-600 text-lg">🔍</span>
                          </div>
                          <div className="flex-1">
                            <h4 className="text-lg font-bold text-yellow-800 mb-2">No APIs Found in Source Code</h4>
                            <p className="text-sm text-yellow-700 leading-relaxed">
                              This could mean the repository doesn't contain API code, or the API patterns are not recognized. 
                              Try connecting to a different repository or check if the code uses supported frameworks.
                            </p>
                            <div className="mt-3 flex space-x-2">
                              <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-300">
                                💡 Tip: Try a different branch
                              </Badge>
                              <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-300">
                                🔧 Check supported frameworks
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                      </CardContent>
                    </Card>

                    {/* Section 3: Matched APIs with Code Suggestions */}
                    {analysisResults.enhanced_analysis?.matched_apis_with_colors && (
                      <Card className="border-2 border-red-200">
                        <CardHeader className="bg-gradient-to-r from-red-50 to-orange-50 border-b">
                          <CardTitle className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Target className="h-5 w-5 text-red-600" />
                              <span className="text-red-800 font-semibold">Matched APIs with Code Suggestions</span>
                            </div>
                            <Badge variant="outline" className="bg-red-100 text-red-700 border-red-300 font-semibold">
                              {analysisResults.enhanced_analysis.matched_apis_with_colors.length}
                            </Badge>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="p-6 space-y-4">
                        <div className="space-y-4">
                          {analysisResults.enhanced_analysis.matched_apis_with_colors.map((api: any, index: number) => (
                            <div key={index} className={`border-l-4 p-4 rounded-r-lg ${
                              api.color_indicator === 'red' ? 'border-l-red-500 bg-red-50' :
                              api.color_indicator === 'green' ? 'border-l-green-500 bg-green-50' :
                              api.color_indicator === 'yellow' ? 'border-l-yellow-500 bg-yellow-50' :
                              'border-l-gray-500 bg-gray-50'
                            }`}>
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center space-x-3">
                                  <div className={`w-3 h-3 rounded-full ${
                                    api.color_indicator === 'red' ? 'bg-red-500' :
                                    api.color_indicator === 'green' ? 'bg-green-500' :
                                    api.color_indicator === 'yellow' ? 'bg-yellow-500' :
                                    'bg-gray-500'
                                  }`}></div>
                                  <div>
                                    <h5 className="font-semibold text-sm text-gray-800">{api.api_endpoint}</h5>
                                    <p className="text-xs text-gray-600">
                                      Confidence: {Math.round(api.match_confidence * 100)}% • File: {api.source_code_info?.file_path}
                                    </p>
                                  </div>
                                </div>
                                <Badge variant={
                                  api.color_indicator === 'red' ? 'destructive' :
                                  api.color_indicator === 'green' ? 'default' :
                                  api.color_indicator === 'yellow' ? 'secondary' :
                                  'outline'
                                }>
                                  {api.color_indicator === 'red' ? 'Issues Found' :
                                   api.color_indicator === 'green' ? 'No Issues' :
                                   api.color_indicator === 'yellow' ? 'Unmatched' :
                                   'Other'}
                                </Badge>
                              </div>
                              
                              <div className="space-y-4">
                                {/* Performance Issues */}
                                {api.performance_issues && api.performance_issues.length > 0 && (
                                  <div>
                                    <h6 className="text-sm font-medium text-red-800 mb-2">Performance Issues:</h6>
                                    <div className="flex flex-wrap gap-1">
                                      {api.performance_issues.map((issue: string, idx: number) => (
                                        <Badge key={idx} variant="destructive" className="text-xs">
                                          {issue}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* Code Suggestions */}
                                {api.code_suggestions && api.code_suggestions.length > 0 && (
                                  <div className="space-y-4">
                                    <h6 className="text-sm font-medium text-gray-800">Code Suggestions:</h6>
           {(api.code_suggestions || []).slice(0, 1).map((suggestion: any, idx: number) => (
                                      <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                                        <div className="space-y-3">
                                          <div>
                                            <h6 className="font-semibold text-gray-900 text-sm">{suggestion.title || suggestion.issue}</h6>
                                            <p className="text-xs text-gray-600 mt-1">{suggestion.description || suggestion.explanation}</p>
                                            {suggestion.summary && (
                                              <p className="text-xs mt-2 px-2 py-1 rounded bg-yellow-50 text-yellow-800 border border-yellow-200">
                                                {suggestion.summary}
                                              </p>
                                            )}
                                          </div>
                                          
                                          {suggestion.current_code && suggestion.improved_code && (
                                            <div className="space-y-3">
                                              {/* View Mode Toggle */}
                                              <div className="flex items-center space-x-2">
                                                <span className="text-xs font-medium text-gray-600">View:</span>
                                                <div className="flex items-center space-x-1">
                                                  <Button
                                                    variant={viewMode === 'side-by-side' ? 'default' : 'outline'}
                                                    size="sm"
                                                    className={`text-xs px-2 py-1 h-6 font-semibold ${
                                                      viewMode === 'side-by-side' 
                                                        ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700' 
                                                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 hover:text-gray-900'
                                                    }`}
                                                    onClick={() => setViewMode('side-by-side')}
                                                  >
                                                    Side by Side
                                                  </Button>
                                                  <Button
                                                    variant={viewMode === 'text-diff' ? 'default' : 'outline'}
                                                    size="sm"
                                                    className={`text-xs px-2 py-1 h-6 font-semibold ${
                                                      viewMode === 'text-diff' 
                                                        ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700' 
                                                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 hover:text-gray-900'
                                                    }`}
                                                    onClick={() => setViewMode('text-diff')}
                                                  >
                                                    Text Diff
                                                  </Button>
                                                </div>
                                              </div>

                                              {/* Side by Side View */}
                                              {viewMode === 'side-by-side' && (
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                                  <div className="space-y-2">
                                                    <div className="flex items-center space-x-2">
                                                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                                                      <span className="text-xs font-medium text-red-700">Current Code</span>
                                                      <Button variant="ghost" size="sm" className="ml-auto text-xs" onClick={() => copyToClipboard(suggestion.current_code)}>Copy</Button>
                                                    </div>
                                                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                                      <pre className={`text-xs text-red-800 whitespace-pre-wrap font-mono ${expandedIndices[idx] ? '' : 'max-h-80'} overflow-y-auto`}>
                                                        {suggestion.current_code}
                                                      </pre>
                                                    </div>
                                                  </div>
                                                  <div className="space-y-2">
                                                    <div className="flex items-center space-x-2">
                                                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                                      <span className="text-xs font-medium text-green-700">Improved Code</span>
                                                      <Button variant="ghost" size="sm" className="ml-auto text-xs" onClick={() => copyToClipboard(suggestion.improved_code)}>Copy</Button>
                                                    </div>
                                                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                                                      <pre className={`text-xs text-green-800 whitespace-pre-wrap font-mono ${expandedIndices[idx] ? '' : 'max-h-80'} overflow-y-auto`}>
                                                        {suggestion.improved_code}
                                                      </pre>
                                                    </div>
                                                  </div>
                                                </div>
                                              )}

                                              {/* Text Diff View */}
                                              {viewMode === 'text-diff' && (
                                                <div className="bg-white border-2 border-gray-300 rounded-lg p-4 shadow-sm">
                                                  <div className="text-sm font-bold text-gray-800 mb-3 flex items-center space-x-2">
                                                    <div className="w-4 h-4 bg-blue-100 rounded-full flex items-center justify-center">
                                                      <span className="text-blue-600 text-xs">📝</span>
                                                    </div>
                                                    <span>Unified Diff View</span>
                                                    <Button variant="ghost" size="sm" className="ml-auto text-xs" onClick={() => copyToClipboard(generateDiff(suggestion.current_code, suggestion.improved_code))}>Copy Diff</Button>
                                                  </div>
                                                  <div className={`bg-gray-900 border border-gray-700 rounded-lg p-4 ${expandedIndices[idx] ? '' : 'max-h-96'} overflow-y-auto`}>
                                                    <pre className="text-sm font-mono leading-relaxed">
                                                      {generateDiff(suggestion.current_code, suggestion.improved_code).split('\n').map((line, i) => (
                                                        <div key={i} className={
                                                          line.startsWith('-') ? 'text-red-300 bg-red-900/20 px-2 py-1 rounded' :
                                                          line.startsWith('+') ? 'text-green-300 bg-green-900/20 px-2 py-1 rounded' :
                                                          'text-gray-300 px-2 py-1'
                                                        }>
                                                          {line}
                                                        </div>
                                                      ))}
                                                    </pre>
                                                  </div>
                                                </div>
                                              )}
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Source Code Info */}
                                {api.source_code_info && (
                                  <div className="bg-gray-50 p-3 rounded border">
                                    <h6 className="text-xs font-medium text-gray-700 mb-2">Source Code Details:</h6>
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                      <div>
                                        <span className="text-gray-600 font-medium">Function:</span>
                                        <span className="ml-1 font-semibold text-gray-800">{api.source_code_info.function_name || 'Unknown'}</span>
                                      </div>
                                      <div>
                                        <span className="text-gray-600 font-medium">Framework:</span>
                                        <span className="ml-1 font-semibold text-gray-800">{api.source_code_info.framework || 'Unknown'}</span>
                                      </div>
                                      <div>
                                        <span className="text-gray-600 font-medium">Complexity:</span>
                                        <span className="ml-1 font-semibold text-gray-800">{api.source_code_info.complexity_score || 0}</span>
                                      </div>
                                      <div>
                                        <span className="text-gray-600 font-medium">Risk Level:</span>
                                        <span className="ml-1 font-semibold text-gray-800">{api.source_code_info.risk_level || 'Unknown'}</span>
                                      </div>
                                    </div>
                                  </div>
                                )}

                                          </div>
                                                        </div>
                                                      ))}
                        </div>
                        </CardContent>
                      </Card>
                    )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default EnhancedGitHubAnalysis;