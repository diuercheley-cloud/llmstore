from setuptools import setup, find_packages

setup(
    name="kleberai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.20.0",
    ],
    description="Minimal SDK for Kleber AI",
    author="Kleber",
    python_requires=">=3.8",
)
