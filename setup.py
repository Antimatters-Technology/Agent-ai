from setuptools import setup, find_packages

setup(
    name="visamate-ai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "python-dateutil",
    ],
    python_requires=">=3.8",
) 