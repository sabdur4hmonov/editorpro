# Video montaj tizimi: muhitni tekshirish va o'rnatish (Windows PowerShell 5.1 yoki yangiroq)
#
# Ishga tushirish (loyiha papkasida):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1              # tekshiradi, so'rab o'rnatadi, sinaydi
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1 -CheckOnly   # faqat tekshiradi, hech narsa o'rnatmaydi
#
# Hech narsa so'ramasdan o'rnatilmaydi. Hamma natija temp\setup_report.txt ga ham yoziladi.
# Skriptni qayta-qayta ishga tushirish xavfsiz: tayyor qadamlar o'tkazib yuboriladi.
param([switch]$CheckOnly)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = '1'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root
foreach ($d in 'temp', 'input', 'output', 'samples') {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null
}
$Report = Join-Path $Root 'temp\setup_report.txt'
Set-Content -LiteralPath $Report -Value ("Setup hisoboti: " + (Get-Date -Format 's')) -Encoding UTF8
$Problems = New-Object System.Collections.ArrayList

function Say([string]$Text, [string]$Color = 'Gray') {
    Write-Host $Text -ForegroundColor $Color
    Add-Content -LiteralPath $Report -Value $Text -Encoding UTF8
}

function Step([string]$Text) {
    Say ''
    Say "=== $Text ===" 'Cyan'
}

function Problem([string]$Text) {
    [void]$Problems.Add($Text)
    Say "  [MUAMMO] $Text" 'Yellow'
}

# Buyruqni cmd orqali ishga tushiradi: chiqishi ekranga ham, hisobotga ham yoziladi.
# Buyruq ichida qo'shtirnoq ishlatilmaydi (yo'llar nisbiy, bo'sh joysiz).
function Run-Logged([string]$CmdLine) {
    Say ">> $CmdLine" 'DarkGray'
    cmd /c "$CmdLine 2>&1" | ForEach-Object {
        Write-Host $_
        Add-Content -LiteralPath $Report -Value $_ -Encoding UTF8
    }
    return $LASTEXITCODE
}

# Dastur bor-yo'qligini bilish uchun birinchi chiqish qatorini qaytaradi (yo'q bo'lsa $null)
function Get-FirstLine([string]$CmdLine) {
    try {
        $out = @(cmd /c "$CmdLine 2>&1" | Where-Object { "$_".Trim() })
        if ($LASTEXITCODE -eq 0 -and $out.Count -gt 0) { return [string]$out[0] }
    } catch { }
    return $null
}

function Find-Python {
    # 3.12 afzal (kutubxonalar eng yaxshi sinalgan), keyin boshqalari
    foreach ($c in @('py -3.12', 'py -3.11', 'py -3.13', 'py -3.10', 'python', 'python3', 'py -3')) {
        $v = Get-FirstLine "$c --version"
        if ($v -and ($v -match '^Python 3\.(\d+)\.')) {
            $minor = [int]$Matches[1]
            if ($minor -ge 9) { return @{ Cmd = $c; Version = $v; Minor = $minor } }
        }
    }
    return $null
}

function Refresh-Path {
    # Yangi o'rnatilgan dasturlar shu terminalda ham ko'rinishi uchun PATH ni qayta o'qiymiz
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
}

function Ask([string]$Question) {
    $answer = Read-Host "$Question [y/N]"
    Add-Content -LiteralPath $Report -Value "$Question -> $answer" -Encoding UTF8
    return ($answer -match '^(y|yes|ha|h)$')
}

function Install-WithWinget([string]$Id, [string]$Name, [string]$Note) {
    # Natijani $script:InstalledAny ga yozadi (funksiya hech narsa qaytarmaydi)
    if (-not $script:Winget) {
        Problem "$Name yo'q va winget ham topilmadi. Qo'lda o'rnating."
        return
    }
    if (-not (Ask "$Name topilmadi. winget bilan o'rnataymi? ($Id, $Note)")) {
        Say '  O''tkazib yuborildi.'
        return
    }
    Say ">> winget install --id $Id -e --source winget" 'DarkGray'
    # winget shu konsolning o'zida ishlaydi: litsenziya savollariga o'zingiz javob berasiz
    try {
        $proc = Start-Process -FilePath 'winget' -ArgumentList @('install', '--id', $Id, '-e', '--source', 'winget') -NoNewWindow -Wait -PassThru
        Say ("  winget chiqish kodi: " + $proc.ExitCode)
    } catch {
        winget install --id $Id -e --source winget | Out-Host
        Say "  winget chiqish kodi: $LASTEXITCODE"
    }
    $script:InstalledAny = $true
    Refresh-Path
}

