# C0MIT: The AI-Powered Git Commit Assistant

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Contributors](https://img.shields.io/github/contributors/yourusername/C0MIT)
![Issues](https://img.shields.io/github/issues/yourusername/C0MIT)
![PRs](https://img.shields.io/github/issues-pr/yourusername/C0MIT)

---

## Project Foundation



**C0MIT** is a customizable Command Line Interface (CLI) tool that leverages LLM's to automate the generation of high-quality, meaningful git commit messages. By analyzing your staged changes, **C0MIT** creates concise, standardized commit messages, enhancing your development workflow and ensuring consistent project documentation.

---

![[3.png]]

####  **Save Time**
##### - Eliminate the tedious task of writing commit messages manually.

#### **Consistency**
###### - Maintain standardized commit messages across your projects.

####  **Clarity**
##### - Generate commit messages that accurately reflect code changes.

#### **Enhanced Productivity**
##### - Streamline your git operations within an interactive CLI.

#### **AI-Powered**
##### - Utilize your favorite AI models to interpret and summarize code diffs.

---

### It's awesome for:
- Rapid development environments requiring quick commits.
- Easy customization to meet strict commit message standards.
- Teams aiming for better collaboration through clear commit histories.
- Developers who frequently forget to write detailed commit messages.


### Quick Start Guide
#### Prerequisites
- **Python**: Version 3.6 or higher.
- **Git**: Installed and configured.
- **API Access**: Sign up for an API key with our AI service provider.

#### Installation
1. **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/C0MIT.git
    cd C0MIT
    ```
2. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Configure the Application**
    Rename `example.config.ini` to `config.ini` and update it with your API credentials:
    ```ini
    [API]
    auth_token = YOUR_API_TOKEN
    api_url = https://api.yourservice.com/v1/chat/completions
    model = your-model-name
    max_tokens = 500
    temperature = 0.7
    max_tokens = 8192
    ```

#### Running C0MIT
To make it easier to run `C0MIT` from any git directory, you can add it to your PATH. Here's how:
1. **Add C0MIT to PATH**
    First, make the `C0MIT` script executable:
    ```bash
    chmod +x /path/to/C0MIT/src/main.py
    ```
    Then, add the directory to your PATH. You can do this by adding the following line to your shell configuration file (e.g., `.bashrc`, `.zshrc`):
    ```bash
    export PATH=$PATH:/path/to/C0MIT/src
    ```
    After adding this line, reload your shell configuration:
    ```bash
    source ~/.bashrc  # or source ~/.zshrc
    ```
2. **Run C0MIT**
    Now you can run `C0MIT` from any git directory:
    ```bash
    C0MIT
    ```
    Follow the interactive prompts to generate and commit your changes.

### Version History and Changelog
#### [1.0.0] - 2023-10-01
- Initial release with core functionalities:
  - AI-powered commit message generation.
  - Interactive staging and unstaging.
  - Git diff visualization.

#### [0.9.0] - 2023-09-15
- Beta release with basic commit generation.

### Release Roadmap
#### Upcoming Features
- **1.1.0**
  - Integration with multiple AI service providers.
  - Customizable commit templates.
- **1.2.0**
  - GUI version for non-CLI users.
  - Enhanced diff visualization with syntax highlighting.
- **1.3.0**
  - Support for non-git version control systems.
  - Multi-language support for commit messages.

---

## Technical Implementation

### Detailed Installation Procedures
#### Windows, macOS, and Linux
1. **Install Python and Git**
    Ensure Python and Git are installed on your system. Refer to the official websites for installation instructions if needed.
2. **Follow the Quick Start Guide**

### Environment Configuration Requirements
- **Python Packages**: Ensure all packages in `requirements.txt` are installed.
- **API Credentials**: Valid `auth_token` and `api_url` in `config.ini`.
- **Network Access**: Outbound internet access for API calls.

### API Reference
#### Function: `generate_commit_message(diff: str) -> str`
Generates a commit message using the AI service.

**Parameters**
- `diff` (str): The git diff of staged changes.

**Returns**
- `str`: The generated commit message.

**Example**
```python
diff = get_git_diff(staged=True)
commit_message = generate_commit_message(diff)
print(commit_message)
```

### Integration Patterns and Best Practices
- **Secure API Credentials**: Do not commit `config.ini` to version control.
- **Automate with Pre-Commit Hooks**: Integrate **C0MIT** into your git workflow.
- **Regular Updates**: Keep dependencies up-to-date for security and performance.

### Performance Optimization Guidelines
- **Limit Diff Size**: Stage only relevant changes to speed up AI processing.
- **Adjust `max_tokens`**: Configure `max_tokens` in `config.ini` based on your needs.
- **Cache API Responses**: Implement caching if you're regenerating commits for the same diff.

### Troubleshooting Guide
#### Common Issues and Solutions
- **API Authentication Errors**
  - *Solution*: Verify your `auth_token` in `config.ini`.
- **No Staged Changes Detected**
  - *Solution*: Ensure you've staged changes using `git add`.
- **Network Timeouts**
  - *Solution*: Check your internet connection and proxy settings.

### Known Limitations and Workarounds
- **Large Diffs**
  - *Limitation*: Processing very large diffs may slow down the commit generation.
  - *Workaround*: Stage changes in smaller batches.
- **API Rate Limits**
  - *Limitation*: Exceeding API limits may result in errors.
  - *Workaround*: Upgrade your API plan or implement rate limiting in your usage.

### Upgrade/Migration Guides
#### Upgrading from 1.0.0 to 1.1.0
1. **Pull the Latest Changes**
    ```bash
    git pull origin main
    ```
2. **Update Dependencies**
    ```bash
    pip install --upgrade -r requirements.txt
    ```
3. **Update Configuration**
    - Add any new configuration options to your `config.ini`.

---

## Community Engagement

### Contribution Workflow and Guidelines
We welcome contributions!

1. **Fork the Repository**
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

### Development Setup Guide
#### Setting Up the Development Environment
1. **Clone Your Fork**
    ```bash
    git clone https://github.com/yourusername/C0MIT.git
    cd C0MIT
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
- **Adhere to PEP 8**: Ensure your code follows Python's style guidelines.
- **Write Tests**: Include unit tests for new features.
- **Documentation**: Update documentation for any code changes.

### Issue and PR Templates
Please use the provided templates when creating issues and pull requests to ensure all necessary information is included.

### Security Disclosure Process
If you discover a security vulnerability, please send an email to [security@yourdomain.com](mailto:security@yourdomain.com). Do not create a public issue.

### Licensing Details
This project is licensed under the [MIT License](LICENSE).

### Support Channels and SLAs
- **GitHub Issues**: For bug reports and feature requests.
- **Email Support**: [support@yourdomain.com](mailto:support@yourdomain.com)
- **Response Time**: We aim to respond within 2 business days.

### Code of Conduct
We are committed to maintaining a welcoming community. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) for more information.

---

## Glossary
- **CLI**: Command Line Interface.
- **API**: Application Programming Interface.
- **Diff**: Difference between versions of files.
- **Commit**: Saving changes to the repository.
- **Staging**: Preparing changes for a commit.
- **Unstaging**: Reversing staging of changes.

---

## Badges
![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Contributors](https://img.shields.io/github/contributors/yourusername/C0MIT)
![Issues](https://img.shields.io/github/issues/yourusername/C0MIT)
![PRs](https://img.shields.io/github/issues-pr/yourusername/C0MIT)
