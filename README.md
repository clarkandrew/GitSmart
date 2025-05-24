<h1 align="center"><strong>GitSmart</strong></h1>

<div align="center">
  <img src="assets/no-bg.png" alt="GitSmart Overview Image" width="30%">
</div>
<h2 align="center"><em>The AI-Powered Git Commit Assistant</em</h2>


<br>
<p align="center">
  <img src="https://img.shields.io/badge/build-passing-brightgreen" alt="Build Status">
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
</p>
<br>

---

<br>

<br>
<p align="center">
    <img src="assets/demo.gif" alt="GitSmart Demo" width="100%">
</p>

<h6>GitSmart is an open-source Command Line Interface (CLI) tool that leverages Artificial Intelligence (AI) to automate the creation of meaningful Git commit messages. By analyzing the changes you've made, **GitSmart** generates concise and standardized commit messages, making it easier to track changes and collaborate with others.</h6>

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
```

```markdown
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

### Quick Setup (Recommended)

You can quickly set up GitSmart using our automated installation script:

```bash
# Clone the repository
git clone https://github.com/clarkandrew/GitSmart.git
cd GitSmart
chmod +x setup.sh
# Run the setup script
./setup.sh

# Then run:
gitsmart

# or
c
```

This script will:
- Set up a Python virtual environment
- Install all dependencies
- Create a configuration file
- Add convenient aliases (`gitsmart` and `c`) to your shell configuration

Follow the on-screen prompts to complete the setup.

### Manual Installation

If you prefer to install manually, follow these steps:

#### 1. Clone the Repository

```bash
git clone https://github.com/clarkandrew/GitSmart.git
cd GitSmart
```

#### 2. Setup Python Virtual Environment

Create and activate a virtual environment (requires Python 3.7 or higher):

```bash
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

#### 4. Configure the Application

Rename the example configuration file and update it with your API credentials:

```bash
cp example.config.ini config.ini
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

#### 5. Setup Command Aliases

Add convenient aliases for `gitsmart` and `c` to your shell configuration file (e.g., `.bashrc`, `.zshrc`):

```bash
# Add these lines to your shell configuration file
alias gitsmart="python -m GitSmart.main"
alias c="python -m GitSmart.main"
```

Reload your shell configuration:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Running GitSmart

In any Git repository, you can now use:

```bash
gitsmart  # or the shorter alias
c
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

### Integration Patterns and Best Practices

- **Secure API Credentials**: Keep your `config.ini` file out of version control (add it to `.gitignore`).
- **Automate with Git Hooks**: Integrate **GitSmart** into your Git workflow using pre-commit hooks.
- **Regular Updates**: Periodically update dependencies for security and performance improvements.

### Performance Optimization Guidelines

- **Limit Diff Size**: Stage only relevant changes to reduce processing time.
- **Adjust AI Settings**: Modify `max_tokens` and `temperature` in `config.ini` to balance performance and output quality.
- **Cache Responses**: Implement caching if you frequently regenerate commit messages for the same changes.

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

### Code Review Standards

- **Adhere to PEP 8**: Follow Python's style guidelines for clean and readable code.
- **Write Tests**: Include unit tests for any new features or bug fixes.
- **Update Documentation**: Ensure that any changes are reflected in the documentation.

### Issue and PR Templates

When creating issues or pull requests, please use the provided templates to include all necessary information.

### Licensing Details

This project is licensed under the [MIT License](LICENSE).

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

````
</files>
</context>

Fix the formatting issues and enhance this readme for opensource github project. Dont add any sections, just improve organization and markdown formatting

```
<h1 align="center"><strong>GitSmart</strong></h1>

<div align="center">
  <img src="assets/no-bg.png" alt="GitSmart Overview Image" width="30%">
</div>
<h2 align="center"><em>The AI-Powered Git Commit Assistant</em</h2>