function New-SpeechSample([string]$Path) {
    # Windows'ning o'z ovozi bilan ~25 soniyalik inglizcha nutq yasaydi (whisper tezligini o'lchash uchun)
    try {
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.SetOutputToWaveFile($Path)
        $synth.Speak('Hello, this is a speed test for the video editing system. ' +
            'We are measuring how fast this computer can turn speech into text. ' +
            'The quick brown fox jumps over the lazy dog. ' +
            'After the test, the script will recommend which model to use. ' +
            'Short videos need fast cuts, clear subtitles, and balanced audio. ' +
            'Thank you for waiting, the test is almost finished.')
        $synth.Dispose()
        return (Test-Path -LiteralPath $Path)
    } catch {
        Say ("  Namuna nutq yaratib bo'lmadi: " + $_.Exception.Message)
        return $false
    }
}

# ---------------------------------------------------------------- 1. kompyuter
Step '1. Kompyuter'
try {
    $cpu = Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1
    $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    Say ("  Tizim: {0} ({1})" -f $os.Caption, $os.Version)
    Say ("  CPU:   {0} ({1} yadro, {2} oqim)" -f $cpu.Name.Trim(), $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)
    Say ("  RAM:   {0:N1} GB" -f ($cs.TotalPhysicalMemory / 1GB))
} catch {
    Say ("  Tizim ma'lumotini o'qib bo'lmadi: " + $_.Exception.Message)
}
try {
    $drive = (Get-Item -LiteralPath $Root).PSDrive
    Say ("  Disk {0}: bo'sh joy {1:N1} GB" -f $drive.Name, ($drive.Free / 1GB))
    if ($drive.Free -lt 5GB) { Problem "Diskda bo'sh joy kam (5 GB dan kam)." }
} catch { }
Say "  Papka: $Root"
Say ("  PowerShell: " + $PSVersionTable.PSVersion.ToString())

# ---------------------------------------------------------------- 2. video karta
Step '2. Video karta'
$HasNvidia = $false
try {
    $gpus = @(Get-CimInstance Win32_VideoController -ErrorAction Stop)
    foreach ($g in $gpus) {
        Say ("  Karta: {0} (drayver {1})" -f $g.Name, $g.DriverVersion)
        if ($g.Name -match 'NVIDIA') { $HasNvidia = $true }
    }
} catch {
    Say ("  Video kartani aniqlab bo'lmadi: " + $_.Exception.Message)
}
$smi = Get-FirstLine 'nvidia-smi --query-gpu=name,memory.total --format=csv,noheader'
if ($smi) {
    Say "  nvidia-smi: $smi"
    $HasNvidia = $true
} else {
    Say '  nvidia-smi: topilmadi'
}
if ($HasNvidia) {
    Say '  XULOSA: NVIDIA karta BOR. Render uchun nvenc ni yoqish mumkin (style.json: video.use_nvenc).' 'Green'
} else {
    Say '  XULOSA: NVIDIA karta YO''Q. Hammasi CPU uchun sozlangan (style.json shunday turibdi).' 'Green'
}
Say "GPU_NVIDIA=$HasNvidia"

# ---------------------------------------------------------------- 3. dasturlar
Step '3. Dasturlar'
$script:Winget = Get-FirstLine 'winget --version'
$Ffmpeg = Get-FirstLine 'ffmpeg -hide_banner -version'
$Ffprobe = Get-FirstLine 'ffprobe -hide_banner -version'
$Git = Get-FirstLine 'git --version'
$Py = Find-Python
function Show-Tool([string]$Name, $Value) {
    if ($Value) { Say ("  [bor]  {0}: {1}" -f $Name, $Value) } else { Say ("  [YO'Q] {0}" -f $Name) 'Yellow' }
}
Show-Tool 'winget' $script:Winget
Show-Tool 'ffmpeg' $Ffmpeg
Show-Tool 'ffprobe' $Ffprobe
Show-Tool 'git' $Git
if ($Py) { Show-Tool 'python' ("{0}  (buyruq: {1})" -f $Py.Version, $Py.Cmd) } else { Show-Tool 'python (3.9+)' $null }
if ($Py) { Show-Tool 'pip' (Get-FirstLine "$($Py.Cmd) -m pip --version") }
if ($Py -and $Py.Minor -ge 14) {
    Say '  Eslatma: Python juda yangi. Ba''zi kutubxonalar hali chiqmagan bo''lishi mumkin; xato bo''lsa 3.12 o''rnatamiz.' 'Yellow'
}

