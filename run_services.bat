@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "APP_COMPOSE_FILE=%ROOT_DIR%\docker-compose.yml"
set "SEG_COMPOSE_DIR=%ROOT_DIR%\coins-obj-seg-main"

set "want_back=false"
set "want_web=false"
set "want_bot=false"

if "%~1"=="" (
  set "want_back=true"
  set "want_web=true"
  set "want_bot=true"
  goto args_done
)

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="-back" (set "want_back=true" & shift & goto parse_args)
if /I "%~1"=="-web"  (set "want_web=true"  & shift & goto parse_args)
if /I "%~1"=="-bot"  (set "want_bot=true"  & shift & goto parse_args)
if /I "%~1"=="-h"    (goto print_help)
if /I "%~1"=="--help" (goto print_help)
echo Unknown option: %~1 1>&2
goto print_help

:args_done
if /I "%want_web%"=="true" set "want_back=true"
if /I "%want_bot%"=="true" set "want_back=true"

call :echo_step "[1/4] Starting PostgreSQL and Redis containers..."
call :ensure_container_running coins_pg -e POSTGRES_DB=practice -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5433:5432 postgres:14
call :ensure_container_running coins_redis -p 6379:6379 redis:7-alpine

call :echo_step "[2/4] Starting local object detection+segmentation stack..."
pushd "%SEG_COMPOSE_DIR%" >nul
docker compose up -d --build florence-api sam-api

call :wait_for_healthy florence-api 1800
call :wait_for_healthy sam-api 1800

docker compose up -d --build predict-api
popd >nul

call :echo_step "[3/4] Starting requested app services..."
set "services="
if /I "%want_back%"=="true" set "services=!services! backend"
if /I "%want_web%"=="true" set "services=!services! web"
if /I "%want_bot%"=="true" (
  docker rm -f coin_detector_telegram_bot >nul 2>&1
  set "services=!services! telegram-bot"
)

docker compose -f "%APP_COMPOSE_FILE%" up -d --build !services!

call :echo_step "[4/4] Current status"
docker compose -f "%APP_COMPOSE_FILE%" ps
pushd "%SEG_COMPOSE_DIR%" >nul
docker compose ps
popd >nul

echo Done.
echo Useful checks:
echo   curl http://127.0.0.1:8000/health
echo   curl http://127.0.0.1:8010/ready
echo   open http://127.0.0.1:3000
exit /b 0

:print_help
echo Usage:
echo   run_services.bat [-back] [-web] [-bot]
echo.
echo Flags:
echo   -back    start backend container
echo   -web     start web container (automatically includes backend)
echo   -bot     start telegram bot container (automatically includes backend)
echo.
echo Examples:
echo   run_services.bat -back -bot
echo   run_services.bat -back -web
echo   run_services.bat -back -web -bot
echo.
echo If no flags are passed, all three are started.
exit /b 0

:ensure_container_running
set "container_name=%~1"
shift
docker container inspect "%container_name%" >nul 2>&1
if %errorlevel%==0 (
  docker start "%container_name%" >nul
) else (
  docker run -d --name "%container_name%" --restart unless-stopped %* >nul
)
exit /b 0

:wait_for_healthy
set "container_name=%~1"
set "timeout_seconds=%~2"
if "%timeout_seconds%"=="" set "timeout_seconds=1200"
set /a waited=0

:wait_loop
for /f "usebackq delims=" %%S in (`docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" "%container_name%" 2^>nul`) do set "status=%%S"
if not defined status set "status=unknown"

if /I "%status%"=="healthy" goto wait_done
if /I "%status%"=="running" goto wait_done
if /I "%status%"=="exited" goto wait_failed
if /I "%status%"=="dead" goto wait_failed

if %waited% GEQ %timeout_seconds% goto wait_timeout
timeout /t 5 /nobreak >nul
set /a waited+=5
goto wait_loop

:wait_failed
echo Container %container_name% failed to start (status=%status%). 1>&2
docker logs --tail 120 "%container_name%" 1>nul 2>&1
exit /b 1

:wait_timeout
echo Timed out waiting for %container_name% to become healthy. 1>&2
docker logs --tail 120 "%container_name%" 1>nul 2>&1
exit /b 1

:wait_done
exit /b 0

:echo_step
echo %~1
exit /b 0
