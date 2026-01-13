# =============================================================
# Windows PowerShell Startup Script - API Server
# Function: Start MindVoice API server, configure HuggingFace mirror and environment variables
# =============================================================

# 设置编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 颜色输出函数
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# 项目根目录
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$API_PORT = 8765
$API_HOST = "127.0.0.1"

# Anaconda 虚拟环境路径
$PYTHON_EXE = "D:\APP\anaconda\envs\my_env3.9\python.exe"

# =============================================================
# HuggingFace 镜像设置（解决网络问题）
# =============================================================
Write-Info "Configuring HuggingFace mirror..."

# Set HuggingFace mirror endpoint (use domestic mirror for faster downloads)
$env:HF_ENDPOINT = "https://hf-mirror.com"

# Disable progress bars (avoid tqdm stderr access failures in Windows background threads)
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TRANSFORMERS_VERBOSITY = "error"

Write-Success "HuggingFace configuration completed"
Write-Info "  HF_ENDPOINT: $env:HF_ENDPOINT"
Write-Info "  HF_HUB_DISABLE_PROGRESS_BARS: $env:HF_HUB_DISABLE_PROGRESS_BARS"
Write-Info "  TRANSFORMERS_VERBOSITY: $env:TRANSFORMERS_VERBOSITY"
Write-Host ""