if ($CheckOnly) {
    Step 'Tekshiruv tugadi (-CheckOnly: hech narsa o''rnatilmadi)'
    Say "Hisobot: $Report"
    exit 0
}

# ---------------------------------------------------------------- 4. yetishmayotganlarini o'rnatish
Step '4. Yetishmayotgan dasturlar'
$script:InstalledAny = $false
if (-not $Ffmpeg -or -not $Ffprobe) {
    Install-WithWinget 'Gyan.FFmpeg' 'FFmpeg' 'taxminan 0.5 GB joy'
    $Ffmpeg = Get-FirstLine 'ffmpeg -hide_banner -version'
    $Ffprobe = Get-FirstLine 'ffprobe -hide_banner -version'
}
if (-not $Py) {
    Install-WithWinget 'Python.Python.3.12' 'Python 3.12' 'taxminan 150 MB joy'
    $Py = Find-Python
}
if (-not $Git) {
    Install-WithWinget 'Git.Git' 'Git' 'taxminan 350 MB joy'
    $Git = Get-FirstLine 'git --version'
}
if (-not $script:InstalledAny) { Say '  Yangi dastur o''rnatilmadi.' }

$needReopen = $false
if (-not $Ffmpeg -or -not $Ffprobe) { Problem 'ffmpeg/ffprobe hali ko''rinmayapti.'; $needReopen = $true }
if (-not $Py) { Problem 'Python hali ko''rinmayapti.'; $needReopen = $true }
if (-not $Git) { Problem 'git hali ko''rinmayapti (git commit qilinmaydi).' }
if ($needReopen) {
    Say ''
    Say 'Agar hozirgina o''rnatgan bo''lsangiz: bu terminalni YOPING, yangisini oching va setup.ps1 ni qayta ishga tushiring' 'Yellow'
    Say '(yangi o''rnatilgan dastur PATH ga faqat yangi terminalda qo''shiladi).' 'Yellow'
    Say "Hisobot: $Report"
    exit 1
}

# ---------------------------------------------------------------- 5. .venv va kutubxonalar
Step '5. Python virtual muhit (.venv) va kutubxonalar'
$VenvPy = '.venv\Scripts\python.exe'
$libsOk = $false
if (-not (Test-Path -LiteralPath $VenvPy)) {
    $code = Run-Logged "$($Py.Cmd) -m venv .venv"
    if ($code -ne 0 -or -not (Test-Path -LiteralPath $VenvPy)) { Problem '.venv yaratib bo''lmadi.' }
} else {
    Say '  .venv allaqachon bor.'
}
if (Test-Path -LiteralPath $VenvPy) {
    Say ("  .venv Python: " + (Get-FirstLine "$VenvPy --version"))
    $check = @(cmd /c "$VenvPy scripts\check_env.py 2>&1")
    if ($check -contains 'libs-ok') {
        Say '  Kutubxonalar allaqachon o''rnatilgan.'
        $libsOk = $true
    } elseif (Ask 'Kutubxonalarni FAQAT .venv ichiga o''rnataymi? (faster-whisper, scenedetect[opencv], opencv-python, numpy, pillow; ~0.5 GB)') {
        [void](Run-Logged "$VenvPy -m pip install --upgrade pip")
        $code = Run-Logged "$VenvPy -m pip install -r requirements.txt"
        if ($code -ne 0) { Problem 'pip install xato bilan tugadi (yuqoridagi qatorlarga qarang).' }
        if ((Run-Logged "$VenvPy scripts\check_env.py") -eq 0) { $libsOk = $true } else { Problem 'Kutubxonalar to''liq o''rnatilmadi.' }
    } else {
        Say '  O''tkazib yuborildi.'
    }
}
if ($libsOk) {
    # o'rnatilgan aniq versiyalarni yozib qo'yamiz
    $freeze = @(cmd /c "$VenvPy -m pip freeze 2>&1")
    $freeze | Set-Content -LiteralPath (Join-Path $Root 'requirements.lock.txt') -Encoding ASCII
    $pins = @('# Asosiy kutubxonalar (aniq versiyalar setup.ps1 tomonidan yozilgan).',
              '# Barcha bog''liq kutubxonalar: requirements.lock.txt')
    foreach ($name in @('faster-whisper', 'scenedetect', 'opencv-python', 'numpy', 'pillow')) {
        $line = $freeze | Where-Object { $_ -match ('^' + [regex]::Escape($name) + '==') } | Select-Object -First 1
        if (-not $line) { $line = $name }
        if ($name -eq 'scenedetect') { $line = $line -replace '^scenedetect', 'scenedetect[opencv]' }
        $pins += $line
        Say "  $line"
    }
    $pins | Set-Content -LiteralPath (Join-Path $Root 'requirements.txt') -Encoding ASCII
    Say '  Versiyalar requirements.txt ga yozildi.'
}

