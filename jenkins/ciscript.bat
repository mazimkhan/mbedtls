@echo off

set ENV_FILE=cienv.bat

REM check if cienv.bat is present
if not exist %ENV_FILE% (
    echo "Environment file %ENV_FILE% does not exist!"
    goto :error
)

call %ENV_FILE%

call :check_env TEST_NAME MBEDTLS_ROOT || goto :error

cd %MBEDTLS_ROOT%

if "%TEST_NAME%"=="mingw-make" (
    cmake . -G "MinGW Makefiles" -DCMAKE_C_COMPILER="gcc"
    mingw32-make clean
    mingw32-make

) else if "%TEST_NAME%"=="msvc12-32" (
    call "C:\\Program Files (x86)\\Microsoft Visual Studio 12.0\\VC\\vcvarsall.bat"
    cmake . -G "Visual Studio 12"
    MSBuild ALL_BUILD.vcxproj

) else if "%TEST_NAME%"=="msvc12-64" (
    call "C:\\Program Files (x86)\\Microsoft Visual Studio 12.0\\VC\\vcvarsall.bat"
    cmake . -G "Visual Studio 12 Win64"
    MSBuild ALL_BUILD.vcxproj

) else if "%TEST_NAME%"=="mingw-iar8" (
    perl scripts\config.pl baremetal
    cmake -D CMAKE_BUILD_TYPE:String=Check -DCMAKE_C_COMPILER="iccarm" -G "MinGW Makefiles" .
    mingw32-make lib

) else (
    echo "Error: Invalid test %TEST_NAME%!"
)


goto :EOF

:check_env
setlocal enabledelayedexpansion
for %%x in (%*) do (
    call set val=%%%%x%%
    if "!val!"=="" (
        echo "Error: Env var %%x not set!"
        exit /b 1
    )
)
endlocal
goto :EOF

:error
REM for intentional error exit set errorlevel
if error == 0 ( errorlevel=1 )
echo Failed with error #%errorlevel%!
exit /b %errorlevel%

