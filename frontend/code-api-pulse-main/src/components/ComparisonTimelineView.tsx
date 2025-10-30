import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TrendingUp, TrendingDown, Minus, Calendar, Target, BarChart3 } from 'lucide-react';

interface TimelineData {
  version: string;
  date: string;
  apis: {
    endpoint: string;
    score: number;
    responseTime: number;
    errorRate: number;
    change: 'improved' | 'declined' | 'stable';
    changePercent: number;
  }[];
}

const ComparisonTimelineView = () => {
  const [baselineVersion, setBaselineVersion] = useState('v1.0');
  const [compareVersion, setCompareVersion] = useState('v1.2');

  const timelineData: TimelineData[] = [];

  const getBaselineData = () => timelineData.find(d => d.version === baselineVersion);
  const getCompareData = () => timelineData.find(d => d.version === compareVersion);

  const calculateComparison = () => {
    const baseline = getBaselineData();
    const compare = getCompareData();
    
    if (!baseline || !compare) return [];

    return baseline.apis.map(baselineApi => {
      const compareApi = compare.apis.find(api => api.endpoint === baselineApi.endpoint);
      if (!compareApi) return { ...baselineApi, comparison: 'missing' };

      const scoreChange = compareApi.score - baselineApi.score;
      const responseChange = ((baselineApi.responseTime - compareApi.responseTime) / baselineApi.responseTime) * 100;
      const errorChange = ((baselineApi.errorRate - compareApi.errorRate) / baselineApi.errorRate) * 100;

      return {
        endpoint: baselineApi.endpoint,
        baseline: baselineApi,
        current: compareApi,
        scoreChange,
        responseChange,
        errorChange,
        overallTrend: scoreChange > 10 ? 'improved' : scoreChange < -10 ? 'declined' : 'stable'
      };
    });
  };

  const comparison = calculateComparison();

  return (
    <div className="space-y-6">
      {/* Version Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Calendar className="h-5 w-5" />
            <span>Performance Comparison Timeline</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <label className="text-sm font-medium">Baseline Version</label>
              <Select value={baselineVersion} onValueChange={setBaselineVersion}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {timelineData.map(version => (
                    <SelectItem key={version.version} value={version.version}>
                      {version.version} ({version.date})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <label className="text-sm font-medium">Compare With</label>
              <Select value={compareVersion} onValueChange={setCompareVersion}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {timelineData.map(version => (
                    <SelectItem key={version.version} value={version.version}>
                      {version.version} ({version.date})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Comparison Results */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Summary Cards */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Version Comparison Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-success/10 rounded-lg border border-success/20">
                <div className="text-2xl font-bold text-success mb-1">
                  {comparison.filter(c => c.overallTrend === 'improved').length}
                </div>
                <div className="text-sm text-muted-foreground">APIs Improved</div>
              </div>

              <div className="text-center p-4 bg-destructive/10 rounded-lg border border-destructive/20">
                <div className="text-2xl font-bold text-destructive mb-1">
                  {comparison.filter(c => c.overallTrend === 'declined').length}
                </div>
                <div className="text-sm text-muted-foreground">APIs Declined</div>
              </div>

              <div className="text-center p-4 bg-secondary/10 rounded-lg border border-secondary/20">
                <div className="text-2xl font-bold text-secondary mb-1">
                  {comparison.filter(c => c.overallTrend === 'stable').length}
                </div>
                <div className="text-sm text-muted-foreground">APIs Stable</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Comparison */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>API Performance Changes</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {comparison.map((api, index) => (
                <div key={index} className="p-4 border rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <h4 className="font-medium">{api.endpoint}</h4>
                      <Badge 
                        variant={api.overallTrend === 'improved' ? 'default' : api.overallTrend === 'declined' ? 'destructive' : 'secondary'}
                        className={api.overallTrend === 'improved' ? 'bg-success/20 text-success' : undefined}
                      >
                        {api.overallTrend === 'improved' && <TrendingUp className="h-3 w-3 mr-1" />}
                        {api.overallTrend === 'declined' && <TrendingDown className="h-3 w-3 mr-1" />}
                        {api.overallTrend === 'stable' && <Minus className="h-3 w-3 mr-1" />}
                        {api.overallTrend}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">Score Change</div>
                      <div className={`font-bold ${api.scoreChange > 0 ? 'text-success' : api.scoreChange < 0 ? 'text-destructive' : 'text-muted-foreground'}`}>
                        {api.scoreChange > 0 ? '+' : ''}{api.scoreChange}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div className="space-y-1">
                      <div className="text-muted-foreground">Performance Score</div>
                      <div className="flex items-center justify-between">
                        <span>{baselineVersion}: {api.baseline.score}</span>
                        <span>→</span>
                        <span className="font-medium">{compareVersion}: {api.current.score}</span>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-muted-foreground">Response Time</div>
                      <div className="flex items-center justify-between">
                        <span>{api.baseline.responseTime}ms</span>
                        <span>→</span>
                        <span className="font-medium">{api.current.responseTime}ms</span>
                      </div>
                      <div className={`text-xs ${api.responseChange > 0 ? 'text-success' : api.responseChange < 0 ? 'text-destructive' : 'text-muted-foreground'}`}>
                        {api.responseChange > 0 ? '+' : ''}{api.responseChange.toFixed(1)}% improvement
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-muted-foreground">Error Rate</div>
                      <div className="flex items-center justify-between">
                        <span>{api.baseline.errorRate}%</span>
                        <span>→</span>
                        <span className="font-medium">{api.current.errorRate}%</span>
                      </div>
                      <div className={`text-xs ${api.errorChange > 0 ? 'text-success' : api.errorChange < 0 ? 'text-destructive' : 'text-muted-foreground'}`}>
                        {api.errorChange > 0 ? '+' : ''}{api.errorChange.toFixed(1)}% improvement
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Timeline View */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Target className="h-5 w-5" />
              <span>Performance Timeline</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {timelineData.map((version, index) => (
                <div key={version.version} className="flex items-start space-x-4">
                  <div className="flex flex-col items-center">
                    <div className={`w-4 h-4 rounded-full ${
                      version.version === baselineVersion || version.version === compareVersion 
                        ? 'bg-primary' 
                        : 'bg-muted'
                    }`}></div>
                    {index < timelineData.length - 1 && (
                      <div className="w-0.5 h-16 bg-border mt-2"></div>
                    )}
                  </div>
                  
                  <div className="flex-1 pb-8">
                    <div className="flex items-center space-x-2 mb-2">
                      <h4 className="font-medium">{version.version}</h4>
                      <Badge variant="outline" className="text-xs">{version.date}</Badge>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {version.apis.map((api, apiIndex) => (
                        <div key={apiIndex} className="p-3 bg-card border rounded-lg">
                          <div className="text-sm font-medium mb-1">{api.endpoint}</div>
                          <div className="text-xs text-muted-foreground">
                            Score: {api.score} | {api.responseTime}ms | {api.errorRate}% errors
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ComparisonTimelineView;