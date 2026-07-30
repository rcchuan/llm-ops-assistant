# MySQL setup using project-local data directory (no admin required for Program Files)
# Usage:
#   cd D:\Dify_agent\scripts
#   .\setup_mysql.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Dify_agent"
$MySqlRoot = "C:\Program Files\MySQL\MySQL Server 8.4"
$Bin = Join-Path $MySqlRoot "bin"
$DataDir = Join-Path $ProjectRoot "storage\mysql\data"
$RootPassword = "DifyOps@2026"
$ProjectEnv = Join-Path $ProjectRoot ".env"
$Port = 3306

Write-Host "=== MySQL setup (project datadir) ===" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $Bin "mysqld.exe"))) {
    throw "MySQL Server not installed. Run: winget install Oracle.MySQL"
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

if (-not (Test-Path (Join-Path $DataDir "mysql"))) {
    Write-Host "[1/4] Initialize datadir: $DataDir" -ForegroundColor Yellow
    & (Join-Path $Bin "mysqld.exe") --initialize-insecure --datadir=$DataDir --console
} else {
    Write-Host "[1/4] Datadir already initialized" -ForegroundColor Gray
}

Write-Host "[2/4] Start mysqld on port $Port ..." -ForegroundColor Yellow
$mysqldProc = Get-Process mysqld -ErrorAction SilentlyContinue
if (-not $mysqldProc) {
    Start-Process -FilePath (Join-Path $Bin "mysqld.exe") `
        -ArgumentList "--datadir=$DataDir", "--port=$Port", "--standalone" `
        -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

Write-Host "[3/4] Set root password ..." -ForegroundColor Yellow
$alterSql = "ALTER USER 'root'@'localhost' IDENTIFIED BY '$RootPassword'; FLUSH PRIVILEGES;"
& (Join-Path $Bin "mysql.exe") -u root -P $Port -e $alterSql 2>$null
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $Bin "mysql.exe") -u root -p$RootPassword -P $Port -e "SELECT 1" 2>$null
}

Write-Host "[4/4] Update .env ..." -ForegroundColor Yellow
if (Test-Path $ProjectEnv) {
    $content = Get-Content $ProjectEnv -Raw -Encoding UTF8
    $content = $content -replace 'MYSQL_PASSWORD=.*', "MYSQL_PASSWORD=$RootPassword"
    $content = $content -replace 'MYSQL_PORT=.*', "MYSQL_PORT=$Port"
    [System.IO.File]::WriteAllText($ProjectEnv, $content, [System.Text.UTF8Encoding]::new($false))
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$Bin*") {
    [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(';') + ";" + $Bin), "User")
}

Write-Host ""
Write-Host "MySQL ready!" -ForegroundColor Green
Write-Host "  datadir : $DataDir"
Write-Host "  password: $RootPassword"
Write-Host "  port    : $Port"
Write-Host "Next: python scripts/init_db.py"
