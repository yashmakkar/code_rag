import aiohttp
import asyncio
from aiohttp import ClientSession
from urllib.parse import urlparse
from typing import List, Optional
from src.utils.config import config
from src.utils.data_config import ALLOWED_FILE_EXTENSIONS, ALLOWED_FILE_SIZE


class Github:
    """
    Async Github client to fetch repository metadata and download files.
    """

    def __init__(self, repo_url: str):
        self.owner: Optional[str] = None
        self.repo: Optional[str] = None
        self.default_branch: Optional[str] = None
        self._extract_owner_and_repo(repo_url)

    def _extract_owner_and_repo(self, repo_url: str) -> None:
        """
        Parse repository URL or `owner/repo` string into components.
        """
        if "github.com" in repo_url:
            path = urlparse(repo_url).path.strip("/")
            parts = path.split("/")
        else:
            parts = repo_url.strip("/").split("/")

        if len(parts) != 2 or not all(parts):
            raise ValueError(
                f"Invalid GitHub repo format: {repo_url}. "
                "Expected 'owner/repo' or a GitHub URL."
            )
        self.owner, self.repo = parts

    async def _get_default_branch(self, session: ClientSession) -> str:
        """
        Fetch the default branch of the repository from GitHub API.
        """
        if self.default_branch:
            return self.default_branch

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": config.user_agent,
        }
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        async with session.get(url, headers=headers, ssl=False) as resp:
            if resp.status != 200:
                raise ValueError(
                    f"Failed to fetch repository info ({resp.status}). "
                    "Ensure the repo URL is correct and public."
                )
            repo_json = await resp.json()
            self.default_branch = repo_json.get("default_branch", "main")
        return self.default_branch

    async def _download_content(self, session: ClientSession, url: str) -> Optional[str]:
        """
        Download raw file content from GitHub.
        Returns None if request fails.
        """
        try:
            async with session.get(url, ssl=False) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception:
            pass
        return None

    async def get_all_useful_files(self) -> List[str]:
        """
        Fetch list of useful files based on allowed extensions and size constraints.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": config.user_agent,
        }

        async with aiohttp.ClientSession() as session:
            branch = await self._get_default_branch(session=session)

            url = (
                f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/"
                f"{branch}?recursive=1"
            )
            async with session.get(url, headers=headers, ssl=False) as resp:
                if resp.status != 200:
                    raise ValueError(
                        f"Failed to fetch repo tree ({resp.status})."
                    )
                tree = (await resp.json()).get("tree", [])

            useful_files = [
                node["path"]
                for node in tree
                if node.get("type") == "blob"
                and node.get("size", 0) <= ALLOWED_FILE_SIZE
                and any(node["path"].endswith(ext) for ext in ALLOWED_FILE_EXTENSIONS)
            ]

        return useful_files

    async def download_useful_files(self, useful_files: List[str]) -> List[Optional[str]]:
        """
        Download raw content of the given useful files in parallel.
        """
        if not useful_files:
            return []

        async with aiohttp.ClientSession() as session:
            branch = await self._get_default_branch(session=session)
            base_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{branch}/"

            tasks = [
                self._download_content(session, f"{base_url}{file_path}")
                for file_path in useful_files
            ]
            raw_code = await asyncio.gather(*tasks)
        return raw_code
