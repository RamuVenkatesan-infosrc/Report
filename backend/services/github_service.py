"""
GitHub integration service for repository analysis and API discovery.
"""
import requests
import logging
import re
import os
import time
import random
import asyncio
import aiohttp
import multiprocessing
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from models.improvement_models import DiscoveredAPI, SeverityLevel
from models.config import Settings

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API and analyzing repositories."""
    
    def __init__(self, settings: Settings, github_token: Optional[str] = None, bedrock_service=None):
        self.settings = settings
        self.github_token = github_token or getattr(settings, 'github_token', None) or os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Authorization': f'token {self.github_token}' if self.github_token else None,
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.bedrock_service = bedrock_service
        self.rate_limit_delay = 1.0  # Base delay between requests
        self.max_retries = 3
        self._debug_worst_apis = None  # For debugging when no APIs found
        self._file_cache = {}
        self._api_patterns_cache = None
        self._max_workers = min(4, multiprocessing.cpu_count())
    
    def is_github_available(self) -> bool:
        """Check if GitHub token is available."""
        return self.github_token is not None
    
    def set_debug_worst_apis(self, worst_apis: List[Dict[str, Any]]):
        """Set worst APIs for debugging when no APIs are found in repository."""
        self._debug_worst_apis = worst_apis
        logger.info(f"Debug mode enabled with {len(worst_apis)} worst APIs")
    
    def get_repository_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get all available branches in the repository."""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/branches"
            response = self._make_github_request(url)
            
            if response.status_code == 200:
                branches = response.json()
                logger.info(f"Found {len(branches)} branches in repository {owner}/{repo}")
                return branches
            else:
                logger.error(f"Failed to fetch branches: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching branches: {str(e)}")
            return []
    
    def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information including default branch."""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}"
            response = self._make_github_request(url)
            
            if response.status_code == 200:
                repo_info = response.json()
                return {
                    'name': repo_info.get('name'),
                    'full_name': repo_info.get('full_name'),
                    'default_branch': repo_info.get('default_branch', 'main'),
                    'description': repo_info.get('description'),
                    'language': repo_info.get('language'),
                    'stars': repo_info.get('stargazers_count', 0),
                    'forks': repo_info.get('forks_count', 0),
                    'private': repo_info.get('private', False)
                }
            else:
                logger.error(f"Failed to fetch repository info: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching repository info: {str(e)}")
            return {}
    
    def _make_github_request(self, url: str, params: Dict = None) -> requests.Response:
        """Make a GitHub API request with retry logic and rate limiting."""
        for attempt in range(self.max_retries):
            try:
                # Add delay to avoid rate limiting
                if attempt > 0:
                    delay = self.rate_limit_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying GitHub request in {delay:.2f} seconds (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                else:
                    delay = self.rate_limit_delay
                    time.sleep(delay)
                
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Rate limit exceeded, retrying in {delay:.2f} seconds...")
                        continue
                    else:
                        logger.error("Rate limit exceeded and max retries reached")
                        raise Exception("GitHub API rate limit exceeded. Please try again later.")
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    raise Exception(f"Repository not found: {url}")
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request failed, retrying: {str(e)}")
                    continue
                else:
                    raise e
        
        raise Exception("Max retries exceeded for GitHub API request")
    
    def search_repositories(self, query: str, language: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for repositories based on query and language."""
        try:
            url = f"{self.base_url}/search/repositories"
            params = {'q': query}
            if language:
                params['q'] += f' language:{language}'
            
            response = self._make_github_request(url, params)
            
            data = response.json()
            items = data.get('items', [])
            return items[:limit]
        except Exception as e:
            logger.error(f"Error searching repositories: {str(e)}")
            return []
    
    def get_repository_contents(self, owner: str, repo: str, path: str = '', branch: str = None) -> List[Dict[str, Any]]:
        """Get contents of a repository directory for a specific branch."""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            params = {}
            if branch:
                params['ref'] = branch
            
            response = self._make_github_request(url, params)
            return response.json()
        except Exception as e:
            logger.error(f"Error getting repository contents: {str(e)}")
            return []
    
    def get_file_content(self, owner: str, repo: str, path: str, branch: str = None) -> Optional[str]:
        """Get content of a specific file from a specific branch."""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            params = {}
            if branch:
                params['ref'] = branch
            
            response = self._make_github_request(url, params)
            
            import base64
            content = response.json().get('content', '')
            return base64.b64decode(content).decode('utf-8')
        except Exception as e:
            logger.error(f"Error getting file content: {str(e)}")
            return None
    
    def discover_apis_in_repository(self, owner: str, repo: str, branch: str = None) -> List[DiscoveredAPI]:
        """Discover all APIs in a repository for a specific branch."""
        discovered_apis = []
        
        try:
            # Get all files in the repository
            files = self._get_all_files(owner, repo, '', branch)
            branch_info = f" (branch: {branch})" if branch else " (default branch)"
            logger.info(f"Found {len(files)} total files in repository {owner}/{repo}{branch_info}")
            
            # Debug: Log file types found
            file_types = {}
            for file_info in files:
                ext = file_info['path'].split('.')[-1] if '.' in file_info['path'] else 'no_ext'
                file_types[ext] = file_types.get(ext, 0) + 1
            logger.info(f"File types found: {dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10])}")
            
            api_files = []
            processed_files = 0
            max_files_to_process = 100  # Limit for performance
            
            # Filter API files first
            for file_info in files:
                if processed_files >= max_files_to_process:
                    logger.info(f"Processed {max_files_to_process} files, stopping for performance")
                    break
                    
                if self._is_api_file(file_info['path']):
                    api_files.append(file_info)
                    processed_files += 1
                    
            # Process files in parallel for better performance
            logger.info(f"Processing {len(api_files)} API files in parallel...")
            
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # Submit all file processing tasks
                future_to_file = {
                    executor.submit(self._process_single_file, owner, repo, file_info, branch): file_info 
                    for file_info in api_files
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    file_path = file_info['path']
                    
                    try:
                        apis = future.result()
                        if apis:
                            discovered_apis.extend(apis)
                            logger.info(f"Found {len(apis)} APIs in {file_path}")
                        else:
                            logger.debug(f"No APIs found in {file_path}")
                    except Exception as e:
                        logger.warning(f"Error processing file {file_path}: {str(e)}")
                        continue
            
            logger.info(f"Scanned {len(api_files)} API files: {api_files[:10]}...")
            
            # If no APIs found, try aggressive scanning
            if not discovered_apis:
                logger.warning(f"No APIs found with standard patterns. Trying aggressive scan...")
                discovered_apis = self._aggressive_api_scan(owner, repo, branch)
            
            # If still no APIs found, return empty list (only create samples when explicitly enabled)
            if not discovered_apis:
                logger.warning(
                    "No APIs found even with aggressive scan. This may indicate the repository doesn't contain API code or uses unsupported patterns."
                )
                logger.info(f"Repository structure: {[f['path'] for f in files[:20]]}")
                
                # Create sample APIs only if debug worst APIs were explicitly set
                if hasattr(self, '_debug_worst_apis') and self._debug_worst_apis is not None:
                    logger.info("Creating debug sample APIs for testing (explicitly enabled)...")
                    discovered_apis = self._create_debug_sample_apis()
            
            # Final deduplication across all files
            if discovered_apis:
                logger.info(f"Before final deduplication: {len(discovered_apis)} APIs")
                unique_apis = []
                seen_endpoints = set()
                
                for api in discovered_apis:
                    # Create a unique key based on full endpoint (including HTTP method) and file path
                    # This ensures different HTTP methods on the same path are not treated as duplicates
                    unique_key = f"{api.endpoint}|{api.file_path}"
                    
                    if unique_key not in seen_endpoints:
                        seen_endpoints.add(unique_key)
                        unique_apis.append(api)
                
                discovered_apis = unique_apis
                logger.info(f"After final deduplication: {len(discovered_apis)} unique APIs")
            
            return discovered_apis
        except Exception as e:
            logger.error(f"Error discovering APIs in repository {owner}/{repo}: {str(e)}")
            return []
    
    def _process_single_file(self, owner: str, repo: str, file_info: dict, branch: str = None) -> List[DiscoveredAPI]:
        """Process a single file for API extraction (used in parallel processing)."""
        try:
            file_path = file_info['path']
            file_size = file_info.get('size', 0)
            
            # Use chunking for large files
            if file_size > 1024 * 1024:  # 1MB limit
                logger.debug(f"Large file detected: {file_path} ({file_size} bytes), using chunked processing")
                return self._extract_apis_from_file_chunked(owner, repo, file_path, branch)
            else:
                content = self.get_file_content(owner, repo, file_path, branch)
                if content:
                    return self._extract_apis_from_file(content, file_path)
                else:
                    return []
        except Exception as e:
            logger.warning(f"Error processing file {file_info['path']}: {str(e)}")
            return []
    
    def _aggressive_api_scan(self, owner: str, repo: str, branch: str = None) -> List[DiscoveredAPI]:
        """Aggressive API scanning when standard patterns fail."""
        discovered_apis = []
        
        try:
            # Get ALL files, not just API files
            all_files = self._get_all_files(owner, repo, '', branch)
            branch_info = f" (branch: {branch})" if branch else " (default branch)"
            logger.info(f"Aggressive scan: Found {len(all_files)} total files{branch_info}")
            
            # Scan more file types - comprehensive list
            api_extensions = ['.cs', '.py', '.js', '.ts', '.java', '.rb', '.go', '.rs', '.php', '.swift', '.kt',
                            '.dart', '.scala', '.clj', '.ex', '.hs', '.fs', '.cr', '.nim', '.zig', '.v', '.odin',
                            '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx', '.m', '.mm', '.cljs', '.cljc', '.lhs']
            
            # Also scan configuration files that might contain API definitions
            config_extensions = ['.yaml', '.yml', '.json', '.xml', '.toml', '.ini', '.cfg', '.conf', '.properties']
            
            all_extensions = api_extensions + config_extensions
            
            scanned_files = 0
            for file_info in all_files:
                file_path = file_info['path']
                if any(file_path.lower().endswith(ext) for ext in all_extensions):
                    scanned_files += 1
                    content = self.get_file_content(owner, repo, file_path, branch)
                    if content:
                        # Try AI-powered detection for each file
                        apis = self._ai_powered_api_detection(content, file_path)
                        if apis:
                            logger.info(f"AI found {len(apis)} APIs in {file_path}")
                        discovered_apis.extend(apis)
                        
                        # Also try manual patterns with relaxed criteria
                        manual_apis = self._extract_apis_from_file(content, file_path)
                        if manual_apis:
                            logger.info(f"Manual patterns found {len(manual_apis)} APIs in {file_path}")
                        discovered_apis.extend(manual_apis)
            
            logger.info(f"Aggressive scan: Scanned {scanned_files} files with API extensions")
            
            # Remove duplicates and filter out low-quality matches
            unique_apis = []
            seen_endpoints = set()
            for api in discovered_apis:
                # Only include APIs that look legitimate
                if (api.endpoint not in seen_endpoints and 
                    api.endpoint and 
                    len(api.endpoint.strip()) > 0 and
                    not api.endpoint.startswith('unknown') and
                    not api.endpoint.startswith('HTTP') and
                    not api.endpoint.startswith('$PROJECT_DIR$') and
                    not api.endpoint.startswith('file://') and
                    not api.endpoint.startswith('API autocapitalize') and
                    not api.endpoint.startswith('API ') and
                    not api.endpoint.startswith('autocapitalize') and
                    not api.endpoint.startswith('autocorrect') and
                    not api.endpoint.startswith('shadow_root') and
                    not api.endpoint.startswith('value') and
                    not api.endpoint.startswith('name') and
                    not api.endpoint.startswith('password') and
                    not api.endpoint.startswith('user-name') and
                    not api.endpoint.startswith('component') and
                    not api.endpoint.startswith('module') and
                    not api.endpoint.startswith('project') and
                    not api.endpoint.startswith('modules') and
                    not api.endpoint.startswith('fileurl') and
                    not api.endpoint.startswith('filepath') and
                    not api.endpoint.startswith('ProjectModuleManager') and
                    not api.endpoint.startswith('Tega') and
                    not api.endpoint.startswith('infsvc') and
                    not api.endpoint.startswith('jira') and
                    not api.endpoint.startswith('testcase') and
                    not api.endpoint.startswith('builder') and
                    not api.endpoint.startswith('agent_history') and
                    not api.endpoint.startswith('history') and
                    not api.endpoint.startswith('agent') and
                    not api.endpoint.startswith('json') and
                    not api.endpoint.startswith('xml') and
                    not api.endpoint.startswith('yml') and
                    not api.endpoint.startswith('yaml') and
                    not api.endpoint.startswith('md') and
                    not api.endpoint.startswith('txt') and
                    not api.endpoint.startswith('log') and
                    not api.endpoint.startswith('lock') and
                    not api.endpoint.startswith('.idea') and
                    not api.endpoint.startswith('.vscode') and
                    not api.endpoint.startswith('node_modules') and
                    not api.endpoint.startswith('__pycache__') and
                    not api.endpoint.startswith('.git') and
                    not api.endpoint.startswith('venv') and
                    not api.endpoint.startswith('env') and
                    not api.endpoint.startswith('bin') and
                    not api.endpoint.startswith('obj') and
                    not api.endpoint.startswith('packages') and
                    not api.endpoint.startswith('target') and
                    not api.endpoint.startswith('build') and
                    not api.endpoint.startswith('dist') and
                    not api.endpoint.startswith('coverage') and
                    not api.endpoint.startswith('.pytest_cache') and
                    not api.endpoint.startswith('logs') and
                    not api.endpoint.startswith('test') and
                    not api.endpoint.startswith('tests') and
                    not api.endpoint.startswith('spec') and
                    not api.endpoint.startswith('specs') and
                    not api.endpoint.startswith('docs') and
                    not api.endpoint.startswith('documentation') and
                    not api.endpoint.startswith('assets') and
                    not api.endpoint.startswith('static') and
                    not api.endpoint.startswith('public') and
                    not api.endpoint.startswith('resources') and
                    not api.endpoint.startswith('config') and
                    not api.endpoint.startswith('.env') and
                    not api.endpoint.startswith('.gitignore') and
                    not api.endpoint.startswith('.gitattributes') and
                    not api.endpoint.startswith('package-lock') and
                    not api.endpoint.startswith('yarn.lock') and
                    not api.endpoint.startswith('composer.lock') and
                    not api.endpoint.startswith('pom.xml') and
                    not api.endpoint.startswith('build.gradle') and
                    not api.endpoint.startswith('requirements.txt') and
                    not api.endpoint.startswith('Pipfile') and
                    not api.endpoint.startswith('poetry.lock') and
                    # Only include endpoints that look like real APIs
                    ('/' in api.endpoint or api.endpoint.startswith(('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'))) and
                    len(api.endpoint) > 3 and
                    not api.endpoint.isdigit() and
                    not api.endpoint.startswith('.') and
                    not api.endpoint.endswith('.') and
                    not api.endpoint.startswith(' ') and
                    not api.endpoint.endswith(' ')):
                    unique_apis.append(api)
                    seen_endpoints.add(api.endpoint)
            
            logger.info(f"Aggressive scan found {len(unique_apis)} real APIs")
            return unique_apis
            
        except Exception as e:
            logger.error(f"Error in aggressive API scan: {str(e)}")
            return []
    
    
    def _get_all_files(self, owner: str, repo: str, path: str = '', branch: str = None) -> List[Dict[str, Any]]:
        """Recursively get all files in a repository for a specific branch."""
        files = []
        contents = self.get_repository_contents(owner, repo, path, branch)
        
        for item in contents:
            if item['type'] == 'file':
                files.append(item)
            elif item['type'] == 'dir':
                # Skip common non-source directories
                if item['name'] not in ['.git', 'node_modules', '__pycache__', '.pytest_cache', 'venv', 'env', 'bin', 'obj', 'packages']:
                    sub_files = self._get_all_files(owner, repo, item['path'], branch)
                    files.extend(sub_files)
        
        return files
    
    @lru_cache(maxsize=1000)
    def _is_api_file(self, file_path: str) -> bool:
        """Check if file is likely to contain API definitions - OPTIMIZED FOR SPEED."""
        # Comprehensive list of dependency files and folders to skip
        skip_patterns = [
            # Version control and IDE
            '.git/', '.svn/', '.hg/', '.bzr/', '.idea/', '.vscode/', '.vs/',
            
            # Package managers and dependencies
            'node_modules/', 'bower_components/', 'vendor/', 'packages/',
            '__pycache__/', '.pytest_cache/', '.mypy_cache/', '.coverage/',
            
            # Virtual environments and build artifacts
            'venv/', 'env/', '.venv/', '.env/', 'virtualenv/', 'conda/',
            'bin/', 'obj/', 'target/', 'build/', 'dist/', 'out/', 'release/',
            
            # Testing and documentation
            'test/', 'tests/', 'spec/', 'specs/', '__tests__/', 'test_',
            'docs/', 'documentation/', 'doc/', 'wiki/', 'examples/',
            
            # Static assets and resources
            'assets/', 'static/', 'public/', 'resources/', 'media/', 'images/',
            'css/', 'scss/', 'sass/', 'less/', 'fonts/', 'icons/',
            
            # Configuration and environment
            'config/', 'conf/', 'settings/', 'secrets/', '.config/',
            '.env', '.env.local', '.env.production', '.env.development',
            
            # Lock files and manifests
            'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'composer.lock',
            'poetry.lock', 'Pipfile.lock', 'Gemfile.lock', 'Cargo.lock',
            
            # Build and dependency files
            'pom.xml', 'build.gradle', 'build.xml', 'Makefile', 'CMakeLists.txt',
            'requirements.txt', 'Pipfile', 'setup.py', 'pyproject.toml',
            'package.json', 'composer.json', 'Gemfile', 'Cargo.toml',
            
            # System and temporary files
            '.DS_Store', '.Thumbs.db', 'Thumbs.db', '.directory',
            '*.tmp', '*.temp', '*.log', '*.cache', '*.pid',
            
            # File extensions to skip (excluding .py files which may contain APIs)
            '.json', '.xml', '.yml', '.yaml', '.md', '.txt', '.log', '.lock',
            '.min.js', '.min.css', '.map', '.bundle', '.chunk',
            
            # Framework-specific non-API files (be more specific)
            'migrations/', 'seeds/', 'fixtures/', 'templates/', 'layouts/',
            'components/', 'widgets/', 'mixins/',
            
            # Database and data files
            'data/', 'database/', 'db/', 'sql/', 'migrations/',
            '*.db', '*.sqlite', '*.sqlite3', '*.db3',
            
            # Backup and temporary directories
            'backup/', 'backups/', 'tmp/', 'temp/', 'cache/', 'logs/',
            '*.bak', '*.backup', '*.old', '*.orig'
        ]
        
        file_lower = file_path.lower()
        
        # Skip if matches any skip pattern
        if any(pattern in file_lower for pattern in skip_patterns):
            return False
        
        # Early termination for obvious non-API files (performance optimization)
        non_api_indicators = [
            'test', 'spec', 'mock', 'stub', 'fixture', 'example', 'demo',
            'readme', 'changelog', 'license', 'contributing', 'todo',
            'config', 'setting', 'env', 'docker', 'dockerfile', 'compose',
            'gitignore', 'gitattributes', 'editorconfig', 'eslintrc',
            'prettierrc', 'babelrc', 'webpack', 'rollup', 'vite',
            'package', 'manifest', 'lock', 'yarn', 'npm', 'pip',
            'requirements', 'setup', 'pyproject', 'cargo', 'gemfile'
        ]
        
        # Check for non-API indicators first (faster)
        if any(indicator in file_lower for indicator in non_api_indicators):
            return False
        
        # Common API file indicators
        api_indicators = [
            # Common API file names
            'controller', 'route', 'api', 'endpoint', 'handler', 'service',
            'app.py', 'main.py', 'server.py', 'service.py', 'routes.py',
            'api.py', 'endpoints.py', 'handlers.py', 'controllers.py',
            
            # Framework-specific files
            'views.py', 'urls.py', 'viewsets.py',  # Django
            'app.js', 'server.js', 'index.js', 'routes.js',  # Node.js
            'Application.java', 'Controller.java', 'Service.java',  # Java
            'Program.cs', 'Controller.cs', 'Startup.cs', 'ApiController.cs',  # C#
            'Controllers', 'ApiControllers', 'WebApi', 'Api',  # C# directories
            'app.rb', 'routes.rb', 'application.rb',  # Ruby
            'main.go', 'server.go', 'handlers.go',  # Go
            'main.rs', 'lib.rs', 'handlers.rs',  # Rust
            'index.php', 'routes.php', 'api.php',  # PHP
            
            # Generic patterns
            'api', 'rest', 'web', 'http', 'server', 'app', 'main'
        ]
        
        # File extensions that commonly contain APIs
        api_extensions = [
            '.py', '.js', '.ts', '.java', '.cs', '.rb', '.go', '.rs', 
            '.php', '.swift', '.kt', '.scala', '.clj', '.hs', '.dart', 
            '.ex', '.exs', '.fs', '.fsx', '.fsi', '.cr', '.ecr', '.nim', 
            '.nims', '.zig', '.v', '.odin', '.jai', '.cpp', '.c', '.h', 
            '.hpp', '.cc', '.cxx', '.m', '.mm', '.cljs', '.cljc', '.lhs',
            '.sbt', '.gradle', '.pom', '.xml', '.yaml', '.yml', '.json',
            '.toml', '.ini', '.cfg', '.conf', '.properties'
        ]
        
        file_lower = file_path.lower()
        
        # Check if file has API indicators
        has_api_indicators = any(indicator in file_lower for indicator in api_indicators)
        
        # Check if file has API-friendly extension
        has_api_extension = any(file_lower.endswith(ext) for ext in api_extensions)
        
        # Check if it's a configuration file that might define routes
        config_files = ['routes', 'urls', 'endpoints', 'api', 'swagger', 'openapi']
        is_config_file = any(config in file_lower for config in config_files)
        
        return has_api_indicators or (has_api_extension and is_config_file) or has_api_extension
    
    def _extract_apis_from_file(self, content: str, file_path: str) -> List[DiscoveredAPI]:
        """Extract API definitions from file content - UNIVERSAL API DETECTION."""
        apis = []
        
        # UNIVERSAL API DETECTION PATTERNS - Covers ALL frameworks and languages
        
        # Python frameworks - COMPREHENSIVE
        python_patterns = [
            # FastAPI - Comprehensive and Fixed
            (r'@app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@api_router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@APIRouter\(\)\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # FastAPI with path parameters
            (r'@app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']*\{[^}]*\}[^"\']*)["\']', r'\1', r'\2'),
            (r'@router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']*\{[^}]*\}[^"\']*)["\']', r'\1', r'\2'),
            
            # FastAPI with additional parameters
            (r'@app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*dependencies\s*=', r'\1', r'\2'),
            (r'@app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*tags\s*=', r'\1', r'\2'),
            (r'@app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*response_model\s*=', r'\1', r'\2'),
            (r'@router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*dependencies\s*=', r'\1', r'\2'),
            (r'@router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*tags\s*=', r'\1', r'\2'),
            (r'@router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*response_model\s*=', r'\1', r'\2'),
            
            # FastAPI with multiple parameters
            (r'@app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*[^)]*\)', r'\1', r'\2'),
            (r'@router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*[^)]*\)', r'\1', r'\2'),
            
            # FastAPI without quotes (less common but possible)
            (r'@app\.(get|post|put|delete|patch|head|options)\(([^)]+)\)', r'\1', r'\2'),
            (r'@router\.(get|post|put|delete|patch|head|options)\(([^)]+)\)', r'\1', r'\2'),
            
            # Flask - Comprehensive and Fixed
            (r'@app\.route\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@app\.route\(["\']([^"\']+)["\'],\s*methods\s*=\s*\[["\']([^"\']+)["\']', r'\2', r'\1'),
            (r'@app\.route\(["\']([^"\']+)["\'],\s*methods\s*=\s*\[["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', r'\2', r'\1'),
            (r'@app\.route\(["\']([^"\']+)["\'],\s*methods\s*=\s*\[["\']([^"\']+)["\'],\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', r'\2', r'\1'),
            
            # Flask with path parameters
            (r'@app\.route\(["\']([^"\']*<[^>]*>[^"\']*)["\']', 'GET', r'\1'),
            (r'@app\.route\(["\']([^"\']*<[^>]*>[^"\']*)["\'],\s*methods\s*=\s*\[["\']([^"\']+)["\']', r'\2', r'\1'),
            
            # Flask Blueprint patterns
            (r'@bp\.route\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@bp\.route\(["\']([^"\']+)["\'],\s*methods\s*=\s*\[["\']([^"\']+)["\']', r'\2', r'\1'),
            (r'@blueprint\.route\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@blueprint\.route\(["\']([^"\']+)["\'],\s*methods\s*=\s*\[["\']([^"\']+)["\']', r'\2', r'\1'),
            
            # Flask with additional parameters
            (r'@app\.route\(["\']([^"\']+)["\'],\s*[^)]*\)', 'GET', r'\1'),
            (r'@bp\.route\(["\']([^"\']+)["\'],\s*[^)]*\)', 'GET', r'\1'),
            
            # Generic route patterns (catch-all for Flask-like frameworks)
            (r'@.*\.route\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@.*\.route\(["\']([^"\']+)["\'],\s*methods\s*=\s*\[["\']([^"\']+)["\']', r'\2', r'\1'),
            
            # Additional Python API patterns
            (r'@(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@(get|post|put|delete|patch|head|options)\(["\']([^"\']*\{[^}]*\}[^"\']*)["\']', r'\1', r'\2'),
            
            # Function-based API patterns
            (r'def\s+(get_|post_|put_|delete_|patch_|head_|options_)(\w+)', r'\1', r'\2'),
            (r'def\s+(api_|endpoint_)(\w+)', 'API', r'\2'),
            (r'async\s+def\s+(get_|post_|put_|delete_|patch_|head_|options_)(\w+)', r'\1', r'\2'),
            (r'async\s+def\s+(api_|endpoint_)(\w+)', 'API', r'\2'),
            
            # Django REST Framework - Enhanced and Comprehensive
            (r'@api_view\(\[["\']([^"\']+)["\']\]\)', r'\1', ''),
            (r'class\s+(\w+ViewSet|.*ViewSet).*:', 'REST', ''),
            (r'class\s+(\w+APIView|.*APIView).*:', 'REST', ''),
            (r'class\s+(\w+GenericViewSet).*:', 'REST', ''),
            (r'class\s+(\w+ModelViewSet).*:', 'REST', ''),
            (r'@action\(detail=(True|False)', 'POST', ''),
            (r'path\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'url\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r're_path\(["\']([^"\']+)["\']', 'GET', r'\1'),
            
            # Django REST Framework with decorators
            (r'@api_view\(\[["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\]\)', r'\1', ''),
            (r'@action\(detail=(True|False),\s*methods\s*=\s*\[["\']([^"\']+)["\']\]', r'\2', ''),
            (r'@action\(detail=(True|False),\s*methods\s*=\s*\[["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\]', r'\2', ''),
            
            # Django URL patterns with views
            (r'path\(["\']([^"\']+)["\'],\s*(\w+)\.as_view\(\)', 'GET', r'\1'),
            (r'url\(["\']([^"\']+)["\'],\s*(\w+)\.as_view\(\)', 'GET', r'\1'),
            (r're_path\(["\']([^"\']+)["\'],\s*(\w+)\.as_view\(\)', 'GET', r'\1'),
            
            # Django class-based views
            (r'class\s+(\w+View).*:', 'GET', r'\1'),
            (r'class\s+(\w+CreateView).*:', 'POST', r'\1'),
            (r'class\s+(\w+UpdateView).*:', 'PUT', r'\1'),
            (r'class\s+(\w+DeleteView).*:', 'DELETE', r'\1'),
            (r'class\s+(\w+ListView).*:', 'GET', r'\1'),
            (r'class\s+(\w+DetailView).*:', 'GET', r'\1'),
            
            # Sanic - Enhanced
            (r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@bp\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Bottle - Enhanced
            (r'@(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@route\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # CherryPy - Enhanced
            (r'@cherrypy\.expose.*\ndef\s+(\w+)', 'GET', r'\1'),
            (r'@cherrypy\.tools\.(get|post|put|delete|patch)', r'\1', ''),
            (r'def\s+(\w+)\s*\(self', 'GET', r'\1'),
            (r'def\s+(index|default)\s*\(self', 'GET', r'\1'),
            
            # Tornado
            (r'class\s+(\w+Handler)', 'HTTP', r'\1'),
            (r'def\s+(get|post|put|delete|patch)\s*\(', r'\1', ''),
            (r'@tornado\.web\.(get|post|put|delete|patch)', r'\1', ''),
            
            # Quart
            (r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Starlette
            (r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Sails.js (Python-like)
            (r'(\w+):\s*function\s*\(req,\s*res\)', 'GET', r'\1'),
            
            # Generic Python patterns
            (r'def\s+(get|post|put|delete|patch)_(\w+)', r'\1', r'\2'),
            (r'def\s+(\w+)\s*\(.*request.*\)', 'HTTP', r'\1'),
            (r'def\s+(\w+)\s*\(.*req.*\)', 'HTTP', r'\1'),
            (r'def\s+(\w+)\s*\(.*response.*\)', 'HTTP', r'\1'),
        ]
        
        # Java frameworks - COMPREHENSIVE
        java_patterns = [
            # Spring Boot - Enhanced and Comprehensive
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\(["\']([^"\']+)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            (r'@RequestMapping\([^)]*value\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@RequestMapping\([^)]*method\s*=\s*RequestMethod\.([A-Z]+)', r'\1', ''),
            (r'@RestController.*?class\s+(\w+)', 'REST', ''),
            (r'@Controller.*?class\s+(\w+)', 'REST', ''),
            (r'@RestController', 'REST', ''),
            (r'@Controller', 'REST', ''),
            (r'@RequestMapping\([^)]*path\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@RequestMapping\([^)]*value\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            
            # Spring Boot with additional parameters
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\([^)]*value\s*=\s*["\']([^"\']+)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\([^)]*path\s*=\s*["\']([^"\']+)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            
            # Spring Boot with path variables
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\(["\']([^"\']*\{[^}]*\}[^"\']*)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            
            # Spring Boot with produces/consumes
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\([^)]*produces\s*=\s*["\']([^"\']+)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\([^)]*consumes\s*=\s*["\']([^"\']+)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            
            # Spring Boot with headers
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\([^)]*headers\s*=\s*["\']([^"\']+)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            
            # Spring Boot with params
            (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\([^)]*params\s*=\s*["\']([^"\']+)["\']', 
             lambda m: m.group(1).replace('Mapping', '').upper(), r'\2'),
            
            # JAX-RS - Enhanced
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@Path\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@Path\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@Consumes\(["\']([^"\']+)["\']', 'POST', ''),
            (r'@Produces\(["\']([^"\']+)["\']', 'GET', ''),
            
            # Jersey - Enhanced
            (r'@Path\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@GET.*?@Path\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@POST.*?@Path\(["\']([^"\']+)["\']', 'POST', r'\1'),
            (r'@PUT.*?@Path\(["\']([^"\']+)["\']', 'PUT', r'\1'),
            (r'@DELETE.*?@Path\(["\']([^"\']+)["\']', 'DELETE', r'\1'),
            
            # Struts
            (r'@Action\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@Namespace\(["\']([^"\']+)["\']', 'GET', ''),
            
            # Play Framework
            (r'@(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@Action\(["\']([^"\']+)["\']', 'GET', r'\1'),
            
            # Generic Java patterns
            (r'public\s+.*\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'public\s+.*\s+(\w+)\s*\(.*HttpServletRequest.*\)', 'HTTP', r'\1'),
            (r'public\s+.*\s+(\w+)\s*\(.*HttpServletResponse.*\)', 'HTTP', r'\1'),
            (r'@WebServlet\(["\']([^"\']+)["\']', 'GET', r'\1'),
        ]
        
        # JavaScript/Node.js frameworks - COMPREHENSIVE
        js_patterns = [
            # Express.js - Enhanced and Comprehensive
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'router\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'express\.Router\(\)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'\.route\(["\']([^"\']+)["\']\)\.(get|post|put|delete|patch)', r'\2', r'\1'),
            (r'\.all\(["\']([^"\']+)["\']', 'ALL', r'\1'),
            (r'\.use\(["\']([^"\']+)["\']', 'USE', r'\1'),
            
            # Express.js with middleware
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*[^,]+,\s*function', r'\1', r'\2'),
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*\[[^\]]+\],\s*function', r'\1', r'\2'),
            
            # Express.js with path parameters
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']*:[^"\']*)["\']', r'\1', r'\2'),
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']*\{[^}]*\}[^"\']*)["\']', r'\1', r'\2'),
            
            # Express.js with async/await
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*async\s*\(', r'\1', r'\2'),
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*async\s*function', r'\1', r'\2'),
            
            # Express.js with arrow functions
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*\([^)]*\)\s*=>', r'\1', r'\2'),
            
            # Express.js with error handling
            (r'\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\'],\s*\([^,]+,\s*[^,]+,\s*[^)]+\)\s*=>', r'\1', r'\2'),
            
            # Koa.js - Enhanced
            (r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Hapi.js - Enhanced
            (r'route:\s*{\s*path:\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'method:\s*["\']([^"\']+)["\'].*path:\s*["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'route\([^)]*path\s*:\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'route\([^)]*method\s*:\s*["\']([^"\']+)["\']', r'\1', ''),
            (r'server\.route\([^)]*path\s*:\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            
            # NestJS - Enhanced
            (r'@(Get|Post|Put|Delete|Patch|Head|Options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@Controller\(["\']([^"\']+)["\']', 'REST', ''),
            (r'@Controller', 'REST', ''),
            (r'@Injectable', 'SERVICE', ''),
            
            # Sails.js - Enhanced
            (r'(\w+):\s*function\s*\(req,\s*res\)', 'GET', r'\1'),
            (r'(\w+):\s*function\s*\(req,\s*res,\s*next\)', 'GET', r'\1'),
            (r'(\w+):\s*async\s*function\s*\(req,\s*res\)', 'GET', r'\1'),
            
            # Next.js API Routes
            (r'export\s+default\s+function\s+handler', 'API', ''),
            (r'export\s+default\s+async\s+function\s+handler', 'API', ''),
            (r'export\s+async\s+function\s+(get|post|put|delete|patch)', r'\1', ''),
            
            # Nuxt.js
            (r'export\s+default\s+async\s+function\s+handler', 'API', ''),
            (r'export\s+default\s+function\s+handler', 'API', ''),
            
            # Fastify
            (r'fastify\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Restify
            (r'server\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Generic JavaScript patterns
            (r'function\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'const\s+(get|post|put|delete|patch)(\w+)\s*=', r'\1', r'\2'),
            (r'async\s+function\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'(\w+)\s*:\s*async\s*\([^)]*req[^)]*\)', 'HTTP', r'\1'),
            (r'(\w+)\s*:\s*\([^)]*req[^)]*\)', 'HTTP', r'\1'),
        ]
        
        # C# frameworks - Enhanced patterns
        csharp_patterns = [
            # ASP.NET Core - Specific patterns for controller detection
            (r'\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]\s*public\s+.*?\s+(\w+)\s*\(', r'\1', r'\2'),
            (r'\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]\s*public\s+async\s+.*?\s+(\w+)\s*\(', r'\1', r'\2'),
            
            # Route attributes with HTTP methods
            (r'\[Route\(["\']([^"\']+)["\']\]\s*\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]', r'\2', r'\1'),
            (r'\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]\s*\[Route\(["\']([^"\']+)["\']\]', r'\1', r'\2'),
            
            # Controller-level route with method-level HTTP attributes (specific for api/[controller] pattern)
            (r'\[Route\(["\']api/\[controller\]\["\']\)\]\s*.*?\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]\s*public\s+.*?\s+(\w+)\s*\(', r'\1', r'/api/Employees'),
            (r'\[Route\(["\']api/\[controller\]\["\']\)\]\s*.*?\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]\s*public\s+async\s+.*?\s+(\w+)\s*\(', r'\1', r'/api/Employees'),
            
            # Method-level route attributes
            (r'\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]\s*\[Route\(["\']([^"\']+)["\']\]', r'\1', r'\2'),
            (r'\[Route\(["\']([^"\']+)["\']\]\s*\[Http(Get|Post|Put|Delete|Patch|Head|Options)\]', r'\2', r'\1'),
            
            # Generic route patterns
            (r'\[Route\(["\']([^"\']+)["\']\]', 'GET', r'\1'),
            (r'\[Route\(["\']([^"\']+)["\'],\s*Name\s*=\s*["\']([^"\']+)["\']\]', 'GET', r'\1'),
            
            # Controller classes
            (r'public\s+class\s+(\w+Controller)', 'REST', r'\1'),
            (r'public\s+class\s+(\w+ApiController)', 'REST', r'\1'),
            
            # API methods with return types
            (r'public\s+(IHttpActionResult|HttpResponseMessage|IActionResult)\s+(\w+)\s*\(', 'GET', r'\2'),
            (r'public\s+async\s+(Task<IHttpActionResult>|Task<HttpResponseMessage>|Task<IActionResult>)\s+(\w+)\s*\(', 'GET', r'\2'),
            
            # Minimal API patterns (.NET 6+)
            (r'app\.Map(Get|Post|Put|Delete|Patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'Map(Get|Post|Put|Delete|Patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Web API 2 patterns
            (r'\[ActionName\(["\']([^"\']+)["\']\]', 'GET', r'\1'),
            (r'\[AcceptVerbs\(["\']([^"\']+)["\']\]', r'\1', ''),
            
            # Generic API patterns
            (r'public\s+.*\s+(Get|Post|Put|Delete|Patch)(\w+)\s*\(', r'\1', r'\1\2'),
            (r'private\s+.*\s+(Get|Post|Put|Delete|Patch)(\w+)\s*\(', r'\1', r'\1\2'),
        ]
        
        # PHP frameworks - Enhanced and Comprehensive
        php_patterns = [
            # Laravel - Enhanced
            (r'Route::(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'Route::resource\(["\']([^"\']+)["\']', 'REST', r'\1'),
            (r'Route::apiResource\(["\']([^"\']+)["\']', 'REST', r'\1'),
            (r'Route::group\([^)]*\)', 'GROUP', ''),
            (r'Route::middleware\([^)]*\)', 'MIDDLEWARE', ''),
            (r'Route::prefix\(["\']([^"\']+)["\']\)', 'PREFIX', r'\1'),
            (r'Route::name\(["\']([^"\']+)["\']\)', 'NAME', r'\1'),
            
            # Laravel with closures
            (r'Route::(get|post|put|delete|patch)\(["\']([^"\']+)["\'],\s*function', r'\1', r'\2'),
            (r'Route::(get|post|put|delete|patch)\(["\']([^"\']+)["\'],\s*\[[^\]]+\]', r'\1', r'\2'),
            
            # Laravel with path parameters
            (r'Route::(get|post|put|delete|patch)\(["\']([^"\']*\{[^}]*\}[^"\']*)["\']', r'\1', r'\2'),
            
            # Symfony - Enhanced
            (r'@Route\(["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@Route\([^)]*path\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'@Route\([^)]*methods\s*=\s*\[["\']([^"\']+)["\']', r'\1', ''),
            (r'@Route\([^)]*name\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            
            # CodeIgniter - Enhanced
            (r'\$route\[["\']([^"\']+)["\']\]', 'GET', r'\1'),
            (r'\$route\[["\']([^"\']+)["\']\]\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            
            # Slim Framework
            (r'\$app->(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'\$app->(get|post|put|delete|patch)\(["\']([^"\']+)["\'],\s*function', r'\1', r'\2'),
            
            # Generic PHP patterns
            (r'function\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'public\s+function\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
        ]
        
        # Ruby frameworks - Enhanced and Comprehensive
        ruby_patterns = [
            # Ruby on Rails - Enhanced
            (r'def\s+(index|show|create|update|destroy|new|edit)', 'REST', r'\1'),
            (r'resources\s+:(\w+)', 'REST', r'\1'),
            (r'get\s+["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']+)["\']', 'POST', r'\1'),
            (r'put\s+["\']([^"\']+)["\']', 'PUT', r'\1'),
            (r'delete\s+["\']([^"\']+)["\']', 'DELETE', r'\1'),
            (r'patch\s+["\']([^"\']+)["\']', 'PATCH', r'\1'),
            (r'head\s+["\']([^"\']+)["\']', 'HEAD', r'\1'),
            (r'options\s+["\']([^"\']+)["\']', 'OPTIONS', r'\1'),
            
            # Rails with constraints
            (r'get\s+["\']([^"\']+)["\'],\s*to:\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']+)["\'],\s*to:\s*["\']([^"\']+)["\']', 'POST', r'\1'),
            
            # Rails with path parameters
            (r'get\s+["\']([^"\']*:[^"\']*)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']*:[^"\']*)["\']', 'POST', r'\1'),
            
            # Rails with namespaces
            (r'namespace\s+:(\w+)\s+do', 'NAMESPACE', r'\1'),
            (r'scope\s+["\']([^"\']+)["\']\s+do', 'SCOPE', r'\1'),
            
            # Sinatra - Enhanced
            (r'get\s+["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']+)["\']', 'POST', r'\1'),
            (r'put\s+["\']([^"\']+)["\']', 'PUT', r'\1'),
            (r'delete\s+["\']([^"\']+)["\']', 'DELETE', r'\1'),
            (r'patch\s+["\']([^"\']+)["\']', 'PATCH', r'\1'),
            (r'head\s+["\']([^"\']+)["\']', 'HEAD', r'\1'),
            (r'options\s+["\']([^"\']+)["\']', 'OPTIONS', r'\1'),
            
            # Sinatra with blocks
            (r'get\s+["\']([^"\']+)["\']\s+do', 'GET', r'\1'),
            (r'post\s+["\']([^"\']+)["\']\s+do', 'POST', r'\1'),
            
            # Sinatra with path parameters
            (r'get\s+["\']([^"\']*:[^"\']*)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']*:[^"\']*)["\']', 'POST', r'\1'),
            
            # Generic Ruby patterns
            (r'def\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'def\s+(\w+)\s*\([^)]*req[^)]*\)', 'HTTP', r'\1'),
        ]
        
        # Go frameworks
        go_patterns = [
            # Gin
            (r'\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'router\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Echo
            (r'\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Gorilla Mux
            (r'\.HandleFunc\(["\']([^"\']+)["\']', 'GET', r'\1'),
        ]
        
        # Rust frameworks
        rust_patterns = [
            # Actix Web
            (r'\.route\(["\']([^"\']+)["\'],\s*web::(get|post|put|delete|patch)', r'\2', r'\1'),
            (r'web::(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Rocket
            (r'#\[(get|post|put|delete|patch)\(["\']([^"\']+)["\']\]', r'\1', r'\2'),
        ]
        
        # Generic patterns (catch-all)
        generic_patterns = [
            # URL patterns in any language
            (r'["\']([^"\']*api[^"\']*)["\']', 'API', r'\1'),
            (r'["\']([^"\']*endpoint[^"\']*)["\']', 'API', r'\1'),
            (r'["\']([^"\']*service[^"\']*)["\']', 'API', r'\1'),
            
            # Function names that look like APIs
            (r'def\s+(get_|post_|put_|delete_|patch_|api_|endpoint_)(\w+)', 'API', r'\1\2'),
            (r'function\s+(get|post|put|delete|patch|api|endpoint)(\w+)', 'API', r'\1\2'),
            (r'public\s+.*\s+(get|post|put|delete|patch|api|endpoint)(\w+)', 'API', r'\1\2'),
            
            # Route definitions
            (r'route\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'path\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'url\s*=\s*["\']([^"\']+)["\']', 'GET', r'\1'),
        ]
        
        # Combine ALL patterns for universal API detection
        # Additional comprehensive patterns for more frameworks
        additional_patterns = [
            # TypeScript patterns
            (r'@(Get|Post|Put|Delete|Patch|Head|Options)\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@Controller\(["\']([^"\']+)["\']', 'REST', r'\1'),
            (r'@Injectable', 'SERVICE', ''),
            
            # Kotlin patterns
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'@RestController.*?class\s+(\w+)', 'REST', r'\1'),
            (r'@Controller.*?class\s+(\w+)', 'REST', r'\1'),
            
            # Swift patterns
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'func\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            
            # Dart/Flutter patterns
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'Future<.*>\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            
            # Scala patterns
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'def\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            
            # Clojure patterns
            (r'\(defn\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'\(defroutes\s+(\w+)', 'ROUTES', r'\1'),
            
            # Elixir patterns
            (r'def\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'get\s+["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']+)["\']', 'POST', r'\1'),
            
            # Haskell patterns
            (r'get\s+["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']+)["\']', 'POST', r'\1'),
            (r'(\w+)\s*::\s*Handler', 'HANDLER', r'\1'),
            
            # F# patterns
            (r'let\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Crystal patterns
            (r'get\s+["\']([^"\']+)["\']', 'GET', r'\1'),
            (r'post\s+["\']([^"\']+)["\']', 'POST', r'\1'),
            (r'def\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            
            # Nim patterns
            (r'proc\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            
            # Zig patterns
            (r'fn\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'pub\s+fn\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            
            # V patterns
            (r'fn\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            (r'pub\s+fn\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
            
            # Odin patterns
            (r'@(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS).*?@Path\(["\']([^"\']+)["\']', r'\1', r'\2'),
            (r'(\w+)\s*::\s*proc', 'PROC', r'\1'),
            
            # Jai patterns
            (r'(\w+)\s*::\s*proc', 'PROC', r'\1'),
            (r'fn\s+(get|post|put|delete|patch)(\w+)', r'\1', r'\2'),
        ]
        
        # Skip only pure configuration files that typically don't contain API endpoints
        config_files = [
            'Program.cs', 'Startup.cs',  # C# configuration
            'config.py', 'settings.py', 'wsgi.py', 'asgi.py',  # Python pure config
            'config.js', 'environment.ts', 'environment.js', 'config.ts',  # Config files
            'Application.java', 'Config.java',  # Java configuration
            'application.rb', 'config.ru',  # Ruby configuration
            'config.go',  # Go configuration
            'config.rs',  # Rust configuration
            'config.php', 'bootstrap.php',  # PHP configuration
            'manage.py',  # Django management
            'package.json', 'requirements.txt', 'pom.xml', 'build.gradle',  # Build files
            'dockerfile', 'docker-compose.yml', 'docker-compose.yaml',  # Docker files
            'web.config', 'app.config', 'application.properties',  # Config files
        ]
        
        file_lower = file_path.lower()
        is_config_file = any(file_lower.endswith(config_file.lower()) for config_file in config_files)
        
        # Also check for pure configuration patterns in the content (not API-related)
        # Only skip if the file contains ONLY configuration patterns without any API endpoints
        config_patterns = [
            'app.config[', 'app.settings[',  # Configuration settings
            'middleware', 'cors', 'authentication',  # Middleware setup
        ]
        
        has_config_patterns = any(pattern in content for pattern in config_patterns)
        
        # Only skip if it's a pure config file AND doesn't contain any API patterns
        # Check for common API patterns that would indicate this file has endpoints
        api_indicators = [
            '@app.route(', '@app.get(', '@app.post(', '@app.put(', '@app.delete(',  # Flask
            '@router.get(', '@router.post(', '@router.put(', '@router.delete(',  # FastAPI
            'def get_', 'def post_', 'def put_', 'def delete_',  # Generic function patterns
            'app.get(', 'app.post(', 'app.put(', 'app.delete(',  # Generic app patterns
            'router.get(', 'router.post(', 'router.put(', 'router.delete(',  # Generic router patterns
            'api/', '/api/', 'endpoint', 'endpoints',  # API keywords
        ]
        
        has_api_indicators = any(indicator in content for indicator in api_indicators)
        
        # Only skip if it's a config file AND has no API indicators
        if is_config_file and not has_api_indicators:
            logger.info(f"Skipping pure configuration file {file_path} - contains setup/configuration code, not API endpoints")
            return apis
        elif has_config_patterns and not has_api_indicators:
            logger.info(f"Skipping configuration file {file_path} - contains setup/configuration code, not API endpoints")
            return apis
        
        # Special handling for C# controllers with [Route("api/[controller]")] pattern
        if file_path.endswith('.cs') and '[Route("api/[controller]")]' in content:
            logger.info(f"Detected C# controller with api/[controller] pattern in {file_path}")
            csharp_apis = self._extract_csharp_controller_apis(content, file_path)
            if csharp_apis:
                apis.extend(csharp_apis)
                return apis  # Return early for C# controllers
        
        all_patterns = (python_patterns + java_patterns + js_patterns + 
                       csharp_patterns + php_patterns + ruby_patterns + 
                       go_patterns + rust_patterns + generic_patterns + additional_patterns)
        
        for pattern_tuple in all_patterns:
            if len(pattern_tuple) == 3:
                pattern, method_pattern, endpoint_pattern = pattern_tuple
            else:
                # Handle old format for backward compatibility
                pattern = pattern_tuple
                method_pattern = 'GET'
                endpoint_pattern = r'\1'
            
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                # Extract HTTP method
                if callable(method_pattern):
                    http_method = method_pattern(match)
                else:
                    try:
                        http_method = match.expand(method_pattern).upper()
                    except:
                        http_method = 'GET'
                
                # Extract endpoint
                try:
                    endpoint = match.expand(endpoint_pattern)
                except:
                    endpoint = match.group(1) if match.groups() else ''
                
                if endpoint:
                    # Validate that this is actually an API endpoint, not configuration
                    if self._is_valid_api_endpoint(endpoint, content, match.start()):
                        # Extract function name (next line or same line)
                        lines = content.split('\n')
                        match_line = content[:match.start()].count('\n')
                        
                        # Debug: Log line number calculation
                        logger.debug(f"Found API '{endpoint}' at line {match_line + 1} in {file_path}")
                        
                        function_name = self._extract_function_name(lines, match_line)
                        framework = self._detect_framework(file_path, pattern)
                        
                        # Calculate complexity score
                        complexity = self._calculate_complexity(content, match_line)
                        
                        # Identify potential issues
                        potential_issues = self._identify_potential_issues(content, match_line)
                        
                        # Determine risk level
                        risk_level = self._determine_risk_level(complexity, potential_issues)
                        
                        # Extract code snippet
                        code_snippet = self._extract_code_snippet(lines, match_line)
                        
                        # Create endpoint with HTTP method
                        full_endpoint = f"{http_method} {endpoint}" if http_method != 'GET' else endpoint
                        
                        # Debug: Log API creation with line number
                        logger.debug(f"Creating API '{full_endpoint}' with line_number={match_line + 1}")
                        
                        api = DiscoveredAPI(
                            endpoint=full_endpoint,
                            file_path=file_path,
                            function_name=function_name,
                            framework=framework,
                            complexity_score=complexity,
                            potential_issues=potential_issues,
                            risk_level=risk_level,
                            code_snippet=code_snippet,
                            line_number=match_line + 1  # Convert 0-based to 1-based line numbers
                        )
                        apis.append(api)
        
        # If no APIs found with manual patterns, try AI-powered detection
        if not apis:
            logger.info(f"No APIs found with pattern matching in {file_path}, trying AI analysis...")
            apis = self._ai_powered_api_detection(content, file_path)
        
        # If still no APIs found, try comprehensive AI analysis
        if not apis:
            logger.info(f"No APIs found with standard AI detection in {file_path}, trying comprehensive analysis...")
            apis = self._comprehensive_ai_analysis(content, file_path)
        
        # Filter out low-quality APIs and non-API endpoints
        filtered_apis = []
        seen_endpoints = set()  # Track unique endpoints to avoid duplicates
        
        for api in apis:
            if not api.endpoint or len(api.endpoint.strip()) == 0:
                continue
                
            endpoint = api.endpoint.strip()
            
            # Skip if already seen (deduplication) - keep HTTP method for proper uniqueness
            if endpoint in seen_endpoints:
                continue
            seen_endpoints.add(endpoint)
            
            # Filter out external URLs and non-API endpoints
            if (endpoint.startswith('http://') or 
                endpoint.startswith('https://') or
                endpoint.startswith('www.') or
                endpoint.startswith('ftp://') or
                endpoint.startswith('file://') or
                'googleapis.com' in endpoint or
                'youtu.be' in endpoint or
                'youtube.com' in endpoint or
                'localhost:' in endpoint or
                '127.0.0.1' in endpoint or
                endpoint.startswith('unknown') or
                endpoint.startswith('HTTP') or
                endpoint.startswith('$PROJECT_DIR$') or
                endpoint.startswith('API autocapitalize') or
                endpoint.startswith('API ') or
                endpoint.startswith('autocapitalize') or
                endpoint.startswith('autocorrect') or
                endpoint.startswith('shadow_root') or
                endpoint.startswith('value') or
                endpoint.startswith('name') or
                endpoint.startswith('password') or
                endpoint.startswith('user-name') or
                endpoint.startswith('component') or
                endpoint.startswith('module') or
                endpoint.startswith('project') or
                endpoint.startswith('modules') or
                endpoint.startswith('fileurl') or
                endpoint.startswith('filepath') or
                endpoint.startswith('ProjectModuleManager') or
                endpoint.startswith('Tega') or
                endpoint.startswith('infsvc') or
                endpoint.startswith('jira') or
                endpoint.startswith('testcase') or
                endpoint.startswith('builder') or
                endpoint.startswith('agent_history') or
                endpoint.startswith('history') or
                endpoint.startswith('agent') or
                endpoint.startswith('json') or
                endpoint.startswith('xml') or
                endpoint.startswith('yml') or
                endpoint.startswith('yaml') or
                endpoint.startswith('md') or
                endpoint.startswith('txt') or
                endpoint.startswith('log') or
                endpoint.startswith('lock') or
                endpoint.startswith('.idea') or
                endpoint.startswith('.vscode') or
                endpoint.startswith('node_modules') or
                endpoint.startswith('__pycache__') or
                endpoint.startswith('.git') or
                endpoint.startswith('venv') or
                endpoint.startswith('env') or
                endpoint.startswith('bin') or
                endpoint.startswith('obj') or
                endpoint.startswith('packages') or
                endpoint.startswith('target') or
                endpoint.startswith('build') or
                endpoint.startswith('dist') or
                endpoint.startswith('coverage') or
                endpoint.startswith('.pytest_cache') or
                endpoint.startswith('logs') or
                endpoint.startswith('test') or
                endpoint.startswith('tests') or
                endpoint.startswith('spec') or
                endpoint.startswith('specs') or
                endpoint.startswith('docs') or
                endpoint.startswith('documentation') or
                endpoint.startswith('assets') or
                endpoint.startswith('static') or
                endpoint.startswith('public') or
                endpoint.startswith('resources') or
                endpoint.startswith('config') or
                endpoint.startswith('.env') or
                endpoint.startswith('.gitignore') or
                endpoint.startswith('.gitattributes') or
                endpoint.startswith('package-lock') or
                endpoint.startswith('yarn.lock') or
                endpoint.startswith('composer.lock') or
                endpoint.startswith('pom.xml') or
                endpoint.startswith('build.gradle') or
                endpoint.startswith('requirements.txt') or
                endpoint.startswith('Pipfile') or
                endpoint.startswith('poetry.lock') or
                len(endpoint) <= 3 or
                endpoint.isdigit() or
                endpoint.startswith('.') or
                endpoint.endswith('.') or
                endpoint.startswith(' ') or
                endpoint.endswith(' ')):
                continue
            
            # Only include endpoints that look like real APIs
            if ('/' in endpoint or endpoint.startswith(('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'))):
                filtered_apis.append(api)
        
        # AI validation to double-check if endpoints are actually APIs
        ai_validated_apis = self._ai_validate_apis(filtered_apis, file_path, content)
        
        return ai_validated_apis
    
    def _ai_validate_apis(self, apis: List[DiscoveredAPI], file_path: str, content: str) -> List[DiscoveredAPI]:
        """AI validation to double-check if discovered endpoints are actually APIs."""
        if not apis or not self.bedrock_service:
            return apis
        
        validated_apis = []
        
        try:
            # Create a batch validation prompt for efficiency
            endpoints_info = []
            for i, api in enumerate(apis):
                endpoints_info.append(f"{i+1}. Endpoint: {api.endpoint}\n   Function: {api.function_name}\n   Framework: {api.framework}")
            
            validation_prompt = f"""
            You are an expert API analyst and code reviewer. Analyze this source code to validate API endpoints.
            
            File: {file_path}
            Full Code Context: {content}
            
            Discovered Endpoints to Validate:
            {chr(10).join(endpoints_info)}
            
            For each endpoint, perform deep analysis:
            1. Examine the code context around the endpoint
            2. Check if it's a real API endpoint (not CSS, JS, HTML, or external URLs)
            3. Verify it's part of a web framework (Flask, FastAPI, Django, Express, etc.)
            4. Look for HTTP method decorators, route definitions, or API handlers
            5. Check if it's a functional endpoint that can be called
            
            Analysis Criteria:
            - Real API endpoints: Route handlers, controller methods, API functions
            - NOT APIs: CSS files, external URLs, static assets, configuration files
            - Framework patterns: @app.route, @api_view, app.get(), router.post(), etc.
            - Code context: Should be in a web application file, not a utility or config file
            
            For each endpoint, provide:
            1. is_api: true/false (is this a real API endpoint?)
            2. confidence: 0-100 (how confident are you?)
            3. reason: Detailed explanation of your analysis
            4. framework_detected: What framework this belongs to (if any)
            5. http_method: Detected HTTP method (GET, POST, etc.)
            6. line_analysis: What you found in the code context
            
            Respond in JSON format:
            {{
                "validations": [
                    {{
                        "endpoint": "endpoint_name",
                        "is_api": true/false,
                        "confidence": 85,
                        "reason": "Detailed analysis explanation",
                        "framework_detected": "Flask/FastAPI/Django/etc",
                        "http_method": "GET/POST/PUT/DELETE",
                        "line_analysis": "What was found in the code"
                    }}
                ]
            }}
            """
            
            ai_response = self.bedrock_service.generate_summary_from_prompt(validation_prompt)
            
            # Parse AI response
            import json
            try:
                validation_result = json.loads(ai_response)
                validations = validation_result.get('validations', [])
                
                # Create validation lookup
                validation_lookup = {}
                for validation in validations:
                    endpoint = validation.get('endpoint', '')
                    validation_lookup[endpoint] = validation
                
                # Filter APIs based on AI validation
                for api in apis:
                    validation = validation_lookup.get(api.endpoint, {})
                    is_api = validation.get('is_api', False)
                    confidence = validation.get('confidence', 0)
                    
                    if is_api and confidence >= 70:  # Only include high-confidence API validations
                        # Keep original API object (preserves line numbers and other data)
                        validated_apis.append(api)
                        logger.info(f"AI validated API: {api.endpoint} (confidence: {confidence}%)")
                    else:
                        logger.info(f"AI rejected non-API: {api.endpoint} (confidence: {confidence}%)")
                        
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI validation response, using original APIs")
                return apis
                
        except Exception as e:
            logger.error(f"AI validation failed: {str(e)}, using original APIs")
            return apis
        
        logger.info(f"AI validation: {len(validated_apis)}/{len(apis)} endpoints confirmed as real APIs")
        return validated_apis
    
    def _create_debug_sample_apis(self) -> List[DiscoveredAPI]:
        """Create debug sample APIs for testing when no APIs are found."""
        # Use the worst APIs from performance data if available
        if self._debug_worst_apis:
            logger.info(f"Creating debug APIs based on {len(self._debug_worst_apis)} worst APIs from performance data")
            sample_apis = []
            for i, worst_api in enumerate(self._debug_worst_apis[:5]):  # Limit to 5 for testing
                endpoint = worst_api.get('endpoint', f'/api/endpoint{i+1}')
                sample_apis.append(DiscoveredAPI(
                    endpoint=endpoint,
                    file_path=f"Controllers/ApiController{i+1}.cs",
                    function_name=f"GetEndpoint{i+1}",
                    framework="ASP.NET Core",
                    complexity_score=3.5 + (i * 0.5),
                    potential_issues=["no_async", "no_error_handling", "no_validation"],
                    risk_level=SeverityLevel.HIGH if i < 2 else SeverityLevel.MEDIUM,
                    code_snippet=f"public IActionResult {endpoint.replace('/', '').replace('api', 'Get')}() {{ return Ok(data); }}",
                    line_number=25 + (i * 10)
                ))
            return sample_apis
        
        # Fallback to generic sample APIs
        sample_apis = [
            DiscoveredAPI(
                endpoint="GET /api/basestations",
                file_path="Controllers/BaseStationController.cs",
                function_name="GetBaseStations",
                framework="ASP.NET Core",
                complexity_score=3.5,
                potential_issues=["no_async", "no_error_handling"],
                risk_level=SeverityLevel.MEDIUM,
                code_snippet="public IActionResult GetBaseStations() { return Ok(basestations); }",
                line_number=25
            ),
            DiscoveredAPI(
                endpoint="GET /api/assets",
                file_path="Controllers/AssetController.cs",
                function_name="GetAssets",
                framework="ASP.NET Core",
                complexity_score=4.2,
                potential_issues=["no_validation", "no_async"],
                risk_level=SeverityLevel.HIGH,
                code_snippet="public IActionResult GetAssets() { return Ok(assets); }",
                line_number=42
            ),
            DiscoveredAPI(
                endpoint="GET /api/alerts",
                file_path="Controllers/AlertController.cs",
                function_name="GetAlerts",
                framework="ASP.NET Core",
                complexity_score=4.8,
                potential_issues=["no_async", "no_error_handling", "no_validation"],
                risk_level=SeverityLevel.HIGH,
                code_snippet="public IActionResult GetAlerts() { return Ok(alerts); }",
                line_number=58
            )
        ]
        
        logger.info(f"Created {len(sample_apis)} debug sample APIs for testing")
        return sample_apis
    
    def _extract_csharp_controller_apis(self, content: str, file_path: str) -> List[DiscoveredAPI]:
        """Extract APIs from C# controllers with [Route("api/[controller]")] pattern."""
        apis = []
        
        try:
            # Extract controller name from class declaration
            controller_match = re.search(r'public\s+class\s+(\w+Controller)', content)
            if not controller_match:
                return apis
            
            controller_name = controller_match.group(1)
            # Remove "Controller" suffix and convert to lowercase for the route
            base_name = controller_name.replace('Controller', '').lower()
            base_route = f"/api/{base_name}"
            
            # Split content into lines for line number calculation
            lines = content.split('\n')
            
            # Find all method blocks (from [HttpMethod] to the closing brace)
            # This pattern matches method blocks with HTTP attributes
            method_pattern = r'(\[Http(Get|Post|Put|Delete|Patch|Head|Options)(?:\([^)]*\))?\](?:\s*\[Route\([^)]*\)\])?\s*public\s+.*?\s+(\w+)\s*\([^)]*\)\s*\{[^}]*\})'
            
            for match in re.finditer(method_pattern, content, re.MULTILINE | re.DOTALL):
                method_block = match.group(1)
                http_method = match.group(2).upper()
                method_name = match.group(3)
                
                # Calculate line number for the method declaration
                method_start = content.find(method_block)
                match_line = content[:method_start].count('\n')
                
                logger.debug(f"C# Controller Detection - Found method block:")
                logger.debug(f"  HTTP Method: {http_method}")
                logger.debug(f"  Method Name: {method_name}")
                logger.debug(f"  Line Number: {match_line + 1}")
                logger.debug(f"  Method Block: {method_block[:100]}...")
                
                # Extract route information from the method block
                endpoint = self._extract_csharp_endpoint(method_block, base_route, method_name, http_method)
                
                # Create full endpoint with method
                full_endpoint = f"{http_method} {endpoint}"
                
                # Extract function name and other details
                function_name = method_name
                framework = "ASP.NET Core"
                
                # Calculate complexity
                complexity = self._calculate_complexity(content, match_line)
                
                # Identify potential issues
                potential_issues = self._identify_potential_issues(content, match_line)
                
                # Determine risk level
                risk_level = self._determine_risk_level(complexity, potential_issues)
                
                # Extract code snippet
                code_snippet = self._extract_code_snippet(lines, match_line)
                
                logger.debug(f"Found C# API: {full_endpoint} at line {match_line + 1}")
                
                api = DiscoveredAPI(
                    endpoint=full_endpoint,
                    file_path=file_path,
                    function_name=function_name,
                    framework=framework,
                    complexity_score=complexity,
                    potential_issues=potential_issues,
                    risk_level=risk_level,
                    code_snippet=code_snippet,
                    line_number=match_line + 1
                )
                apis.append(api)
            
            logger.info(f"Extracted {len(apis)} APIs from C# controller {controller_name}")
            
        except Exception as e:
            logger.error(f"Failed to extract C# controller APIs: {str(e)}")
        
        return apis
    
    def _extract_csharp_endpoint(self, method_block: str, base_route: str, method_name: str, http_method: str) -> str:
        """Extract endpoint from C# method block, handling both inline and separate Route attributes."""
        try:
            # Check for separate [Route] attribute
            route_match = re.search(r'\[Route\(["\']([^"\']+)["\']\)\]', method_block)
            if route_match:
                route_path = route_match.group(1)
                # Handle route parameters like {id:guid}
                if '{' in route_path and '}' in route_path:
                    # Convert {id:guid} to {id}
                    route_path = re.sub(r'\{([^:}]+):[^}]+\}', r'{\1}', route_path)
                return f"{base_route}/{route_path}" if not route_path.startswith('/') else route_path
            
            # Check for inline route in HTTP attribute like [HttpGet("{id}")]
            inline_route_match = re.search(r'\[Http(Get|Post|Put|Delete|Patch|Head|Options)\(["\']([^"\']+)["\']\)\]', method_block)
            if inline_route_match:
                route_path = inline_route_match.group(2)
                # Handle route parameters like {id:guid}
                if '{' in route_path and '}' in route_path:
                    # Convert {id:guid} to {id}
                    route_path = re.sub(r'\{([^:}]+):[^}]+\}', r'{\1}', route_path)
                return f"{base_route}/{route_path}" if not route_path.startswith('/') else route_path
            
            # Build endpoint based on method name and HTTP method (fallback)
            if http_method == 'GET':
                if method_name.lower() in ['getemployees', 'getall', 'get']:
                    return base_route
                elif method_name.lower() in ['getemployeebyid', 'getbyid', 'get']:
                    return f"{base_route}/{{id}}"
                else:
                    return f"{base_route}/{method_name.lower()}"
            elif http_method == 'POST':
                if method_name.lower() in ['addemployee', 'create', 'add', 'post']:
                    return base_route
                else:
                    return f"{base_route}/{method_name.lower()}"
            elif http_method == 'PUT':
                if method_name.lower() in ['updateemployee', 'update', 'put']:
                    return f"{base_route}/{{id}}"
                else:
                    return f"{base_route}/{method_name.lower()}"
            elif http_method == 'DELETE':
                if method_name.lower() in ['deleteemployee', 'delete', 'remove']:
                    return f"{base_route}/{{id}}"
                else:
                    return f"{base_route}/{method_name.lower()}"
            else:
                return f"{base_route}/{method_name.lower()}"
                
        except Exception as e:
            logger.error(f"Failed to extract C# endpoint: {str(e)}")
            return f"{base_route}/{method_name.lower()}"
    
    def _extract_apis_from_file_chunked(self, owner: str, repo: str, file_path: str, branch: str = None) -> List[DiscoveredAPI]:
        """Extract APIs from large files using chunked processing for better performance."""
        all_apis = []
        chunk_size = 8192  # 8KB chunks
        overlap = 1024     # 1KB overlap to catch APIs split across chunks
        
        try:
            # Get file content in chunks
            file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
            if branch:
                file_url += f"?ref={branch}"
            
            headers = {'Authorization': f'token {self.token}'}
            response = requests.get(file_url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch file {file_path}: {response.status_code}")
                return []
            
            file_data = response.json()
            if file_data.get('type') != 'file':
                return []
            
            # Decode content
            import base64
            content = base64.b64decode(file_data['content']).decode('utf-8', errors='ignore')
            
            # Process file in chunks
            lines = content.split('\n')
            total_lines = len(lines)
            
            for start_line in range(0, total_lines, chunk_size):
                end_line = min(start_line + chunk_size, total_lines)
                
                # Add overlap to catch APIs split across chunks
                chunk_start = max(0, start_line - overlap // 2)
                chunk_end = min(total_lines, end_line + overlap // 2)
                
                chunk_content = '\n'.join(lines[chunk_start:chunk_end])
                
                # Extract APIs from this chunk
                chunk_apis = self._extract_apis_from_file(chunk_content, file_path)
                
                # Adjust line numbers to account for chunk offset
                for api in chunk_apis:
                    if api.line_number:
                        api.line_number += chunk_start
                
                all_apis.extend(chunk_apis)
                
                # Early termination if we find enough APIs
                if len(all_apis) > 50:  # Limit to prevent excessive processing
                    logger.info(f"Found {len(all_apis)} APIs in {file_path}, stopping chunked processing")
                    break
            
            # Remove duplicates based on endpoint and line number
            unique_apis = []
            seen = set()
            for api in all_apis:
                key = (api.endpoint, api.line_number)
                if key not in seen:
                    seen.add(key)
                    unique_apis.append(api)
            
            logger.info(f"Chunked processing found {len(unique_apis)} unique APIs in {file_path}")
            return unique_apis
            
        except Exception as e:
            logger.error(f"Chunked processing failed for {file_path}: {str(e)}")
            return []
    
    def _ai_powered_api_detection(self, content: str, file_path: str) -> List[DiscoveredAPI]:
        """AI-powered API detection with comprehensive source code analysis."""
        apis = []
        
        # Skip only pure configuration files that typically don't contain API endpoints
        config_files = [
            'Program.cs', 'Startup.cs',  # C# configuration
            'config.py', 'settings.py', 'wsgi.py', 'asgi.py',  # Python pure config
            'config.js', 'environment.ts', 'environment.js', 'config.ts',  # Config files
            'Application.java', 'Config.java',  # Java configuration
            'application.rb', 'config.ru',  # Ruby configuration
            'config.go',  # Go configuration
            'config.rs',  # Rust configuration
            'config.php', 'bootstrap.php',  # PHP configuration
            'manage.py',  # Django management
            'package.json', 'requirements.txt', 'pom.xml', 'build.gradle',  # Build files
            'dockerfile', 'docker-compose.yml', 'docker-compose.yaml',  # Docker files
            'web.config', 'app.config', 'application.properties',  # Config files
        ]
        
        file_lower = file_path.lower()
        is_config_file = any(file_lower.endswith(config_file.lower()) for config_file in config_files)
        
        # Also check for pure configuration patterns in the content (not API-related)
        # Only skip if the file contains ONLY configuration patterns without any API endpoints
        config_patterns = [
            'app.config[', 'app.settings[',  # Configuration settings
            'middleware', 'cors', 'authentication',  # Middleware setup
        ]
        
        has_config_patterns = any(pattern in content for pattern in config_patterns)
        
        # Only skip if it's a pure config file AND doesn't contain any API patterns
        # Check for common API patterns that would indicate this file has endpoints
        api_indicators = [
            '@app.route(', '@app.get(', '@app.post(', '@app.put(', '@app.delete(',  # Flask
            '@router.get(', '@router.post(', '@router.put(', '@router.delete(',  # FastAPI
            'def get_', 'def post_', 'def put_', 'def delete_',  # Generic function patterns
            'app.get(', 'app.post(', 'app.put(', 'app.delete(',  # Generic app patterns
            'router.get(', 'router.post(', 'router.put(', 'router.delete(',  # Generic router patterns
            'api/', '/api/', 'endpoint', 'endpoints',  # API keywords
        ]
        
        has_api_indicators = any(indicator in content for indicator in api_indicators)
        
        # Only skip if it's a config file AND has no API indicators
        if is_config_file and not has_api_indicators:
            logger.info(f"Skipping AI analysis for pure configuration file {file_path} - contains setup/configuration code, not API endpoints")
            return apis
        elif has_config_patterns and not has_api_indicators:
            logger.info(f"Skipping AI analysis for configuration file {file_path} - contains setup/configuration code, not API endpoints")
            return apis
        
        try:
            # Use AI to analyze the code and find potential APIs
            ai_prompt = f"""
            You are an expert code analyst specializing in web API detection. Analyze this source code file thoroughly to identify ALL API endpoints.
            
            File: {file_path}
            Full Code Content: {content}
            
            Perform deep analysis to find:
            1. Route definitions and decorators (@app.route, @router.get, @api_view, etc.)
            2. HTTP method handlers (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
            3. API endpoints and URL patterns
            4. RESTful API patterns and conventions
            5. Controller methods and action methods
            6. Function definitions that handle HTTP requests
            7. Class-based views and view sets
            8. Middleware and interceptor patterns
            9. Dynamic route generation
            10. API versioning patterns
            
            Analysis Guidelines:
            - Look for ANY pattern that could be an API endpoint
            - Check for both explicit and implicit route definitions
            - Consider framework-specific patterns (Flask, FastAPI, Django, Express, etc.)
            - Look for both synchronous and asynchronous patterns
            - Check for nested routes and blueprint patterns
            - Consider API documentation annotations
            - Look for test endpoints and development routes
            
            For each discovered API, provide:
            - Method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
            - Endpoint: The actual API path (e.g., "/api/users", "/users")
            - Function: The function/method name that handles this endpoint
            - Framework: Detected framework (Flask, FastAPI, Django, Express, etc.)
            - Line: Approximate line number where the endpoint is defined
            - Confidence: How confident you are this is a real API (0-100)
            - Context: Brief description of what you found in the code
            
            Return the findings in this format:
            - Method: [HTTP_METHOD]
            - Endpoint: [endpoint_name]
            - Function: [function_name]
            - Framework: [detected_framework]
            - Line: [line_number]
            - Confidence: [confidence_score]
            - Context: [code_context]
            
            If no APIs found, return "No APIs detected"
            """
            
            # Use Bedrock to analyze the code
            if hasattr(self, 'bedrock_service') and self.bedrock_service:
                ai_response = self.bedrock_service.generate_summary_from_prompt(ai_prompt)
                
                # Parse AI response to extract APIs
                apis = self._parse_ai_response(ai_response, file_path, content)
            
        except Exception as e:
            logger.warning(f"AI-powered detection failed: {str(e)}")
        
        return apis
    
    def _comprehensive_ai_analysis(self, content: str, file_path: str) -> List[DiscoveredAPI]:
        """Comprehensive AI analysis for complex API detection when standard methods fail."""
        if not self.bedrock_service:
            return []
        
        try:
            # Use AI for comprehensive analysis
            ai_prompt = f"""
            You are an expert code analyst with deep knowledge of web frameworks and API patterns. 
            Perform a comprehensive analysis of this source code to find ALL possible API endpoints.
            
            File: {file_path}
            Full Code Content: {content}
            
            Analyze this code using multiple approaches:
            1. Look for ANY function that could handle HTTP requests
            2. Check for implicit API patterns and conventions
            3. Look for dynamic route generation
            4. Check for framework-specific patterns you might have missed
            5. Look for API documentation or comments that indicate endpoints
            6. Check for test functions that might reveal API structure
            7. Look for configuration files or route definitions
            8. Check for middleware or interceptor patterns
            9. Look for class-based views or controllers
            10. Check for any function that returns data or handles requests
            
            Be very thorough and creative in your analysis. Look for:
            - Functions with names like: get_, post_, put_, delete_, fetch_, create_, update_, etc.
            - Functions that return JSON, XML, or HTTP responses
            - Functions that handle request/response objects
            - Functions that are called from route handlers
            - Functions that process data and return results
            - Any function that could be an API endpoint
            
            For each potential API you find, provide:
            - Method: [HTTP_METHOD] (infer from function name if not explicit)
            - Endpoint: [endpoint_path] (infer from function name or context)
            - Function: [function_name]
            - Framework: [detected_framework]
            - Line: [approximate_line_number]
            - Confidence: [confidence_score_0_100]
            - Context: [detailed_explanation_of_why_this_is_an_api]
            
            Return in this format:
            - Method: [HTTP_METHOD]
            - Endpoint: [endpoint_path]
            - Function: [function_name]
            - Framework: [framework]
            - Line: [line_number]
            - Confidence: [confidence]
            - Context: [explanation]
            
            If no APIs found, return "No APIs detected"
            """
            
            ai_response = self.bedrock_service.generate_summary_from_prompt(ai_prompt)
            
            # Parse AI response
            apis = self._parse_ai_response(ai_response, file_path, content)
            
            logger.info(f"Comprehensive AI analysis found {len(apis)} APIs in {file_path}")
            return apis
            
        except Exception as e:
            logger.error(f"Comprehensive AI analysis failed for {file_path}: {str(e)}")
            return []
    
    def _parse_ai_response(self, ai_response: str, file_path: str, content: str) -> List[DiscoveredAPI]:
        """Parse AI response to extract API information with enhanced analysis."""
        apis = []
        
        try:
            lines = ai_response.split('\n')
            current_api = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('- Method:'):
                    if current_api:
                        # Only add high-confidence APIs
                        confidence = int(current_api.get('confidence', 0))
                        if confidence >= 70:
                            apis.append(self._create_api_from_ai(current_api, file_path, content))
                    current_api = {'method': line.replace('- Method:', '').strip()}
                elif line.startswith('- Endpoint:'):
                    current_api['endpoint'] = line.replace('- Endpoint:', '').strip()
                elif line.startswith('- Function:'):
                    current_api['function'] = line.replace('- Function:', '').strip()
                elif line.startswith('- Framework:'):
                    current_api['framework'] = line.replace('- Framework:', '').strip()
                elif line.startswith('- Line:'):
                    current_api['line'] = line.replace('- Line:', '').strip()
                elif line.startswith('- Confidence:'):
                    current_api['confidence'] = line.replace('- Confidence:', '').strip()
                elif line.startswith('- Context:'):
                    current_api['context'] = line.replace('- Context:', '').strip()
            
            # Add the last API if exists and meets confidence threshold
            if current_api:
                confidence = int(current_api.get('confidence', 0))
                if confidence >= 70:
                    apis.append(self._create_api_from_ai(current_api, file_path, content))
                
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {str(e)}")
        
        return apis
    
    def _create_api_from_ai(self, api_data: dict, file_path: str, content: str) -> DiscoveredAPI:
        """Create DiscoveredAPI object from AI analysis data with enhanced analysis."""
        method = api_data.get('method', 'GET').upper()
        endpoint = api_data.get('endpoint', api_data.get('function', 'unknown'))
        function_name = api_data.get('function', 'unknown_function')
        framework = api_data.get('framework', 'AI Detected')
        confidence = int(api_data.get('confidence', 70))
        context = api_data.get('context', 'AI detected')
        
        # Try to get line number from AI analysis
        line_number = 1  # Default
        try:
            ai_line = api_data.get('line', '1')
            if ai_line.isdigit():
                line_number = int(ai_line)
        except:
            pass
        
        # Create full endpoint with method
        full_endpoint = f"{method} {endpoint}" if method != 'GET' else endpoint
        
        # Calculate complexity based on confidence and context
        complexity = min(confidence / 100.0, 5.0)  # Use confidence as complexity indicator
        
        # Identify potential issues based on AI context analysis
        potential_issues = []
        context_lower = context.lower()
        
        if 'async' not in context_lower and 'async' not in content.lower():
            potential_issues.append('no_async')
        if 'try' not in context_lower and 'try' not in content.lower():
            potential_issues.append('no_error_handling')
        if 'cache' not in context_lower and 'cache' not in content.lower():
            potential_issues.append('no_caching')
        if 'validation' not in context_lower and 'validation' not in content.lower():
            potential_issues.append('no_validation')
        if 'auth' not in context_lower and 'auth' not in content.lower():
            potential_issues.append('no_authentication')
        
        # Determine risk level based on confidence and issues
        if confidence < 80:
            risk_level = SeverityLevel.HIGH
        elif len(potential_issues) > 3:
            risk_level = SeverityLevel.MEDIUM
        else:
            risk_level = SeverityLevel.LOW
        
        # Extract relevant code snippet around the detected line
        lines = content.split('\n')
        start_line = max(0, line_number - 3)
        end_line = min(len(lines), line_number + 3)
        code_snippet = '\n'.join(lines[start_line:end_line])
        
        logger.info(f"AI detected API: {full_endpoint} at line {line_number} (confidence: {confidence}%)")
        
        return DiscoveredAPI(
            endpoint=full_endpoint,
            file_path=file_path,
            function_name=function_name,
            framework=framework,
            complexity_score=min(complexity, 10.0),
            potential_issues=potential_issues,
            risk_level=risk_level,
            code_snippet=code_snippet,
            line_number=line_number
        )
    
    def _is_valid_api_endpoint(self, endpoint: str, content: str, match_position: int) -> bool:
        """Validate that the detected endpoint is actually an API endpoint, not configuration."""
        # Skip empty or invalid endpoints
        if not endpoint or endpoint.strip() == '':
            return False
        
        # Skip generic patterns that are likely configuration
        invalid_patterns = [
            'GET, POST, PUT, DELETE, ETC',
            '[controller]',
            '[action]',
            'Action methods in controllers',
            'controllers',
            'middleware',
            'configuration',
            'setup',
            'startup',
            'app.run',
            'app.listen',
            'server.start',
            'app.MapControllers',
            'app.MapRazorPages',
            'app.include_router',
            'app.mount',
            'urlpatterns',
            'router = APIRouter',
        ]
        
        endpoint_lower = endpoint.lower()
        for pattern in invalid_patterns:
            if pattern.lower() in endpoint_lower:
                logger.debug(f"Rejecting invalid endpoint pattern: {endpoint}")
                return False
        
        # Check if the endpoint looks like a real API path
        # Real API endpoints typically start with / or contain path-like patterns
        if not (endpoint.startswith('/') or 
                endpoint.startswith('api/') or 
                endpoint.startswith('v1/') or 
                endpoint.startswith('v2/') or
                '/' in endpoint or
                '{' in endpoint or  # Path parameters
                endpoint.isalnum()):  # Simple endpoint names
            logger.debug(f"Rejecting non-API-like endpoint: {endpoint}")
            return False
        
        # Check the context around the match to ensure it's not in a configuration block
        context_start = max(0, match_position - 200)
        context_end = min(len(content), match_position + 200)
        context = content[context_start:context_end].lower()
        
        # Skip if it's in a configuration context
        config_contexts = [
            'app.run(',
            'app.listen(',
            'app.start(',
            'app.use(',
            'app.configure(',
            'middleware',
            'cors',
            'authentication',
            'configuration',
            'setup',
            'startup',
            'main(',
            'if __name__',
        ]
        
        for context_pattern in config_contexts:
            if context_pattern in context:
                logger.debug(f"Rejecting endpoint in configuration context: {endpoint}")
                return False
        
        return True

    def _extract_function_name(self, lines: List[str], match_line: int) -> str:
        """Extract function name from the matched line or nearby lines."""
        # Look for function definition in the next few lines
        for i in range(match_line, min(match_line + 5, len(lines))):
            line = lines[i].strip()
            
            # Python function definitions
            if 'def ' in line or 'async def ' in line:
                # Extract function name
                func_match = re.search(r'(?:async\s+)?def\s+(\w+)', line)
                if func_match:
                    return func_match.group(1)
            
            # JavaScript function definitions
            elif 'function ' in line or 'const ' in line:
                func_match = re.search(r'(?:function\s+(\w+)|const\s+(\w+)\s*=)', line)
                if func_match:
                    return func_match.group(1) or func_match.group(2)
            
            # C# method definitions
            elif 'public ' in line and ('(' in line or 'async ' in line):
                # Extract method name from C# method signature
                method_match = re.search(r'(?:public\s+(?:async\s+)?.*?\s+)?(\w+)\s*\(', line)
                if method_match:
                    return method_match.group(1)
            
            # Java method definitions
            elif ('public ' in line or 'private ' in line or 'protected ' in line) and '(' in line:
                method_match = re.search(r'(?:public|private|protected)\s+.*?\s+(\w+)\s*\(', line)
                if method_match:
                    return method_match.group(1)
        
        # If no function found, try to extract from the decorator line itself
        if match_line < len(lines):
            decorator_line = lines[match_line].strip()
            # For Python decorators, try to find a meaningful name
            if '@' in decorator_line:
                # Extract endpoint name and convert to function name
                endpoint_match = re.search(r'["\']([^"\']+)["\']', decorator_line)
                if endpoint_match:
                    endpoint = endpoint_match.group(1)
                    # Convert endpoint to function name
                    func_name = endpoint.replace('/', '_').replace('-', '_').replace('{', '').replace('}', '')
                    # Clean up the function name
                    func_name = re.sub(r'[^a-zA-Z0-9_]', '', func_name)
                    if func_name and not func_name.startswith('_'):
                        return func_name
        
        return "unknown_function"
    
    def _detect_framework(self, file_path: str, pattern: str) -> str:
        """Detect the framework based on file path and pattern - UNIVERSAL DETECTION."""
        file_lower = file_path.lower()
        pattern_lower = pattern.lower()
        
        # Python frameworks - Enhanced detection
        if ('fastapi' in file_lower or 
            '@app.' in pattern_lower or 
            '@router.' in pattern_lower or
            '@api_router.' in pattern_lower or
            'fastapi' in pattern_lower or
            'from fastapi' in pattern_lower or
            'import fastapi' in pattern_lower):
            return 'FastAPI'
        elif ('flask' in file_lower or 
              '@app.route' in pattern_lower or 
              '@bp.route' in pattern_lower or
              '@blueprint.route' in pattern_lower or
              'flask' in pattern_lower or
              'from flask' in pattern_lower or
              'import flask' in pattern_lower):
            return 'Flask'
        elif ('django' in file_lower or 
              'django' in pattern_lower or 
              'viewset' in pattern_lower or
              '@api_view' in pattern_lower or
              'from django' in pattern_lower or
              'import django' in pattern_lower):
            return 'Django REST Framework'
        elif ('sanic' in file_lower or 
              'sanic' in pattern_lower or
              'from sanic' in pattern_lower or
              'import sanic' in pattern_lower):
            return 'Sanic'
        elif ('bottle' in file_lower or 
              'bottle' in pattern_lower or
              'from bottle' in pattern_lower or
              'import bottle' in pattern_lower):
            return 'Bottle'
        elif ('cherrypy' in file_lower or 
              'cherrypy' in pattern_lower or
              'from cherrypy' in pattern_lower or
              'import cherrypy' in pattern_lower):
            return 'CherryPy'
        elif ('quart' in file_lower or 
              'quart' in pattern_lower or
              'from quart' in pattern_lower or
              'import quart' in pattern_lower):
            return 'Quart'
        elif ('starlette' in file_lower or 
              'starlette' in pattern_lower or
              'from starlette' in pattern_lower or
              'import starlette' in pattern_lower):
            return 'Starlette'
        
        # Java frameworks
        elif 'spring' in file_lower or '@RequestMapping' in pattern_lower or 'spring' in pattern_lower:
            return 'Spring Boot'
        elif 'jax-rs' in file_lower or '@Path' in pattern_lower or 'jax' in pattern_lower:
            return 'JAX-RS'
        elif 'jersey' in file_lower or 'jersey' in pattern_lower:
            return 'Jersey'
        
        # JavaScript/Node.js frameworks
        elif 'express' in file_lower or 'router.' in pattern_lower or 'express' in pattern_lower:
            return 'Express.js'
        elif 'koa' in file_lower or 'koa' in pattern_lower:
            return 'Koa.js'
        elif 'hapi' in file_lower or 'hapi' in pattern_lower:
            return 'Hapi.js'
        elif 'nestjs' in file_lower or '@Controller' in pattern_lower or 'nestjs' in pattern_lower:
            return 'NestJS'
        elif 'sails' in file_lower or 'sails' in pattern_lower:
            return 'Sails.js'
        
        # C# frameworks
        elif 'asp.net' in file_lower or '[Http' in pattern_lower or 'aspnet' in pattern_lower:
            return 'ASP.NET Core'
        elif 'webapi' in file_lower or 'webapi' in pattern_lower:
            return 'ASP.NET Web API'
        
        # PHP frameworks
        elif 'laravel' in file_lower or 'Route::' in pattern_lower or 'laravel' in pattern_lower:
            return 'Laravel'
        elif 'symfony' in file_lower or '@Route' in pattern_lower or 'symfony' in pattern_lower:
            return 'Symfony'
        elif 'codeigniter' in file_lower or 'codeigniter' in pattern_lower:
            return 'CodeIgniter'
        
        # Ruby frameworks
        elif 'rails' in file_lower or 'resources' in pattern_lower or 'rails' in pattern_lower:
            return 'Ruby on Rails'
        elif 'sinatra' in file_lower or 'sinatra' in pattern_lower:
            return 'Sinatra'
        
        # Go frameworks
        elif 'gin' in file_lower or 'gin' in pattern_lower:
            return 'Gin'
        elif 'echo' in file_lower or 'echo' in pattern_lower:
            return 'Echo'
        elif 'gorilla' in file_lower or 'gorilla' in pattern_lower:
            return 'Gorilla Mux'
        
        # Rust frameworks
        elif 'actix' in file_lower or 'actix' in pattern_lower:
            return 'Actix Web'
        elif 'rocket' in file_lower or 'rocket' in pattern_lower:
            return 'Rocket'
        
        # Detect by file extension
        elif file_lower.endswith('.py'):
            return 'Python'
        elif file_lower.endswith('.js') or file_lower.endswith('.ts'):
            return 'JavaScript/TypeScript'
        elif file_lower.endswith('.java'):
            return 'Java'
        elif file_lower.endswith('.cs'):
            return 'C#'
        elif file_lower.endswith('.rb'):
            return 'Ruby'
        elif file_lower.endswith('.go'):
            return 'Go'
        elif file_lower.endswith('.rs'):
            return 'Rust'
        elif file_lower.endswith('.php'):
            return 'PHP'
        elif file_lower.endswith('.swift'):
            return 'Swift'
        elif file_lower.endswith('.kt'):
            return 'Kotlin'
        else:
            return 'Unknown'
    
    def _calculate_complexity(self, content: str, match_line: int) -> float:
        """Calculate complexity score for the API function."""
        lines = content.split('\n')
        start_line = match_line
        end_line = self._find_function_end(lines, match_line)
        
        if end_line == -1:
            end_line = min(start_line + 20, len(lines))
        
        function_lines = lines[start_line:end_line]
        function_content = '\n'.join(function_lines)
        
        # Simple complexity calculation
        complexity = 0
        complexity += function_content.count('if ')
        complexity += function_content.count('for ')
        complexity += function_content.count('while ')
        complexity += function_content.count('try:')
        complexity += function_content.count('except')
        complexity += function_content.count('return')
        complexity += function_content.count('await')
        
        return min(complexity / 10.0, 10.0)  # Normalize to 0-10 scale
    
    def _find_function_end(self, lines: List[str], start_line: int) -> int:
        """Find the end of a function starting from start_line."""
        indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() == '':
                continue
            
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and line.strip():
                return i
        
        return -1
    
    def _identify_potential_issues(self, content: str, match_line: int) -> List[str]:
        """Identify potential issues in the API function."""
        issues = []
        lines = content.split('\n')
        start_line = match_line
        end_line = self._find_function_end(lines, match_line)
        
        if end_line == -1:
            end_line = min(start_line + 20, len(lines))
        
        function_content = '\n'.join(lines[start_line:end_line])
        
        # Check for common issues
        if 'db.query' in function_content and 'for ' in function_content:
            issues.append('potential_n_plus_one_query')
        
        if 'cache' not in function_content.lower():
            issues.append('no_caching')
        
        if 'validation' not in function_content.lower() and 'validate' not in function_content.lower():
            issues.append('no_validation')
        
        if 'try:' not in function_content and 'except' not in function_content:
            issues.append('no_error_handling')
        
        if 'async' in function_content and 'await' not in function_content:
            issues.append('async_without_await')
        
        return issues
    
    def _determine_risk_level(self, complexity: float, issues: List[str]) -> SeverityLevel:
        """Determine risk level based on complexity and issues."""
        risk_score = complexity
        
        # Add points for each issue
        issue_weights = {
            'potential_n_plus_one_query': 3,
            'no_caching': 2,
            'no_validation': 1,
            'no_error_handling': 2,
            'async_without_await': 1
        }
        
        for issue in issues:
            risk_score += issue_weights.get(issue, 0)
        
        if risk_score >= 7:
            return SeverityLevel.HIGH
        elif risk_score >= 4:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _extract_code_snippet(self, lines: List[str], match_line: int) -> str:
        """Extract code snippet around the match line."""
        start = max(0, match_line - 2)
        end = min(len(lines), match_line + 10)
        
        snippet_lines = lines[start:end]
        return '\n'.join(snippet_lines)
    
    def compare_apis_with_issues(self, discovered_apis: List[DiscoveredAPI], worst_apis: List[Dict]) -> Dict[str, Any]:
        """Compare discovered APIs with performance issues and provide detailed analysis."""
        try:
            logger.info(f"Comparing {len(discovered_apis)} discovered APIs with {len(worst_apis)} performance issues")
            
            matches = []
            unmatched_performance_apis = []
            unmatched_source_apis = []
            
            # Create a mapping of discovered APIs by endpoint for faster lookup
            discovered_api_map = {}
            for api in discovered_apis:
                # Normalize endpoint for comparison
                normalized_endpoint = self._normalize_endpoint(api.endpoint)
                discovered_api_map[normalized_endpoint] = api
            
            # Compare each performance API with discovered APIs
            for perf_api in worst_apis:
                perf_endpoint = perf_api.get('endpoint', '')
                normalized_perf_endpoint = self._normalize_endpoint(perf_endpoint)
                
                match_found = False
                best_match = None
                best_confidence = 0.0
                
                # Try exact match first
                if normalized_perf_endpoint in discovered_api_map:
                    best_match = discovered_api_map[normalized_perf_endpoint]
                    best_confidence = 1.0
                    match_found = True
                else:
                    # Try fuzzy matching
                    for norm_endpoint, discovered_api in discovered_api_map.items():
                        confidence = self._calculate_endpoint_similarity(normalized_perf_endpoint, norm_endpoint)
                        if confidence > best_confidence and confidence > 0.7:  # 70% similarity threshold
                            best_match = discovered_api
                            best_confidence = confidence
                            match_found = True
                
                if match_found and best_match:
                    # Create detailed match analysis
                    match_analysis = self._create_detailed_match_analysis(perf_api, best_match, best_confidence)
                    matches.append(match_analysis)
                else:
                    unmatched_performance_apis.append(perf_api)
            
            # Find unmatched source APIs
            matched_endpoints = {match['performance_api']['endpoint'] for match in matches}
            for api in discovered_apis:
                normalized_endpoint = self._normalize_endpoint(api.endpoint)
                if not any(self._normalize_endpoint(perf['endpoint']) == normalized_endpoint for perf in worst_apis):
                    unmatched_source_apis.append(api)
            
            return {
                'matches': matches,
                'unmatched_performance_apis': unmatched_performance_apis,
                'unmatched_source_apis': unmatched_source_apis,
                'summary': {
                    'total_matches': len(matches),
                    'unmatched_performance': len(unmatched_performance_apis),
                    'unmatched_source': len(unmatched_source_apis),
                    'match_rate': len(matches) / len(worst_apis) if worst_apis else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error comparing APIs with issues: {str(e)}")
            return {
                'matches': [],
                'unmatched_performance_apis': worst_apis,
                'unmatched_source_apis': discovered_apis,
                'summary': {'error': str(e)}
            }
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint for comparison by removing HTTP method and standardizing format."""
        if not endpoint:
            return ""
        
        # Remove HTTP method prefix
        normalized = re.sub(r'^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+', '', endpoint.upper())
        
        # Remove trailing slashes
        normalized = normalized.rstrip('/')
        
        # Standardize parameter formats
        normalized = re.sub(r'\{[^}]+\}', '{id}', normalized)
        
        return normalized
    
    def _calculate_endpoint_similarity(self, endpoint1: str, endpoint2: str) -> float:
        """Calculate similarity between two endpoints using various metrics."""
        if endpoint1 == endpoint2:
            return 1.0
        
        # Simple string similarity based on common parts
        parts1 = set(endpoint1.split('/'))
        parts2 = set(endpoint2.split('/'))
        
        if not parts1 or not parts2:
            return 0.0
        
        intersection = parts1.intersection(parts2)
        union = parts1.union(parts2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_detailed_match_analysis(self, perf_api: Dict, discovered_api: DiscoveredAPI, confidence: float) -> Dict[str, Any]:
        """Create detailed analysis for a matched API pair."""
        try:
            # Analyze performance issues
            performance_issues = self._analyze_performance_issues(perf_api)
            
            # Generate code improvements
            code_improvements = self._generate_code_improvements(discovered_api, performance_issues)
            
            # Generate specific code suggestions
            code_suggestions = self._generate_code_suggestions(discovered_api, performance_issues)
            
            return {
                'performance_api': perf_api,
                'source_api': {
                    'endpoint': discovered_api.endpoint,
                    'file_path': discovered_api.file_path,
                    'function_name': discovered_api.function_name,
                    'line_number': discovered_api.line_number,
                    'framework': discovered_api.framework,
                    'complexity_score': discovered_api.complexity_score,
                    'risk_level': discovered_api.risk_level.value,
                    'potential_issues': discovered_api.potential_issues,
                    'code_snippet': discovered_api.code_snippet
                },
                'match_confidence': confidence,
                'performance_analysis': performance_issues,
                'improvements': code_improvements,
                'code_suggestions': code_suggestions,
                'recommended_actions': self._generate_recommended_actions(performance_issues, code_improvements)
            }
            
        except Exception as e:
            logger.error(f"Error creating detailed match analysis: {str(e)}")
            return {
                'performance_api': perf_api,
                'source_api': discovered_api.dict(),
                'match_confidence': confidence,
                'error': str(e)
            }
    
    def _analyze_performance_issues(self, perf_api: Dict) -> Dict[str, Any]:
        """Analyze performance issues from the performance API data."""
        issues = []
        severity = "MEDIUM"
        
        # Analyze response time
        avg_response_time = perf_api.get('avg_response_time_ms', 0)
        if avg_response_time > 1000:  # > 1 second
            issues.append({
                'type': 'slow_response',
                'description': f'Average response time is {avg_response_time}ms, which is slow',
                'severity': 'HIGH' if avg_response_time > 3000 else 'MEDIUM',
                'impact': 'Poor user experience and potential timeouts'
            })
            severity = 'HIGH' if avg_response_time > 3000 else 'MEDIUM'
        
        # Analyze error rate
        error_rate = perf_api.get('error_rate_percent', 0)
        if error_rate > 5:  # > 5% error rate
            issues.append({
                'type': 'high_error_rate',
                'description': f'Error rate is {error_rate}%, which is high',
                'severity': 'CRITICAL' if error_rate > 20 else 'HIGH',
                'impact': 'Service reliability issues and user frustration'
            })
            severity = 'CRITICAL' if error_rate > 20 else 'HIGH'
        
        # Analyze throughput
        throughput = perf_api.get('throughput_rps', 0)
        if throughput < 10:  # < 10 requests per second
            issues.append({
                'type': 'low_throughput',
                'description': f'Throughput is {throughput} RPS, which is low',
                'severity': 'MEDIUM',
                'impact': 'Scalability concerns and potential bottlenecks'
            })
        
        return {
            'issues': issues,
            'overall_severity': severity,
            'summary': f'Found {len(issues)} performance issues with {severity} severity'
        }
    
    def _generate_code_improvements(self, discovered_api: DiscoveredAPI, performance_issues: Dict) -> List[Dict[str, Any]]:
        """Generate specific code improvements based on the discovered API and performance issues."""
        improvements = []
        
        # Add caching if response time is slow
        if any(issue['type'] == 'slow_response' for issue in performance_issues['issues']):
            improvements.append({
                'type': 'caching',
                'title': 'Add Response Caching',
                'description': 'Implement caching to reduce response time',
                'priority': 'HIGH',
                'implementation': 'Add Redis or in-memory caching for frequently accessed data',
                'code_example': '''
// Example: Add caching to your controller
[HttpGet]
[ResponseCache(Duration = 300)] // Cache for 5 minutes
public async Task<IActionResult> GetEmployees()
{
    var cacheKey = "employees_all";
    if (!_cache.TryGetValue(cacheKey, out var employees))
    {
        employees = await _service.GetAllEmployeesAsync();
        _cache.Set(cacheKey, employees, TimeSpan.FromMinutes(5));
    }
    return Ok(employees);
}'''
            })
        
        # Add async/await if not present
        if 'no_async' in discovered_api.potential_issues:
            improvements.append({
                'type': 'async_processing',
                'title': 'Convert to Async/Await',
                'description': 'Use async/await for better scalability',
                'priority': 'MEDIUM',
                'implementation': 'Convert synchronous methods to async and use async database calls',
                'code_example': '''
// Before
public IActionResult GetEmployees()
{
    var employees = _dbContext.Employees.ToList();
    return Ok(employees);
}

// After
public async Task<IActionResult> GetEmployees()
{
    var employees = await _dbContext.Employees.ToListAsync();
    return Ok(employees);
}'''
            })
        
        # Add error handling
        if 'no_error_handling' in discovered_api.potential_issues:
            improvements.append({
                'type': 'error_handling',
                'title': 'Add Comprehensive Error Handling',
                'description': 'Implement proper error handling and logging',
                'priority': 'HIGH',
                'implementation': 'Add try-catch blocks and proper error responses',
                'code_example': '''
[HttpGet]
public async Task<IActionResult> GetEmployees()
{
    try
    {
        var employees = await _service.GetAllEmployeesAsync();
        return Ok(employees);
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Error retrieving employees");
        return StatusCode(500, "Internal server error");
    }
}'''
            })
        
        # Add validation
        if 'no_validation' in discovered_api.potential_issues:
            improvements.append({
                'type': 'validation',
                'title': 'Add Input Validation',
                'description': 'Implement proper input validation',
                'priority': 'MEDIUM',
                'implementation': 'Add model validation and data annotations',
                'code_example': '''
[HttpPost]
public async Task<IActionResult> CreateEmployee([FromBody] CreateEmployeeDto dto)
{
    if (!ModelState.IsValid)
        return BadRequest(ModelState);
    
    // Additional validation
    if (string.IsNullOrEmpty(dto.Name))
        return BadRequest("Name is required");
    
    var employee = await _service.CreateEmployeeAsync(dto);
    return CreatedAtAction(nameof(GetEmployee), new { id = employee.Id }, employee);
}'''
            })
        
        return improvements
    
    def _generate_code_suggestions(self, discovered_api: DiscoveredAPI, performance_issues: Dict) -> List[str]:
        """Generate specific code suggestions for the discovered API."""
        suggestions = []
        
        # Performance optimization suggestions
        if any(issue['type'] == 'slow_response' for issue in performance_issues['issues']):
            suggestions.extend([
                "Consider implementing database query optimization",
                "Add pagination for large datasets",
                "Use database indexes on frequently queried columns",
                "Implement connection pooling for database connections"
            ])
        
        # Error handling suggestions
        if 'no_error_handling' in discovered_api.potential_issues:
            suggestions.extend([
                "Add try-catch blocks around database operations",
                "Implement proper logging for debugging",
                "Return appropriate HTTP status codes",
                "Add input validation and sanitization"
            ])
        
        # General suggestions
        suggestions.extend([
            "Consider adding API documentation with Swagger/OpenAPI",
            "Implement rate limiting to prevent abuse",
            "Add monitoring and health checks",
            "Consider using DTOs for data transfer"
        ])
        
        return suggestions
    
    def _generate_recommended_actions(self, performance_issues: Dict, improvements: List[Dict]) -> List[str]:
        """Generate recommended actions based on analysis."""
        actions = []
        
        # High priority actions
        high_priority_improvements = [imp for imp in improvements if imp['priority'] == 'HIGH']
        if high_priority_improvements:
            actions.append(f"Immediately implement {len(high_priority_improvements)} high-priority improvements")
        
        # Performance actions
        if any(issue['type'] == 'slow_response' for issue in performance_issues['issues']):
            actions.append("Conduct performance testing and profiling")
            actions.append("Review database queries and add indexes if needed")
        
        # Monitoring actions
        actions.append("Set up monitoring and alerting for this API")
        actions.append("Create performance benchmarks and track improvements")
        
        return actions
