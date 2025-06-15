#!/usr/bin/env python3
"""
Unit tests for the enhanced push functionality in GitSmart.

Tests the new branch and remote selection features that allow users to:
1. Select which branch to push (current, local, or remote branches)
2. Select which remote(s) to push to
3. Get enhanced error handling and user feedback

These tests ensure the functionality works correctly while maintaining
the high code quality standards that prevent maintenance nightmares.
"""

import unittest
import subprocess
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock, call
import sys

# Add GitSmart to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from GitSmart.git_utils import (
    get_current_branch,
    get_all_branches,
    get_git_remotes,
    push_to_remote
)


class TestEnhancedPush(unittest.TestCase):
    """Test cases for enhanced push functionality."""

    def setUp(self):
        """Set up test environment."""
        self.original_dir = os.getcwd()
        self.test_dir = tempfile.mkdtemp(prefix="gitsmart_test_")
        os.chdir(self.test_dir)

        # Initialize a test git repository
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create initial commit
        with open("test.txt", "w") as f:
            f.write("test content")
        subprocess.run(["git", "add", "test.txt"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_get_current_branch_success(self):
        """Test successful retrieval of current branch."""
        branch = get_current_branch()
        self.assertIsNotNone(branch)
        self.assertIsInstance(branch, str)
        self.assertTrue(len(branch) > 0)

    @patch('GitSmart.git_utils.subprocess.run')
    def test_get_current_branch_failure(self, mock_run):
        """Test handling of git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        branch = get_current_branch()
        self.assertIsNone(branch)

    def test_get_all_branches_basic(self):
        """Test basic branch retrieval."""
        branches = get_all_branches()

        self.assertIsInstance(branches, dict)
        self.assertIn('local', branches)
        self.assertIn('remote', branches)
        self.assertIsInstance(branches['local'], list)
        self.assertIsInstance(branches['remote'], list)

        # Should at least have master/main branch
        self.assertTrue(len(branches['local']) >= 1)

    def test_get_all_branches_with_multiple_branches(self):
        """Test branch retrieval with multiple local branches."""
        # Create additional branches
        subprocess.run(["git", "checkout", "-b", "feature/test"], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "hotfix/urgent"], check=True, capture_output=True)

        branches = get_all_branches()

        # Should have at least the branches we created plus master
        self.assertTrue(len(branches['local']) >= 3)

        expected_branches = ["feature/test", "hotfix/urgent"]
        for expected in expected_branches:
            self.assertIn(expected, branches['local'])

    @patch('GitSmart.git_utils.subprocess.run')
    def test_get_all_branches_failure(self, mock_run):
        """Test handling of branch command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        branches = get_all_branches()
        self.assertEqual(branches, {"local": [], "remote": []})

    def test_get_git_remotes_no_remotes(self):
        """Test remote retrieval when no remotes are configured."""
        remotes = get_git_remotes()

        self.assertIsInstance(remotes, dict)
        self.assertEqual(len(remotes), 0)

    def test_get_git_remotes_with_remotes(self):
        """Test remote retrieval with configured remotes."""
        # Add test remotes
        subprocess.run([
            "git", "remote", "add", "origin",
            "https://github.com/test/repo.git"
        ], check=True, capture_output=True)

        subprocess.run([
            "git", "remote", "add", "upstream",
            "https://github.com/upstream/repo.git"
        ], check=True, capture_output=True)

        remotes = get_git_remotes()

        self.assertIsInstance(remotes, dict)
        self.assertEqual(len(remotes), 2)
        self.assertIn("origin", remotes)
        self.assertIn("upstream", remotes)
        self.assertEqual(remotes["origin"], "https://github.com/test/repo.git")
        self.assertEqual(remotes["upstream"], "https://github.com/upstream/repo.git")

    @patch('GitSmart.git_utils.subprocess.run')
    def test_get_git_remotes_failure(self, mock_run):
        """Test handling of remote command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        remotes = get_git_remotes()
        self.assertEqual(remotes, {})

    @patch('GitSmart.git_utils.subprocess.run')
    def test_push_to_remote_success_with_branch(self, mock_run):
        """Test successful push with specific branch."""
        mock_run.return_value = MagicMock()

        result = push_to_remote("origin", "https://github.com/test/repo.git", "main")

        self.assertIn("Successfully", result)
        self.assertIn("main", result)
        self.assertIn("origin", result)

        # Verify the correct command was called
        mock_run.assert_called_once_with(["git", "push", "origin", "main"], check=True)

    @patch('GitSmart.git_utils.subprocess.run')
    def test_push_to_remote_success_current_branch(self, mock_run):
        """Test successful push without specifying branch (current branch)."""
        mock_run.return_value = MagicMock()

        result = push_to_remote("origin", "https://github.com/test/repo.git")

        self.assertIn("Successfully", result)
        self.assertIn("origin", result)

        # Verify the correct command was called
        mock_run.assert_called_once_with(["git", "push", "origin"], check=True)

    @patch('GitSmart.git_utils.subprocess.run')
    def test_push_to_remote_failure_with_branch(self, mock_run):
        """Test push failure with specific branch."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git push')

        result = push_to_remote("origin", "https://github.com/test/repo.git", "main")

        self.assertIn("Failed", result)
        self.assertIn("main", result)
        self.assertIn("origin", result)

    @patch('GitSmart.git_utils.subprocess.run')
    def test_push_to_remote_failure_current_branch(self, mock_run):
        """Test push failure without specifying branch."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git push')

        result = push_to_remote("origin", "https://github.com/test/repo.git")

        self.assertIn("Failed", result)
        self.assertIn("origin", result)

    def test_branch_parsing_with_current_indicator(self):
        """Test that branch parsing correctly handles current branch indicator."""
        # Switch to a different branch
        subprocess.run(["git", "checkout", "-b", "test-branch"], check=True, capture_output=True)

        branches = get_all_branches()
        current = get_current_branch()

        # Current branch should be in the local branches list
        self.assertIn(current, branches['local'])
        self.assertEqual(current, "test-branch")

    def test_remote_branch_parsing(self):
        """Test parsing of remote branches when they exist."""
        # Add a remote and fetch (simulate remote branches)
        subprocess.run([
            "git", "remote", "add", "test-remote",
            "https://github.com/test/repo.git"
        ], check=True, capture_output=True)

        # Create a mock remote branch reference
        remote_ref_dir = os.path.join(self.test_dir, ".git", "refs", "remotes", "test-remote")
        os.makedirs(remote_ref_dir, exist_ok=True)

        # Write a ref file to simulate a remote branch
        with open(os.path.join(remote_ref_dir, "main"), "w") as f:
            f.write("abc123def456\n")

        # The function should handle this gracefully even if no actual remote branches
        branches = get_all_branches()
        self.assertIsInstance(branches['remote'], list)

    def test_integration_branch_and_remote_selection(self):
        """Test integration of branch and remote selection."""
        # Set up multiple branches and remotes
        subprocess.run(["git", "checkout", "-b", "feature"], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "hotfix"], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/test/repo.git"], check=True)
        subprocess.run(["git", "remote", "add", "fork", "https://github.com/user/repo.git"], check=True)

        # Get current state
        current_branch = get_current_branch()
        all_branches = get_all_branches()
        remotes = get_git_remotes()

        # Verify we have the expected state
        self.assertEqual(current_branch, "hotfix")
        self.assertTrue(len(all_branches['local']) >= 3)  # master, feature, hotfix
        self.assertEqual(len(remotes), 2)

        # Verify branch selection would work
        self.assertIn("feature", all_branches['local'])
        self.assertIn("hotfix", all_branches['local'])

        # Verify remote selection would work
        self.assertIn("origin", remotes)
        self.assertIn("fork", remotes)

    def test_edge_case_empty_branch_name(self):
        """Test handling of edge cases in branch names."""
        with patch('GitSmart.git_utils.subprocess.run') as mock_run:
            # Mock empty branch name response
            mock_run.return_value = MagicMock()
            mock_run.return_value.stdout = "  \n"

            branch = get_current_branch()
            self.assertIsNone(branch)

    def test_edge_case_malformed_remote_output(self):
        """Test handling of malformed remote command output."""
        with patch('GitSmart.git_utils.subprocess.run') as mock_run:
            # Mock malformed remote output
            mock_run.return_value = MagicMock()
            mock_run.return_value.stdout = "malformed\noutput\nwithout\nproper\nformat\n"

            remotes = get_git_remotes()
            # Should handle gracefully and return empty dict or partial results
            self.assertIsInstance(remotes, dict)

    def test_branch_with_special_characters(self):
        """Test handling of branch names with special characters."""
        # Create branch with special characters (common in feature branches)
        special_branch = "feature/JIRA-123_fix-urgent-bug"
        subprocess.run(["git", "checkout", "-b", special_branch], check=True, capture_output=True)

        current = get_current_branch()
        branches = get_all_branches()

        self.assertEqual(current, special_branch)
        self.assertIn(special_branch, branches['local'])

    def test_performance_with_many_branches(self):
        """Test performance doesn't degrade with many branches."""
        # Create multiple branches to test performance
        for i in range(10):
            subprocess.run([
                "git", "checkout", "-b", f"test-branch-{i}"
            ], check=True, capture_output=True)

        # Should complete quickly and return all branches
        branches = get_all_branches()
        self.assertTrue(len(branches['local']) >= 11)  # original + 10 new branches


class TestEnhancedPushIntegration(unittest.TestCase):
    """Integration tests for the enhanced push functionality."""

    def test_cli_flow_integration(self):
        """Test that the enhanced functions integrate properly with cli_flow."""
        # This test ensures our new functions can be imported and used
        # in the context they'll be used in cli_flow.py

        from GitSmart.git_utils import (
            get_current_branch,
            get_all_branches,
            get_git_remotes,
            push_to_remote
        )

        # Verify functions exist and are callable
        self.assertTrue(callable(get_current_branch))
        self.assertTrue(callable(get_all_branches))
        self.assertTrue(callable(get_git_remotes))
        self.assertTrue(callable(push_to_remote))

        # Verify function signatures
        import inspect

        # get_current_branch should take no required parameters
        sig = inspect.signature(get_current_branch)
        self.assertEqual(len(sig.parameters), 0)

        # get_all_branches should take no required parameters
        sig = inspect.signature(get_all_branches)
        self.assertEqual(len(sig.parameters), 0)

        # get_git_remotes should take no required parameters
        sig = inspect.signature(get_git_remotes)
        self.assertEqual(len(sig.parameters), 0)

        # push_to_remote should take remote, url, and optional branch
        sig = inspect.signature(push_to_remote)
        params = list(sig.parameters.keys())
        self.assertIn('remote', params)
        self.assertIn('url', params)
        self.assertIn('branch', params)

        # branch parameter should be optional (have default)
        branch_param = sig.parameters['branch']
        self.assertTrue(branch_param.default is None)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
