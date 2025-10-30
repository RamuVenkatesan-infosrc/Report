import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { ChevronDown, ChevronRight, Plus, Minus, FileText } from 'lucide-react';

interface DiffLine {
  type: 'added' | 'deleted' | 'modified' | 'context' | 'unchanged';
  old_line_num?: number;
  new_line_num?: number;
  old_content: string;
  new_content: string;
  change_type: string;
}

interface DiffStats {
  changes_count: number;
  additions_count: number;
  deletions_count: number;
}

interface DiffData {
  side_by_side: DiffLine[];
  unified_diff: string;
  line_by_line: DiffLine[];
  stats: DiffStats;
}

interface DiffViewerProps {
  improvement: any;
  diff: DiffData;
}

const DiffViewer: React.FC<DiffViewerProps> = ({ improvement, diff }) => {
  const [activeTab, setActiveTab] = useState<'side-by-side' | 'unified' | 'line-by-line'>('side-by-side');
  const [expandedLines, setExpandedLines] = useState<Set<number>>(new Set());

  const toggleLineExpansion = (index: number) => {
    const newExpanded = new Set(expandedLines);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedLines(newExpanded);
  };

  const getLineIcon = (type: string) => {
    switch (type) {
      case 'added':
        return <Plus className="w-3 h-3 text-green-600" />;
      case 'deleted':
        return <Minus className="w-3 h-3 text-red-600" />;
      case 'modified':
        return <FileText className="w-3 h-3 text-yellow-600" />;
      default:
        return <div className="w-3 h-3" />;
    }
  };

  const getLineColor = (type: string) => {
    switch (type) {
      case 'added':
        return 'bg-green-50 border-l-4 border-green-500';
      case 'deleted':
        return 'bg-red-50 border-l-4 border-red-500';
      case 'modified':
        return 'bg-yellow-50 border-l-4 border-yellow-500';
      default:
        return 'bg-gray-50';
    }
  };

  const renderSideBySideDiff = () => (
    <div className="space-y-1">
      {diff.side_by_side.map((line, index) => (
        <div
          key={index}
          className={`flex items-start p-2 rounded ${getLineColor(line.type)}`}
        >
          <div className="flex items-center space-x-2 mr-4">
            {getLineIcon(line.type)}
            <span className="text-xs text-gray-500 w-8">
              {line.old_line_num || '-'}
            </span>
            <span className="text-xs text-gray-500 w-8">
              {line.new_line_num || '-'}
            </span>
          </div>
          <div className="flex-1 font-mono text-sm">
            {line.type === 'modified' ? (
              <div className="space-y-1">
                <div className="text-red-600 line-through">{line.old_content}</div>
                <div className="text-green-600">{line.new_content}</div>
              </div>
            ) : (
              <div className={line.type === 'deleted' ? 'text-red-600' : line.type === 'added' ? 'text-green-600' : 'text-gray-700'}>
                {line.old_content || line.new_content}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  const renderUnifiedDiff = () => (
    <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm">
      {diff.unified_diff}
    </pre>
  );

  const renderLineByLineDiff = () => (
    <div className="space-y-1">
      {diff.line_by_line.map((line, index) => (
        <div
          key={index}
          className={`flex items-start p-2 rounded ${getLineColor(line.type)}`}
        >
          <div className="flex items-center space-x-2 mr-4">
            {getLineIcon(line.type)}
            <span className="text-xs text-gray-500 w-12">
              {line.line_num}
            </span>
          </div>
          <div className="flex-1 font-mono text-sm">
            {line.type === 'modified' ? (
              <div className="space-y-1">
                <div className="text-red-600 line-through">{line.old_content}</div>
                <div className="text-green-600">{line.new_content}</div>
              </div>
            ) : (
              <div className={line.type === 'deleted' ? 'text-red-600' : line.type === 'added' ? 'text-green-600' : 'text-gray-700'}>
                {line.old_content || line.new_content}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{improvement.title}</CardTitle>
          <div className="flex space-x-2">
            <Badge variant="outline">{improvement.priority}</Badge>
            <Badge variant="secondary">{improvement.category}</Badge>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">{improvement.description}</p>
        <div className="flex space-x-4 text-sm text-muted-foreground">
          <span>Changes: {diff.stats.changes_count}</span>
          <span className="text-green-600">+{diff.stats.additions_count}</span>
          <span className="text-red-600">-{diff.stats.deletions_count}</span>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="side-by-side">Side by Side</TabsTrigger>
            <TabsTrigger value="unified">Unified Diff</TabsTrigger>
            <TabsTrigger value="line-by-line">Line by Line</TabsTrigger>
          </TabsList>
          
          <TabsContent value="side-by-side" className="mt-4">
            {renderSideBySideDiff()}
          </TabsContent>
          
          <TabsContent value="unified" className="mt-4">
            {renderUnifiedDiff()}
          </TabsContent>
          
          <TabsContent value="line-by-line" className="mt-4">
            {renderLineByLineDiff()}
          </TabsContent>
        </Tabs>
        
        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-blue-900">Expected Improvement:</span>
            <span className="text-blue-700">{improvement.expected_improvement}</span>
          </div>
          <div className="flex items-center justify-between text-sm mt-1">
            <span className="font-medium text-blue-900">Implementation Effort:</span>
            <span className="text-blue-700">{improvement.implementation_effort}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default DiffViewer;
