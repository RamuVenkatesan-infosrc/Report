import { useState, useRef, useCallback, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Upload, FileText, BarChart3, TrendingUp, AlertTriangle, CheckCircle, Settings, Star, X, Download, RefreshCw, Brain } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import AnalysisConfiguration from './AnalysisConfiguration';
import { apiService, AnalysisConfig, AnalysisResponse, AnalysisResult } from '@/services/api';

interface APIResult {
  endpoint: string;
  time: string;
  score: number;
  reason: string;
  severity?: 'critical' | 'major' | 'minor';
  issue?: string;
  isCritical?: boolean;
  isIgnored?: boolean;
}

interface ConfigurableReportAnalysisProps {
  onAnalysisComplete?: (analysisData: any) => void;
  initialAnalysisData?: AnalysisResponse | null;
  isLoadingLatestAnalysis?: boolean;
}

const ConfigurableReportAnalysis = ({ 
  onAnalysisComplete, 
  initialAnalysisData, 
  isLoadingLatestAnalysis 
}: ConfigurableReportAnalysisProps) => {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [showConfiguration, setShowConfiguration] = useState(false);
  const [analysisConfig, setAnalysisConfig] = useState<AnalysisConfig | null>(null);
  const [apiOverrides, setApiOverrides] = useState<{[key: string]: {critical: boolean, ignored: boolean}}>({});
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(initialAnalysisData || null);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Update analysis data when initial data changes
  useEffect(() => {
    if (initialAnalysisData) {
      setAnalysisData(initialAnalysisData);
      setAnalysisComplete(true);
    }
  }, [initialAnalysisData]);

  // File handling functions
  const handleFileSelect = useCallback((file: File) => {
    // Validate file type
    const allowedTypes = [
      'text/xml', 'application/xml', 'text/csv', 'application/csv',
      'application/json', 'application/zip', 'application/x-zip-compressed',
      'text/plain', 'application/octet-stream'
    ];
    
    const fileExtension = file.name.toLowerCase().split('.').pop();
    const allowedExtensions = ['xml', 'csv', 'jtl', 'json', 'zip', 'txt'];
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension || '')) {
      toast({
        title: "Invalid file type",
        description: "Please upload XML, CSV, JTL, JSON, ZIP, or TXT files only.",
        variant: "destructive",
      });
      return;
    }

    setSelectedFile(file);
    setError(null);
    toast({
      title: "File selected",
      description: `${file.name} is ready for analysis`,
    });
  }, [toast]);

  const handleFileUpload = async () => {
    if (!selectedFile) {
      toast({
        title: "No file selected",
        description: "Please select a file to upload",
        variant: "destructive",
      });
      return;
    }

    setIsAnalyzing(true);
    setUploadProgress(0);
    setError(null);
    setAnalysisComplete(false);
    setAnalysisData(null);
    
    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Call the API
      const response = await apiService.analyzeReport(selectedFile, analysisConfig || {});
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setAnalysisData(response);
      setAnalysisComplete(true);
      
      // Notify parent component about analysis completion
      if (onAnalysisComplete) {
        onAnalysisComplete(response);
      }
      
      toast({
        title: "Analysis complete",
        description: `Successfully analyzed ${response.processed_files.length} files`,
      });
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze report';
      setError(errorMessage);
      toast({
        title: "Analysis failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const resetAnalysis = () => {
    clearAnalysis();
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    // Also clear the parent state
    if (onAnalysisComplete) {
      onAnalysisComplete(null);
    }
  };

  const handleConfigSave = (config: AnalysisConfig) => {
    setAnalysisConfig(config);
    setShowConfiguration(false);
    toast({
      title: "Configuration saved",
      description: "Analysis configuration has been updated",
    });
  };

  const toggleApiCritical = (endpoint: string) => {
    setApiOverrides(prev => ({
      ...prev,
      [endpoint]: {
        ...prev[endpoint],
        critical: !prev[endpoint]?.critical,
        ignored: false
      }
    }));
  };

  const toggleApiIgnored = (endpoint: string) => {
    setApiOverrides(prev => ({
      ...prev,
      [endpoint]: {
        ...prev[endpoint],
        ignored: !prev[endpoint]?.ignored,
        critical: false
      }
    }));
  };

  const clearAnalysis = () => {
    setAnalysisData(null);
    setAnalysisComplete(false);
    setSelectedFile(null);
    setError(null);
    setApiOverrides({});
    toast({
      title: "Analysis cleared",
      description: "You can now upload a new file for analysis",
    });
  };

  // Calculate API scores based on configuration
  const calculateApiScore = (api: AnalysisResult): number => {
    const responseTime = api.avg_response_time_ms;
    const errorRate = api.error_rate_percent;
    const throughput = api.throughput_rps;
    const percentile95 = api.percentile_95_latency_ms;
    
    let score = 100;
    let hasAnyThreshold = false;
    
    // Response time scoring (Good: <= threshold, Bad: >= threshold)
    if (analysisConfig?.response_time_good_threshold !== undefined) {
      hasAnyThreshold = true;
      if (responseTime > analysisConfig.response_time_good_threshold) {
        score -= 25; // Penalty for exceeding good threshold
      }
    }
    if (analysisConfig?.response_time_bad_threshold !== undefined) {
      hasAnyThreshold = true;
      if (responseTime >= analysisConfig.response_time_bad_threshold) {
        score -= 40; // Heavy penalty for reaching bad threshold
      }
    }
    
    // Error rate scoring (Good: <= threshold, Bad: >= threshold)
    if (analysisConfig?.error_rate_good_threshold !== undefined) {
      hasAnyThreshold = true;
      if (errorRate > analysisConfig.error_rate_good_threshold) {
        score -= 20; // Penalty for exceeding good threshold
      }
    }
    if (analysisConfig?.error_rate_bad_threshold !== undefined) {
      hasAnyThreshold = true;
      if (errorRate >= analysisConfig.error_rate_bad_threshold) {
        score -= 35; // Heavy penalty for reaching bad threshold
      }
    }
    
    // Throughput scoring (Good: >= threshold, Bad: <= threshold)
    if (analysisConfig?.throughput_good_threshold !== undefined) {
      hasAnyThreshold = true;
      if (throughput < analysisConfig.throughput_good_threshold) {
        score -= 15; // Penalty for not reaching good threshold
      }
    }
    if (analysisConfig?.throughput_bad_threshold !== undefined) {
      hasAnyThreshold = true;
      if (throughput <= analysisConfig.throughput_bad_threshold) {
        score -= 25; // Heavy penalty for reaching bad threshold
      }
    }
    
    // 95th percentile latency scoring (Good: <= threshold, Bad: >= threshold)
    if (analysisConfig?.percentile_95_latency_good_threshold !== undefined) {
      hasAnyThreshold = true;
      if (percentile95 > analysisConfig.percentile_95_latency_good_threshold) {
        score -= 20; // Penalty for exceeding good threshold
      }
    }
    if (analysisConfig?.percentile_95_latency_bad_threshold !== undefined) {
      hasAnyThreshold = true;
      if (percentile95 >= analysisConfig.percentile_95_latency_bad_threshold) {
        score -= 35; // Heavy penalty for reaching bad threshold
      }
    }
    
    // If no config or no thresholds set, use default scoring based on industry standards
    if (!hasAnyThreshold) {
      // Default industry standards
      if (responseTime > 1000) score -= 30; // > 1 second is slow
      if (responseTime > 2000) score -= 20; // > 2 seconds is very slow
      
      if (errorRate > 1) score -= 20; // > 1% error rate is concerning
      if (errorRate > 5) score -= 25; // > 5% error rate is bad
      
      if (throughput < 50) score -= 15; // < 50 RPS is low
      if (throughput < 10) score -= 20; // < 10 RPS is very low
      
      if (percentile95 > 2000) score -= 20; // > 2 second 95th percentile is slow
      if (percentile95 > 5000) score -= 25; // > 5 second 95th percentile is very slow
    }
    
    return Math.max(score, 0);
  };

  // Convert AnalysisResult to APIResult for display
  const convertToAPIResult = (api: AnalysisResult): APIResult => {
    // If thresholds are set, use backend categorization; otherwise use frontend scoring
    const hasThresholds = analysisConfig && Object.values(analysisConfig).some(val => val !== undefined && val !== null);
    
    let score, severity, reason, issue;
    
    if (hasThresholds) {
      // Use backend categorization when thresholds are set
      // Backend has already categorized APIs based on thresholds
      if (api.is_good_response_time || api.is_good_error_rate || api.is_good_throughput || api.is_good_percentile_95_latency) {
        score = 90;
        severity = 'minor';
        reason = 'Meets good performance criteria';
        issue = 'No issues';
      } else if (api.is_bad_response_time || api.is_bad_error_rate || api.is_bad_throughput || api.is_bad_percentile_95_latency) {
        score = 30;
        severity = 'critical';
        reason = 'Exceeds bad performance thresholds';
        issue = 'Critical performance issues';
      } else {
        // Unmatched conditions
        score = 60;
        severity = 'major';
        reason = 'Falls between good and bad thresholds';
        issue = 'Minor performance concerns';
      }
    } else {
      // Use frontend scoring when no thresholds are set
      score = calculateApiScore(api);
      severity = score >= 80 ? 'minor' : score >= 60 ? 'major' : 'critical';
      reason = getPerformanceReason(api);
      issue = getPerformanceIssue(api);
    }
    
    return {
      endpoint: api.endpoint,
      time: `${api.avg_response_time_ms.toFixed(0)}ms`,
      score: Math.round(score),
      reason,
      severity,
      issue,
      isCritical: severity === 'critical',
      isIgnored: apiOverrides[api.endpoint]?.ignored || false
    };
  };

  const getPerformanceReason = (api: AnalysisResult): string => {
    const reasons = [];
    if (api.is_good_response_time) reasons.push('Fast response time');
    if (api.is_good_error_rate) reasons.push('Low error rate');
    if (api.is_good_throughput) reasons.push('High throughput');
    if (api.is_good_percentile_95_latency) reasons.push('Good 95th percentile');
    
    // If no good flags, check if it's actually good based on our scoring
    if (reasons.length === 0) {
      const score = calculateApiScore(api);
      if (score >= 80) {
        return 'Good overall performance';
      } else if (score >= 60) {
        return 'Moderate performance';
      } else {
        return 'Performance issues detected';
      }
    }
    return reasons.join(', ');
  };

  const getPerformanceIssue = (api: AnalysisResult): string => {
    const issues = [];
    if (api.is_bad_response_time) issues.push('Slow response time');
    if (api.is_bad_error_rate) issues.push('High error rate');
    if (api.is_bad_throughput) issues.push('Low throughput');
    if (api.is_bad_percentile_95_latency) issues.push('High 95th percentile latency');
    
    // If no bad flags, check if it's actually bad based on our scoring
    if (issues.length === 0) {
      const score = calculateApiScore(api);
      if (score < 60) {
        return 'Multiple performance issues';
      } else if (score < 80) {
        return 'Minor performance concerns';
      } else {
        return 'No issues';
      }
    }
    return issues.join(', ');
  };

  // Get processed data from backend categorization
  const bestApis = analysisData?.analysis.best_api.map(convertToAPIResult) || [];
  const worstApis = analysisData?.analysis.worst_api.map(convertToAPIResult) || [];
  const moderateApis = analysisData?.analysis.details.map(convertToAPIResult) || [];
  
  // Check if both good and bad thresholds are set (for unmatched conditions)
  const hasBothThresholds = analysisConfig && 
    Object.values(analysisConfig).some(val => val !== undefined && val !== null) &&
    (analysisConfig.response_time_good_threshold !== undefined || analysisConfig.error_rate_good_threshold !== undefined || analysisConfig.throughput_good_threshold !== undefined || analysisConfig.percentile_95_latency_good_threshold !== undefined) &&
    (analysisConfig.response_time_bad_threshold !== undefined || analysisConfig.error_rate_bad_threshold !== undefined || analysisConfig.throughput_bad_threshold !== undefined || analysisConfig.percentile_95_latency_bad_threshold !== undefined);
  
  // Combine all issues (worst + moderate) into one issues list, unless both thresholds are set
  const allIssues = hasBothThresholds ? worstApis : [...worstApis, ...moderateApis];
  
  const totalApis = (analysisData?.analysis.best_api.length || 0) + 
                   (analysisData?.analysis.worst_api.length || 0) + 
                   (analysisData?.analysis.details.length || 0);

  return (
    <div className="space-y-8">
      {/* Configuration Toggle */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Performance Analysis</h2>
          <p className="text-muted-foreground">
            {analysisConfig ? 'Using custom configuration' : 'Using default configuration'}
            {initialAnalysisData && (
              <span className="ml-2 text-primary">• Loaded from storage</span>
            )}
            {!initialAnalysisData && !analysisComplete && (
              <span className="ml-2 text-muted-foreground">• Ready for new analysis</span>
            )}
          </p>
        </div>
        <Button 
          variant="outline" 
          onClick={() => setShowConfiguration(!showConfiguration)}
          className="flex items-center space-x-2"
        >
          <Settings className="h-4 w-4" />
          <span>Configure Analysis</span>
        </Button>
      </div>

      {/* Configuration Panel */}
      {showConfiguration && (
        <AnalysisConfiguration 
          onConfigSave={handleConfigSave}
          currentConfig={analysisConfig}
        />
      )}

      {/* Loading Latest Analysis */}
      {isLoadingLatestAnalysis && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-4">
              <RefreshCw className="h-6 w-6 animate-spin text-primary" />
              <div>
                <h3 className="font-semibold">Loading Latest Analysis</h3>
                <p className="text-sm text-muted-foreground">
                  Retrieving your most recent analysis from storage...
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Upload className="h-5 w-5" />
            <span>Upload Performance Reports</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div 
            className={`border-2 border-dashed rounded-lg p-8 text-center space-y-4 transition-colors ${
              isDragOver 
                ? 'border-primary bg-primary/5' 
                : 'border-border hover:border-primary/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
              <div className="w-16 h-16 mx-auto gradient-primary rounded-full flex items-center justify-center">
                <FileText className="h-8 w-8 text-white" />
              </div>
              <div>
              <h3 className="text-lg font-medium">
                {selectedFile ? selectedFile.name : 'Drop files here or click to upload'}
              </h3>
                <p className="text-muted-foreground">
                Supports XML, CSV, JTL, JSON, ZIP files and archives
              </p>
              {selectedFile && (
                <p className="text-sm text-primary mt-2">
                  File size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              )}
              </div>
            
            <input
              ref={fileInputRef}
              type="file"
              accept=".xml,.csv,.jtl,.json,.zip,.txt"
              onChange={handleFileInputChange}
              className="hidden"
            />
              
              {isAnalyzing && (
                <div className="space-y-4">
                  <Progress value={uploadProgress} className="w-full max-w-md mx-auto" />
                  <p className="text-sm text-muted-foreground">Analyzing performance data...</p>
                </div>
              )}
            
            {error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="flex gap-2 justify-center">
              <Button 
                onClick={() => fileInputRef.current?.click()}
                disabled={isAnalyzing}
                variant="outline"
              >
                <Upload className="h-4 w-4 mr-2" />
                Select File
              </Button>
              
              {selectedFile && (
            <Button 
              onClick={handleFileUpload} 
              disabled={isAnalyzing}
              className="shadow-primary"
            >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <BarChart3 className="h-4 w-4 mr-2" />
                      Analyze Report
                    </>
                  )}
                </Button>
              )}
              
              {analysisComplete && (
                <Button 
                  onClick={resetAnalysis}
                  variant="outline"
                >
                  <X className="h-4 w-4 mr-2" />
                  Reset
            </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Results */}
      {analysisComplete && analysisData && (
        <>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Best Performing API</p>
                    <p className="text-2xl font-bold text-success">
                      {bestApis.length > 0 ? bestApis[0].endpoint : 'N/A'}
                    </p>
                    <p className="text-sm text-success">
                      {bestApis.length > 0 ? bestApis[0].time : 'No data'}
                    </p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-success" />
                </div>
              </CardContent>
            </Card>

            <Card className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Worst Performing API</p>
                    <p className="text-2xl font-bold text-destructive">
                      {worstApis.length > 0 ? worstApis[0].endpoint : 'N/A'}
                    </p>
                    <p className="text-sm text-destructive">
                      {worstApis.length > 0 ? worstApis[0].time : 'No data'}
                    </p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-destructive" />
                </div>
              </CardContent>
            </Card>

            <Card className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Issues by Severity</p>
                    <div className="flex space-x-2 mt-1">
                      <Badge variant="destructive" className="text-xs">
                        {worstApis.filter(api => api.severity === 'critical').length} Critical
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {moderateApis.filter(api => api.severity === 'major').length} Major
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {bestApis.filter(api => api.severity === 'minor').length} Minor
                      </Badge>
                    </div>
                  </div>
                  <BarChart3 className="h-8 w-8 text-warning" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Analysis with Manual Overrides */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-success flex items-center justify-between">
                  <span>Best Performing APIs</span>
                  <Badge variant="secondary" className="bg-success/20 text-success">
                    {bestApis.length} APIs
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {bestApis.length > 0 ? (
                    bestApis.map((api, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-success/10 rounded-lg border border-success/20">
                        <div className="flex-1">
                          <p className="font-medium text-success">{api.endpoint}</p>
                          <p className="text-sm text-muted-foreground">{api.reason}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-success">{api.time}</p>
                          <p className="text-sm text-success">Score: {api.score}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No best performing APIs found</p>
                      <p className="text-sm">All APIs may have performance issues</p>
                      </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-destructive flex items-center justify-between">
                  <span>Performance Issues</span>
                  <Badge variant="destructive">
                    {allIssues.length} Issues
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {allIssues.length > 0 ? (
                    allIssues.map((api, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-destructive/10 rounded-lg border border-destructive/20">
                        <div className="flex-1">
                          <p className="font-medium text-destructive">{api.endpoint}</p>
                          <p className="text-sm text-muted-foreground">{api.issue || api.reason || 'Performance issue detected'}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-destructive">{api.time || `${api.score}%`}</p>
                          <span className={`text-xs px-2 py-1 rounded ${
                            api.severity === 'critical' ? 'bg-destructive text-destructive-foreground' : 
                            api.severity === 'major' ? 'bg-warning text-warning-foreground' : 
                            'bg-secondary text-secondary-foreground'
                          }`}>
                            {api.severity?.toUpperCase() || 'ISSUE'}
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                    <p>No performance issues found</p>
                      <p className="text-sm">All APIs are performing well</p>
                      </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Configuration Summary */}
          {analysisConfig && (
            <Card className="border-primary/20 bg-primary/5">
              <CardHeader>
                <CardTitle className="text-primary">Active Configuration Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="font-medium">Configuration Type</Label>
                    <p className="text-sm text-muted-foreground">Custom Analysis Settings</p>
                  </div>
                  <div>
                    <Label className="font-medium">Thresholds Applied</Label>
                    <p className="text-sm text-muted-foreground">
                      {Object.keys(analysisConfig).filter(key => analysisConfig[key as keyof AnalysisConfig] !== undefined).length} settings
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Report Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Report Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-card rounded-lg border">
                    <p className="text-2xl font-bold text-primary">{totalApis}</p>
                    <p className="text-sm text-muted-foreground">Total APIs Analyzed</p>
                  </div>
                  <div className="text-center p-4 bg-card rounded-lg border">
                    <p className="text-2xl font-bold text-success">{bestApis.length}</p>
                    <p className="text-sm text-muted-foreground">Well-Performing</p>
                  </div>
                  <div className="text-center p-4 bg-card rounded-lg border">
                    <p className="text-2xl font-bold text-warning">{moderateApis.length}</p>
                    <p className="text-sm text-muted-foreground">Moderate</p>
                  </div>
                  <div className="text-center p-4 bg-card rounded-lg border">
                    <p className="text-2xl font-bold text-destructive">{worstApis.length}</p>
                    <p className="text-sm text-muted-foreground">Critical Issues</p>
                  </div>
                </div>

                <div className="prose prose-sm max-w-none">
                  <h4 className="text-lg font-semibold mb-3 flex items-center space-x-2">
                    <Brain className="h-5 w-5 text-primary" />
                    <span>AI-Powered Performance Assessment</span>
                  </h4>
                  
                  {/* AI Summary */}
                  {analysisData.analysis.insights && (
                    <div className="mb-6 p-4 bg-primary/5 rounded-lg border border-primary/20">
                      <p className="text-muted-foreground mb-4">
                        {analysisData.analysis.insights.summary}
                      </p>
                      
                      {/* Key Metrics */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div className="text-center p-3 bg-card rounded-lg">
                          <p className="text-sm text-muted-foreground">Avg Response Time</p>
                          <p className="font-semibold">{analysisData.analysis.insights.key_metrics.avg_response_time_ms}ms</p>
                        </div>
                        <div className="text-center p-3 bg-card rounded-lg">
                          <p className="text-sm text-muted-foreground">Avg Error Rate</p>
                          <p className="font-semibold">{analysisData.analysis.insights.key_metrics.avg_error_rate_percent}%</p>
                        </div>
                        <div className="text-center p-3 bg-card rounded-lg">
                          <p className="text-sm text-muted-foreground">Avg Throughput</p>
                          <p className="font-semibold">{analysisData.analysis.insights.key_metrics.avg_throughput_rps} RPS</p>
                        </div>
                        <div className="text-center p-3 bg-card rounded-lg">
                          <p className="text-sm text-muted-foreground">95th Percentile</p>
                          <p className="font-semibold">{analysisData.analysis.insights.key_metrics.overall_95th_percentile_ms}ms</p>
                        </div>
                      </div>
                      
                      {/* API Distribution */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div className="text-center p-3 bg-success/10 rounded-lg border border-success/20">
                          <p className="text-sm text-success">Best APIs</p>
                          <p className="font-semibold text-success">{analysisData.analysis.insights.key_metrics.best_performing}</p>
                        </div>
                        <div className="text-center p-3 bg-destructive/10 rounded-lg border border-destructive/20">
                          <p className="text-sm text-destructive">Worst APIs</p>
                          <p className="font-semibold text-destructive">{analysisData.analysis.insights.key_metrics.worst_performing}</p>
                        </div>
                        <div className="text-center p-3 bg-warning/10 rounded-lg border border-warning/20">
                          <p className="text-sm text-warning">Unmatched Conditions</p>
                          <p className="font-semibold text-warning">{hasBothThresholds ? moderateApis.length : (analysisData.analysis.insights.key_metrics.unmatched_conditions || 0)}</p>
                        </div>
                        <div className="text-center p-3 bg-primary/10 rounded-lg border border-primary/20">
                          <p className="text-sm text-primary">Total APIs</p>
                          <p className="font-semibold text-primary">{analysisData.analysis.insights.key_metrics.total_apis}</p>
                        </div>
                      </div>
                      
                      

                      {/* Unmatched Conditions - Show when both thresholds are set */}
                      {hasBothThresholds && moderateApis.length > 0 && (
                        <div className="mt-4">
                          <h5 className="font-semibold text-warning mb-2">APIs with Unmatched Conditions ({moderateApis.length})</h5>
                          <div className="space-y-2">
                            {moderateApis.map((api, index) => (
                              <div key={index} className="p-3 bg-warning/10 rounded-lg border border-warning/20">
                                <div className="flex justify-between items-start">
                                  <div>
                                    <p className="font-medium text-warning">{api.endpoint}</p>
                                    <p className="text-sm text-muted-foreground">{api.reason}</p>
                                  </div>
                                  <div className="text-right text-sm">
                                    <p className="text-warning">{api.time}</p>
                                    <p className="text-muted-foreground">{api.score}% score</p>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* AI Recommendations */}
                      {analysisData.analysis.insights.recommendations.length > 0 && (
                        <div className="mt-4">
                          <h5 className="font-semibold text-primary mb-2">AI Recommendations</h5>
                          <ul className="space-y-1">
                            {analysisData.analysis.insights.recommendations.map((rec, index) => (
                              <li key={index} className="flex items-start space-x-2 text-sm">
                                <span className="text-primary mt-1">•</span>
                                <span className="text-muted-foreground">{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Fallback to basic summary if no AI insights */}
                  {!analysisData.analysis.insights && (
                  <p className="text-muted-foreground mb-4">
                      {analysisData.summary}
                  </p>
                  )}
                  
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 bg-card rounded-lg border">
                        <h5 className="font-semibold text-primary mb-2">Files Processed</h5>
                        <ul className="text-sm text-muted-foreground space-y-1">
                          {analysisData.processed_files.map((file, index) => (
                            <li key={index} className="flex items-center">
                              <CheckCircle className="h-3 w-3 mr-2 text-success" />
                              {file}
                            </li>
                          ))}
                        </ul>
                      </div>
                      
                      {analysisData.skipped_files.length > 0 && (
                        <div className="p-4 bg-card rounded-lg border">
                          <h5 className="font-semibold text-warning mb-2">Files Skipped</h5>
                          <ul className="text-sm text-muted-foreground space-y-1">
                            {analysisData.skipped_files.map((file, index) => (
                              <li key={index} className="flex items-center">
                                <X className="h-3 w-3 mr-2 text-warning" />
                                {file}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                    
                    {analysisData.thresholds_used && (
                      <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
                        <h5 className="font-semibold text-primary mb-2">Analysis Thresholds Used</h5>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          {analysisData.thresholds_used.response_time_good_threshold && (
                            <div>
                              <span className="text-muted-foreground">Response Time Good:</span>
                              <p className="font-medium">{analysisData.thresholds_used.response_time_good_threshold}ms</p>
                            </div>
                          )}
                          {analysisData.thresholds_used.response_time_bad_threshold && (
                            <div>
                              <span className="text-muted-foreground">Response Time Bad:</span>
                              <p className="font-medium">{analysisData.thresholds_used.response_time_bad_threshold}ms</p>
                            </div>
                          )}
                          {analysisData.thresholds_used.error_rate_good_threshold && (
                            <div>
                              <span className="text-muted-foreground">Error Rate Good:</span>
                              <p className="font-medium">{analysisData.thresholds_used.error_rate_good_threshold}%</p>
                            </div>
                          )}
                          {analysisData.thresholds_used.error_rate_bad_threshold && (
                            <div>
                              <span className="text-muted-foreground">Error Rate Bad:</span>
                              <p className="font-medium">{analysisData.thresholds_used.error_rate_bad_threshold}%</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default ConfigurableReportAnalysis;
