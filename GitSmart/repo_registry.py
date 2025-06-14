"""
Repository Registry for GitSmart

This module manages a persistent registry of Git repositories that GitSmart has worked with,
enabling it to find and operate on the correct repository regardless of the current working directory.

Features:
- Persistent storage of repository information
- Repository discovery and registration
- Multi-repository management
- Path resolution and validation
- Repository switching and selection
"""

import os
import json
import hashlib
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from diskcache import Cache

from .config import logger, DEBUG
from .utils import get_git_root


@dataclass
class RepositoryInfo:
    """Information about a tracked repository."""
    name: str
    path: str
    remote_url: Optional[str]
    last_accessed: float
    created_at: float
    branch_count: int
    commit_count: int
    file_count: int
    repo_id: str  # Unique identifier based on remote URL or path hash
    aliases: List[str]  # Alternative names for this repo

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepositoryInfo':
        """Create from dictionary."""
        return cls(**data)


class RepositoryRegistry:
    """
    Manages a persistent registry of Git repositories.

    The registry stores information about repositories that GitSmart has worked with,
    allowing it to find and operate on the correct repository even when run from
    different directories.
    """

    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize the repository registry.

        Args:
            registry_path: Custom path for registry storage. If None, uses default.
        """
        if registry_path:
            self.registry_dir = Path(registry_path)
        else:
            # Use user's home directory for cross-session persistence
            self.registry_dir = Path.home() / ".gitsmart" / "registry"

        self.registry_dir.mkdir(parents=True, exist_ok=True)

        # Use diskcache for persistent storage
        self.cache = Cache(str(self.registry_dir / "repo_cache"))

        # Registry file for backup/export
        self.registry_file = self.registry_dir / "repositories.json"

        # Current active repository
        self._current_repo: Optional[RepositoryInfo] = None

        # Load existing registry
        self._load_registry()

    def _load_registry(self):
        """Load the repository registry from persistent storage."""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)

                # Migrate data to cache if needed
                for repo_id, repo_data in data.get('repositories', {}).items():
                    if repo_id not in self.cache:
                        repo_info = RepositoryInfo.from_dict(repo_data)
                        self.cache[repo_id] = repo_info

                if DEBUG:
                    logger.debug(f"Loaded {len(data.get('repositories', {}))} repositories from registry")

        except Exception as e:
            if DEBUG:
                logger.error(f"Error loading registry: {e}")

    def _save_registry(self):
        """Save the repository registry to persistent storage."""
        try:
            # Export cache to JSON for backup
            data = {
                'version': '1.0',
                'last_updated': time.time(),
                'repositories': {}
            }

            for repo_id in self.cache:
                repo_info = self.cache[repo_id]
                if isinstance(repo_info, RepositoryInfo):
                    data['repositories'][repo_id] = repo_info.to_dict()

            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)

            if DEBUG:
                logger.debug(f"Saved {len(data['repositories'])} repositories to registry")

        except Exception as e:
            if DEBUG:
                logger.error(f"Error saving registry: {e}")

    def _generate_repo_id(self, repo_path: str, remote_url: Optional[str] = None) -> str:
        """
        Generate a unique repository ID.

        Args:
            repo_path: Path to the repository
            remote_url: Remote URL if available

        Returns:
            Unique repository identifier
        """
        if remote_url:
            # Use remote URL hash for remote repositories
            return hashlib.sha256(remote_url.encode()).hexdigest()[:16]
        else:
            # Use path hash for local repositories
            abs_path = os.path.abspath(repo_path)
            return hashlib.sha256(abs_path.encode()).hexdigest()[:16]

    def _get_repo_stats(self, repo_path: str) -> Tuple[int, int, int]:
        """
        Get repository statistics.

        Args:
            repo_path: Path to the repository

        Returns:
            Tuple of (branch_count, commit_count, file_count)
        """
        try:
            os.chdir(repo_path)

            # Count branches
            branch_result = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True, text=True, check=True
            )
            branch_count = len([line for line in branch_result.stdout.split('\n') if line.strip()])

            # Count commits
            commit_result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, check=True
            )
            commit_count = int(commit_result.stdout.strip())

            # Count tracked files
            file_result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True, text=True, check=True
            )
            file_count = len([line for line in file_result.stdout.split('\n') if line.strip()])

            return branch_count, commit_count, file_count

        except Exception as e:
            if DEBUG:
                logger.error(f"Error getting repo stats: {e}")
            return 0, 0, 0

    def _get_remote_url(self, repo_path: str) -> Optional[str]:
        """
        Get the remote URL for a repository.

        Args:
            repo_path: Path to the repository

        Returns:
            Remote URL or None if not available
        """
        try:
            os.chdir(repo_path)
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _extract_repo_name(self, repo_path: str, remote_url: Optional[str] = None) -> str:
        """
        Extract a meaningful repository name.

        Args:
            repo_path: Path to the repository
            remote_url: Remote URL if available

        Returns:
            Repository name
        """
        if remote_url:
            # Extract name from remote URL
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]

            # Handle different URL formats
            if '/' in remote_url:
                return remote_url.split('/')[-1]
            else:
                return remote_url
        else:
            # Use directory name
            return os.path.basename(os.path.abspath(repo_path))

    def discover_repository(self, search_path: Optional[str] = None) -> Optional[RepositoryInfo]:
        """
        Discover and register a Git repository.

        Args:
            search_path: Path to search for repository. If None, uses current directory.

        Returns:
            RepositoryInfo if repository found and registered, None otherwise
        """
        try:
            original_cwd = os.getcwd()

            if search_path:
                os.chdir(search_path)

            # Try to find git root
            repo_path = get_git_root()
            if not repo_path:
                return None

            os.chdir(repo_path)

            # Get repository information
            remote_url = self._get_remote_url(repo_path)
            repo_id = self._generate_repo_id(repo_path, remote_url)

            # Check if already registered
            if repo_id in self.cache:
                repo_info = self.cache[repo_id]
                # Update last accessed time
                repo_info.last_accessed = time.time()
                self.cache[repo_id] = repo_info
                self._save_registry()

                if DEBUG:
                    logger.debug(f"Found existing repository: {repo_info.name}")

                return repo_info

            # Register new repository
            repo_name = self._extract_repo_name(repo_path, remote_url)
            branch_count, commit_count, file_count = self._get_repo_stats(repo_path)

            repo_info = RepositoryInfo(
                name=repo_name,
                path=repo_path,
                remote_url=remote_url,
                last_accessed=time.time(),
                created_at=time.time(),
                branch_count=branch_count,
                commit_count=commit_count,
                file_count=file_count,
                repo_id=repo_id,
                aliases=[]
            )

            # Store in registry
            self.cache[repo_id] = repo_info
            self._save_registry()

            if DEBUG:
                logger.debug(f"Registered new repository: {repo_name} at {repo_path}")

            return repo_info

        except Exception as e:
            if DEBUG:
                logger.error(f"Error discovering repository: {e}")
            return None
        finally:
            try:
                os.chdir(original_cwd)
            except:
                pass

    def register_repository_by_name(self, repo_name: str, repo_path: str) -> Optional[RepositoryInfo]:
        """
        Manually register a repository with a specific name.

        Args:
            repo_name: Name to assign to the repository
            repo_path: Path to the repository

        Returns:
            RepositoryInfo if successfully registered, None otherwise
        """
        try:
            # Validate that it's a git repository
            if not os.path.exists(os.path.join(repo_path, '.git')):
                if DEBUG:
                    logger.error(f"Not a git repository: {repo_path}")
                return None

            original_cwd = os.getcwd()
            os.chdir(repo_path)

            remote_url = self._get_remote_url(repo_path)
            repo_id = self._generate_repo_id(repo_path, remote_url)

            # Check if already exists
            if repo_id in self.cache:
                repo_info = self.cache[repo_id]
                # Update name if different
                if repo_info.name != repo_name:
                    if repo_name not in repo_info.aliases:
                        repo_info.aliases.append(repo_info.name)
                    repo_info.name = repo_name
                    repo_info.last_accessed = time.time()
                    self.cache[repo_id] = repo_info
                    self._save_registry()
                return repo_info

            # Create new registration
            branch_count, commit_count, file_count = self._get_repo_stats(repo_path)

            repo_info = RepositoryInfo(
                name=repo_name,
                path=os.path.abspath(repo_path),
                remote_url=remote_url,
                last_accessed=time.time(),
                created_at=time.time(),
                branch_count=branch_count,
                commit_count=commit_count,
                file_count=file_count,
                repo_id=repo_id,
                aliases=[]
            )

            self.cache[repo_id] = repo_info
            self._save_registry()

            if DEBUG:
                logger.debug(f"Manually registered repository: {repo_name} at {repo_path}")

            return repo_info

        except Exception as e:
            if DEBUG:
                logger.error(f"Error registering repository {repo_name}: {e}")
            return None
        finally:
            try:
                os.chdir(original_cwd)
            except:
                pass

    def find_repository_by_name(self, name: str) -> Optional[RepositoryInfo]:
        """
        Find a repository by name or alias.

        Args:
            name: Repository name or alias to search for

        Returns:
            RepositoryInfo if found, None otherwise
        """
        for repo_id in self.cache:
            repo_info = self.cache[repo_id]
            if isinstance(repo_info, RepositoryInfo):
                if (repo_info.name.lower() == name.lower() or
                    name.lower() in [alias.lower() for alias in repo_info.aliases]):
                    # Update last accessed
                    repo_info.last_accessed = time.time()
                    self.cache[repo_id] = repo_info
                    return repo_info

        return None

    def find_repository_by_path(self, path: str) -> Optional[RepositoryInfo]:
        """
        Find a repository by path.

        Args:
            path: Repository path to search for

        Returns:
            RepositoryInfo if found, None otherwise
        """
        abs_path = os.path.abspath(path)

        for repo_id in self.cache:
            repo_info = self.cache[repo_id]
            if isinstance(repo_info, RepositoryInfo):
                if os.path.abspath(repo_info.path) == abs_path:
                    # Update last accessed
                    repo_info.last_accessed = time.time()
                    self.cache[repo_id] = repo_info
                    return repo_info

        return None

    def list_repositories(self) -> List[RepositoryInfo]:
        """
        List all registered repositories.

        Returns:
            List of RepositoryInfo objects sorted by last accessed time
        """
        repos = []
        for repo_id in self.cache:
            repo_info = self.cache[repo_id]
            if isinstance(repo_info, RepositoryInfo):
                repos.append(repo_info)

        # Sort by last accessed (most recent first)
        repos.sort(key=lambda x: x.last_accessed, reverse=True)
        return repos

    def get_current_repository(self) -> Optional[RepositoryInfo]:
        """
        Get the currently active repository.

        Returns:
            Current RepositoryInfo or None if no repository is active
        """
        return self._current_repo

    def set_current_repository(self, repo_info: RepositoryInfo) -> bool:
        """
        Set the currently active repository and change to its directory.

        Args:
            repo_info: Repository to make active

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(repo_info.path):
                if DEBUG:
                    logger.error(f"Repository path does not exist: {repo_info.path}")
                return False

            os.chdir(repo_info.path)
            self._current_repo = repo_info

            # Update last accessed
            repo_info.last_accessed = time.time()
            self.cache[repo_info.repo_id] = repo_info
            self._save_registry()

            if DEBUG:
                logger.debug(f"Changed to repository: {repo_info.name} at {repo_info.path}")

            return True

        except Exception as e:
            if DEBUG:
                logger.error(f"Error setting current repository: {e}")
            return False

    def switch_to_repository(self, identifier: str) -> Optional[RepositoryInfo]:
        """
        Switch to a repository by name, alias, or path.

        Args:
            identifier: Repository name, alias, or path

        Returns:
            RepositoryInfo if successful, None otherwise
        """
        # First try by name
        repo_info = self.find_repository_by_name(identifier)

        # If not found, try by path
        if not repo_info:
            repo_info = self.find_repository_by_path(identifier)

        # If still not found, try to discover at the given path
        if not repo_info and os.path.exists(identifier):
            repo_info = self.discover_repository(identifier)

        if repo_info and self.set_current_repository(repo_info):
            return repo_info

        return None

    def remove_repository(self, identifier: str) -> bool:
        """
        Remove a repository from the registry.

        Args:
            identifier: Repository name, alias, or repo_id

        Returns:
            True if removed, False if not found
        """
        # Find the repository
        repo_info = self.find_repository_by_name(identifier)

        if not repo_info:
            # Try to find by repo_id
            if identifier in self.cache:
                repo_info = self.cache[identifier]

        if repo_info:
            del self.cache[repo_info.repo_id]
            self._save_registry()

            if self._current_repo and self._current_repo.repo_id == repo_info.repo_id:
                self._current_repo = None

            if DEBUG:
                logger.debug(f"Removed repository: {repo_info.name}")

            return True

        return False

    def add_alias(self, repo_identifier: str, alias: str) -> bool:
        """
        Add an alias to a repository.

        Args:
            repo_identifier: Repository name or ID
            alias: Alias to add

        Returns:
            True if successful, False otherwise
        """
        repo_info = self.find_repository_by_name(repo_identifier)

        if repo_info and alias not in repo_info.aliases:
            repo_info.aliases.append(alias)
            self.cache[repo_info.repo_id] = repo_info
            self._save_registry()

            if DEBUG:
                logger.debug(f"Added alias '{alias}' to repository {repo_info.name}")

            return True

        return False

    def update_repository_stats(self, repo_info: RepositoryInfo) -> bool:
        """
        Update repository statistics.

        Args:
            repo_info: Repository to update

        Returns:
            True if successful, False otherwise
        """
        try:
            original_cwd = os.getcwd()

            if self.set_current_repository(repo_info):
                branch_count, commit_count, file_count = self._get_repo_stats(repo_info.path)

                repo_info.branch_count = branch_count
                repo_info.commit_count = commit_count
                repo_info.file_count = file_count
                repo_info.last_accessed = time.time()

                self.cache[repo_info.repo_id] = repo_info
                self._save_registry()

                return True

            return False

        except Exception as e:
            if DEBUG:
                logger.error(f"Error updating repository stats: {e}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except:
                pass

    def cleanup_invalid_repositories(self) -> int:
        """
        Remove repositories that no longer exist on disk.

        Returns:
            Number of repositories removed
        """
        invalid_repos = []

        for repo_id in self.cache:
            repo_info = self.cache[repo_id]
            if isinstance(repo_info, RepositoryInfo):
                if not os.path.exists(repo_info.path):
                    invalid_repos.append(repo_id)

        for repo_id in invalid_repos:
            del self.cache[repo_id]

        if invalid_repos:
            self._save_registry()

            if DEBUG:
                logger.debug(f"Cleaned up {len(invalid_repos)} invalid repositories")

        return len(invalid_repos)

    def export_registry(self, export_path: str) -> bool:
        """
        Export the registry to a JSON file.

        Args:
            export_path: Path to export the registry

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'version': '1.0',
                'exported_at': time.time(),
                'repositories': {}
            }

            for repo_id in self.cache:
                repo_info = self.cache[repo_id]
                if isinstance(repo_info, RepositoryInfo):
                    data['repositories'][repo_id] = repo_info.to_dict()

            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2)

            if DEBUG:
                logger.debug(f"Exported registry to {export_path}")

            return True

        except Exception as e:
            if DEBUG:
                logger.error(f"Error exporting registry: {e}")
            return False

    def import_registry(self, import_path: str) -> bool:
        """
        Import repositories from a JSON file.

        Args:
            import_path: Path to import the registry from

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)

            imported_count = 0
            for repo_id, repo_data in data.get('repositories', {}).items():
                repo_info = RepositoryInfo.from_dict(repo_data)

                # Only import if path still exists
                if os.path.exists(repo_info.path):
                    self.cache[repo_id] = repo_info
                    imported_count += 1

            self._save_registry()

            if DEBUG:
                logger.debug(f"Imported {imported_count} repositories from {import_path}")

            return True

        except Exception as e:
            if DEBUG:
                logger.error(f"Error importing registry: {e}")
            return False


