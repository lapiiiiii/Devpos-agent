from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ):
        self.token = token
        self.owner = owner
        self.repo = repo
        self._client = None

    async def initialize(self):
        if self.token and not self._client:
            try:
                from github import Github
                self._client = Github(self.token)
                logger.info("GitHub client initialized")
            except ImportError:
                logger.warning("PyGithub not installed, using mock mode")

    def get_repo(self):
        if self._client and self.owner and self.repo:
            return self._client.get_repo(f"{self.owner}/{self.repo}")
        return None

    async def get_issues(self, state: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
        repo = self.get_repo()
        if not repo:
            return self._mock_issues()
        try:
            issues = repo.get_issues(state=state, sort="updated", direction="desc")
            return [
                {
                    "id": issue.id,
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body or "",
                    "state": issue.state,
                    "labels": [l.name for l in issue.labels],
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                }
                for issue in list(issues)[:limit]
            ]
        except Exception as e:
            logger.error(f"Error fetching issues: {e}")
            return self._mock_issues()

    async def get_commits(self, limit: int = 50) -> List[Dict[str, Any]]:
        repo = self.get_repo()
        if not repo:
            return self._mock_commits()
        try:
            commits = repo.get_commits()
            return [
                {
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date.isoformat(),
                    "url": commit.html_url,
                }
                for commit in list(commits)[:limit]
            ]
        except Exception as e:
            logger.error(f"Error fetching commits: {e}")
            return self._mock_commits()

    async def get_pulls(self, state: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
        repo = self.get_repo()
        if not repo:
            return self._mock_pulls()
        try:
            pulls = repo.get_pulls(state=state, sort="updated", direction="desc")
            return [
                {
                    "id": pr.id,
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body or "",
                    "state": pr.state,
                    "user": pr.user.login,
                    "labels": [l.name for l in pr.labels],
                    "created_at": pr.created_at.isoformat(),
                    "merged": pr.merged,
                }
                for pr in list(pulls)[:limit]
            ]
        except Exception as e:
            logger.error(f"Error fetching pulls: {e}")
            return self._mock_pulls()

    async def get_pr_diff(self, pr_number: int) -> str:
        repo = self.get_repo()
        if not repo:
            return self._mock_pr_diff()
        try:
            pr = repo.get_pull(pr_number)
            files = pr.get_files()
            diff_content = []
            for f in files:
                diff_content.append(f"### File: {f.filename}\n```diff\n{f.patch}\n```")
            return "\n\n".join(diff_content)
        except Exception as e:
            logger.error(f"Error fetching PR diff: {e}")
            return self._mock_pr_diff()

    async def scan_pr_security(self, pr_number: int) -> Dict[str, Any]:
        diff = await self.get_pr_diff(pr_number)

        sensitive_patterns = {
            "env文件": r"\.env",
            "密码": r"password\s*=\s*['\"][^'\"]+['\"]",
            "API_Token": r"api[_-]?token\s*=\s*['\"][^'\"]+['\"]",
            "GitHub_Token": r"ghp_[a-zA-Z0-9]+|github_pat_[a-zA-Z0-9]+",
            "AWS密钥": r"AKIA[0-9A-Z]{16}",
            "私钥": r"-----BEGIN.*PRIVATE KEY-----",
            "数据库连接": r"(mongodb|mysql|postgresql)://[^@]+@",
            "内部IP": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
            "身份证": r"\d{17}[\dXx]",
            "手机号": r"1[3-9]\d{9}",
            "邮箱": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        }

        findings = []
        for pattern_name, pattern in sensitive_patterns.items():
            import re
            matches = re.finditer(pattern, diff, re.IGNORECASE)
            for match in matches:
                context = diff[max(0, match.start()-50):min(len(diff), match.end()+50)]
                findings.append({
                    "type": pattern_name,
                    "matched": match.group(),
                    "context": f"...{context}...",
                })

        return {
            "pr_number": pr_number,
            "total_findings": len(findings),
            "risk_level": "high" if len(findings) > 0 else "low",
            "findings": findings,
        }

    async def get_workflow_runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        repo = self.get_repo()
        if not repo:
            return self._mock_workflow_runs()
        try:
            runs = repo.get_workflow_runs()
            return [
                {
                    "id": run.id,
                    "name": run.name,
                    "status": run.status,
                    "conclusion": run.conclusion,
                    "branch": run.head_branch,
                    "commit": run.head_sha,
                    "created_at": run.created_at.isoformat(),
                    "updated_at": run.updated_at.isoformat(),
                }
                for run in list(runs)[:limit]
            ]
        except Exception as e:
            logger.error(f"Error fetching workflow runs: {e}")
            return self._mock_workflow_runs()

    def _mock_issues(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": 1,
                "number": 101,
                "title": "Login page not loading on Safari",
                "body": "Bug description: Users report login page fails to load on Safari browser",
                "state": "open",
                "labels": ["bug", "browser-compatibility"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": 2,
                "number": 102,
                "title": "Add dark mode support",
                "body": "Feature request for dark mode theme",
                "state": "open",
                "labels": ["enhancement", "ui"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        ]

    def _mock_commits(self) -> List[Dict[str, Any]]:
        return [
            {
                "sha": "abc123def456",
                "message": "Fix: resolve login timeout issue on Safari",
                "author": "developer1",
                "date": datetime.now().isoformat(),
                "url": "https://github.com/example/repo/commit/abc123",
            },
            {
                "sha": "def456ghi789",
                "message": "Feat: add dark mode toggle component",
                "author": "developer2",
                "date": datetime.now().isoformat(),
                "url": "https://github.com/example/repo/commit/def456",
            },
        ]

    def _mock_pr_diff(self) -> str:
        return """### File: config.py
```diff
+ API_KEY = "sk-1234567890abcdef"
+ password = "admin123"
```

### File: .env
```diff
+ DATABASE_URL=mysql://user:password123@localhost:3306/db
+ SECRET_KEY=my-secret-key-12345
```

### File: utils.py
```diff
+ phone = "13800138000"
+ email = "user@company.internal.com"
```"""

    def _mock_pulls(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": 1,
                "number": 45,
                "title": "Fix login timeout bug",
                "body": "This PR fixes the login timeout issue on Safari",
                "state": "open",
                "user": "developer1",
                "labels": ["bug", "urgent"],
                "created_at": datetime.now().isoformat(),
                "merged": False,
            },
        ]

    def _mock_workflow_runs(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": 1001,
                "name": "CI Pipeline",
                "status": "completed",
                "conclusion": "success",
                "branch": "main",
                "commit": "abc123",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": 1002,
                "name": "CI Pipeline",
                "status": "completed",
                "conclusion": "failure",
                "branch": "feature/login-fix",
                "commit": "def456",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        ]
