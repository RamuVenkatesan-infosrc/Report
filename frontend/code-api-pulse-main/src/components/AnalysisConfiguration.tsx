import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Settings } from 'lucide-react';
import { AnalysisConfig } from '@/services/api';

interface AnalysisConfigurationProps {
  onConfigSave: (config: AnalysisConfig) => void;
  currentConfig?: AnalysisConfig | null;
}

const AnalysisConfiguration = ({ onConfigSave, currentConfig }: AnalysisConfigurationProps) => {
  const [thresholds, setThresholds] = useState<AnalysisConfig>({
    response_time_good_threshold: undefined,
    response_time_bad_threshold: undefined,
    error_rate_good_threshold: undefined,
    error_rate_bad_threshold: undefined,
    throughput_good_threshold: undefined,
    throughput_bad_threshold: undefined,
    percentile_95_latency_good_threshold: undefined,
    percentile_95_latency_bad_threshold: undefined
  });

  // Load current config when component mounts or config changes
  useEffect(() => {
    if (currentConfig) {
      setThresholds(currentConfig);
    }
  }, [currentConfig]);

  const handleSaveConfig = () => {
    onConfigSave(thresholds);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="h-5 w-5" />
            <span>Analysis Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="space-y-6 p-4 bg-secondary/20 rounded-lg">
              <Label className="text-base font-semibold">Performance Thresholds</Label>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <Label>Response Time (milliseconds)</Label>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary" className="bg-success/20 text-success">Good</Badge>
                      <Input 
                        type="number" 
                        step="50"
                        value={thresholds.response_time_good_threshold || ''}
                        onChange={(e) => setThresholds({...thresholds, response_time_good_threshold: parseFloat(e.target.value) || undefined})}
                        className="w-24"
                        placeholder="500"
                      />
                      <span className="text-sm text-muted-foreground">≤ ms</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="destructive">Bad</Badge>
                      <Input 
                        type="number" 
                        step="100"
                        value={thresholds.response_time_bad_threshold || ''}
                        onChange={(e) => setThresholds({...thresholds, response_time_bad_threshold: parseFloat(e.target.value) || undefined})}
                        className="w-24"
                        placeholder="2000"
                      />
                      <span className="text-sm text-muted-foreground">&gt; ms</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <Label>Error Rate (%)</Label>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary" className="bg-success/20 text-success">Good</Badge>
                      <Input 
                        type="number" 
                        step="0.1"
                        value={thresholds.error_rate_good_threshold || ''}
                        onChange={(e) => setThresholds({...thresholds, error_rate_good_threshold: parseFloat(e.target.value) || undefined})}
                        className="w-20"
                        placeholder="1"
                      />
                      <span className="text-sm text-muted-foreground">≤ %</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="destructive">Bad</Badge>
                      <Input 
                        type="number" 
                        step="0.1"
                        value={thresholds.error_rate_bad_threshold || ''}
                        onChange={(e) => setThresholds({...thresholds, error_rate_bad_threshold: parseFloat(e.target.value) || undefined})}
                        className="w-20"
                        placeholder="5"
                      />
                      <span className="text-sm text-muted-foreground">&gt; %</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <Label>Throughput (RPS)</Label>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary" className="bg-success/20 text-success">Good</Badge>
                      <Input 
                        type="number" 
                        value={thresholds.throughput_good_threshold || ''}
                        onChange={(e) => setThresholds({...thresholds, throughput_good_threshold: parseFloat(e.target.value) || undefined})}
                        className="w-24"
                        placeholder="100"
                      />
                      <span className="text-sm text-muted-foreground">≥ RPS</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="destructive">Bad</Badge>
                      <Input 
                        type="number" 
                        value={thresholds.throughput_bad_threshold || ''}
                        onChange={(e) => setThresholds({...thresholds, throughput_bad_threshold: parseFloat(e.target.value) || undefined})}
                        className="w-24"
                        placeholder="10"
                      />
                      <span className="text-sm text-muted-foreground">&lt; RPS</span>
                    </div>
                  </div>
                </div>

                
              </div>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <Button onClick={handleSaveConfig}>
              Save Configuration
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalysisConfiguration;