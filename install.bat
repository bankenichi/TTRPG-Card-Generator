@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"

echo ==============================================
echo TTRPG Card Generator Installer
echo ==============================================

:: Updated to target Python 3.14.1
set "PYTHON_DIR=%CD%\python-env"
set "PYTHON_ZIP=python-3.14.1-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.14.1/python-3.14.1-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

:: Portable Git settings
set "PORTABLE_GIT_DIR=%CD%\git-portable"
set "GIT_ZIP=PortableGit.7z.exe"
set "GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/PortableGit-2.45.2-64-bit.7z.exe"
set "GIT_EXE=%PORTABLE_GIT_DIR%\bin\git.exe"

echo.
echo [1/4] Checking for Git...
git --version >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo Git is already installed on this system.
    set "GIT_CMD=git"
) ELSE (
    if EXIST "%GIT_EXE%" (
        echo Portable Git already set up.
        set "GIT_CMD=%GIT_EXE%"
    ) ELSE (
        echo Git not found. Downloading portable Git...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%GIT_URL%', '%GIT_ZIP%')"
        IF !ERRORLEVEL! NEQ 0 (
            echo Failed to download portable Git. Please check your internet connection.
            if /i not "%TTRPG_INSTALL_HEADLESS%"=="1" pause
            exit /b 1
        )

        echo Extracting portable Git ^(this may take a moment^)...
        mkdir "%PORTABLE_GIT_DIR%"
        powershell -NoProfile -Command "$arg='-o'+[char]34+$env:PORTABLE_GIT_DIR+[char]34; $p=Start-Process -FilePath (Join-Path (Get-Location) $env:GIT_ZIP) -ArgumentList @($arg,'-y') -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode"
        IF !ERRORLEVEL! NEQ 0 (
            echo Failed to extract portable Git.
            if /i not "%TTRPG_INSTALL_HEADLESS%"=="1" pause
            exit /b 1
        )

        echo Cleaning up Git archive...
        del "%GIT_ZIP%"

        IF NOT EXIST "%GIT_EXE%" (
            echo Could not locate git.exe after extraction. Setup cannot continue.
            if /i not "%TTRPG_INSTALL_HEADLESS%"=="1" pause
            exit /b 1
        )

        echo Portable Git installed successfully.
        set "GIT_CMD=%GIT_EXE%"
    )
)

echo.
echo [2/4] Setting up standalone Python environment...
IF NOT EXIST "%PYTHON_DIR%\python.exe" (
    echo Downloading Portable Python 3.14...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PYTHON_URL%', '%PYTHON_ZIP%')"
    
    echo Extracting Python...
    mkdir "%PYTHON_DIR%"
    powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"
    
    echo Cleaning up zip file...
    del "%PYTHON_ZIP%"

    echo Enabling site-packages and local imports...
    powershell -Command "(Get-Content '%PYTHON_DIR%\python314._pth') -replace '#import site', 'import site' | Set-Content '%PYTHON_DIR%\python314._pth'"
    echo .. >> "%PYTHON_DIR%\python314._pth"

    echo Downloading get-pip.py...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%GET_PIP_URL%', 'get-pip.py')"

    echo Installing pip...
    "%PYTHON_DIR%\python.exe" get-pip.py
    del get-pip.py
) ELSE (
    echo Standalone Python environment already exists.
    findstr /x /l /c:".." "%PYTHON_DIR%\python314._pth" >nul
    if errorlevel 1 (
        echo .. >> "%PYTHON_DIR%\python314._pth"
    )
)

echo.
echo [3/4] Downloading Generator files...
IF NOT EXIST ".git" (
    echo Cloning TTRPG Card Generator repository...
    "%GIT_CMD%" clone https://github.com/bankenichi/TTRPG-Card-Generator temp_gen
    IF !ERRORLEVEL! NEQ 0 (
        echo Failed to clone the generator repository!
        if /i not "%TTRPG_INSTALL_HEADLESS%"=="1" pause
        exit /b 1
    )
    echo Moving files...
    robocopy "temp_gen" "%CD%" /e /move /xd "%CD%\python-env" "%CD%\git-portable" "%CD%\generators" >nul
    rmdir /s /q "temp_gen" 2>nul
) ELSE (
    echo Generator files already present.
)

echo.
echo [4/4] Handing over to GUI Installer...
if /i "%TTRPG_INSTALL_HEADLESS%"=="1" (
    "%PYTHON_DIR%\python.exe" gui_installer.py --headless
) else (
    "%PYTHON_DIR%\python.exe" gui_installer.py
)
exit /b %ERRORLEVEL%
