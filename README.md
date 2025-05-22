<h1 align="center"><strong>GitSmart</strong></h1>
<h2 align="center"><em>The AI-Powered Git Commit Assistant</em></h2>

<div align="center">
  <img src="assets/no-bg.png" alt="GitSmart Overview Image">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/build-passing-brightgreen" alt="Build Status">
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
</p>

---

**GitSmart** is an open-source Command Line Interface (CLI) tool that leverages Artificial Intelligence (AI) to automate the creation of meaningful Git commit messages. By analyzing the changes you've made, **GitSmart** generates concise and standardized commit messages, making it easier to track changes and collaborate with others.

<div align="center">
  <img src="assets/cc.png" alt="GitSmart Overview Image">
</div>

---

## Why You'd Need GitSmart

#### **Streamlined Workflow**

- **Automated Commit Messages**: Automatically generate precise commit messages, saving time and reducing manual effort.

#### **Consistent Version History**

- **Standardized Messages**: Ensure a clean and organized commit history, making it easier for project tracking, management, and debugging.

#### **Seamless Integration**

- **User-Friendly CLI**: Simplify your Git workflow with an interactive command-line interface designed for efficiency and ease of use.

#### **Enhanced Code Reviews**

- **Accurate Summaries**: Produce commit messages that precisely reflect changes, enhancing code review processes and collaboration.

#### **Custom AI Integration**

- **Adaptive AI Insights**: Choose from leading language models like OpenAI, Anthropic, or Llama to get tailored AI assistance. This customization adapts to your coding style and preferences, significantly enhancing how you summarize and interpret code differences.

---

## **Key Features**

- **AI-Powered Commit Messages**: Automatically generate meaningful and standardized commit messages based on your code changes.
- **Track Changes**: Maintain a detailed history of modifications to your codebase.
- **Revert to Previous Versions**: Easily roll back to earlier states of your project.
- **Branch and Merge**: Experiment with new ideas without affecting the main project branch.
- **Collaborate Seamlessly**: Work with others by merging changes and resolving conflicts efficiently.

---

## **AI-driven Chain-of-Thought Analysis for Deep Understanding of Any Change**

```shell
╭─────────────────────────────────── assets/no-bg.png [Staged] ────────────────────────────────────╮
│                                                                                                  │
│                       1 diff --git a/assets/no-bg.png b/assets/no-bg.png                         │
│                       2 new file mode 100644                                                     │
│                       3 index 0000000..caa7508                                                   │
│                       4 Binary files /dev/null and b/assets/no-bg.png differ                     │
│                                                                                                  │
╰───────────────────────────────────────────── +0, -0 ─────────────────────────────────────────────╯
```

```markdown
**Step-by-Step Thinking:**

1. **Observations**:
   - The `README.md` file has been modified to update an image link.
   - Specifically, the `GitSmart Overview Image` source has changed from `assets/comit.png` to `assets/no-bg.png`.
   - A new file, `no-bg.png`, has been added to the `assets` directory.
   - The nature of the change suggests a visual update, potentially for aesthetic or branding reasons.

2. **Rationale**:
   - Chosen Icon: 💄 (for UI improvements, as the change affects the visual aspect of the project)
   - Theme: Update of graphical asset for potential branding or layout adjustments.

<COMMIT_MESSAGE>
💄 Update README Image Asset

**WHAT:** Replaced `comit.png` with `no-bg.png` in README.md
**WHY:** Refresh project's visual identity by updating the GitSmart Overview Image to a new version without background (`no-bg.png`), enhancing overall UI consistency and appeal.

**DETAILS:**
- **Affected File(s):**
  - `README.md`: Updated image link to reflect new asset.
  - `assets/no-bg.png`: Newly added image file, replacing the original `comit.png`.
- **Impact:** This change modernizes the project's front-facing visuals in the README, ensuring a more engaging and up-to-date first impression for visitors.
</COMMIT_MESSAGE>
```

---

## **Getting Started**

### 1. Clone the Repository

```bash
git clone https://github.com/clarkandrew/GitSmart.git
```

### 2. **Install Dependencies**

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. **Configure the Application**

Rename the example configuration file and update it with your API credentials:

```bash
mv example.config.ini config.ini
```

Edit `config.ini`:

```ini
[API]
auth_token = YOUR_API_TOKEN
api_url = https://api.yourservice.com/v1/chat/completions
model = your-model-name
max_tokens = 500
temperature = 0.7
```

### 4. **Run GitSmart**

To use **GitSmart** from any Git directory, add it to your system's PATH:

#### a. Make the Script Executable

```bash
chmod +x /path/to/GitSmart/src/main.py
```

#### b. Add GitSmart to PATH

Add the following line to your shell configuration file (e.g., `.bashrc`, `.zshrc`):

```bash
export PATH=$PATH:/path/to/GitSmart/src
```

Reload your shell configuration:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

#### c. Execute GitSmart

In your Git repository, run:

```bash
GitSmart
```

Follow the on-screen prompts to generate and commit your changes.

---

<div align="center">
  <img src="assets/bb.png" alt="GitSmart Overview Image">
</div>

---

## **Version History and Changelog**

### [1.0.0] - 2023-10-01

- Initial release with core features:
  - AI-powered commit message generation.
  - Interactive staging and unstaging of files.
  - Git diff visualization within the CLI.

### [0.9.0] - 2023-09-15

- Beta release with basic commit generation capabilities.

---

## **Release Roadmap**

### Upcoming Features

- **1.1.0**
  - Support for multiple AI service providers.
  - Customizable commit message templates.

