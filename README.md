# Blobserver Onboarding Document

## Introduction

This document outlines the key tasks for onboarding the `blobserver` project, focusing on reviewing the Docker container version, defining aims for dependency updates, and identifying gaps in automated testing.

## Task 1: Review the Docker Container Version

### Current Python Version

The `blobserver` is currently running Python version 3.11.

### Insights and Risks

- **Compatibility**: Python 3.11 is generally compatible with most libraries. However, some packages in `requirements.txt` and `tests/requirements.txt` may not fully support it. For example, `Werkzeug` and `Flask` are typically quick to update, but always verify compatibility with the latest Python version.

- **Known Issues**: No major issues have been reported with Python 3.11 affecting the packages in your `requirements.txt` files. However, always check the release notes of each package for specific issues.

- **Docker Base Image**: The use of `FROM python:alpine` in the Dockerfile can lead to compatibility issues with Python packages requiring system dependencies not available in Alpine Linux.

### Plan to Overcome Risks

1. **Dependency Audit**: Regularly check for updates to dependencies and verify their compatibility with Python 3.11 using tools like `pipdeptree`.

2. **Testing**: Implement comprehensive testing, including unit and integration tests, to catch issues arising from Python 3.11.

3. **Monitoring**: Set up monitoring to quickly detect and address runtime issues related to Python 3.11.

4. **Docker Base Image Update**: Consider using a more compatible base image, such as `python:3.11-slim`, to reduce compatibility issues.

5. **Fallback Plan**: Maintain a stable version of the Docker container with an earlier Python version as a fallback.

6. **Review Dependabot PRs**: Regularly review and merge pending pull requests from Dependabot to keep dependencies up-to-date. [Dependabot PRs](https://github.com/ScilifelabDataCentre/blobserver/issues?q=is%3Apr+is%3Aopen+author%3Aapp%2Fdependabot)

## Task 2: Define Aims for Updates of Dependencies (Based on Trivy Results)

### Aims and Timeframes

- **Critical Vulnerabilities**: Address within one week to prevent severe security breaches.
- **High Vulnerabilities**: Resolve within two weeks to maintain application security.
- **Medium and Low Vulnerabilities**: Address within a month to ensure overall security hygiene.
- **Negligible and Unknown**: Review and address as part of regular maintenance cycles.

## Task 3: Identify Significant Gaps in Automated Testing

### Current Testing Coverage

The test suite includes tests for browser user access, API user access, and anonymous access. However, there are significant gaps:

1. **Security Tests**: Lack of tests for SQL injection, XSS vulnerabilities, and authentication bypass attempts.
2. **Performance Tests**: No performance or load tests to ensure the application can handle expected traffic.
3. **Unit Tests**: Limited unit test coverage for individual functions and methods.

### Recommendations

- **Expand Security Testing**: Implement tests to identify and mitigate vulnerabilities.
- **Introduce Performance Testing**: Conduct tests to ensure the application can handle load and stress.
- **Increase Unit Testing**: Improve coverage for utility functions and critical logic.

By addressing these gaps, we can increase confidence in the codebase's stability and security, making it safer to apply updates and maintain the application.