<br>
<p align="center">
  <img src="https://img.shields.io/badge/build-passing-brightgreen" alt="Build Status">
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
</p>
<br>

---

<br>

<br>
<p align="center">
    <img src="assets/demo.gif" alt="GitSmart Demo" width="100%">
</p>

<h6>GitSmart is an open-source Command Line Interface (CLI) tool that leverages Artificial Intelligence (AI) to automate the creation of meaningful Git commit messages. By analyzing the changes you've made, **GitSmart** generates concise and standardized commit messages, making it easier to track changes and collaborate with others.</h6>

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
```

```markdown
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

### Quick Setup (Recommended)

You can quickly set up GitSmart using our automated installation script:

```bash
# Clone the repository
git clone https://github.com/clarkandrew/GitSmart.git
cd GitSmart
chmod +x setup.sh
# Run the setup script
./setup.sh

# Then run:
gitsmart

# or
c
```

This script will:
- Set up a Python virtual environment
- Install all dependencies
- Create a configuration file
- Add convenient aliases (`gitsmart` and `c`) to your shell configuration

Follow the on-screen prompts to complete the setup.

### Manual Installation

If you prefer to install manually, follow these steps:

#### 1. Clone the Repository

```bash
git clone https://github.com/clarkandrew/GitSmart.git
cd GitSmart
```

#### 2. Setup Python Virtual Environment

Create and activate a virtual environment (requires Python 3.7 or higher):

```bash
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

#### 4. Configure the Application

Rename the example configuration file and update it with your API credentials:

```bash
cp example.config.ini config.ini
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

#### 5. Setup Command Aliases

Add convenient aliases for `gitsmart` and `c` to your shell configuration file (e.g., `.bashrc`, `.zshrc`):

```bash
# Add these lines to your shell configuration file
alias gitsmart="python -m GitSmart.main"
alias c="python -m GitSmart.main"
```

Reload your shell configuration:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Running GitSmart

In any Git repository, you can now use:

```bash
gitsmart  # or the shorter alias
c
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

### Integration Patterns and Best Practices

- **Secure API Credentials**: Keep your `config.ini` file out of version control (add it to `.gitignore`).
- **Automate with Git Hooks**: Integrate **GitSmart** into your Git workflow using pre-commit hooks.
- **Regular Updates**: Periodically update dependencies for security and performance improvements.

### Performance Optimization Guidelines

- **Limit Diff Size**: Stage only relevant changes to reduce processing time.
- **Adjust AI Settings**: Modify `max_tokens` and `temperature` in `config.ini` to balance performance and output quality.
- **Cache Responses**: Implement caching if you frequently regenerate commit messages for the same changes.

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

### Code Review Standards

- **Adhere to PEP 8**: Follow Python's style guidelines for clean and readable code.
- **Write Tests**: Include unit tests for any new features or bug fixes.
- **Update Documentation**: Ensure that any changes are reflected in the documentation.

### Issue and PR Templates

When creating issues or pull requests, please use the provided templates to include all necessary information.

### Licensing Details

This project is licensed under the [MIT License](LICENSE).

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

```

## Agent

I'll fix the formatting issues and enhance the README for better organization and improved markdown formatting. Let me analyze the current content and make the necessary improvements.

**Use Tool: thinking (tooluse_jxUmsB6LTTy-6HFZttdeTQ)**
```json
{
  "content": "Let me analyze the formatting issues in the current README:\n\n1. Missing closing tag in the h2 element: `<h2 align=\"center\"><em>The AI-Powered Git Commit Assistant</em</h2>` is missing the closing bracket for the `em` tag.\n\n2. There are some HTML elements that should be converted to pure Markdown for better consistency.\n\n3. Some spacing issues with multiple `<br>` tags that make the document look inconsistent.\n\n4. Code blocks are using inconsistent formatting that might not render properly.\n\n5. The overall structure could use some standardization and clean-up to improve readability.\n\nI'll enhance the README by:\n1. Converting HTML elements to Markdown where appropriate\n2. Fixing the broken tags\n3. Standardizing heading formats\n4. Improving spacing and layout\n5. Ensuring consistent code block formatting\n6. Making sure all links work properly\n7. Enhancing the visual presentation while maintaining all content\n\nI'll maintain all existing sections as requested, just improve the organization and formatting."
}
```

**Tool Results: tooluse_jxUmsB6LTTy-6HFZttdeTQ**

Finished thinking.
## Agent

Here's the enhanced README with improved formatting and organization:

```GitSmart/README.md#L1-999
<h1 align="center"><strong>GitSmart</strong></h1>

