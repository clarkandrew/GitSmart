from setuptools import setup, find_packages

setup(
    name="gitsmart",
    version="0.1.0",
    description="AI-Powered Git Commit Assistant",
    author="Your Name",
    packages=find_packages(),  # or ["GitSmart"] if you prefer explicitly
    install_requires=[
        "questionary>=1.10.0",
        "rich>=13.0.0",
        "requests>=2.28.0",
        "prompt_toolkit>=3.0.0",
        # etc.
    ],
    entry_points={
        "console_scripts": [
            "gitsmart = GitSmart.main:entry_point",
            # The left side is the CLI command, the right side is
            # "package.module:function" for your main script
        ]
    },
    python_requires=">=3.7"
)
