<#
.SYNOPSIS
  Подготовка Windows-окружения для Shorts Studio (HyperFrames + whisper.cpp + FFmpeg).

.DESCRIPTION
  Поэтапно: проверка окружения -> FFmpeg -> HyperFrames + Chrome Headless Shell -> whisper.cpp
  (интеграция HyperFrames, русская модель) -> навыки Claude Code -> проект shorts-studio -> тестовый рендер.
  Уже работающие компоненты не переустанавливаются. Существующие файлы проекта не перезаписываются.
  Права администратора не нужны; если winget попросит повышение (UAC) — это запрос Windows, решаете вы.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -Model medium
#>
[CmdletBinding()]
param(
  [string]$ProjectDir = (Join-Path $env:USERPROFILE "shorts-studio"),
  [ValidateSet("small", "medium", "large-v3")]
  [string]$Model = "small",
  [switch]$SkipSkills,
  [switch]$Play
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$TemplateDir = Split-Path -Parent $PSScriptRoot
$Report = New-Object System.Collections.Generic.List[string]

function Step($n, $text) { Write-Host ""; Write-Host "=== [$n] $text ===" -ForegroundColor Cyan }
function Ok($text) { Write-Host "  OK  $text" -ForegroundColor Green; $Report.Add("OK    $text") }
function Info($text) { Write-Host "  ..  $text" }
function Warn($text) { Write-Host "  !!  $text" -ForegroundColor Yellow; $Report.Add("WARN  $text") }
function Fail($text) {
  Write-Host "  XX  $text" -ForegroundColor Red
  $Report.Add("FAIL  $text")
  Write-Host ""; $Report | ForEach-Object { Write-Host $_ }
  exit 1
}
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
  $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $user = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$machine;$user"
}
# Запуск внешней программы: вывод виден, ненулевой код возврата -> исключение.
function Run($file) {
  $rest = $args
  & $file @rest
  if ($LASTEXITCODE -ne 0) { throw "$file $($rest -join ' ') завершился с кодом $LASTEXITCODE" }
}
# Запуск с подавленным выводом; возвращает код возврата. В PowerShell 5.1 перенаправление stderr
# внешней программы при ErrorActionPreference=Stop превращается в исключение, поэтому здесь Continue.
function Quiet($file) {
  $rest = $args
  $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  try { & $file @rest *> $null; return $LASTEXITCODE } finally { $ErrorActionPreference = $prev }
}
function FirstLine($file) {
  $rest = $args
  try { (& $file @rest | Select-Object -First 1) } catch { $null }
}
function Winget-Install($id) {
  if (-not (Has "winget")) { Fail "winget не найден. Установите 'App Installer' из Microsoft Store и запустите скрипт снова." }
  Info "winget install --id $id"
  & winget install --id $id -e --source winget --accept-source-agreements --accept-package-agreements
  # -1978335189 = APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE (уже установлено)
  if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) { Fail "winget install $id завершился с кодом $LASTEXITCODE" }
  Refresh-Path
}

# ---------------------------------------------------------------- 1
Step 1 "Проверка окружения"
$os = Get-CimInstance Win32_OperatingSystem
Info "ОС: $($os.Caption) $($os.Version) ($env:PROCESSOR_ARCHITECTURE)"
if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") { Warn "Архитектура $env:PROCESSOR_ARCHITECTURE: готовые сборки whisper.cpp рассчитаны на x64." }
Info ("winget:  " + $(if (Has "winget") { FirstLine winget --version } else { "нет" }))
Info ("Node.js: " + $(if (Has "node") { FirstLine node --version } else { "нет" }))
Info ("npm:     " + $(if (Has "npm") { FirstLine npm --version } else { "нет" }))
Info ("Git:     " + $(if (Has "git") { FirstLine git --version } else { "нет" }))
Info ("Python:  " + $(if (Has "python") { FirstLine python --version } else { "нет (не требуется)" }))
$chrome = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
Info ("Chrome:  " + $(if ($chrome) { (Get-Item $chrome).VersionInfo.ProductVersion } else { "нет (HyperFrames использует свой Chrome Headless Shell)" }))
Info ("Claude Code: " + $(if (Has "claude") { FirstLine claude --version } else { "не найден в PATH" }))

