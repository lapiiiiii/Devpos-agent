from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JiraClient:
    def __init__(
        self,
        url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        self.url = url
        self.email = email
        self.api_token = api_token
        self._client = None

    async def initialize(self):
        if self.url and self.email and self.api_token:
            try:
                from jira import JIRA
                options = {"server": self.url}
                self._client = JIRA(
                    options,
                    basic_auth=(self.email, self.api_token)
                )
                logger.info("Jira client initialized")
            except ImportError:
                logger.warning("python-jira not installed, using mock mode")
            except Exception as e:
                logger.error(f"Error initializing Jira client: {e}")

    async def get_issues(
        self,
        project: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        if self._client:
            try:
                jql = "updated >= -30d"
                if project:
                    jql += f' AND project = "{project}"'
                if status:
                    jql += f' AND status = "{status}"'
                issues = self._client.search_issues(
                    jql, maxResults=limit, fields="summary,description,status,labels,created,updated"
                )
                return [
                    {
                        "id": issue.id,
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "description": getattr(issue.fields, 'description', '') or '',
                        "status": issue.fields.status.name,
                        "labels": getattr(issue.fields, 'labels', []) or [],
                        "created": issue.fields.created,
                        "updated": issue.fields.updated,
                    }
                    for issue in issues
                ]
            except Exception as e:
                logger.error(f"Error fetching Jira issues: {e}")
        return self._mock_issues()

    async def get_bugs(self, project: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        issues = await self.get_issues(project=project, limit=limit * 2)
        bugs = [i for i in issues if 'bug' in str(i.get('labels', [])).lower()]
        return bugs[:limit]

    async def get_issue_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        if self._client:
            try:
                issue = self._client.issue(key)
                return {
                    "id": issue.id,
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "description": getattr(issue.fields, 'description', '') or '',
                    "status": issue.fields.status.name,
                    "labels": getattr(issue.fields, 'labels', []) or [],
                    "created": issue.fields.created,
                    "updated": issue.fields.updated,
                }
            except Exception as e:
                logger.error(f"Error fetching Jira issue {key}: {e}")
        mock_issues = self._mock_issues()
        for issue in mock_issues:
            if issue.get("key") == key:
                return issue
        return None

    def _mock_issues(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "10001",
                "key": "PROJ-101",
                "summary": "Login page renders blank on Safari",
                "description": "Users report that the login page shows a blank screen when using Safari browser. Steps to reproduce: 1. Open Safari 2. Navigate to login page 3. Page appears blank",
                "status": "To Do",
                "labels": ["bug", "browser-safari", "priority-high"],
                "created": "2026-04-01T10:00:00.000Z",
                "updated": "2026-04-03T15:30:00.000Z",
            },
            {
                "id": "10002",
                "key": "PROJ-102",
                "summary": "Add dark mode theme",
                "description": "Feature request to add dark mode support to the application for better user experience in low-light conditions.",
                "status": "In Progress",
                "labels": ["enhancement", "ui", "priority-medium"],
                "created": "2026-03-28T09:00:00.000Z",
                "updated": "2026-04-02T11:20:00.000Z",
            },
            {
                "id": "10003",
                "key": "PROJ-103",
                "summary": "API response time degradation",
                "description": "Performance monitoring shows increased API response times over the past week. Need to investigate root cause.",
                "status": "Done",
                "labels": ["performance", "investigation"],
                "created": "2026-03-25T14:00:00.000Z",
                "updated": "2026-04-01T16:45:00.000Z",
            },
            {
                "id": "10004",
                "key": "PROJ-104",
                "summary": "Memory leak in background worker",
                "description": "Background worker process shows continuous memory growth over time, leading to eventual OOM errors.",
                "status": "To Do",
                "labels": ["bug", "performance", "priority-critical"],
                "created": "2026-04-04T08:30:00.000Z",
                "updated": "2026-04-04T08:30:00.000Z",
            },
        ]
