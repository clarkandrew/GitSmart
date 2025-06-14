import os
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from diskcache import Cache
import logging

from .config import logger, DEBUG
from .utils import get_git_root

"""
Repository Manager Module

This module provides persistent repository tracking and management capabilities
for GitSmart. It allows the system to:

1. Discover and register git repositories
2. Store repository metadata persistently
3. Switch between different repositories
4. Locate repositories by name from any directory
5. Maintain repository-specific configurations

The repository manager uses a global cache to store repository information
and provides methods to work with multiple repositories seamlessly.
"""


class RepositoryManager:
    """
    Manages multiple git repositories with persistent storage and discovery.

    This class handles:
    - Repository discovery and registration
    - Persistent storage of repository metadata
    - Repository switching and location
    - Cross-directory repository operations
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the repository manager with persistent cache."""

        # Use global cache directory or create one in user's home
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.gitsmart/repositories")

        os.makedirs(cache_dir, exist_ok=True)
        self.cache = Cache(cache_dir)
        self.cache_dir = cache_dir

        # Current active repository
        self._current_repo = None

        # Initialize logger
        self.logger = logger

    def discover_repository(self, path: str = None) -> Optional[Dict[str, str]]:
        """
        Discover git repository information from a given path.

        Args:
            path: Path to search for git repository. If None, uses current directory.

        Returns:
            Dictionary with repository information or None if no git repo found.
        """
        try:
            original_cwd = os.getcwd()

            if path:
                if not os.path.exists(path):
                    self.logger.error(f"Path does not exist: {path}")
                    return None
                os.chdir(path)

            # Get git root directory
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True
            )
            repo_root = result.stdout.strip()

            # Get repository name (directory name)
            repo_name = os.path.basename(repo_root)

            # Get remote URL if available
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                remote_url = result.stdout.strip()
            except subprocess.CalledProcessError:
                remote_url = None

            # Get current branch
            try:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                current_branch = result.stdout.strip()
            except subprocess.CalledProcessError:
                current_branch = "main"

            # Get repository status
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                has_changes = bool(result.stdout.strip())
            except subprocess.CalledProcessError:
                has_changes = False

            repo_info = {
                "name": repo_name,
                "path": repo_root,
                "remote_url": remote_url,
                "current_branch": current_branch,
                "has_changes": has_changes,
                "discovered_at": os.getcwd(),
                "last_accessed": None
            }

            if DEBUG:
                self.logger.debug(f"Discovered repository: {repo_info}")

            return repo_info

        except subprocess.CalledProcessError as e:
            if DEBUG:
                self.logger.debug(f"No git repository found in {path or os.getcwd()}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error discovering repository: {e}")
            return None
        finally:
            os.chdir(original_cwd)

    def register_repository(self, repo_info: Dict[str, str] = None, path: str = None) -> bool:
        """
        Register a repository in the persistent cache.

        Args:
            repo_info: Repository information dictionary. If None, discovers from path.
            path: Path to discover repository from. If None, uses current directory.

        Returns:
            True if registration successful, False otherwise.
        """
        try:
            if repo_info is None:
                repo_info = self.discover_repository(path)
                if repo_info is None:
                    return False

            repo_name = repo_info["name"]
            repo_path = repo_info["path"]

            # Check for name conflicts
            existing_repos = self.list_repositories()
            for existing_name, existing_info in existing_repos.items():
                if existing_name != repo_name and existing_info["path"] == repo_path:
                    # Same path, different name - update name
                    self.logger.warning(f"Repository path {repo_path} already registered as '{existing_name}', updating to '{repo_name}'")
                    self.cache.delete(existing_name)
                elif existing_name == repo_name and existing_info["path"] != repo_path:
                    # Same name, different path - create unique name
                    counter = 1
                    original_name = repo_name
                    while repo_name in existing_repos:
                        repo_name = f"{original_name}_{counter}"
                        counter += 1
                    repo_info["name"] = repo_name
                    self.logger.warning(f"Repository name conflict resolved: using '{repo_name}' instead of '{original_name}'")

            # Add registration timestamp
            import time
            repo_info["registered_at"] = time.time()
            repo_info["last_accessed"] = time.time()

            # Store in cache
            self.cache[repo_name] = repo_info

            if DEBUG:
                self.logger.debug(f"Registered repository '{repo_name}' at {repo_path}")

            return True

        except Exception as e:
            self.logger.error(f"Error registering repository: {e}")
            return False

    def get_repository(self, repo_name: str) -> Optional[Dict[str, str]]:
        """
        Get repository information by name.

        Args:
            repo_name: Name of the repository to retrieve.

        Returns:
            Repository information dictionary or None if not found.
        """
        try:
            repo_info = self.cache.get(repo_name)
            if repo_info:
                # Update last accessed time
                import time
                repo_info["last_accessed"] = time.time()
                self.cache[repo_name] = repo_info

                # Verify the repository still exists
                if not os.path.exists(repo_info["path"]):
                    self.logger.warning(f"Repository path no longer exists: {repo_info['path']}")
                    return None

                return repo_info
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving repository '{repo_name}': {e}")
            return None

    def list_repositories(self) -> Dict[str, Dict[str, str]]:
        """
        List all registered repositories.

        Returns:
            Dictionary mapping repository names to their information.
        """
        try:
            repositories = {}
            for key in self.cache:
                try:
                    repo_info = self.cache[key]
                    if isinstance(repo_info, dict) and "path" in repo_info:
                        # Verify repository still exists
                        if os.path.exists(repo_info["path"]):
                            repositories[key] = repo_info
                        else:
                            # Clean up non-existent repositories
                            self.logger.warning(f"Removing non-existent repository: {key}")
                            self.cache.delete(key)
                except Exception as e:
                    self.logger.error(f"Error reading repository {key}: {e}")
                    continue

            return repositories
        except Exception as e:
            self.logger.error(f"Error listing repositories: {e}")
            return {}

    def remove_repository(self, repo_name: str) -> bool:
        """
        Remove a repository from the registry.

        Args:
            repo_name: Name of the repository to remove.

        Returns:
            True if removal successful, False otherwise.
        """
        try:
            if repo_name in self.cache:
                del self.cache[repo_name]
                if DEBUG:
                    self.logger.debug(f"Removed repository '{repo_name}' from registry")
                return True
            else:
                self.logger.warning(f"Repository '{repo_name}' not found in registry")
                return False
        except Exception as e:
            self.logger.error(f"Error removing repository '{repo_name}': {e}")
            return False

    def set_current_repository(self, repo_name: str) -> bool:
        """
        Set the current active repository.

        Args:
            repo_name: Name of the repository to set as current.

        Returns:
            True if successful, False otherwise.
        """
        try:
            repo_info = self.get_repository(repo_name)
            if repo_info:
                self._current_repo = repo_info
                # Store current repo in cache for persistence
                self.cache["_current_repo"] = repo_name
                if DEBUG:
                    self.logger.debug(f"Set current repository to '{repo_name}'")
                return True
            else:
                self.logger.error(f"Repository '{repo_name}' not found")
                return False
        except Exception as e:
            self.logger.error(f"Error setting current repository: {e}")
            return False

    def get_current_repository(self) -> Optional[Dict[str, str]]:
        """
        Get the current active repository.

        Returns:
            Current repository information or None if no current repo set.
        """
        try:
            if self._current_repo:
                return self._current_repo

            # Try to load from cache
            current_repo_name = self.cache.get("_current_repo")
            if current_repo_name:
                repo_info = self.get_repository(current_repo_name)
                if repo_info:
                    self._current_repo = repo_info
                    return repo_info

            # Try to discover from current directory
            repo_info = self.discover_repository()
            if repo_info:
                # Auto-register and set as current
                if self.register_repository(repo_info):
                    self.set_current_repository(repo_info["name"])
                    return repo_info

            return None
        except Exception as e:
            self.logger.error(f"Error getting current repository: {e}")
            return None

    def switch_to_repository(self, repo_name: str) -> Tuple[bool, Optional[str]]:
        """
        Switch to a repository and change working directory.

        Args:
            repo_name: Name of the repository to switch to.

        Returns:
            Tuple of (success, previous_directory)
        """
        try:
            previous_dir = os.getcwd()

            repo_info = self.get_repository(repo_name)
            if not repo_info:
                return False, previous_dir

            repo_path = repo_info["path"]
            if not os.path.exists(repo_path):
                self.logger.error(f"Repository path does not exist: {repo_path}")
                return False, previous_dir

            os.chdir(repo_path)
            self.set_current_repository(repo_name)

            if DEBUG:
                self.logger.debug(f"Switched to repository '{repo_name}' at {repo_path}")

            return True, previous_dir
        except Exception as e:
            self.logger.error(f"Error switching to repository '{repo_name}': {e}")
            return False, os.getcwd()

    def find_repository_by_name_or_path(self, identifier: str) -> Optional[Dict[str, str]]:
        """
        Find repository by name or path.

        Args:
            identifier: Repository name or path to search for.

        Returns:
            Repository information if found, None otherwise.
        """
        try:
            # First try as exact name match
            repo_info = self.get_repository(identifier)
            if repo_info:
                return repo_info

            # Try as partial name match
            repositories = self.list_repositories()
            for repo_name, repo_data in repositories.items():
                if identifier.lower() in repo_name.lower():
                    return repo_data

            # Try as path match
            identifier_path = os.path.abspath(os.path.expanduser(identifier))
            for repo_name, repo_data in repositories.items():
                if os.path.abspath(repo_data["path"]) == identifier_path:
                    return repo_data

            # Try to discover if it's a valid path
            if os.path.exists(identifier):
                discovered = self.discover_repository(identifier)
                if discovered:
                    # Auto-register discovered repository
                    if self.register_repository(discovered):
                        return discovered

            return None
        except Exception as e:
            self.logger.error(f"Error finding repository '{identifier}': {e}")
            return None

    def update_repository_status(self, repo_name: str = None) -> bool:
        """
        Update repository status information.

        Args:
            repo_name: Repository name to update. If None, updates current repository.

        Returns:
            True if update successful, False otherwise.
        """
        try:
            if repo_name is None:
                current_repo = self.get_current_repository()
                if not current_repo:
                    return False
                repo_name = current_repo["name"]

            repo_info = self.get_repository(repo_name)
            if not repo_info:
                return False

            # Temporarily switch to repository to get updated status
            original_cwd = os.getcwd()
            try:
                os.chdir(repo_info["path"])
                updated_info = self.discover_repository(repo_info["path"])
                if updated_info:
                    # Preserve registration metadata
                    updated_info["registered_at"] = repo_info.get("registered_at")
                    updated_info["last_accessed"] = repo_info.get("last_accessed")

                    # Update cache
                    self.cache[repo_name] = updated_info

                    # Update current repo if it's the same
                    if self._current_repo and self._current_repo["name"] == repo_name:
                        self._current_repo = updated_info

                    return True
            finally:
                os.chdir(original_cwd)

            return False
        except Exception as e:
            self.logger.error(f"Error updating repository status: {e}")
            return False

    def auto_discover_repositories(self, search_paths: List[str] = None) -> List[Dict[str, str]]:
        """
        Automatically discover repositories in common locations.

        Args:
            search_paths: List of paths to search. If None, uses common locations.

        Returns:
            List of discovered repository information dictionaries.
        """
        if search_paths is None:
            # Common repository locations
            home = os.path.expanduser("~")
            search_paths = [
                os.path.join(home, "projects"),
                os.path.join(home, "dev"),
                os.path.join(home, "src"),
                os.path.join(home, "code"),
                os.path.join(home, "git"),
                os.path.join(home, "Documents", "projects"),
                os.path.join(home, "workspace"),
                "/usr/local/src",
                "/opt/projects"
            ]

        discovered_repos = []

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            try:
                # Search for .git directories
                for root, dirs, files in os.walk(search_path):
                    if ".git" in dirs:
                        try:
                            repo_info = self.discover_repository(root)
                            if repo_info:
                                discovered_repos.append(repo_info)
                                # Auto-register discovered repositories
                                self.register_repository(repo_info)
                        except Exception as e:
                            if DEBUG:
                                self.logger.debug(f"Error discovering repo in {root}: {e}")
                            continue

                    # Don't recurse into .git directories
                    if ".git" in dirs:
                        dirs.remove(".git")

            except Exception as e:
                self.logger.error(f"Error searching path {search_path}: {e}")
                continue

        if DEBUG:
            self.logger.debug(f"Auto-discovered {len(discovered_repos)} repositories")

        return discovered_repos

    def get_repository_stats(self) -> Dict[str, any]:
        """
        Get statistics about registered repositories.

        Returns:
            Dictionary with repository statistics.
        """
        try:
            repositories = self.list_repositories()

            stats = {
                "total_repositories": len(repositories),
                "repositories_with_changes": 0,
                "repositories_with_remotes": 0,
                "most_recent_access": None,
                "branches": {},
                "cache_size": len(self.cache),
                "cache_location": self.cache_dir
            }

            most_recent_time = 0

            for repo_name, repo_info in repositories.items():
                # Count repositories with changes
                if repo_info.get("has_changes"):
                    stats["repositories_with_changes"] += 1

                # Count repositories with remotes
                if repo_info.get("remote_url"):
                    stats["repositories_with_remotes"] += 1

                # Track branch usage
                branch = repo_info.get("current_branch", "unknown")
                stats["branches"][branch] = stats["branches"].get(branch, 0) + 1

                # Find most recent access
                last_accessed = repo_info.get("last_accessed", 0)
                if last_accessed > most_recent_time:
                    most_recent_time = last_accessed
                    stats["most_recent_access"] = repo_name

            return stats
        except Exception as e:
            self.logger.error(f"Error getting repository stats: {e}")
            return {"error": str(e)}

    def export_repositories(self, file_path: str = None) -> bool:
        """
        Export repository registry to a JSON file.

        Args:
            file_path: Path to export file. If None, uses default location.

        Returns:
            True if export successful, False otherwise.
        """
        try:
            if file_path is None:
                file_path = os.path.join(self.cache_dir, "repositories_backup.json")

            repositories = self.list_repositories()

            export_data = {
                "export_timestamp": time.time(),
                "gitsmart_version": "1.1.0",
                "repositories": repositories
            }

            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            self.logger.info(f"Exported {len(repositories)} repositories to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting repositories: {e}")
            return False

    def import_repositories(self, file_path: str) -> bool:
        """
        Import repository registry from a JSON file.

        Args:
            file_path: Path to import file.

        Returns:
            True if import successful, False otherwise.
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Import file does not exist: {file_path}")
                return False

            with open(file_path, 'r') as f:
                import_data = json.load(f)

            repositories = import_data.get("repositories", {})
            imported_count = 0

            for repo_name, repo_info in repositories.items():
                # Verify repository still exists
                if os.path.exists(repo_info.get("path", "")):
                    self.cache[repo_name] = repo_info
                    imported_count += 1
                else:
                    self.logger.warning(f"Skipped importing non-existent repository: {repo_name}")

            self.logger.info(f"Imported {imported_count} repositories from {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error importing repositories: {e}")
            return False


# Global repository manager instance
_repo_manager = None


def get_repo_manager() -> RepositoryManager:
    """Get the global repository manager instance."""
    global _repo_manager
    if _repo_manager is None:
        _repo_manager = RepositoryManager()
    return _repo_manager


def get_current_repo_info() -> Optional[Dict[str, str]]:
    """Get current repository information."""
    manager = get_repo_manager()
    return manager.get_current_repository()


def switch_to_repo(repo_name: str) -> Tuple[bool, Optional[str]]:
    """Switch to a specific repository."""
    manager = get_repo_manager()
    return manager.switch_to_repository(repo_name)


def register_current_repo() -> bool:
    """Register the current directory as a repository."""
    manager = get_repo_manager()
    return manager.register_repository()


def list_all_repos() -> Dict[str, Dict[str, str]]:
    """List all registered repositories."""
    manager = get_repo_manager()
    return manager.list_repositories()


def find_repo(identifier: str) -> Optional[Dict[str, str]]:
    """Find repository by name or path."""
    manager = get_repo_manager()
    return manager.find_repository_by_name_or_path(identifier)
