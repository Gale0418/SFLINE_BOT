[CmdletBinding()]
param(
    [string]$GoogleKeySource,
    [int]$GoogleKeyLine,
    [string]$GoogleModel = 'gemma-4-26b-a4b-it'
)

$ErrorActionPreference = 'Stop'

if ($PSBoundParameters.ContainsKey('GoogleKeyLine') -and -not $GoogleKeySource) {
    throw 'GoogleKeyLine 必須搭配 GoogleKeySource 使用。'
}
if ($GoogleKeySource) {
    if (-not (Test-Path -LiteralPath $GoogleKeySource -PathType Leaf)) {
        throw "指定的金鑰來源檔案不存在: $GoogleKeySource"
    }
    if ($GoogleKeyLine -lt 1) {
        throw "GoogleKeyLine 必須為大於等於 1 的行號。"
    }
    $lines = @(Get-Content -LiteralPath $GoogleKeySource -Encoding UTF8)
    if ($GoogleKeyLine -gt $lines.Count) {
        throw "指定的行號 ($GoogleKeyLine) 超出檔案總行數 ($($lines.Count))。"
    }
    $key = $lines[$GoogleKeyLine - 1].Trim()
    if ([string]::IsNullOrWhiteSpace($key)) {
        throw "指定的行 ($GoogleKeyLine) 內容為空或僅包含空白。"
    }
    $env:AI_PROVIDER = 'google'
    $env:GEMINI_API_KEY = $key
    $env:GEMINI_MODEL = $GoogleModel
    if (-not $env:MODEL_TIMEOUT_SECONDS) {
        $env:MODEL_TIMEOUT_SECONDS = '5'
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    Get-Content -LiteralPath $envPath -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$' -and -not [Environment]::GetEnvironmentVariable($matches[1].Trim(), 'Process')) {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2], 'Process')
        }
    }
}
if (-not $env:MODEL_TIMEOUT_SECONDS) {
    # Current dispatcher defaults are validated against LINE's reply-token budget at 5 seconds.
    $env:MODEL_TIMEOUT_SECONDS = '5'
}
if (-not $env:PUBLIC_BASE_URL) {
    try {
        $tunnels = Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 2
        $httpsTunnel = $tunnels.tunnels | Where-Object { $_.public_url -like 'https://*' } | Select-Object -First 1
        if ($httpsTunnel) {
            $env:PUBLIC_BASE_URL = $httpsTunnel.public_url.TrimEnd('/')
            Write-Host "已自動使用 ngrok 公開網址提供知識卡圖片。"
        }
    }
    catch {
        Write-Warning '找不到 ngrok HTTPS tunnel；知識卡仍可顯示文字，但暫不附圖片。'
    }
}
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw '找不到 Python 3.11 虛擬環境，請先依 README 執行安裝。'
}
& $pythonPath -m eternal_polaris