$nodeMajor = 0
if (Has "node") { $nodeMajor = [int]((FirstLine node --version).TrimStart("v").Split(".")[0]) }
if ($nodeMajor -lt 22) {
  Info "HyperFrames требует Node.js >= 22, найдено: $nodeMajor"
  Winget-Install "OpenJS.NodeJS.LTS"
  $nodeMajor = [int]((FirstLine node --version).TrimStart("v").Split(".")[0])
  if ($nodeMajor -lt 22) { Fail "Node.js >= 22 не появился в PATH. Откройте новый терминал и запустите скрипт снова." }
}
Ok "Node.js $(FirstLine node --version), npm $(FirstLine npm --version)"
if (-not (Has "git")) { Winget-Install "Git.Git" }
if (-not (Has "git")) { Fail "Git не появился в PATH. Откройте новый терминал и запустите скрипт снова." }
Ok "Git: $(FirstLine git --version) (Git Bash нужен навыкам HyperFrames)"

# ---------------------------------------------------------------- 2
Step 2 "FFmpeg"
if ((Has "ffmpeg") -and (Has "ffprobe")) {
  Info "FFmpeg уже в PATH — не переустанавливаю"
} else {
  Winget-Install "Gyan.FFmpeg"
}
if (-not ((Has "ffmpeg") -and (Has "ffprobe"))) { Fail "ffmpeg/ffprobe не найдены в PATH после установки. Откройте новый терминал и запустите скрипт снова." }
if ((Quiet ffmpeg -version) -ne 0) { Fail "ffmpeg -version завершился с ошибкой" }
if ((Quiet ffprobe -version) -ne 0) { Fail "ffprobe -version завершился с ошибкой" }
Ok "$(FirstLine ffmpeg -version)  [$((Get-Command ffmpeg).Source)]"
Ok "$(FirstLine ffprobe -version)  [$((Get-Command ffprobe).Source)]"

# ---------------------------------------------------------------- 3
Step 3 "HyperFrames CLI"
if (Has "hyperframes") {
  Info "HyperFrames уже установлен — не переустанавливаю"
} else {
  Run npm install -g hyperframes@latest
  Refresh-Path
}
if (-not (Has "hyperframes")) { Fail "Команда hyperframes не найдена после npm install -g" }
$hfVersion = FirstLine hyperframes --version
$hfLatest = FirstLine npm view hyperframes version
Ok "HyperFrames $hfVersion (последняя в npm: $hfLatest)"
if ($hfLatest -and $hfVersion -ne $hfLatest) { Warn "Есть обновление: npm install -g hyperframes@latest" }
Run hyperframes browser ensure
Ok "Chrome Headless Shell для рендера установлен"