# Global registry instance
_registry_instance: Optional[RepositoryRegistry] = None


def get_repository_registry() -> RepositoryRegistry:
    """Get the global repository registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = RepositoryRegistry()
    return _registry_instance


def ensure_repository_context(repo_name: Optional[str] = None) -> Optional[RepositoryInfo]:
    """
    Ensure we're working in the correct repository context.

    This function:
    1. If repo_name is provided, switches to that repository
    2. If no repo_name, tries to discover current repository
    3. If discovery fails, uses the last accessed repository

    Args:
        repo_name: Optional repository name to switch to

    Returns:
        RepositoryInfo of the active repository, or None if no repository available
    """
    registry = get_repository_registry()

    # If repo_name is specified, try to switch to it
    if repo_name:
        repo_info = registry.switch_to_repository(repo_name)
        if repo_info:
            return repo_info
        else:
            if DEBUG:
                logger.error(f"Could not find repository: {repo_name}")
            return None

    # Try to discover current repository
    repo_info = registry.discover_repository()
    if repo_info:
        registry.set_current_repository(repo_info)
        return repo_info

    # Fall back to most recently accessed repository
    repos = registry.list_repositories()
    if repos:
        most_recent = repos[0]  # Already sorted by last_accessed
        if registry.set_current_repository(most_recent):
            if DEBUG:
                logger.debug(f"Using most recent repository: {most_recent.name}")
            return most_recent

    # No repository available
    if DEBUG:
        logger.error("No repository context available")
    return None
