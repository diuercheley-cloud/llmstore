from setuptools import find_packages, setup

setup(
    name="kleberai",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.20.0",
    ],
    entry_points={
        "console_scripts": [
            "agentctl=kleberai.cli:main",
        ],
    },
    extras_require={
        "dev": ["pytest>=7.0", "pytest-asyncio>=0.21"],
    },
    description="Python SDK for the Kleber AI Agentic Platform",
    author="Kleber",
    python_requires=">=3.8",
)