# ---------------------------------------------------------------- 4
Step 4 "Распознавание речи: whisper.cpp (интеграция HyperFrames), модель $Model, русский язык"
$whisper = $null
if ($env:HYPERFRAMES_WHISPER_PATH -and (Test-Path $env:HYPERFRAMES_WHISPER_PATH)) {
  $whisper = $env:HYPERFRAMES_WHISPER_PATH
  Info "Уже задан HYPERFRAMES_WHISPER_PATH — не переустанавливаю"
} elseif (Has "whisper-cli") {
  $whisper = (Get-Command whisper-cli).Source
  Info "whisper-cli уже в PATH — не переустанавливаю"
} else {
  # Официальный релиз ggml-org/whisper.cpp (тот же проект, который HyperFrames собирает из исходников на macOS/Linux).
  $headers = @{ "User-Agent" = "shorts-studio-setup" }
  $release = Invoke-RestMethod -Uri "https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest" -Headers $headers
  $asset = $release.assets | Where-Object { $_.name -eq "whisper-bin-x64.zip" } | Select-Object -First 1
  if (-not $asset) {
    Fail ("В релизе $($release.tag_name) нет whisper-bin-x64.zip. Доступно: " + (($release.assets | ForEach-Object name) -join ", "))
  }
  $dest = Join-Path $env:LOCALAPPDATA "shorts-studio\whisper.cpp\$($release.tag_name)"
  $zip = Join-Path $env:TEMP "whisper-bin-x64-$($release.tag_name).zip"
  Info "Скачиваю $($asset.browser_download_url)"
  Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
  $hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
  if ($asset.digest -and $asset.digest -like "sha256:*") {
    if ($asset.digest.Substring(7).ToLower() -ne $hash) { Remove-Item $zip; Fail "SHA-256 не совпадает с опубликованным GitHub — файл удалён." }
    Ok "SHA-256 совпадает с опубликованным на GitHub: $hash"
  } else {
    Warn "GitHub не опубликовал контрольную сумму для архива; SHA-256 скачанного файла: $hash"
  }
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
  Expand-Archive -Path $zip -DestinationPath $dest
  Remove-Item $zip
  $whisper = (Get-ChildItem $dest -Recurse -Filter "whisper-cli.exe" | Select-Object -First 1).FullName
  if (-not $whisper) { Fail "В архиве нет whisper-cli.exe ($dest)" }
}
$whisperCode = Quiet $whisper --help
if ($whisperCode -eq -1073741515) {
  Fail "whisper-cli.exe не запускается: нет Microsoft Visual C++ Redistributable. Установите (нужны права администратора): winget install --id Microsoft.VCRedist.2015+.x64 -e — затем запустите скрипт снова."
} elseif ($whisperCode -ne 0) {
  Fail "whisper-cli.exe --help завершился с кодом $whisperCode"
}
# HyperFrames на Windows не находит собственную сборку (ищет имя без .exe), поэтому путь задаётся явно.
[Environment]::SetEnvironmentVariable("HYPERFRAMES_WHISPER_PATH", $whisper, "User")
$env:HYPERFRAMES_WHISPER_PATH = $whisper
Ok "whisper-cli: $whisper (HYPERFRAMES_WHISPER_PATH записан в переменные пользователя)"

# Реальная проверка: синтез русской фразы средствами Windows -> транскрипция HyperFrames.
$probeDir = Join-Path $env:TEMP "shorts-studio-asr-probe"
if (Test-Path $probeDir) { Remove-Item $probeDir -Recurse -Force }
New-Item -ItemType Directory -Path $probeDir | Out-Null
$probeWav = Join-Path $probeDir "probe.wav"
$phrase = "Привет! Это проверка русских субтитров."
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$ruVoice = $synth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq "ru-RU" } | Select-Object -First 1
if ($ruVoice) { $synth.SelectVoice($ruVoice.VoiceInfo.Name) } else { Warn "Русский голос Windows не установлен — проверка пройдёт на голосе по умолчанию, текст сравниваться не будет." }
$synth.SetOutputToWaveFile($probeWav)
$synth.Speak($phrase)
$synth.Dispose()
Info "Скачивание модели ggml-$Model.bin при первом запуске может занять несколько минут"
Run hyperframes transcribe $probeWav -d $probeDir --engine whisper --model $Model --language ru
$transcript = Join-Path $probeDir "transcript.json"
if (-not (Test-Path $transcript)) { Fail "hyperframes transcribe не создал transcript.json" }
$words = Get-Content $transcript -Raw -Encoding UTF8 | ConvertFrom-Json
$heard = ($words | ForEach-Object { $_.text }) -join " "
Info "Распознано: $heard"
if ($ruVoice -and $heard -notmatch "[а-яА-ЯёЁ]") { Fail "В распознанном тексте нет кириллицы — проверьте модель (не *.en) и язык." }
Ok "Транскрибация на русском работает: $($words.Count) слов с временными метками (модель $Model)"