<div align="center">
  <img src="assets/no-bg.png" alt="GitSmart Overview Image" width="30%">
</div>
<h2 align="center"><em>The AI-Powered Git Commit Assistant</em></h2>

<p align="center">
  <img src="https://img.shields.io/badge/build-passing-brightgreen" alt="Build Status">
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
</p>

---

<p align="center">
  <img src="assets/demo.gif" alt="GitSmart Demo" width="100%">
</p>

<p align="center">
  GitSmart is an open-source Command Line Interface (CLI) tool that leverages Artificial Intelligence (AI) to automate the creation of meaningful Git commit messages. By analyzing the changes you've made, <strong>GitSmart</strong> generates concise and standardized commit messages, making it easier to track changes and collaborate with others.
</p>

---

## Why You'd Need GitSmart

### **Streamlined Workflow**
- **Automated Commit Messages**: Automatically generate precise commit messages, saving time and reducing manual effort.

### **Consistent Version History**
- **Standardized Messages**: Ensure a clean and organized commit history, making it easier for project tracking, management, and debugging.

### **Seamless Integration**
- **User-Friendly CLI**: Simplify your Git workflow with an interactive command-line interface designed for efficiency and ease of use.

### **Enhanced Code Reviews**
- **Accurate Summaries**: Produce commit messages that precisely reflect changes, enhancing code review processes and collaboration.

### **Custom AI Integration**
- **Adaptive AI Insights**: Choose from leading language models like OpenAI, Anthropic, or Llama to get tailored AI assistance. This customization adapts to your coding style and preferences, significantly enhancing how you summarize and interpret code differences.

---

## Key Features

- **AI-Powered Commit Messages**: Automatically generate meaningful and standardized commit messages based on your code changes.
- **Track Changes**: Maintain a detailed history of modifications to your codebase.
- **Revert to Previous Versions**: Easily roll back to earlier states of your project.
- **Branch and Merge**: Experiment with new ideas without affecting the main project branch.
- **Collaborate Seamlessly**: Work with others by merging changes and resolving conflicts efficiently.

---

## AI-driven Chain-of-Thought Analysis for Deep Understanding of Any Change

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

**Step-by-Step Thinking:**

1. **Observations**:
   - The `README.md` file has been modified to update an image link.
   - Specifically, the `GitSmart Overview Image` source has changed from `assets/comit.png` to `assets/no-bg.png`.
   - A new file, `no-bg.png`, has been added to the `assets` directory.
   - The nature of the change suggests a visual update, potentially for aesthetic or branding reasons.

2. **Rationale**:
   - Chosen Icon: 💄 (for UI improvements, as the change affects the visual aspect of the project)
   - Theme: Update of graphical asset for potential branding or layout adjustments.

**Example Commit Message:**
```
💄 Update README Image Asset

**WHAT:** Replaced `comit.png` with `no-bg.png` in README.md
**WHY:** Refresh project's visual identity by updating the GitSmart Overview Image to a new version without background (`no-bg.png`), enhancing overall UI consistency and appeal.

**DETAILS:**
- **Affected File(s):**
  - `README.md`: Updated image link to reflect new asset.
  - `assets/no-bg.png`: Newly added image file, replacing the original `comit.png`.
- **Impact:** This change modernizes the project's front-facing visuals in the README, ensuring a more engaging and up-to-date first impression for visitors.
```