# =============================================================
# 环境检查
# =============================================================
function Test-Environment {
    # 检查指定的 Python 可执行文件是否存在
    if (-not (Test-Path $PYTHON_EXE)) {
        Write-Error "Python executable not found: $PYTHON_EXE"
        Write-Info "Please check if Anaconda environment path is correct"
        exit 1
    }
    
    Write-Info "Using Python: $PYTHON_EXE"
    
    # Check Python version
    $pythonVersion = & $PYTHON_EXE --version 2>&1
    Write-Info "Python version: $pythonVersion"
    
    # 检查关键模块
    $testResult = & $PYTHON_EXE -c "import fastapi, uvicorn" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Required modules missing"
        $installCmd = "& `"$PYTHON_EXE`" -m pip install -r requirements.txt"
        Write-Info "Please install dependencies: $installCmd"
        exit 1
    }
    
    Write-Success "Environment check passed"
}

# =============================================================
# 端口检查
# =============================================================
function Test-Port {
    param([int]$Port, [string]$IPAddress = "127.0.0.1")
    
    try {
        $connection = Test-NetConnection -ComputerName $IPAddress -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
        return $connection
    } catch {
        return $false
    }
}

# =============================================================
# 清理进程
# =============================================================
function Stop-APIProcesses {
    Write-Info "Cleaning up processes..."
    
    # 查找占用端口的进程
    $portProcesses = @()
    $portConnections = Get-NetTCPConnection -LocalPort $API_PORT -ErrorAction SilentlyContinue
    if ($portConnections) {
        $portProcesses = $portConnections | Select-Object -ExpandProperty OwningProcess -Unique
    }
    
    # 查找 API 服务器进程（使用 CIM 获取命令行）
    $apiProcesses = @()
    try {
        $cimProcesses = Get-CimInstance Win32_Process | Where-Object { 
            $_.ExecutablePath -like "*python*" -and 
            $_.CommandLine -like "*api_server.py*" 
        }
        if ($cimProcesses) {
            $apiProcesses = $cimProcesses | Select-Object -ExpandProperty ProcessId
        }
    } catch {
        # 如果 CIM 查询失败，使用进程名过滤（不够精确）
        $psProcesses = Get-Process | Where-Object { 
            $_.ProcessName -like "*python*"
        } -ErrorAction SilentlyContinue
        if ($psProcesses) {
            $apiProcesses = $psProcesses | Select-Object -ExpandProperty Id
        }
    }
    
    # 合并所有进程 ID
    $allPids = @()
    if ($portProcesses) {
        $allPids += $portProcesses
    }
    if ($apiProcesses) {
        $allPids += $apiProcesses
    }
    $allPids = $allPids | Select-Object -Unique
    
    if ($allPids) {
        foreach ($pid in $allPids) {
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            } catch {
                # 忽略错误
            }
        }
        Start-Sleep -Seconds 1
    }
    
    Write-Success "Process cleanup completed"
}

# =============================================================
# 启动 API 服务器
# =============================================================
function Start-APIServer {
    Write-Info "Starting API server..."
    
    # Check port
    if (Test-Port -Port $API_PORT -IPAddress $API_HOST) {
        Write-Warning "Port $API_PORT is in use, cleaning up..."
        Stop-APIProcesses
        Start-Sleep -Seconds 1
        
        if (Test-Port -Port $API_PORT -IPAddress $API_HOST) {
            Write-Error "Port $API_PORT is still in use after cleanup"
            Write-Info "Please manually close the process using the port:"
            Write-Info "  netstat -ano | findstr :$API_PORT"
            return @{Success = $false}
        }
    }
    
    # 检查指定的 Python 可执行文件是否存在
    if (-not (Test-Path $PYTHON_EXE)) {
        Write-Error "Python executable not found: $PYTHON_EXE"
        return @{Success = $false}
    }
    
    # Check API server script
    $apiScript = Join-Path $PROJECT_DIR "api_server.py"
    if (-not (Test-Path $apiScript)) {
        Write-Error "API server script not found: $apiScript"
        return @{Success = $false}
    }
    
    # Create log directory
    $logDir = Join-Path $PROJECT_DIR "logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }
    
    $logFile = Join-Path $logDir "api_server_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    # Start API server
    Write-Info "Start command: $PYTHON_EXE $apiScript --port $API_PORT --host $API_HOST"
    Write-Info "Log file: $logFile"
    
    # 在后台启动进程（使用 cmd 来合并标准输出和标准错误）
    # PowerShell 的 Start-Process 不能将 stdout 和 stderr 重定向到同一个文件
    # 使用 cmd /k 来执行命令，并使用 2>&1 重定向（/k 保持 cmd 运行直到 Python 结束）
    $cmdArgs = "/k `"$PYTHON_EXE`" `"$apiScript`" --port $API_PORT --host $API_HOST > `"$logFile`" 2>&1"
    
    $cmdProcess = Start-Process -FilePath "cmd.exe" `
        -ArgumentList $cmdArgs `
        -WindowStyle Hidden `
        -PassThru
    
    if (-not $cmdProcess) {
        Write-Error "API server startup failed"
        return @{Success = $false}
    }
    
    # 等待一下，让 Python 进程启动
    Start-Sleep -Milliseconds 1000
    
    # 查找实际的 Python 进程（通过命令行参数匹配）
    $processId = $null
    try {
        $pythonProcesses = Get-CimInstance Win32_Process | Where-Object {
            $_.ExecutablePath -eq $PYTHON_EXE -and
            $_.CommandLine -like "*api_server.py*"
        }
        
        if ($pythonProcesses) {
            $processId = $pythonProcesses[0].ProcessId
        }
    } catch {
        # 如果 CIM 查询失败，尝试其他方法
        Write-Warning "Cannot find Python process via CIM query, trying other methods..."
    }
    
    if (-not $processId) {
        # If still not found, use cmd process ID (less accurate but works)
        Write-Warning "Cannot find Python process, using cmd process ID: $($cmdProcess.Id)"
        $processId = $cmdProcess.Id
    }
    
    Write-Info "API 服务器 PID: $processId"
    
    # Wait for server to start
    Write-Info "Waiting for API server to be ready..."
    $maxWait = 25
    $waited = 0
    $ready = $false
    
    while ($waited -lt $maxWait -and -not $ready) {
        Start-Sleep -Seconds 1
        $waited++
        
        # 检查进程是否还在运行
        $processRunning = $false
        try {
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                $processRunning = $true
            }
        } catch {
            # 忽略错误，继续检查
        }
        
        if (-not $processRunning) {
            Write-Error "API server process exited"
            Write-Info "Check log: Get-Content $logFile -Tail 20"
            if (Test-Path $logFile) {
                Write-Info "Log content:"
                Get-Content $logFile -Tail 20 | ForEach-Object { Write-Host "  $_" }
            }
            return @{Success = $false; ProcessId = $processId; CmdProcessId = $cmdProcess.Id; LogFile = $logFile}
        }
        
        # 检查 API 是否响应
        try {
            $response = Invoke-WebRequest -Uri "http://${API_HOST}:${API_PORT}/" `
                -UseBasicParsing `
                -TimeoutSec 1 `
                -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 404) {
                $ready = $true
            }
        } catch {
            # 继续等待
        }
        
        if ($waited % 5 -eq 0) {
            $waitSeconds = $waited
            $waitMsg = "Waiting... " + $waitSeconds + " seconds"
            Write-Info $waitMsg
        }
    }
    
    if ($ready) {
        $waitedSeconds = $waited
        $readyMsg = "API server ready, waited " + $waitedSeconds + " seconds"
        Write-Success $readyMsg
        return @{Success = $true; ProcessId = $processId; CmdProcessId = $cmdProcess.Id; LogFile = $logFile}
    } else {
        $timeoutSeconds = $waited
        $timeoutMsg = "API server startup timeout, waited " + $timeoutSeconds + " seconds"
        Write-Error $timeoutMsg
        Write-Info "Check log: Get-Content $logFile -Tail 50"
        if (Test-Path $logFile) {
            Write-Info "Log content:"
            Get-Content $logFile -Tail 50 | ForEach-Object { Write-Host "  $_" }
        }
        try {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        } catch {
            # 忽略错误
        }
        try {
            Stop-Process -Id $cmdProcess.Id -Force -ErrorAction SilentlyContinue
        } catch {
            # 忽略错误
        }
        return @{Success = $false; ProcessId = $processId; CmdProcessId = $cmdProcess.Id; LogFile = $logFile}
    }
}

# =============================================================
# 主函数
# =============================================================
function Main {
    Write-Info "=========================================="
    Write-Info "MindVoice API Server - Windows Startup"
    Write-Info "=========================================="
    Write-Host ""
    
    # 切换到项目目录
    Set-Location $PROJECT_DIR
    
    # 环境检查
    Test-Environment
    
    # 检查单实例运行
    if (Test-Port -Port $API_PORT -IPAddress $API_HOST) {
        Write-Warning "Port $API_PORT is in use"
        $response = Read-Host "Stop old instance and start new one? (y/N)"
        if ($response -eq "y" -or $response -eq "Y") {
            Stop-APIProcesses
            Start-Sleep -Seconds 1
        } else {
            Write-Info "Exiting"
            exit 0
        }
    }
    
    # 启动 API 服务器
    $result = Start-APIServer
    if ($result.Success) {
        Write-Host ""
        Write-Success "API server running (http://${API_HOST}:${API_PORT})"
        Write-Host ""
        Write-Info "Press Ctrl+C to stop the server"
        Write-Host ""
        
        # 保持运行（等待 Python 进程）
        $processId = $result.ProcessId
        try {
            $running = $true
            while ($running) {
                Start-Sleep -Seconds 1
                try {
                    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if (-not $proc) {
                        $running = $false
                    }
                } catch {
                    $running = $false
                }
            }
            Write-Info "Server stopped"
        } catch {
            Write-Info "Server stopped"
        }
    } else {
        Write-Error "Startup failed"
        exit 1
    }
}

# 处理命令行参数
if ($args.Count -gt 0) {
    switch ($args[0]) {
        "--help" {
            Write-Host "Usage: .\start_api.ps1 [options]"
            Write-Host ""
            Write-Host "Options:"
            Write-Host "  --help      Show help information"
            Write-Host ""
            Write-Host "Features:"
            Write-Host "  - Auto-configure HuggingFace mirror (use domestic mirror for faster downloads)"
            Write-Host "  - Disable progress bars (avoid Windows background thread errors)"
            Write-Host "  - Start API server"
            exit 0
        }
        default {
            Write-Error "Unknown parameter: $($args[0])"
            Write-Info "Use --help to view help information"
            exit 1
        }
    }
}

# 执行主函数
Main