- **1.2.0**
  - Graphical User Interface (GUI) for users who prefer not to use the command line.
  - Enhanced diff visualization with syntax highlighting.

- **1.3.0**
  - Compatibility with other version control systems (e.g., Mercurial, SVN).
  - Multi-language support for commit messages.

---

## **Technical Implementation**

### Installation Procedures for Windows, macOS, and Linux

1. **Install Python and Git**

   - **Python**: Download from the [official website](https://www.python.org/downloads/).
   - **Git**: Download from the [official website](https://git-scm.com/downloads).

2. **Follow the Quick Start Guide**

   Proceed with cloning the repository and installing dependencies as outlined above.

### Environment Configuration Requirements

- **Python Packages**: Ensure all packages in `requirements.txt` are installed.
- **API Credentials**: Valid `auth_token` and `api_url` in `config.ini`.
- **Network Access**: Internet connection is required for API calls.

### API Reference

#### Function: `generate_commit_message(diff: str) -> str`

Generates a commit message using the AI service.

**Parameters**

- `diff` (str): The Git diff of staged changes.

**Returns**

- `str`: The generated commit message.

**Example**

```python
diff = get_git_diff(staged=True)
commit_message = generate_commit_message(diff)
print(commit_message)
```

### Integration Patterns and Best Practices

- **Secure API Credentials**: Keep your `config.ini` file out of version control (add it to `.gitignore`).
- **Automate with Git Hooks**: Integrate **GitSmart** into your Git workflow using pre-commit hooks.
- **Regular Updates**: Periodically update dependencies for security and performance improvements.

### Performance Optimization Guidelines

- **Limit Diff Size**: Stage only relevant changes to reduce processing time.
- **Adjust AI Settings**: Modify `max_tokens` and `temperature` in `config.ini` to balance performance and output quality.
- **Cache Responses**: Implement caching if you frequently regenerate commit messages for the same changes.

### Troubleshooting Guide

#### Common Issues and Solutions

- **API Authentication Errors**
  - *Solution*: Verify your `auth_token` and `api_url` in `config.ini`.

- **No Staged Changes Detected**
  - *Solution*: Stage your changes using `git add <file>` before running **GitSmart**.

- **Network Timeouts**
  - *Solution*: Check your internet connection and firewall settings.

### Known Limitations and Workarounds

- **Large Diffs**
  - *Limitation*: Processing very large diffs may slow down the AI response.
  - *Workaround*: Commit changes in smaller batches.

- **API Rate Limits**
  - *Limitation*: Exceeding API limits may result in errors.
  - *Workaround*: Monitor your usage or upgrade your API plan.

---

## **Community Engagement**

### Contribution Workflow and Guidelines

We welcome contributions from developers of all experience levels!

1. **Fork the Repository**

   Click the "Fork" button at the top right corner of the GitHub page.

2. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Commit Your Changes**

   ```bash
   git commit -m "Description of your changes"
   ```

4. **Push to Your Fork**

   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request**

   Submit your pull request for review.

### Development Setup Guide

#### Setting Up the Development Environment

1. **Clone Your Fork**

   ```bash
   git clone https://github.com/yourusername/GitSmart.git
   cd GitSmart
   ```

2. **Install Development Dependencies**

   ```bash
   pip install -r dev-requirements.txt
   ```

3. **Run Tests**

   ```bash
   pytest
   ```

### Code Review Standards

- **Adhere to PEP 8**: Follow Python's style guidelines for clean and readable code.
- **Write Tests**: Include unit tests for any new features or bug fixes.
- **Update Documentation**: Ensure that any changes are reflected in the documentation.

### Issue and PR Templates

When creating issues or pull requests, please use the provided templates to include all necessary information.

### Security Disclosure Process

If you discover a security vulnerability, please contact us directly at [security@yourdomain.com](mailto:security@yourdomain.com) instead of opening a public issue.

### Licensing Details

This project is licensed under the [MIT License](LICENSE).

### Support Channels and SLAs

- **GitHub Issues**: For bug reports and feature requests.
- **Email Support**: [support@yourdomain.com](mailto:support@yourdomain.com)
- **Response Time**: We aim to respond within 2 business days.

### Code of Conduct

We are committed to fostering a welcoming community. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) for more information.

---

## **Before and After: Transforming Your Git Commits with GitSmart**

**Before:**

Your Git commit messages are a tangled mess—full of vague descriptions like "fix stuff" or "update files," making it hard to track changes and collaborate effectively.

**After:**

Run **GitSmart** and enjoy the perks of AI-powered commit messages that are clear, standardized, and meaningful. Effortlessly track changes, collaborate seamlessly, and maintain a professional project history without the hassle.

---

## **Glossary**

- **AI (Artificial Intelligence)**: Technology that enables computers to perform tasks that typically require human intelligence.
- **API (Application Programming Interface)**: A set of rules that allows programs to communicate with each other.
- **CLI (Command Line Interface)**: A text-based interface used to interact with software.
- **Commit**: A record of changes made to files in a Git repository.
- **Diff**: A display showing the changes between two versions of a file.
- **Git**: A version control system for tracking changes in files and coordinating work on those files among multiple people.
- **Staging**: The process of selecting changes to include in the next commit.
- **Unstaging**: Removing changes from the staging area.
- **Version Control System**: Software that helps manage changes to source code over time.

---

**Start transforming your Git workflow today with GitSmart. Enhance your productivity, improve collaboration, and maintain a clean project history effortlessly. [Get Started Now](#getting-started).**

---
