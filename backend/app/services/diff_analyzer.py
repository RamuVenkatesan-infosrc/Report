#!/usr/bin/env python3
"""
Diff Analyzer Service for Code Comparison
"""

import difflib
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DiffResult:
    """Result of a diff comparison."""
    side_by_side: List[Dict[str, Any]]
    unified_diff: str
    line_by_line: List[Dict[str, Any]]
    changes_count: int
    additions_count: int
    deletions_count: int

class DiffAnalyzer:
    """Analyzes differences between old and new code."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_code_diff(self, old_code: str, new_code: str, 
                         old_title: str = "OLD CODE", 
                         new_title: str = "NEW CODE") -> DiffResult:
        """Analyze differences between old and new code."""
        
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        
        # Generate side-by-side diff
        side_by_side = self._generate_side_by_side_diff(old_lines, new_lines, old_title, new_title)
        
        # Generate unified diff
        unified_diff = self._generate_unified_diff(old_lines, new_lines, old_title, new_title)
        
        # Generate line-by-line diff
        line_by_line = self._generate_line_by_line_diff(old_lines, new_lines)
        
        # Count changes
        changes_count = sum(1 for line in side_by_side if line.get('type') in ['added', 'deleted', 'modified'])
        additions_count = sum(1 for line in side_by_side if line.get('type') == 'added')
        deletions_count = sum(1 for line in side_by_side if line.get('type') == 'deleted')
        
        return DiffResult(
            side_by_side=side_by_side,
            unified_diff=unified_diff,
            line_by_line=line_by_line,
            changes_count=changes_count,
            additions_count=additions_count,
            deletions_count=deletions_count
        )
    
    def _generate_side_by_side_diff(self, old_lines: List[str], new_lines: List[str], 
                                   old_title: str, new_title: str) -> List[Dict[str, Any]]:
        """Generate side-by-side diff."""
        diff_lines = []
        
        # Use difflib to get the differences
        differ = difflib.unified_diff(old_lines, new_lines, 
                                    fromfile=old_title, tofile=new_title, lineterm='')
        
        # Convert to side-by-side format
        old_line_num = 1
        new_line_num = 1
        
        for line in differ:
            if line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('@@'):
                # Parse line numbers from @@ -old_start,old_count +new_start,new_count @@
                parts = line.split('@@')[1].strip()
                if ' ' in parts:
                    old_part, new_part = parts.split(' ', 1)
                    if old_part.startswith('-'):
                        old_line_num = int(old_part[1:].split(',')[0])
                    if new_part.startswith('+'):
                        new_line_num = int(new_part[1:].split(',')[0])
                continue
            elif line.startswith('-'):
                # Deleted line
                diff_lines.append({
                    'type': 'deleted',
                    'old_line_num': old_line_num,
                    'new_line_num': None,
                    'old_content': line[1:].rstrip(),
                    'new_content': '',
                    'change_type': 'deletion'
                })
                old_line_num += 1
            elif line.startswith('+'):
                # Added line
                diff_lines.append({
                    'type': 'added',
                    'old_line_num': None,
                    'new_line_num': new_line_num,
                    'old_content': '',
                    'new_content': line[1:].rstrip(),
                    'change_type': 'addition'
                })
                new_line_num += 1
            else:
                # Context line (unchanged)
                diff_lines.append({
                    'type': 'context',
                    'old_line_num': old_line_num,
                    'new_line_num': new_line_num,
                    'old_content': line[1:].rstrip() if line.startswith(' ') else line.rstrip(),
                    'new_content': line[1:].rstrip() if line.startswith(' ') else line.rstrip(),
                    'change_type': 'unchanged'
                })
                old_line_num += 1
                new_line_num += 1
        
        return diff_lines
    
    def _generate_unified_diff(self, old_lines: List[str], new_lines: List[str], 
                              old_title: str, new_title: str) -> str:
        """Generate unified diff."""
        differ = difflib.unified_diff(old_lines, new_lines, 
                                    fromfile=old_title, tofile=new_title, lineterm='')
        return '\n'.join(differ)
    
    def _generate_line_by_line_diff(self, old_lines: List[str], new_lines: List[str]) -> List[Dict[str, Any]]:
        """Generate line-by-line diff."""
        diff_lines = []
        
        # Use SequenceMatcher for more detailed comparison
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for i in range(i1, i2):
                    diff_lines.append({
                        'line_num': i + 1,
                        'type': 'unchanged',
                        'old_content': old_lines[i].rstrip(),
                        'new_content': new_lines[i].rstrip(),
                        'change_type': 'unchanged'
                    })
            elif tag == 'delete':
                for i in range(i1, i2):
                    diff_lines.append({
                        'line_num': i + 1,
                        'type': 'deleted',
                        'old_content': old_lines[i].rstrip(),
                        'new_content': '',
                        'change_type': 'deletion'
                    })
            elif tag == 'insert':
                for j in range(j1, j2):
                    diff_lines.append({
                        'line_num': j + 1,
                        'type': 'added',
                        'old_content': '',
                        'new_content': new_lines[j].rstrip(),
                        'change_type': 'addition'
                    })
            elif tag == 'replace':
                for i in range(i1, i2):
                    diff_lines.append({
                        'line_num': i + 1,
                        'type': 'modified',
                        'old_content': old_lines[i].rstrip(),
                        'new_content': new_lines[j1 + (i - i1)].rstrip() if j1 + (i - i1) < j2 else '',
                        'change_type': 'modification'
                    })
        
        return diff_lines
    
    def generate_improvement_diffs(self, improvements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate diff analysis for all improvements."""
        diff_results = []
        
        for improvement in improvements:
            if 'current_code' in improvement and 'improved_code' in improvement:
                diff_result = self.analyze_code_diff(
                    improvement['current_code'],
                    improvement['improved_code'],
                    f"OLD: {improvement.get('title', 'Code')}",
                    f"NEW: {improvement.get('title', 'Code')}"
                )
                
                diff_results.append({
                    'improvement': improvement,
                    'diff': {
                        'side_by_side': diff_result.side_by_side,
                        'unified_diff': diff_result.unified_diff,
                        'line_by_line': diff_result.line_by_line,
                        'stats': {
                            'changes_count': diff_result.changes_count,
                            'additions_count': diff_result.additions_count,
                            'deletions_count': diff_result.deletions_count
                        }
                    }
                })
        
        return diff_results
