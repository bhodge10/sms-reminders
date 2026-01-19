@echo off
set PYTHONPATH=C:\pylibs;C:\Remyndrs

REM Load .env.test if it exists, otherwise use defaults
if exist .env.test (
    for /f "tokens=1,2 delims==" %%a in (.env.test) do (
        set %%a=%%b
    )
)

REM Handle special test commands
if "%1"=="ai" (
    echo Running AI accuracy tests...
    "C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest tests/test_ai_accuracy.py -v %2 %3 %4 %5
    goto :eof
)

if "%1"=="report" (
    echo Generating AI accuracy report...
    "C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest tests/test_ai_accuracy.py::TestAIAccuracyReport -v -s
    goto :eof
)

if "%1"=="quick" (
    echo Running quick tests (skipping slow/AI tests)...
    "C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest tests/ -v -m "not slow" %2 %3 %4 %5
    goto :eof
)

if "%1"=="flow" (
    echo Running conversation flow tests...
    "C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest tests/test_conversation_flows.py -v -s %2 %3 %4 %5
    goto :eof
)

if "%1"=="flowreport" (
    echo Generating conversation flow report...
    "C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest tests/test_conversation_flows.py::TestConversationFlowReport -v -s
    goto :eof
)

if "%1"=="e2e" (
    echo Running end-to-end tests and generating report...
    "C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest tests/test_e2e_flows.py::TestE2EReport -v -s
    goto :eof
)

if "%1"=="e2eall" (
    echo Running all end-to-end scenario tests...
    "C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest tests/test_e2e_flows.py::TestE2EFlows -v %2 %3 %4 %5
    goto :eof
)

"C:\Users\BradHodge\AppData\Local\Microsoft\WindowsApps\python3.13.exe" -m pytest %*
