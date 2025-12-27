# GitHub Actions CI/CD Workflows

This directory contains automated CI/CD workflows for the AuditOps Streamlit application.

## Workflows

### `test.yml` - CI/CD Tests & Linting

**Triggers:**
- Push to `main`, `master`, or `develop` branches
- Pull requests to `main`, `master`, or `develop` branches
- Manual trigger via GitHub Actions UI

**Jobs:**

#### 1. **Test** (Matrix: Python 3.10, 3.11, 3.12)
- Runs pytest with coverage reporting
- Parallel test execution with `pytest-xdist`
- Uploads coverage reports to Codecov
- Uploads HTML coverage report as artifact

#### 2. **Lint** (Code Quality Checks)
- **Black**: Code formatting check
- **isort**: Import statement sorting
- **flake8**: Python linting (syntax errors and PEP8)
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency security check

#### 3. **Integration Test** (with Database)
- Runs integration tests marked with `@pytest.mark.integration`
- Requires Supabase test credentials in GitHub Secrets
- Only runs on main branch or ready PRs

#### 4. **Build Check**
- Verifies Python syntax
- Checks that modules can be imported
- Ensures app builds without errors

#### 5. **Summary**
- Aggregates results from all jobs
- Posts summary to GitHub Actions summary page

## GitHub Secrets Required

For integration tests to work, add these secrets to your repository:

**Settings → Secrets and variables → Actions → New repository secret**

- `SUPABASE_TEST_URL` - Your test Supabase project URL
- `SUPABASE_TEST_KEY` - Your test Supabase anon or service role key

**Optional:**
- `CODECOV_TOKEN` - For uploading coverage to Codecov (get from codecov.io)

## Local Testing

Run the same tests locally:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests with coverage
pytest tests/ -v --cov=auditops-streamlit/src --cov-report=html

# Run linting
black --check auditops-streamlit/ tests/
isort --check-only auditops-streamlit/ tests/
flake8 auditops-streamlit/ tests/
bandit -r auditops-streamlit/

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Viewing Results

### GitHub Actions UI
1. Go to **Actions** tab in GitHub
2. Click on a workflow run
3. View detailed logs for each job
4. Download artifacts (coverage reports)

### Pull Request Checks
- Status checks appear automatically on PRs
- Click "Details" to view full logs
- Green checkmark = all tests passed
- Red X = tests failed (click to see why)

### Coverage Reports
- HTML coverage report uploaded as artifact
- Download from workflow run page
- Open `htmlcov/index.html` in browser

## Configuration Files

Related configuration files:

- `.github/workflows/test.yml` - This workflow definition
- `pytest.ini` - Pytest configuration (markers, paths, options)
- `requirements-test.txt` - Testing dependencies
- `.flake8` - Flake8 linting configuration (optional)
- `.coveragerc` - Coverage reporting configuration (optional)

## Customization

### Skip CI for a Commit
Add `[skip ci]` or `[ci skip]` to your commit message:
```bash
git commit -m "docs: update README [skip ci]"
```

### Run Only Specific Tests
Add labels to your PR to control which tests run (requires workflow modification).

### Modify Matrix
Edit `test.yml` to add/remove Python versions:
```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

## Troubleshooting

### Tests Failing in CI but Pass Locally
- Check Python version (CI uses 3.10, 3.11, 3.12)
- Check environment variables (use TESTING=true in CI)
- Check file paths (CI uses Linux, you might use Windows)

### Linting Failures
- Run locally: `black auditops-streamlit/ tests/`
- Commit the formatted files
- Push to trigger CI again

### Integration Tests Skipped
- Add `SUPABASE_TEST_URL` and `SUPABASE_TEST_KEY` secrets
- Or mark as `continue-on-error: true` (already done)

### Codecov Upload Failing
- Add `CODECOV_TOKEN` secret
- Or remove codecov upload step from workflow

## Best Practices

1. ✅ **Run tests locally before pushing**
2. ✅ **Keep tests fast** (use mocks for external services)
3. ✅ **Mark slow tests** with `@pytest.mark.slow`
4. ✅ **Mark integration tests** with `@pytest.mark.integration`
5. ✅ **Add tests for bug fixes** to prevent regression
6. ✅ **Maintain >80% code coverage**

## Status Badge

Add to your README:
```markdown
[![CI/CD - Tests & Linting](https://github.com/Matty-1337/auditops-streamlit/actions/workflows/test.yml/badge.svg)](https://github.com/Matty-1337/auditops-streamlit/actions/workflows/test.yml)
```

## Support

For issues with CI/CD:
1. Check workflow logs in GitHub Actions
2. Run tests locally to reproduce
3. Review this documentation
4. Check pytest.ini and test configuration
