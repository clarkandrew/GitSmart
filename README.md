# C0MIT

C0MIT is a powerful command-line tool designed to streamline your Git workflow. It assists with generating commit messages, staging and unstaging files, and displaying commit history. Leveraging the `rich` library for styled console output and `questionary` for interactive prompts, C0MIT provides a user-friendly and visually appealing interface.

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Features](#features)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

## Introduction

Welcome to C0MIT! This tool is designed to be the go-to library for anyone looking to enhance their Git workflow. Whether you're a seasoned developer or just getting started, C0MIT offers a range of features to make your Git experience smoother and more efficient.

## Installation

To install C0MIT, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/c0mit.git
    cd c0mit
    ```

2. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

To use C0MIT, simply run the `main.py` script:

```sh
python src/main.py
```

You will be presented with a menu of options to choose from:

- **Generate commit for staged files**: Generate a commit message for the currently staged files.
- **Review Staged Changes**: Review the changes that are currently staged.
- **Stage Files**: Stage selected files for commit.
- **Unstage Files**: Unstage selected files.
- **History**: Display the commit history.
- **Exit**: Exit the tool.

### Examples

1. **Generate a commit message for staged files**:
    ```sh
    python src/main.py
    # Select "Generate commit for staged files" from the menu
    ```

2. **Stage files**:
    ```sh
    python src/main.py
    # Select "Stage Files" from the menu
    # Select the files you want to stage
    ```

3. **Display commit history**:
    ```sh
    python src/main.py
    # Select "History" from the menu
    ```

## Configuration

C0MIT can be configured using the following options:

- **API Token**: Set the `AUTH_TOKEN` variable in `src/main.py` with your API token.
    ```python
    AUTH_TOKEN = "Bearer your_api_token"
    ```

- **API URL**: Set the `API_URL` variable in `src/main.py` with the URL of the API.
    ```python
    API_URL = "http://your_api_url/v1/chat/completions"
    ```

- **Model**: Set the `MODEL` variable in `src/main.py` with the model you want to use.
    ```python
    MODEL = "your_model"
    ```

- **Theme**: Customize the theme by modifying the `THEME` dictionary in `src/main.py`.
    ```python
    THEME = {
        "primary": "#678cb1",
        "secondary": "#8ea6c0",
        "accent": "#ffcb6b",
        "success": "#98c379",
        "error": "#e06c75",
        "warning": "#e5c07b",
        "background": "#282c34",
        "text": "#abb2bf",
    }
    ```

## Features

- **Generate Commit Messages**: Automatically generate commit messages based on the diff of staged files.
- **Review Staged Changes**: Display a detailed view of the changes that are currently staged.
- **Stage and Unstage Files**: Easily stage or unstage files for commit.
- **Display Commit History**: View the commit history with details of additions and deletions.
- **Capture the Full Image with Chain-of-thought prompts**: Use our masterful LLM prompts or customize it with your own for a seamless user experience.
- **Intuitive and Simple CLI**: Enjoy a visually appealing interface with styled console output using the `rich` library.

## Contributing

We welcome contributions to C0MIT! If you would like to contribute, please follow these guidelines:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Make your changes and commit them with a descriptive message.
4. Push your changes to your fork.
5. Submit a pull request to the main repository.

Please ensure that your code adheres to the existing style and includes appropriate tests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Contact

For any questions or feedback, please reach out to us at [your-email@example.com](mailto:your-email@example.com).

## Acknowledgments

We would like to thank the contributors and the open-source community for their support and contributions to this project.
