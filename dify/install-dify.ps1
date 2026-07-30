# Dify 本地安装脚本（Windows）
# 用法：在 PowerShell 中执行
#   cd D:\Dify_agent\dify
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
#   .\install-dify.ps1

$ErrorActionPreference = "Stop"
$DifyRoot = "D:\dify"
$DockerDir = Join-Path $DifyRoot "docker"

function Test-DockerReady {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        Write-Host "[!] 未检测到 Docker。请先安装 Docker Desktop 并启动（托盘图标为 Running）。" -ForegroundColor Yellow
        Write-Host "    安装：winget install -e Docker.DockerDesktop" -ForegroundColor Yellow
        return $false
    }
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Docker 已安装但未运行。请打开 Docker Desktop 等待启动完成。" -ForegroundColor Yellow
        return $false
    }
    return $true
}

function Clone-Dify {
    if (Test-Path $DockerDir) {
        Write-Host "[OK] 已存在 $DockerDir，跳过克隆" -ForegroundColor Green
        return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $DifyRoot) | Out-Null
    $mirrors = @(
        "https://github.com/langgenius/dify.git",
        "https://gitclone.com/github.com/langgenius/dify.git",
        "https://mirror.ghproxy.com/https://github.com/langgenius/dify.git"
    )
    foreach ($url in $mirrors) {
        Write-Host "尝试克隆: $url"
        git clone --depth 1 $url $DifyRoot 2>&1
        if ($LASTEXITCODE -eq 0 -and (Test-Path $DockerDir)) {
            Write-Host "[OK] 克隆成功" -ForegroundColor Green
            return
        }
    }
    Write-Host "[!] 自动克隆失败。请手动：" -ForegroundColor Red
    Write-Host "  1. 浏览器打开 https://github.com/langgenius/dify/archive/refs/heads/main.zip 下载解压到 D:\dify"
    Write-Host "  2. 或用手机热点重试: git clone https://github.com/langgenius/dify.git D:\dify"
    exit 1
}

function Start-Dify {
    Push-Location $DockerDir
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "[OK] 已创建 docker\.env" -ForegroundColor Green
    }
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] docker compose 启动失败" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " Dify 已启动（首次约需 2-5 分钟拉镜像）" -ForegroundColor Cyan
    Write-Host " 浏览器打开: http://localhost/install" -ForegroundColor Cyan
    Write-Host " 配置教程:   D:\Dify_agent\dify\SETUP_手把手教程.md" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

if (-not (Test-DockerReady)) { exit 1 }
Clone-Dify
Start-Dify
