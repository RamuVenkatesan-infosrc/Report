import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Loader2, AlertCircle, ChevronLeft, ChevronRight, FileCode, CheckCircle, Copy, Download } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import apiService from '@/services/api';

interface Suggestion {
  title: string;
  issue?: string;
  explanation?: string;
  description?: string;
  priority?: string;
  category?: string;
  current_code: string;
  improved_code: string;
  expected_improvement?: string;
  implementation_effort?: string;
  summary?: string;
  diff?: {
    side_by_side?: any;
    unified_diff?: string;
    line_by_line?: any;
    stats?: { changes_count: number; additions_count: number; deletions_count: number };
  };
}

interface FileSuggestions {
  file_path: string;
  suggestions: Suggestion[];
}

interface AnalysisData {
  status: string;
  analysis_type: string;
  repository_info: {
    owner: string;
    repo: string;
    branch: string;
    total_files_analyzed: number;
    total_files_found: number;
    files_skipped_extension: number;
    files_skipped_content: number;
  };
  files_with_suggestions: FileSuggestions[];
  summary: {
    files_with_suggestions: number;
    total_suggestions: number;
    analysis_coverage: string;
  };
}

interface Props {
  githubRepo: string;
  branch?: string;
}

const FullRepositoryAnalysis = ({ githubRepo, branch }: Props) => {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileSuggestions | null>(null);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
  const [viewMode, setViewMode] = useState<'side-by-side' | 'text-diff'>('side-by-side');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    const runAnalysis = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const res = await apiService.analyzeFullRepository(githubRepo, branch);
        
        if (res.status === 'success') {
        setData(res);
          
          // Auto-select first file with suggestions
          if (res.files_with_suggestions && res.files_with_suggestions.length > 0) {
            setSelectedFile(res.files_with_suggestions[0]);
            setSelectedSuggestionIndex(0);
          }
          
          toast({
            title: "Analysis Complete",
            description: `Found ${res.summary.total_suggestions} suggestions in ${res.summary.files_with_suggestions} files`,
          });
        } else {
          throw new Error('Analysis failed');
        }
      } catch (e: any) {
        const errorMsg = e.message || 'Failed to analyze repository';
        setError(errorMsg);
        console.error('Full repo analysis failed', e);
        
        toast({
          title: "Analysis Failed",
          description: errorMsg,
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };
    
    runAnalysis();
  }, [githubRepo, branch, toast]);

  const handleFileSelect = (file: FileSuggestions) => {
    setSelectedFile(file);
    setSelectedSuggestionIndex(0); // Reset to first suggestion when changing files
  };

  const handlePreviousSuggestion = () => {
    setSelectedSuggestionIndex(prev => Math.max(0, prev - 1));
  };

  const handleNextSuggestion = () => {
    const maxIndex = (selectedFile?.suggestions.length || 1) - 1;
    setSelectedSuggestionIndex(prev => Math.min(maxIndex, prev + 1));
  };

  const copyToClipboard = (code: string, label: string) => {
    navigator.clipboard.writeText(code);
    toast({
      title: "Copied",
      description: `${label} copied to clipboard`,
    });
  };

  const downloadCode = (code: string, filename: string) => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    
    toast({
      title: "Downloaded",
      description: `${filename} has been downloaded`,
    });
  };

  const suggestions = selectedFile?.suggestions || [];
  const currentSuggestion = suggestions[selectedSuggestionIndex];
  
  // Helper function to get suggestion description
  const getSuggestionDescription = (suggestion: Suggestion) => {
    return suggestion.explanation || suggestion.description || suggestion.issue || suggestion.title;
  };

  // Loading State
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Analyzing Repository...</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm text-gray-600">
              This may take a few minutes depending on repository size. AI is analyzing each file for issues and improvements.
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="space-y-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <div className="font-semibold">Analysis Failed</div>
            <div className="text-sm mt-1">{error}</div>
            <div className="text-xs mt-2">
              Possible reasons: Invalid repository, GitHub token issues, or AWS Bedrock not configured
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Empty State
  if (!data || !data.files_with_suggestions || data.files_with_suggestions.length === 0) {
    return (
      <div className="space-y-6">
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            <div className="font-semibold">No Issues Found</div>
            <div className="text-sm mt-1">
              Great news! The analysis didn't find any significant issues in the repository code.
            </div>
            {data?.repository_info && (
              <div className="text-xs mt-2 text-gray-600">
                Analyzed {data.repository_info.total_files_analyzed} files in {data.repository_info.owner}/{data.repository_info.repo}
              </div>
            )}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Analysis Summary */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-2xl font-bold text-blue-600">{data.summary.total_suggestions}</div>
              <div className="text-xs text-gray-600">Total Suggestions</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">{data.summary.files_with_suggestions}</div>
              <div className="text-xs text-gray-600">Files with Issues</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600">{data.repository_info.total_files_analyzed}</div>
              <div className="text-xs text-gray-600">Files Analyzed</div>
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-700">{data.summary.analysis_coverage}</div>
              <div className="text-xs text-gray-600">Coverage</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Analysis View */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileCode className="h-5 w-5" />
            <span>Code Suggestions</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* File List Sidebar */}
            <div className="lg:col-span-1 space-y-2">
              <h4 className="font-semibold text-sm text-gray-700 mb-3">Files with Suggestions</h4>
              <div className="border rounded-md divide-y max-h-[600px] overflow-y-auto">
                {data.files_with_suggestions.map((f) => (
                  <button
                    key={f.file_path}
                    className={`w-full text-left px-3 py-3 hover:bg-gray-50 transition-colors ${
                      selectedFile?.file_path === f.file_path 
                        ? 'bg-blue-50 border-l-4 border-blue-500' 
                        : 'border-l-4 border-transparent'
                    }`}
                    onClick={() => handleFileSelect(f)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-gray-800 truncate font-mono" title={f.file_path}>
                        {f.file_path.split('/').pop()}
                      </span>
                      <Badge variant="secondary" className="shrink-0">
                        {f.suggestions.length}
                      </Badge>
                    </div>
                    <div className="text-xs text-gray-500 truncate mt-1" title={f.file_path}>
                      {f.file_path}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Suggestion Details */}
            <div className="lg:col-span-2 space-y-4">
              {/* Header with navigation */}
              <div className="flex items-center justify-between border-b pb-3">
                <div className="flex-1">
                  <div className="text-xs text-gray-500 mb-1">Selected file</div>
                  <div className="font-mono text-sm font-medium text-gray-900 truncate" title={selectedFile?.file_path}>
                    {selectedFile?.file_path || '-'}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Button 
                    variant={viewMode === 'side-by-side' ? 'default' : 'outline'} 
                    size="sm" 
                    onClick={() => setViewMode('side-by-side')}
                  >
                    Side by Side
                  </Button>
                  <Button 
                    variant={viewMode === 'text-diff' ? 'default' : 'outline'} 
                    size="sm" 
                    onClick={() => setViewMode('text-diff')}
                  >
                    Full Code
                  </Button>
                </div>
              </div>

              {/* Suggestion Navigation */}
              {suggestions.length > 1 && (
                <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                  <div className="text-sm font-medium text-gray-700">
                    Suggestion {selectedSuggestionIndex + 1} of {suggestions.length}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handlePreviousSuggestion}
                      disabled={selectedSuggestionIndex === 0}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleNextSuggestion}
                      disabled={selectedSuggestionIndex === suggestions.length - 1}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}

              {currentSuggestion ? (
                <div className="space-y-4">
                  {/* Suggestion Header */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
                    <div className="font-semibold text-lg text-gray-900 mb-2">{currentSuggestion.title}</div>
                    {currentSuggestion.issue && (
                      <div className="text-sm text-red-700 mb-2">
                        <strong>Issue:</strong> {currentSuggestion.issue}
                      </div>
                    )}
                    <div className="text-sm text-gray-700">
                      {getSuggestionDescription(currentSuggestion)}
                    </div>
                    {currentSuggestion.expected_improvement && (
                      <div className="mt-3 px-3 py-2 rounded bg-green-100 text-green-800 border border-green-300 text-sm">
                        <strong>✓ Expected Improvement:</strong> {currentSuggestion.expected_improvement}
                      </div>
                    )}
                  </div>

                  {/* Code Views */}
                  {viewMode === 'side-by-side' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Current Code */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-sm font-semibold text-red-700">Current Code (Issues)</div>
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            onClick={() => copyToClipboard(currentSuggestion.current_code, 'Current code')}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                        <pre className="bg-red-50 border-2 border-red-300 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap overflow-auto leading-relaxed">
                          {currentSuggestion.current_code}
                        </pre>
                      </div>

                      {/* Improved Code */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-sm font-semibold text-green-700">Corrected Code (Solution)</div>
                          <div className="flex gap-1">
                            <Button 
                              size="sm" 
                              variant="ghost" 
                              onClick={() => copyToClipboard(currentSuggestion.improved_code, 'Improved code')}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                            <Button 
                              size="sm" 
                              variant="ghost" 
                              onClick={() => downloadCode(currentSuggestion.improved_code, `${selectedFile?.file_path.split('/').pop()}.fixed`)}
                            >
                              <Download className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        <pre className="bg-green-50 border-2 border-green-300 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap overflow-auto leading-relaxed">
                          {currentSuggestion.improved_code}
                        </pre>
                      </div>
                    </div>
                  )}

                  {viewMode === 'text-diff' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold text-gray-700">Complete Corrected Code</div>
                        <div className="flex gap-1">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => copyToClipboard(currentSuggestion.improved_code, 'Complete code')}
                          >
                            <Copy className="h-3 w-3 mr-1" />
                            Copy
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => downloadCode(currentSuggestion.improved_code, `${selectedFile?.file_path.split('/').pop()}.fixed`)}
                          >
                            <Download className="h-3 w-3 mr-1" />
                            Download
                          </Button>
                        </div>
                      </div>
                      <div className="bg-gradient-to-b from-green-50 to-white border-2 border-green-300 rounded-lg p-5 overflow-auto">
                        <pre className="text-sm font-mono leading-relaxed whitespace-pre-wrap text-gray-800">
                          {currentSuggestion.improved_code}
                        </pre>
                          </div>
                      
                      {/* Show original for reference */}
                      <details className="mt-4">
                        <summary className="cursor-pointer text-sm font-semibold text-gray-600 hover:text-gray-800 p-2 bg-gray-100 rounded">
                          Show Original Code (with issues)
                        </summary>
                        <div className="mt-2 bg-red-50 border border-red-200 rounded-lg p-4 overflow-auto">
                          <pre className="text-sm font-mono leading-relaxed whitespace-pre-wrap text-gray-700">
                            {currentSuggestion.current_code}
                      </pre>
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-sm text-gray-500 py-12">
                  No suggestions available for the selected file.
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default FullRepositoryAnalysis;
