$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    throw '找不到 .env，請先執行金鑰遷移。'
}
Get-Content -LiteralPath $envPath -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2], 'Process')
    }
}
if (-not $env:NGROK_AUTHTOKEN) {
    throw '缺少 NGROK_AUTHTOKEN。'
}
$port = if ($env:APP_PORT) { $env:APP_PORT } else { '5000' }
$ngrokPath = $env:NGROK_EXE
if (-not $ngrokPath) {
    $ngrokCommand = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($ngrokCommand) {
        $ngrokPath = $ngrokCommand.Source
    }
}
if (-not $ngrokPath) {
    $bundledCandidate = 'C:\Users\USER\miniconda3\Scripts\ngrok.exe'
    if (Test-Path -LiteralPath $bundledCandidate) {
        $ngrokPath = $bundledCandidate
    }
}
if (-not $ngrokPath -or -not (Test-Path -LiteralPath $ngrokPath)) {
    throw '找不到 ngrok。請把 ngrok 加入 PATH，或在 .env 設定 NGROK_EXE。'
}
& $ngrokPath http $port
