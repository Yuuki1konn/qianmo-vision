<#
.SYNOPSIS
    把本地模型资产发布到 GitHub Releases，并补齐仓库描述与 topics。

.DESCRIPTION
    仓库不跟踪模型文件（体积大且是二进制），模型统一走 Releases 分发。
    本脚本做三件事：
      1. 确保 tag 对应的 Release 存在（默认 models-v1）
      2. 把 releases/models-v1/ 下的模型逐个上传（已存在的同名 asset 自动跳过）
      3. 顺手设置仓库 description 与 topics

.PARAMETER Token
    GitHub Token。优先取参数，其次取环境变量 GITHUB_TOKEN。
    需要权限：classic token 勾 `repo`；fine-grained token 给 Contents: Read and write。

.PARAMETER Repo
    仓库全名，默认 Yuuki1konn/qianmo-vision。

.PARAMETER Tag
    Release tag，默认 models-v1（与 README 里的下载链接一致）。

.PARAMETER AssetDir
    模型所在目录，默认 releases/models-v1。

.EXAMPLE
    $env:GITHUB_TOKEN = "ghp_xxxxxxxx"
    pwsh ./scripts/publish_release.ps1

.EXAMPLE
    pwsh ./scripts/publish_release.ps1 -Token $env:GITHUB_TOKEN -Tag models-v1
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
$headers = @{
    "Authorization"          = "Bearer $Token"
    "Accept"                 = "application/vnd.github+json"
    "X-GitHub-Api-Version"   = "2022-11-28"
    "User-Agent"             = "qianmo-vision-release-script"
}

function Invoke-GitHub {
    param(
        [string]$Method,
        [string]$Uri,
        $Body,
        [string]$InFile,
        [string]$ContentType = "application/json"
    )
    $params = @{ Method = $Method; Uri = $Uri; Headers = $headers }
    if ($InFile) {
        $params.InFile = $InFile
        $params.ContentType = $ContentType
    }
    elseif ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 5)
        $params.ContentType = "application/json"
    }
    return Invoke-RestMethod @params
}

# ---------- 0. 前置检查 ----------
if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "缺少 Token。请设置环境变量 GITHUB_TOKEN，或用 -Token 传入。"
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$dir = if ([System.IO.Path]::IsPathRooted($AssetDir)) { $AssetDir } else { Join-Path $root $AssetDir }
if (-not (Test-Path -LiteralPath $dir)) {
    throw "找不到模型目录：$dir"
}

$files = Get-ChildItem -LiteralPath $dir -File | Where-Object { $_.Extension -in @(".tflite", ".onnx", ".pt") }
if (-not $files) {
    throw "$dir 里没有 .tflite / .onnx / .pt 文件。"
}

Write-Host "仓库: $Repo"
Write-Host "Tag : $Tag"
Write-Host "待传: $($files.Count) 个文件，共 $([math]::Round(($files | Measure-Object Length -Sum).Sum / 1MB, 1)) MB"
foreach ($f in $files) {
    Write-Host ("  - {0}  ({1:N1} MB)" -f $f.Name, ($f.Length / 1MB))
}

# ---------- 1. 取或建 Release ----------
$release = $null
try {
    $release = Invoke-GitHub -Method Get -Uri "$api/repos/$Repo/releases/tags/$Tag"
    Write-Host "`nRelease 已存在，复用：$($release.html_url)"
}
catch {
    Write-Host "`nRelease 不存在，创建中…"
    $release = Invoke-GitHub -Method Post -Uri "$api/repos/$Repo/releases" -Body @{
        tag_name         = $Tag
        name             = $Title
        body             = "QianMo Vision 端侧模型资产。下载后放入 ``android/app/src/main/assets/``，SHA-256 见 README。"
        draft            = $false
        prerelease       = $false
    }
    Write-Host "已创建：$($release.html_url)"
}

# ---------- 2. 上传 asset ----------
$uploadBase = ($release.upload_url -replace '\{\?name,label\}', '')
$existing = @($release.assets | ForEach-Object { $_.name })

foreach ($f in $files) {
    if ($existing -contains $f.Name) {
        Write-Host "跳过（已存在）：$($f.Name)"
        continue
    }
    Write-Host "上传：$($f.Name) …"
    $encoded = [uri]::EscapeDataString($f.Name)
    Invoke-GitHub -Method Post -Uri "$uploadBase?name=$encoded" -InFile $f.FullName -ContentType "application/octet-stream" | Out-Null
    Write-Host "  完成"
}

# ---------- 3. 仓库描述与 topics ----------
Write-Host "`n更新仓库信息…"
Invoke-GitHub -Method Patch -Uri "$api/repos/$Repo" -Body @{
    description = $Description
    topics      = $Topics
} | Out-Null
Write-Host "已设置 description 与 $($Topics.Count) 个 topics"

Write-Host "`n全部完成：$($release.html_url)"
Write-Host "验证下载链接：$($release.html_url)/download/$Tag/<文件名>"
