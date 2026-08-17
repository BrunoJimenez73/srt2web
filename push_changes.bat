git add -A
git commit -m "fix: CI failures - add PyJWT, fix Playwright server readiness

- Add explicit PyJWT installation to CI (fixes ModuleNotFoundError: jwt)
- Add pytest-mock for mocking in tests
- Fix Playwright workflow: wait for server /status endpoint with retries
- Add proper server readiness check with /status endpoint
- Playwright tests now wait for server readiness before running"
git push origin main