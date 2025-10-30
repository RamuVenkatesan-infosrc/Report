import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Upload, FileText, BarChart3, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

const ReportAnalysis = () => {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  const handleFileUpload = () => {
    setIsAnalyzing(true);
    setUploadProgress(0);
    
    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsAnalyzing(false);
          setAnalysisComplete(true);
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  return (
    <div className="space-y-8">
      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Upload className="h-5 w-5" />
            <span>Upload Performance Reports</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border-2 border-dashed border-border rounded-lg p-8 text-center space-y-4">
            <div className="w-16 h-16 mx-auto gradient-primary rounded-full flex items-center justify-center">
              <FileText className="h-8 w-8 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-medium">Drop files here or click to upload</h3>
              <p className="text-muted-foreground">
                Supports PDF, DOCX, TXT, CSV, PPTX files and ZIP archives
              </p>
            </div>
            
            {isAnalyzing && (
              <div className="space-y-4">
                <Progress value={uploadProgress} className="w-full max-w-md mx-auto" />
                <p className="text-sm text-muted-foreground">Analyzing performance data...</p>
              </div>
            )}
            
            <Button 
              onClick={handleFileUpload} 
              disabled={isAnalyzing}
              className="shadow-primary"
            >
              {isAnalyzing ? 'Analyzing...' : 'Upload & Analyze'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Results */}
      {analysisComplete && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Best Performing API</p>
                    <p className="text-2xl font-bold text-success">/api/users</p>
                    <p className="text-sm text-success">95ms avg response</p>
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
                    <p className="text-2xl font-bold text-destructive">/api/orders</p>
                    <p className="text-sm text-destructive">2.3s avg response</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-destructive" />
                </div>
              </CardContent>
            </Card>

            <Card className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Issues Found</p>
                    <p className="text-2xl font-bold text-warning">18</p>
                    <p className="text-sm text-success flex items-center">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      24% improvement
                    </p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-warning" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Analysis */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-success">Best Performing APIs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { endpoint: '/api/users', time: '95ms', score: '98%', reason: 'Efficient caching' },
                    { endpoint: '/api/auth', time: '120ms', score: '95%', reason: 'Optimized queries' },
                    { endpoint: '/api/products', time: '145ms', score: '92%', reason: 'Good indexing' },
                  ].map((api, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-success/10 rounded-lg border border-success/20">
                      <div>
                        <p className="font-medium text-success">{api.endpoint}</p>
                        <p className="text-sm text-muted-foreground">{api.reason}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-success">{api.time}</p>
                        <p className="text-sm text-success">{api.score}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-destructive">Performance Issues</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { endpoint: '/api/orders', time: '2.3s', issue: 'N+1 Query Problem', severity: 'High' },
                    { endpoint: '/api/analytics', time: '1.8s', issue: 'Missing Index', severity: 'Medium' },
                    { endpoint: '/api/reports', time: '1.2s', issue: 'Large Payload', severity: 'Medium' },
                  ].map((api, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-destructive/10 rounded-lg border border-destructive/20">
                      <div>
                        <p className="font-medium text-destructive">{api.endpoint}</p>
                        <p className="text-sm text-muted-foreground">{api.issue}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-destructive">{api.time}</p>
                        <span className={`text-xs px-2 py-1 rounded ${
                          api.severity === 'High' ? 'bg-destructive text-destructive-foreground' : 'bg-warning text-warning-foreground'
                        }`}>
                          {api.severity}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* AI Insights */}
          <Card>
            <CardHeader>
              <CardTitle>AI-Generated Insights & Recommendations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                  <h4 className="font-semibold text-primary mb-2">🎯 Priority Fix: /api/orders endpoint</h4>
                  <p className="text-sm text-muted-foreground mb-3">
                    The orders endpoint is experiencing severe N+1 query issues, causing 2.3s average response times. 
                    This affects 15% of your user base and causes checkout abandonment.
                  </p>
                  <div className="space-y-2 text-sm">
                    <p><strong>Root Cause:</strong> Lazy loading relationships without eager loading</p>
                    <p><strong>Suggested Fix:</strong> Implement eager loading for order items and user data</p>
                    <p><strong>Expected Improvement:</strong> 80% reduction in response time (from 2.3s to ~460ms)</p>
                  </div>
                </div>

                <div className="p-4 bg-secondary/10 rounded-lg border border-secondary/20">
                  <h4 className="font-semibold text-secondary mb-2">💡 Optimization Opportunity: Caching Strategy</h4>
                  <p className="text-sm text-muted-foreground mb-3">
                    Your best-performing endpoints use effective caching. Apply similar patterns to underperforming APIs.
                  </p>
                  <div className="space-y-2 text-sm">
                    <p><strong>Recommendation:</strong> Implement Redis caching for frequently accessed data</p>
                    <p><strong>Impact:</strong> 40-60% performance improvement across 8 endpoints</p>
                  </div>
                </div>

                <Button className="w-full" variant="secondary">
                  Generate Detailed Implementation Plan
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default ReportAnalysis;