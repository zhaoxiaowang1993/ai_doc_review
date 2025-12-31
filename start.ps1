# ============================================================
# 🚀 AI Document Review - 一键启动脚本 (PowerShell)
# ============================================================
# 功能：同时启动后端 API 和前端 UI
# 用法：右键点击 start.ps1 -> 使用 PowerShell 运行
#       或在 PowerShell 中执行: .\start.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "AI Document Review - Launcher"

# 颜色输出函数
function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Write-Banner {
    Write-Color ""
    Write-Color "╔══════════════════════════════════════════════════════════╗" "Cyan"
    Write-Color "║        🚀 AI Document Review - 一键启动                  ║" "Cyan"
    Write-Color "╚══════════════════════════════════════════════════════════╝" "Cyan"
    Write-Color ""
}

# 检查 Node.js
function Test-NodeJS {
    try {
        $version = node --version 2>$null
        if ($version) {
            Write-Color "✅ Node.js: $version" "Green"
            return $true
        }
    } catch {}
    Write-Color "❌ Node.js 未安装，请先安装 Node.js" "Red"
    return $false
}

# 检查 Python
function Test-Python {
    try {
        $version = python --version 2>$null
        if ($version) {
            Write-Color "✅ Python: $version" "Green"
            return $true
        }
    } catch {}
    Write-Color "❌ Python 未安装，请先安装 Python" "Red"
    return $false
}

# 主流程
Write-Banner

$ProjectRoot = $PSScriptRoot
Write-Color "📁 项目目录: $ProjectRoot" "Yellow"
Write-Color ""

# 环境检查
Write-Color "🔍 环境检查..." "Yellow"
$nodeOk = Test-NodeJS
$pythonOk = Test-Python

if (-not ($nodeOk -and $pythonOk)) {
    Write-Color ""
    Write-Color "⚠️  请先安装缺失的依赖后重试" "Red"
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Color ""

# 检查环境变量文件
$envFile = Join-Path $ProjectRoot "app\api\.env"
if (-not (Test-Path $envFile)) {
    Write-Color "⚠️  未找到 app\api\.env 文件" "Yellow"
    Write-Color "   请复制 app\api\.env.tpl 并重命名为 .env，然后配置 API Key" "Yellow"
    Write-Color ""
}

# 启动后端
Write-Color "🔧 启动后端服务 (FastAPI)..." "Cyan"
$backendPath = Join-Path $ProjectRoot "app\api"
$backendCmd = @"
cd '$backendPath'
if (Test-Path 'venv\Scripts\Activate.ps1') {
    & '.\venv\Scripts\Activate.ps1'
}
python -m uvicorn main:app --host 0.0.0.0 --port 1231 --reload
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

Write-Color "   ✅ 后端服务已在新窗口启动" "Green"
Write-Color "   📍 API 地址: http://localhost:1231" "White"
Write-Color "   📍 API 文档: http://localhost:1231/docs" "White"
Write-Color ""

# 等待后端启动
Write-Color "⏳ 等待后端服务启动 (5秒)..." "Yellow"
Start-Sleep -Seconds 5

# 启动前端
Write-Color "🎨 启动前端服务 (Vite)..." "Cyan"
$frontendPath = Join-Path $ProjectRoot "app\ui"
$frontendCmd = @"
cd '$frontendPath'
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

Write-Color "   ✅ 前端服务已在新窗口启动" "Green"
Write-Color "   📍 前端地址: http://localhost:1230" "White"
Write-Color ""

# 完成
Write-Color "═══════════════════════════════════════════════════════════" "Cyan"
Write-Color "🎉 所有服务已启动！" "Green"
Write-Color ""
Write-Color "📌 服务地址:" "Yellow"
Write-Color "   • 前端 UI:  http://localhost:1230" "White"
Write-Color "   • 后端 API: http://localhost:1231" "White"
Write-Color "   • API 文档: http://localhost:1231/docs" "White"
Write-Color ""
Write-Color "📌 关闭服务:" "Yellow"
Write-Color "   • 关闭各自的 PowerShell 窗口即可停止服务" "White"
Write-Color "═══════════════════════════════════════════════════════════" "Cyan"
Write-Color ""

# 询问是否打开浏览器
$openBrowser = Read-Host "是否打开浏览器？(Y/n)"
if ($openBrowser -ne "n" -and $openBrowser -ne "N") {
    Start-Process "http://localhost:1230"
}

Write-Color ""
Write-Color "按 Enter 键关闭此窗口（服务会继续运行）..." "Gray"
Read-Host

