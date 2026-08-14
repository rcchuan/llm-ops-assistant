# 一键运行（MySQL 已启动前提下）
# cd D:\Dify_agent\scripts
# .\run_all.ps1

$ErrorActionPreference = "Stop"
Set-Location "D:\Dify_agent"

Write-Host "1/4 init db..." -ForegroundColor Cyan
python scripts/init_db.py

Write-Host "2/4 clean corpus..." -ForegroundColor Cyan
python data_clean.py --clean

Write-Host "3/4 upload to Dify..." -ForegroundColor Cyan
python data_clean.py --upload

Write-Host "4/4 work orders..." -ForegroundColor Cyan
python work_order_sql.py --all

Write-Host "Done. Start web: python app.py" -ForegroundColor Green
