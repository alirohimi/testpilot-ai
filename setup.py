from setuptools import setup, find_packages

setup(
    name="testpilot-ai",
    version="0.1.0",
    description="AI-powered pytest plugin for intelligent test failure triage, scrubbing, and classification",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Hermes Agent",
    author_email="agent@hermes.ai",
    license="MIT",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pytest>=7.0.0",
        "pydantic>=2.0.0",
        "openai>=1.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "pytest11": [
            "testpilot = testpilot_ai.plugin",
        ],
    },
)