# ---------------------------------------------------------------- 6. whisper sinovi
Step '6. Whisper sinovi (small, int8, CPU)'
$whisperOk = $false
if ($libsOk) {
    if (Ask 'Whisper "small" modelini yuklab, tezligini o''lchaymi? (internetdan ~0.5 GB, bir necha daqiqa)') {
        New-Item -ItemType Directory -Force -Path (Join-Path $Root 'temp\selftest') | Out-Null
        $sample = Join-Path $Root 'temp\selftest\speech.wav'
        if (-not (Test-Path -LiteralPath $sample)) { [void](New-SpeechSample $sample) }
        if (-not (Test-Path -LiteralPath $sample)) {
            [void](Run-Logged "$VenvPy scripts\selftest.py --no-whisper")
        }
        $code = Run-Logged "$VenvPy scripts\bench_whisper.py --models small"
        if ($code -eq 0) { $whisperOk = $true } else { Problem 'Whisper sinovi xato bilan tugadi.' }
    } else {
        Say '  O''tkazib yuborildi. Model birinchi marta ishlatilganda o''zi yuklanadi.'
    }
} else {
    Say '  Kutubxonalar o''rnatilmagani uchun o''tkazib yuborildi.'
}

# ---------------------------------------------------------------- 7. tizim sinovi
Step '7. Tizim sinovi (10 soniyalik test video bilan butun zanjir)'
$selftestOk = $false
if (Test-Path -LiteralPath $VenvPy) {
    if ($whisperOk) { $code = Run-Logged "$VenvPy scripts\selftest.py" }
    else { $code = Run-Logged "$VenvPy scripts\selftest.py --no-whisper" }
    if ($code -eq 0) { $selftestOk = $true } else { Problem 'Tizim sinovi o''tmadi (yuqoridagi [XATO] qatorlariga qarang).' }
} else {
    Say '  .venv yo''q, o''tkazib yuborildi.'
}

# ---------------------------------------------------------------- 8. git
Step '8. Git'
if ($Git) {
    if (-not (Test-Path -LiteralPath '.git')) { [void](Run-Logged 'git init') } else { Say '  Git ombori allaqachon bor.' }
    $gitName = Get-FirstLine 'git config user.name'
    $gitEmail = Get-FirstLine 'git config user.email'
    if (-not $gitName -or -not $gitEmail) {
        Problem 'git user.name / user.email sozlanmagan, commit qilinmadi. Sozlang: git config --global user.name "Ism"  va  git config --global user.email "pochta"'
    } else {
        [void](Run-Logged 'git add -A')
        $pending = @(cmd /c 'git status --porcelain 2>&1')
        if ($pending.Count -gt 0) {
            $msg = @('Video montaj tizimi: skriptlar, uslub va qoidalar', '',
                     'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>',
                     'Claude-Session: https://claude.ai/code/session_01WFm4FXBESJD44RvtdPkeK1')
            $msg | Set-Content -LiteralPath (Join-Path $Root 'temp\commit_msg.txt') -Encoding ASCII
            $code = Run-Logged 'git commit -q -F temp\commit_msg.txt'
            if ($code -ne 0) { Problem 'git commit xato bilan tugadi.' }
        } else {
            Say '  Commit qiladigan o''zgarish yo''q.'
        }
        [void](Run-Logged 'git log --oneline -n 3')
    }
} else {
    Say '  git yo''q, o''tkazib yuborildi.'
}

# ---------------------------------------------------------------- yakun
Step 'YAKUN'
Say "  NVIDIA karta:   $HasNvidia"
Say "  Kutubxonalar:   $libsOk"
Say "  Whisper sinovi: $whisperOk"
Say "  Tizim sinovi:   $selftestOk"
if ($Problems.Count -eq 0) {
    Say '  Hammasi tayyor.' 'Green'
} else {
    Say ("  Muammolar: " + $Problems.Count) 'Yellow'
    foreach ($p in $Problems) { Say "   - $p" 'Yellow' }
}
Say ''
Say "Hisobot: $Report"
Say 'Endi Claude''ga "bo''ldi" deb yozing, u hisobotni o''zi o''qiydi.'
if ($Problems.Count -eq 0) { exit 0 } else { exit 1 }
