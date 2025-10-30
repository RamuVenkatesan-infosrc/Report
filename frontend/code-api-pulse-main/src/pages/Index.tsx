import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import Overview from '@/components/Overview';
import ConfigurableReportAnalysis from '@/components/ConfigurableReportAnalysis';
import GitHubAnalysis from '@/components/EnhancedGitHubAnalysis';
import AIInsights from '@/components/AIInsights';
import { AnalysisResult, AnalysisResponse } from '@/services/api';
import { apiService } from '@/services/api';

const Index = () => {
  const [issuesApis, setIssuesApis] = useState<AnalysisResult[]>([]);
  const [githubAnalysisResults, setGithubAnalysisResults] = useState<any>(null);
  const [reportAnalysisData, setReportAnalysisData] = useState<AnalysisResponse | null>(null);
  const [isLoadingLatestAnalysis, setIsLoadingLatestAnalysis] = useState(false);

  // Clear analysis data on page refresh/load
  useEffect(() => {
    const clearDataOnRefresh = async () => {
      try {
        await apiService.clearAnalysis();
        setReportAnalysisData(null);
        setIssuesApis([]);
      } catch (error) {
        console.log('Could not clear analysis data:', error);
      }
    };
    
    clearDataOnRefresh();
  }, []); // Run once on component mount

  const handleReportAnalysisComplete = (analysisData: any) => {
    // Store the complete analysis data
    setReportAnalysisData(analysisData);
    // Extract Issues APIs from the analysis data
    const issues = analysisData?.analysis?.worst_api || [];
    setIssuesApis(issues);
  };

  const handleGithubAnalysisComplete = (results: any) => {
    setGithubAnalysisResults(results);
  };

  // Load latest analysis when switching to reports section (only on explicit action if needed)
  const loadLatestAnalysis = async () => {
    if (reportAnalysisData) return; // Already have data
    
    setIsLoadingLatestAnalysis(true);
    try {
      const latestAnalysis = await apiService.getLatestPerformanceAnalysis();
      if (latestAnalysis.status === 'success' && latestAnalysis.analysis) {
        // The GET endpoint now returns the same format as POST
        setReportAnalysisData(latestAnalysis);
        setIssuesApis(latestAnalysis.analysis.worst_api || []);
      }
    } catch (error) {
      console.log('No previous analysis found or error loading:', error);
    } finally {
      setIsLoadingLatestAnalysis(false);
    }
  };

  return (
    <DashboardLayout>
      {(activeSection: string, setActiveSection: (section: string) => void) => {
        // Removed auto-fetch during render to prevent UI shaking
        switch (activeSection) {
          case 'reports':
            return (
              <ConfigurableReportAnalysis 
                onAnalysisComplete={handleReportAnalysisComplete}
                initialAnalysisData={reportAnalysisData}
                isLoadingLatestAnalysis={isLoadingLatestAnalysis}
              />
            );
          case 'github':
            return <GitHubAnalysis />;
          case 'insights':
            return <AIInsights />;
          default:
            return <Overview onNavigate={setActiveSection} />;
        }
      }}
    </DashboardLayout>
  );
};

export default Index;
