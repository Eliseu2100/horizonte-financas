$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    $pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Crie a .venv e instale requirements-dev.txt antes do build.' }
    & $pythonExe scripts/prepare_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Preparação do ícone falhou.' }
    & $pythonExe -m PyInstaller --noconfirm --windowed --onedir --name Elisei --icon src/elisei.ico --add-data 'src/elisei.ico;.' --exclude-module PySide6.QtWebEngineCore --exclude-module tkinter src/launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Build do executável falhou.' }
    # Qt usa a ICU nativa do Windows. O coletor pode selecionar uma ICU com exports incompatíveis.
    $incompatibleIcu = Join-Path $projectRoot 'dist/Elisei/_internal/icuuc.dll'
    if (Test-Path -LiteralPath $incompatibleIcu) { Remove-Item -LiteralPath $incompatibleIcu }
    & $pythonExe scripts/collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'Coleta de licenças falhou.' }
    Write-Host 'Executável disponível em dist/Elisei/Elisei.exe'
} finally { Pop-Location }
    
