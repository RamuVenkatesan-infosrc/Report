import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { MessageCircle, Send, Bot, User, Lightbulb, TrendingUp, AlertTriangle, Upload, FileText, Image } from 'lucide-react';

const AIInsights = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm your AI assistant for API performance analysis. Upload a performance report or connect to a GitHub repository to get started with analysis and optimization suggestions."
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setUploadedFiles(prev => [...prev, ...files]);
    
    // Add message about uploaded files
    const fileMessage = {
      role: 'user',
      content: `📁 Uploaded ${files.length} file(s): ${files.map(f => f.name).join(', ')}`
    };
    setMessages(prev => [...prev, fileMessage]);
    
    // Simulate AI analysis of uploaded files
    setTimeout(() => {
      const aiResponse = {
        role: 'assistant',
        content: `I've received your files: ${files.map(f => f.name).join(', ')}. I can analyze performance reports, log files, configuration files, and screenshots. What specific questions do you have about these files?`
      };
      setMessages(prev => [...prev, aiResponse]);
    }, 1000);
  };

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage = { role: 'user', content: inputValue };
    setMessages(prev => [...prev, userMessage]);
    
    // Simulate AI response
    setTimeout(() => {
      const aiResponse = {
        role: 'assistant',
        content: getAIResponse(inputValue)
      };
      setMessages(prev => [...prev, aiResponse]);
    }, 1000);

    setInputValue('');
  };

  const getAIResponse = (query: string) => {
    const lowerQuery = query.toLowerCase();
    
    return "I'm ready to help with API performance analysis! To provide specific recommendations, please:\n\n1. **Upload a performance report** (XML, CSV, JTL, JSON, ZIP)\n2. **Connect to a GitHub repository** for source code analysis\n3. **Ask specific questions** about your API performance\n\nOnce you have data loaded, I can help with:\n\n• **Performance Issues**: Root cause analysis and solutions\n• **Code Optimization**: Specific improvement suggestions\n• **Database Queries**: N+1 problems, indexing, eager loading\n• **Caching Strategies**: Redis, query caching, HTTP caching\n• **Monitoring**: Setting up performance alerts";
  };

  const quickActions = [
    { 
      title: "Analyze API Performance", 
      description: "Get detailed analysis of your slowest endpoints",
      icon: TrendingUp,
      color: "text-primary"
    },
    { 
      title: "Fix N+1 Queries", 
      description: "Learn how to optimize database queries",
      icon: AlertTriangle,
      color: "text-warning"
    },
    { 
      title: "Caching Strategy", 
      description: "Implement effective caching patterns",
      icon: Lightbulb,
      color: "text-success"
    },
  ];

  return (
    <div className="space-y-8">
      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {quickActions.map((action, index) => {
          const Icon = action.icon;
          return (
            <Card key={index} className="card-hover cursor-pointer">
              <CardContent className="p-6">
                <div className="flex items-center space-x-3 mb-3">
                  <Icon className={`h-6 w-6 ${action.color}`} />
                  <h3 className="font-semibold">{action.title}</h3>
                </div>
                <p className="text-sm text-muted-foreground">{action.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* AI Chat Interface */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <MessageCircle className="h-5 w-5" />
            <span>AI Assistant</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Messages */}
            <div className="h-96 overflow-y-auto space-y-4 p-4 bg-muted/30 rounded-lg">
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex items-start space-x-2 max-w-[80%] ${
                    message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                  }`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      message.role === 'user' 
                        ? 'bg-primary text-primary-foreground' 
                        : 'gradient-secondary text-white'
                    }`}>
                      {message.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className={`px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-card border border-border'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* File Upload Area */}
            <div className="border-2 border-dashed border-border rounded-lg p-4 text-center">
              <div className="flex items-center justify-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Upload className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Upload files or images for analysis</span>
                </div>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.csv,.png,.jpg,.jpeg"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload">
                  <Button variant="outline" size="sm" className="cursor-pointer">
                    <FileText className="w-4 h-4 mr-2" />
                    Choose Files
                  </Button>
                </label>
              </div>
              {uploadedFiles.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {uploadedFiles.map((file, index) => (
                    <span key={index} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                      {file.name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Input */}
            <div className="flex space-x-2">
              <Input
                placeholder="Ask about API performance, optimization, or any issues..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                className="flex-1"
              />
              <Button onClick={handleSendMessage} disabled={!inputValue.trim()}>
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Insights Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Insights Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h4 className="font-semibold text-success">✅ Strengths Identified</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-muted rounded-full" />
                  <span>No data available - upload a report to see strengths</span>
                </li>
              </ul>
            </div>
            
            <div className="space-y-4">
              <h4 className="font-semibold text-warning">⚠️ Areas for Improvement</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-muted rounded-full" />
                  <span>No data available - upload a report to see areas for improvement</span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AIInsights;