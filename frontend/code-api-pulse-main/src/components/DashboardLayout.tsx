import { useState } from 'react';
import { Activity, Github, BarChart3, FileText, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface DashboardLayoutProps {
  children: (activeSection: string, setActiveSection: (section: string) => void) => React.ReactNode;
}

const DashboardLayout = ({ children }: DashboardLayoutProps) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeSection, setActiveSection] = useState('overview');

  const navigation = [
    { id: 'overview', name: 'Overview', icon: Activity, current: activeSection === 'overview' },
    { id: 'reports', name: 'Report Analysis', icon: BarChart3, current: activeSection === 'reports' },
    { id: 'github', name: 'GitHub Analysis', icon: Github, current: activeSection === 'github' },
    { id: 'insights', name: 'AI Insights', icon: FileText, current: activeSection === 'insights' },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div className={cn(
        "flex flex-col transition-smooth border-r border-border bg-card",
        sidebarOpen ? "w-64" : "w-16"
      )}>
        <div className="flex h-16 items-center px-6 border-b border-border">
          <div className={cn("flex items-center", sidebarOpen ? "space-x-3" : "justify-center")}>
            <div className="w-8 h-8 gradient-primary rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-primary-foreground" />
            </div>
            {sidebarOpen && (
              <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                API Analytics
              </h1>
            )}
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={cn(
                  "w-full flex items-center px-3 py-3 text-sm font-medium rounded-lg transition-smooth",
                  item.current
                    ? "bg-primary text-primary-foreground shadow-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted",
                  !sidebarOpen && "justify-center px-0"
                )}
              >
                <Icon className={cn("h-5 w-5", sidebarOpen ? "mr-3" : "")} />
                {sidebarOpen && item.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between h-16 px-6 border-b border-border bg-card/50 backdrop-blur-sm">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-muted-foreground hover:text-foreground"
            >
              {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </Button>
            <div>
              <h2 className="text-lg font-semibold capitalize">{activeSection}</h2>
              <p className="text-sm text-muted-foreground">
                {activeSection === 'overview' && 'Dashboard overview and quick insights'}
                {activeSection === 'reports' && 'Upload and analyze performance reports'}
                {activeSection === 'github' && 'Analyze GitHub repositories and code'}
                {activeSection === 'insights' && 'AI-powered recommendations and insights'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <Card className="px-4 py-2 bg-success/10 border-success/20">
              <div className="text-sm font-medium text-success">System Online</div>
            </Card>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {children(activeSection, setActiveSection)}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;