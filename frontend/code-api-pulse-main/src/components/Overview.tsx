import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, Activity, Zap, Github, Upload, RefreshCw } from 'lucide-react';
import dashboardHero from '@/assets/dashboard-hero.jpg';
import apiIcon from '@/assets/api-icon.jpg';
import githubIcon from '@/assets/github-icon.jpg';
import { useState, useEffect } from 'react';
import { apiService } from '@/services/api';

interface OverviewProps {
  onNavigate?: (section: string) => void;
}

const Overview = ({ onNavigate }: OverviewProps) => {
  // State for real-time data
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Fetch performance data
  const fetchPerformanceData = async () => {
    try {
      setIsLoading(true);
      const data = await apiService.getLatestPerformanceAnalysis();
      setPerformanceData(data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error fetching performance data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    fetchPerformanceData();
    
    const interval = setInterval(fetchPerformanceData, 30000);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  // Manual refresh
  const handleRefresh = () => {
    fetchPerformanceData();
  };

  // Navigation handlers
  const handleUploadReport = () => {
    onNavigate?.('reports');
  };

  const handleConnectGitHub = () => {
    onNavigate?.('github');
  };

  const handleStartAnalysis = () => {
    onNavigate?.('reports');
  };

  const handleConnectRepository = () => {
    onNavigate?.('github');
  };

  // Calculate stats from performance data
  const calculateStats = () => {
    if (!performanceData) {
      return [
        {
          title: 'APIs Analyzed',
          value: '0',
          change: '0%',
          trend: 'stable',
          icon: Activity,
          gradient: 'gradient-primary'
        },
        {
          title: 'Performance Issues',
          value: '0',
          change: '0%',
          trend: 'stable',
          icon: TrendingDown,
          gradient: 'gradient-secondary'
        },
        {
          title: 'Avg Response Time',
          value: 'N/A',
          change: '0%',
          trend: 'stable',
          icon: Zap,
          gradient: 'gradient-success'
        },
        {
          title: 'Repositories',
          value: '0',
          change: '0%',
          trend: 'stable',
          icon: Github,
          gradient: 'gradient-primary'
        },
      ];
    }

    const totalApis = performanceData.total_apis || 0;
    const worstApis = performanceData.worst_apis?.length || 0;
    const bestApis = performanceData.best_apis?.length || 0;
    const avgResponseTime = performanceData.worst_apis?.length > 0 
      ? Math.round(performanceData.worst_apis.reduce((sum: number, api: any) => sum + (api.avg_response_time_ms || 0), 0) / performanceData.worst_apis.length)
      : 0;

    return [
      {
        title: 'APIs Analyzed',
        value: totalApis.toString(),
        change: totalApis > 0 ? '+100%' : '0%',
        trend: totalApis > 0 ? 'up' : 'stable',
        icon: Activity,
        gradient: 'gradient-primary'
      },
      {
        title: 'Performance Issues',
        value: worstApis.toString(),
        change: worstApis > 0 ? `${Math.round((worstApis / totalApis) * 100)}%` : '0%',
        trend: worstApis > 0 ? 'up' : 'stable',
        icon: TrendingDown,
        gradient: 'gradient-secondary'
      },
      {
        title: 'Avg Response Time',
        value: avgResponseTime > 0 ? `${avgResponseTime}ms` : 'N/A',
        change: avgResponseTime > 1000 ? '+50%' : avgResponseTime > 0 ? '-10%' : '0%',
        trend: avgResponseTime > 1000 ? 'up' : avgResponseTime > 0 ? 'down' : 'stable',
        icon: Zap,
        gradient: 'gradient-success'
      },
      {
        title: 'Repositories',
        value: '1', // Assuming 1 connected repository
        change: '0%',
        trend: 'stable',
        icon: Github,
        gradient: 'gradient-primary'
      },
    ];
  };

  const stats = calculateStats();

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <Card className="relative overflow-hidden border-0 shadow-card">
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-20"
          style={{ backgroundImage: `url(${dashboardHero})` }}
        />
        <div className="relative gradient-primary">
          <CardContent className="p-8">
            <div className="max-w-2xl">
              <h1 className="text-4xl font-bold text-primary-foreground mb-4">
                AccelApi
              </h1>
              <p className="text-xl text-primary-foreground/90 mb-8">
                Analyze API performance, detect bottlenecks, and generate targeted improvements 
                with AI-powered insights and GitHub integration.
              </p>
               <div className="flex flex-wrap gap-4">
                 <Button 
                   size="lg" 
                   variant="secondary"
                   className="bg-white/20 text-white border-white/20 hover:bg-white/30 backdrop-blur-sm"
                   onClick={handleUploadReport}
                 >
                   <Upload className="mr-2 h-5 w-5" />
                   Upload Report
                 </Button>
                 <Button 
                   size="lg" 
                   variant="outline"
                   className="bg-white/10 text-white border-white/20 hover:bg-white/20 backdrop-blur-sm"
                   onClick={handleConnectGitHub}
                 >
                   <Github className="mr-2 h-5 w-5" />
                   Connect GitHub
                 </Button>
                 <Button 
                   size="lg" 
                   variant="outline"
                   className="bg-white/10 text-white border-white/20 hover:bg-white/20 backdrop-blur-sm"
                   onClick={handleRefresh}
                   disabled={isLoading}
                 >
                   <RefreshCw className={`mr-2 h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                   {isLoading ? 'Refreshing...' : 'Refresh Data'}
                 </Button>
               </div>
              
              {/* Last Updated Info */}
              {lastUpdated && (
                <div className="mt-4 text-sm text-primary-foreground/80">
                  Last updated: {lastUpdated.toLocaleTimeString()}
                  {performanceData && (
                    <span className="ml-2">
                      • {performanceData.total_apis || 0} APIs analyzed
                    </span>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </div>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title} className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                    <p className="text-3xl font-bold mt-1">{stat.value}</p>
                    <div className="flex items-center mt-2">
                      {stat.trend === 'up' ? (
                        <TrendingUp className="h-4 w-4 text-success mr-1" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-success mr-1" />
                      )}
                      <span className="text-sm font-medium text-success">{stat.change}</span>
                    </div>
                  </div>
                  <div className={`${stat.gradient} rounded-full p-3`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="card-hover">
          <CardHeader className="pb-4">
            <div className="flex items-center space-x-3">
              <img src={apiIcon} alt="API Analysis" className="w-10 h-10 rounded-lg" />
              <div>
                <CardTitle>Report Analysis</CardTitle>
                <p className="text-sm text-muted-foreground">Upload performance reports and get AI insights</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Upload PDF, DOCX, CSV files or zip archives to analyze API performance data. 
              Get detailed insights about best/worst performing APIs with actionable suggestions.
            </p>
            <Button className="w-full" onClick={handleStartAnalysis}>
              <Upload className="mr-2 h-4 w-4" />
              Start Analysis
            </Button>
          </CardContent>
        </Card>

        <Card className="card-hover">
          <CardHeader className="pb-4">
            <div className="flex items-center space-x-3">
              <img src={githubIcon} alt="GitHub Analysis" className="w-10 h-10 rounded-lg" />
              <div>
                <CardTitle>GitHub Integration</CardTitle>
                <p className="text-sm text-muted-foreground">Analyze source code and generate improvements</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Connect your GitHub repositories to analyze source code, compare with performance data, 
              and generate targeted code improvements with diff previews.
            </p>
            <Button variant="secondary" className="w-full" onClick={handleConnectRepository}>
              <Github className="mr-2 h-4 w-4" />
              Connect Repository
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {(performanceData ? [
              { 
                action: 'Performance Analysis Completed', 
                file: `${performanceData.total_apis || 0} APIs analyzed`, 
                time: lastUpdated?.toLocaleTimeString() || 'Just now', 
                status: 'success' 
              },
              { 
                action: 'Performance Issues Detected', 
                file: `${performanceData.worst_apis?.length || 0} APIs with issues`, 
                time: lastUpdated?.toLocaleTimeString() || 'Just now', 
                status: 'warning' 
              },
              { 
                action: 'Best Performing APIs', 
                file: `${performanceData.best_apis?.length || 0} APIs performing well`, 
                time: lastUpdated?.toLocaleTimeString() || 'Just now', 
                status: 'success' 
              },
            ] : [
              { action: 'No recent activity', file: 'Upload a report to get started', time: 'N/A', status: 'info' },
            ]).map((item, index) => (
              <div key={index} className="flex items-center justify-between py-3 border-b border-border last:border-0">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    item.status === 'success' ? 'bg-green-500' :
                    item.status === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
                  }`} />
                  <div>
                    <p className="font-medium">{item.action}</p>
                    <p className="text-sm text-muted-foreground">{item.file}</p>
                  </div>
                </div>
                <span className="text-sm text-muted-foreground">{item.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Overview;