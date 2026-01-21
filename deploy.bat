@echo off
REM Deploy helper - staging-first workflow
REM Usage:
REM   deploy staging    - Create PR from current branch to staging
REM   deploy prod       - Create PR from staging to main (production)
REM   deploy status     - Show what's in staging vs main

if "%1"=="staging" (
    echo Creating PR to staging...
    gh pr create --base staging --fill
    goto :eof
)

if "%1"=="prod" (
    echo Creating PR from staging to production...
    gh pr create --base main --head staging --title "Deploy staging to production" --body "Promoting tested changes from staging to production."
    goto :eof
)

if "%1"=="status" (
    echo.
    echo === STAGING vs MAIN ===
    echo.
    echo Commits in staging not in main:
    git log origin/main..origin/staging --oneline
    echo.
    echo Commits in main not in staging:
    git log origin/staging..origin/main --oneline
    echo.
    goto :eof
)

if "%1"=="sync" (
    echo Syncing local branches with remote...
    git fetch origin
    git checkout main
    git pull origin main
    git checkout staging
    git pull origin staging
    echo Done!
    goto :eof
)

echo.
echo Deploy Helper - Staging-First Workflow
echo.
echo Usage:
echo   deploy staging  - Create PR from current branch to staging
echo   deploy prod     - Create PR from staging to main (production)
echo   deploy status   - Show differences between staging and main
echo   deploy sync     - Sync local branches with remote
echo.
echo Workflow:
echo   1. Create feature branch
echo   2. Make changes and commit
echo   3. deploy staging     (test in staging)
echo   4. deploy prod        (promote to production)
echo.
