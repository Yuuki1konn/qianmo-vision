<#
.SYNOPSIS
    把本地模型资产发布到 GitHub Releases，并补齐仓库描述与 topics。

.DESCRIPTION
    仓库不跟踪模型文件（体积大且是二进制），模型统一走 Releases 分发。
    本脚本做三件事：
      1. 确保 tag 对应的 Release 存在（默认 models-v1）
      2. 把 releases/models-v1/ 下的模型逐个上传（已存在的同名 asset 自动跳过）
      3. 补齐仓库 description 与 topics

    Token 获取顺序：-Token 参数 → 环境变量 GITHUB_TOKEN → 复用 git 凭据管理器里 push 用过的凭据。
    只要这个仓库 push 成功过，直接运行脚本即可，不用手动贴 token。

    传输统一走 curl.exe（Windows 10+ 自带）：PowerShell 的 Invoke-RestMethod 在部分代理/证书
    环境会报 "The SSL connection could not be established"，curl 走系统证书链更稳。

.PARAMETER Token
    GitHub Token。留空则自动从 git credential 读取。

.PARAMETER Repo
    仓库全名，默认 Yuuki1konn/qianmo-vision。

.PARAMETER Tag
    Release tag，默认 models-v1（与 README 里的下载链接一致）。

.PARAMETER AssetDir
    模型所在目录，默认 releases/models-v1。

.EXAMPLE
    pwsh ./scripts/publish_release.ps1

.EXAMPLE
    $env:GITHUB_TOKEN = "ghp_xxx"; pwsh ./scripts/publish_release.ps1 -Tag models-v1
#>
param(
    [string]$Token = $env:GITHUB_TOKEN,
    [string]$Repo = "Yuuki1konn/qianmo-vision",
    [string]$Tag = "models-v1",
    [string]$Title = "模型资产 v1（QianMo Vision）",
    [string]$AssetDir = "releases/models-v1",
    [string]$Description = "端侧感知基线：可行驶区域分割 + 二轮车/障碍物检测 + 中文语音告警（Android / TFLite）",
    [string[]]$Topics = @(
        "android", "kotlin", "tflite", "onnx", "pytorch", "yolov8",
        "semantic-segmentation", "object-detection", "edge-ai", "adas", "camerax", "rural"
    )
)

$ErrorActionPreference = "Stop"
$api = "https://api.github.com"
$ua = "qianmo-vision-release-script"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("qm-release-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $work -Force | Out-Null

function Get-GitHubToken {
    if (-not [string]::IsNullOrWhiteSpace($Token)) { return $Token }
    if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) { return $env:GITHUB_TOKEN }

    $env:GCM_INTERACTIVE = "never"
    $env:GIT_TERMINAL_PROMPT = "0"
    $resp = "protocol=https`nhost=github.com`n`n" | git credential fill 2>$null
    $found = ($resp | Where-Object { $_ -like "password=*" }) -replace "^password=", ""
    if ([string]::IsNullOrWhiteSpace($found)) {
        throw "没有可用 Token。请先 git push 一次（让凭据管理器存下凭据），或设置 GITHUB_TOKEN。"
    }
    Write-Host "已复用 git 凭据管理器里的 Token（$($found.Substring(0, [Math]::Min(4, $found.Length)))***）"
    return $found
}

# 统一请求：响应体写文件，状态码单独取，避免 PowerShell 解析原生输出时踩坑
function Invoke-Curl {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Json,
        [string]$UploadFile
    )
    $outFile = Join-Path $work ("resp-" + [guid]::NewGuid().ToString("N").Substring(0, 8) + ".json")
    # 注意：HTTP 方法必须大写，否则 GitHub 会回 403（curl 会原样发送 -X 的字符串）
    $verb = $Method.ToUpperInvariant()
    $cargs = @(
        "-s", "-o", $outFile, "-w", "%{http_code}",
        "-X", $verb, $Uri,
        "-H", "Authorization: Bearer $script:token",
        "-H", "Accept: application/vnd.github+json",
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "-H", "User-Agent: $ua"
    )
    if ($UploadFile) {
        $cargs += @("-H", "Content-Type: application/octet-stream", "--data-binary", "@$UploadFile")
    }
    elseif ($Json) {
        $bodyFile = Join-Path $work ("body-" + [guid]::NewGuid().ToString("N").Substring(0, 8) + ".json")
        [System.IO.File]::WriteAllText($bodyFile, ($Json | ConvertTo-Json -Compress), $utf8)
        $cargs += @("-H", "Content-Type: application/json", "--data-binary", "@$bodyFile")
    }

    $code = (& curl.exe @cargs) -join ""
    if ($env:QM_DEBUG) {
        $shown = ($cargs | ForEach-Object { if ($_ -like "Authorization*") { "Authorization: Bearer ***" } else { $_ } }) -join " | "
        Write-Host "[debug] curl $shown"
        Write-Host "[debug] code=$code"
    }
    $raw = if (Test-Path -LiteralPath $outFile) { Get-Content -LiteralPath $outFile -Raw } else { "" }
    if ($code -notmatch "^2\d\d$") {
        $snippet = if ($raw.Length -gt 400) { $raw.Substring(0, 400) } else { $raw }
        throw "HTTP $code  $Method $Uri`n$snippet"
    }
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    return $raw | ConvertFrom-Json
}