# ---------------------------------------------------------------- 5
Step 5 "Навыки HyperFrames для Claude Code"
$skillsDir = Join-Path $env:USERPROFILE ".claude\skills"
if ($SkipSkills) {
  Warn "Пропущено по флагу -SkipSkills"
} elseif (Test-Path (Join-Path $skillsDir "hyperframes\SKILL.md")) {
  Info "Навыки уже установлены — не переустанавливаю (обновление: hyperframes skills update)"
} else {
  Run npx --yes skills add heygen-com/hyperframes -g -a claude-code -s "*" -y
}
if (-not $SkipSkills) {
  foreach ($s in "hyperframes", "embedded-captions", "talking-head-recut", "general-video", "hyperframes-cli") {
    if (-not (Test-Path (Join-Path $skillsDir "$s\SKILL.md"))) { Fail "Навык $s не найден в $skillsDir" }
  }
  Ok "Навыки в $skillsDir (/hyperframes, /embedded-captions, /talking-head-recut, /general-video …)"
}

# ---------------------------------------------------------------- 6
Step 6 "Проект $ProjectDir"
if ((Resolve-Path $TemplateDir).Path -eq [IO.Path]::GetFullPath($ProjectDir)) { Fail "Шаблон и проект — одна папка. Запустите скрипт из клона репозитория." }
$exclude = '\\(node_modules|\.hyperframes)\\|\\output\\.+\.mp4$|\\templates\\selftest\\assets\\(gsap\.min\.js|source\.mp4)$'
$copied = 0; $kept = 0
Get-ChildItem $TemplateDir -Recurse -File -Force | Where-Object { $_.FullName -notmatch $exclude } | ForEach-Object {
  $rel = $_.FullName.Substring($TemplateDir.Length).TrimStart("\")
  $target = Join-Path $ProjectDir $rel
  if (Test-Path $target) { $kept++ } else {
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    Copy-Item $_.FullName $target
    $copied++
  }
}
Ok "Файлов скопировано: $copied, уже существовало (не тронуто): $kept"
Push-Location $ProjectDir
try {
  Run npm install --no-fund --no-audit
  Ok "Зависимости проекта установлены"

  # ------------------------------------------------------------ 7
  Step 7 "Тестовый рендер"
  $out = Join-Path $ProjectDir "output\selftest.mp4"
  if (Test-Path $out) { Remove-Item $out }
  Run npm run selftest
  if (-not (Test-Path $out)) { Fail "Рендер не создал $out" }
  $probe = & ffprobe -v error -show_entries "stream=codec_name,width,height:format=duration" -of json $out | ConvertFrom-Json
  $v = $probe.streams | Where-Object { $_.width } | Select-Object -First 1
  if ($v.codec_name -ne "h264" -or $v.width -ne 1080 -or $v.height -ne 1920) { Fail "Неожиданные параметры видео: $($v.codec_name) $($v.width)x$($v.height)" }
  $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $decodeErr = & ffmpeg -v error -i $out -f null - 2>&1
  $decodeCode = $LASTEXITCODE
  $ErrorActionPreference = $prev
  if ($decodeCode -ne 0 -or $decodeErr) { Fail "Ошибки при полном декодировании ${out}: $decodeErr" }
  Ok ("MP4 воспроизводится: h264 1080x1920, {0:N1} c, {1:N1} МБ -> $out" -f [double]$probe.format.duration, ((Get-Item $out).Length / 1MB))
  if ($Play) { Start-Process $out }
} finally {
  Pop-Location
}

# ---------------------------------------------------------------- итог
Write-Host ""
Write-Host "=== Итог ===" -ForegroundColor Cyan
$Report | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host "Проект: $ProjectDir"
Write-Host "Монтаж: положите видео в $ProjectDir\input, затем в новом терминале:"
Write-Host "  cd `"$ProjectDir`"; claude"
Write-Host "  > смонтируй input\<файл>.mp4"
Write-Host "(новый терминал нужен, чтобы подхватились PATH и HYPERFRAMES_WHISPER_PATH)"
