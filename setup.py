from setuptools import setup, find_packages

setup(
    name="qgjob",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "qgjob=qgjob.cli:cli",
        ],
    },
    author="QualGent",
    description="CLI tool for QualGent job orchestration",
    python_requires=">=3.7",
)