---

## Getting Started

### Quick Setup (Recommended)

You can quickly set up GitSmart using our automated installation script:

```bash
# Clone the repository
git clone https://github.com/clarkandrew/GitSmart.git
cd GitSmart
chmod +x setup.sh
# Run the setup script
./setup.sh

# Then run:
gitsmart

# or
c
```

This script will:
- Set up a Python virtual environment
- Install all dependencies
- Create a configuration file
- Add convenient aliases (`gitsmart` and `c`) to your shell configuration

Follow the on-screen prompts to complete the setup.

### Manual Installation

If you prefer to install manually, follow these steps:

#### 1. Clone the Repository

```bash
git clone https://github.com/clarkandrew/GitSmart.git
cd GitSmart
```

#### 2. Setup Python Virtual Environment

Create and activate a virtual environment (requires Python 3.7 or higher):

```bash
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

#### 4. Configure the Application

Rename the example configuration file and update it with your API credentials:

```bash
cp example.config.ini config.ini
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

#### 5. Setup Command Aliases

Add convenient aliases for `gitsmart` and `c` to your shell configuration file (e.g., `.bashrc`, `.zshrc`):

```bash
# Add these lines to your shell configuration file
alias gitsmart="python -m GitSmart.main"
alias c="python -m GitSmart.main"
```

Reload your shell configuration:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Running GitSmart

In any Git repository, you can now use:

```bash
gitsmart  # or the shorter alias
c
```

Follow the on-screen prompts to generate and commit your changes.

---

<div align="center">
  <img src="assets/bb.png" alt="GitSmart Overview Image">
</div>

---

## Version History and Changelog

### [1.0.0] - 2023-10-01

- Initial release with core features:
  - AI-powered commit message generation.
  - Interactive staging and unstaging of files.
  - Git diff visualization within the CLI.

### [0.9.0] - 2023-09-15

- Beta release with basic commit generation capabilities.

---

## Release Roadmap

### Upcoming Features

- **1.1.0**
  - Support for multiple AI service providers.
  - Customizable commit message templates.

- **1.2.0**
  - Graphical User Interface (GUI) for users who prefer not to use the command line.
  - Enhanced diff visualization with syntax highlighting.

---

## Technical Implementation

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

### Integration Patterns and Best Practices

- **Secure API Credentials**: Keep your `config.ini` file out of version control (add it to `.gitignore`).
- **Automate with Git Hooks**: Integrate **GitSmart** into your Git workflow using pre-commit hooks.
- **Regular Updates**: Periodically update dependencies for security and performance improvements.

### Performance Optimization Guidelines

- **Limit Diff Size**: Stage only relevant changes to reduce processing time.
- **Adjust AI Settings**: Modify `max_tokens` and `temperature` in `config.ini` to balance performance and output quality.
- **Cache Responses**: Implement caching if you frequently regenerate commit messages for the same changes.

---

## Community Engagement

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

### Code Review Standards

- **Adhere to PEP 8**: Follow Python's style guidelines for clean and readable code.
- **Write Tests**: Include unit tests for any new features or bug fixes.
- **Update Documentation**: Ensure that any changes are reflected in the documentation.

### Issue and PR Templates

When creating issues or pull requests, please use the provided templates to include all necessary information.

### Licensing Details

This project is licensed under the [MIT License](LICENSE).

### Code of Conduct

We are committed to fostering a welcoming community. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) for more information.

---

## Before and After: Transforming Your Git Commits with GitSmart

**Before:**

Your Git commit messages are a tangled mess—full of vague descriptions like "fix stuff" or "update files," making it hard to track changes and collaborate effectively.

**After:**

Run **GitSmart** and enjoy the perks of AI-powered commit messages that are clear, standardized, and meaningful. Effortlessly track changes, collaborate seamlessly, and maintain a professional project history without the hassle.

---

## Glossary

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
