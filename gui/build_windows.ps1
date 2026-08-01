$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$release = Join-Path $root "release"

python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller markdown
python -m PyInstaller --noconfirm (Join-Path $root "LinkDistill.spec")

$webviewLib = Join-Path (python -c "import webview, pathlib; print(pathlib.Path(webview.__file__).parent / 'lib')") ""
$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$hostExe = Join-Path $root "dist\LinkDistill\LinkDistill.WebView2Host.exe"
$webviewCore = Join-Path $webviewLib "Microsoft.Web.WebView2.Core.dll"
$webviewForms = Join-Path $webviewLib "Microsoft.Web.WebView2.WinForms.dll"
& $csc /nologo /target:winexe /platform:x64 /out:$hostExe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll "/reference:$webviewCore" "/reference:$webviewForms" (Join-Path $root "WebView2Host.cs")
Copy-Item -LiteralPath (Join-Path $webviewLib "Microsoft.Web.WebView2.Core.dll") -Destination (Join-Path $root "dist\LinkDistill") -Force
Copy-Item -LiteralPath (Join-Path $webviewLib "Microsoft.Web.WebView2.WinForms.dll") -Destination (Join-Path $root "dist\LinkDistill") -Force
Copy-Item -LiteralPath (Join-Path $webviewLib "runtimes\win-x64\native\WebView2Loader.dll") -Destination (Join-Path $root "dist\LinkDistill") -Force
$webviewSetup = Join-Path $root "dist\LinkDistill\MicrosoftEdgeWebview2Setup.exe"
Invoke-WebRequest -UseBasicParsing -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" -OutFile $webviewSetup

$ytDlp = Join-Path $root "dist\LinkDistill\yt-dlp.exe"
$localYtDlp = Get-Command yt-dlp.exe -ErrorAction SilentlyContinue
if ($localYtDlp) {
    Copy-Item -LiteralPath $localYtDlp.Source -Destination $ytDlp -Force
} else {
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile $ytDlp
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    $ffmpeg = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter ffmpeg.exe -Recurse | Select-Object -First 1
}
if (-not $ffmpeg) { throw "ffmpeg.exe was not found" }
$ffmpegPath = if ($ffmpeg.Source) { $ffmpeg.Source } else { $ffmpeg.FullName }
Copy-Item -LiteralPath $ffmpegPath -Destination (Join-Path $root "dist\LinkDistill\ffmpeg.exe") -Force
$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $ffprobe) {
    $ffprobe = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter ffprobe.exe -Recurse | Select-Object -First 1
}
if ($ffprobe) {
    $ffprobePath = if ($ffprobe.Source) { $ffprobe.Source } else { $ffprobe.FullName }
    Copy-Item -LiteralPath $ffprobePath -Destination (Join-Path $root "dist\LinkDistill\ffprobe.exe") -Force
}

if (-not (Test-Path -LiteralPath $release)) { New-Item -ItemType Directory -Path $release | Out-Null }
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$isccPath = if ($iscc) { $iscc.Source } else { "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path -LiteralPath $isccPath)) { throw "Inno Setup compiler was not found" }
& $isccPath (Join-Path $root "installer.iss")
