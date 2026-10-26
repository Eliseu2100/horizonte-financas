$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$toolDir = Join-Path $projectRoot 'build/inno'
$compiler = Join-Path $toolDir 'tools/ISCC.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    New-Item -ItemType Directory -Force $toolDir | Out-Null
    $archive = Join-Path $toolDir 'inno.zip'
    Invoke-WebRequest 'https://www.nuget.org/api/v2/package/Tools.InnoSetup/6.7.3' -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $toolDir -Force
}
& $compiler /Q (Join-Path $PSScriptRoot 'installer.iss')
if ($LASTEXITCODE -ne 0) { throw 'Compilação do instalador falhou.' }
$installer = Join-Path $projectRoot 'release/Horizonte-Instalar-0.2.0-Windows-x64.exe'
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLower()
"$hash  $(Split-Path $installer -Leaf)" | Set-Content -Encoding utf8 (Join-Path $projectRoot 'release/SHA256.txt')
  
