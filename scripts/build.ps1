param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$buildProject = Split-Path -Parent $PSScriptRoot
$buildApp = Join-Path $buildProject 'work\app'

& $Python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx `
    --name CICMasker `
    --icon (Join-Path $buildApp 'cic_masker.ico') `
    --version-file (Join-Path $buildApp 'version_info.txt') `
    --distpath (Join-Path $buildProject 'outputs') `
    --workpath (Join-Path $buildProject 'work\pyinstaller\build') `
    --specpath (Join-Path $buildProject 'work\pyinstaller') `
    --exclude-module pandas --exclude-module numpy --exclude-module openpyxl `
    --exclude-module lxml --exclude-module sqlite3 --exclude-module dateutil `
    --exclude-module tzdata (Join-Path $buildApp 'cic_masker.py')
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
