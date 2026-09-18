@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem Meeting Arena Brain - repo scaffold/bootstrap
rem
rem Run this from the root of the cloned GitHub repo:
rem   C:\Projects\meeting_arena_brain
rem
rem Default remote:
rem   https://github.com/Transititioned/meeting_arena_brain.git
rem
rem Optional: pass a different remote URL as argument 1:
rem   MAKE_BRAIN_REPO.cmd https://github.com/<user>/<repo>.git
rem
rem Safe to run more than once.
rem Empty folders get .gitkeep so GitHub/Codex can see the structure.
rem ============================================================

cd /d "%~dp0"
set "REPO=%CD%"
set "DEFAULT_REMOTE=https://github.com/Transititioned/meeting_arena_brain.git"
set "REMOTE_URL=%~1"

if "%REMOTE_URL%"=="" set "REMOTE_URL=%DEFAULT_REMOTE%"

echo.
echo === Meeting Arena Brain repo scaffold ===
echo Repo:   %REPO%
echo Remote: %REMOTE_URL%
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git was not found on PATH.
    echo Install Git for Windows, then run this file again.
    pause
    exit /b 1
)

if not exist ".git\" (
    echo Initialising Git repository...
    git init
    if errorlevel 1 goto :GitError
)

git branch -M main >nul 2>nul

call :EnsureDir "arena_brain"
call :EnsureDir "config"
call :EnsureDir "config\actors"
call :EnsureDir "config\moves"
call :EnsureDir "tests"
call :EnsureDir "scripts"

if not exist ".gitignore" (
    echo Creating .gitignore...
    > ".gitignore" (
        echo # Python
        echo __pycache__/
        echo *.py[cod]
        echo .pytest_cache/
        echo.
        echo # Virtual environments
        echo .venv/
        echo venv/
        echo.
        echo # Secrets / local config
        echo .env
        echo .env.*
        echo !.env.example
        echo.
        echo # IDE / OS
        echo .vscode/
        echo .idea/
        echo Thumbs.db
        echo .DS_Store
        echo.
        echo # Local logs / scratch
        echo *.log
        echo tmp/
    )
)

git remote get-url origin >nul 2>nul
if errorlevel 1 (
    echo Adding origin: %REMOTE_URL%
    git remote add origin "%REMOTE_URL%"
    if errorlevel 1 goto :GitError
) else (
    for /f "delims=" %%R in ('git remote get-url origin') do set "CURRENT_REMOTE=%%R"
    if /I not "!CURRENT_REMOTE!"=="%REMOTE_URL%" (
        echo.
        echo WARNING: origin currently points to:
        echo   !CURRENT_REMOTE!
        echo Expected:
        echo   %REMOTE_URL%
        echo.
        choice /M "Update origin to the expected GitHub repo"
        if errorlevel 2 (
            echo Leaving origin unchanged.
        ) else (
            git remote set-url origin "%REMOTE_URL%"
            if errorlevel 1 goto :GitError
        )
    )
)

git add -A
if errorlevel 1 goto :GitError

git diff --cached --quiet
if errorlevel 1 (
    echo Creating scaffold commit...
    git commit -m "Create Meeting Arena Brain scaffold"
    if errorlevel 1 (
        echo.
        echo Git could not create the commit.
        echo If Git identity is not configured, run once:
        echo   git config --global user.name "Your Name"
        echo   git config --global user.email "you@example.com"
        echo Then run this script again.
        pause
        exit /b 1
    )
) else (
    echo Nothing new to commit.
)

echo.
echo Repo status:
git status --short --branch

echo.
echo Pushing main to origin...
git push -u origin main
if errorlevel 1 (
    echo.
    echo Repo structure is ready locally, but push failed.
    echo Check GitHub authentication / remote permissions and retry:
    echo   git push -u origin main
    pause
    exit /b 1
)

echo.
echo DONE.
echo.
echo Cloud repo is now ready for Codex.
echo Empty folders are preserved with .gitkeep.
echo.
echo Expected structure:
echo   arena_brain\
echo   config\actors\
echo   config\moves\
echo   tests\
echo   scripts\
echo.
pause
exit /b 0

:EnsureDir
set "D=%~1"

if not exist "%D%\" (
    echo Creating %D%
    mkdir "%D%"
    if errorlevel 1 exit /b 1
)

set "HAS_CONTENT="
for /f "delims=" %%F in ('dir /b /a "%D%" 2^>nul') do set "HAS_CONTENT=1"

if not defined HAS_CONTENT (
    echo Preserving empty folder %D% with .gitkeep
    type nul > "%D%\.gitkeep"
)

exit /b 0

:GitError
echo.
echo ERROR: A Git command failed.
echo Repo files have not been deleted or overwritten.
pause
exit /b 1