try {
    # ---------- 0. 前置检查 ----------
    $script:token = Get-GitHubToken

    $root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    $dir = if ([System.IO.Path]::IsPathRooted($AssetDir)) { $AssetDir } else { Join-Path $root $AssetDir }
    if (-not (Test-Path -LiteralPath $dir)) { throw "找不到模型目录：$dir" }

    $files = Get-ChildItem -LiteralPath $dir -File | Where-Object { $_.Extension -in @(".tflite", ".onnx", ".pt") }
    if (-not $files) { throw "$dir 里没有 .tflite / .onnx / .pt 文件。" }

    Write-Host "仓库: $Repo"
    Write-Host "Tag : $Tag"
    Write-Host "待传: $($files.Count) 个文件，共 $([math]::Round(($files | Measure-Object Length -Sum).Sum / 1MB, 1)) MB"
    foreach ($f in $files) { Write-Host ("  - {0}  ({1:N1} MB)" -f $f.Name, ($f.Length / 1MB)) }

    # ---------- 1. 取或建 Release ----------
    $release = $null
    try {
        $release = Invoke-Curl -Method Get -Uri "$api/repos/$Repo/releases/tags/$Tag"
        Write-Host "`nRelease 已存在，复用：$($release.html_url)"
    }
    catch {
        if ($_.Exception.Message -notmatch "HTTP 404") { throw }
        Write-Host "`nRelease 不存在，创建中…"
        $release = Invoke-Curl -Method Post -Uri "$api/repos/$Repo/releases" -Json @{
            tag_name   = $Tag
            name       = $Title
            body       = "QianMo Vision 端侧模型资产。下载后放入 android/app/src/main/assets/，SHA-256 见 README。"
            draft      = $false
            prerelease = $false
        }
        Write-Host "已创建：$($release.html_url)"
    }

    # ---------- 2. 上传 asset ----------
    $uploadBase = ($release.upload_url -replace "\{\?name,label\}", "")
    $existing = @($release.assets | ForEach-Object { $_.name })

    foreach ($f in $files) {
        if ($existing -contains $f.Name) {
            Write-Host "跳过（已存在）：$($f.Name)"
            continue
        }
        Write-Host ("上传：{0}  ({1:N1} MB) …" -f $f.Name, ($f.Length / 1MB))
        $encoded = [uri]::EscapeDataString($f.Name)
        Invoke-Curl -Method Post -Uri "$uploadBase`?name=$encoded" -UploadFile $f.FullName | Out-Null
        Write-Host "  完成"
    }

    # ---------- 3. 仓库描述与 topics ----------
    Write-Host "`n更新仓库信息…"
    Invoke-Curl -Method Patch -Uri "$api/repos/$Repo" -Json @{ description = $Description } | Out-Null
    Invoke-Curl -Method Put -Uri "$api/repos/$Repo/topics" -Json @{ names = $Topics } | Out-Null
    Write-Host "已设置 description 与 $($Topics.Count) 个 topics"

    # ---------- 4. 校验 ----------
    $final = Invoke-Curl -Method Get -Uri "$api/repos/$Repo/releases/tags/$Tag"
    Write-Host "`nRelease 现状：$($final.html_url)"
    foreach ($a in $final.assets) {
        Write-Host ("  - {0}  {1:N1} MB  {2}" -f $a.name, ($a.size / 1MB), $a.digest)
    }
    Write-Host "`n下载直链：https://github.com/$Repo/releases/download/$Tag/<文件名>"
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
