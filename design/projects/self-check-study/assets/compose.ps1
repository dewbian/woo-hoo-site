# Play Store 등록용 스크린샷 합성 스크립트.
# HTML+Playwright 경로가 mcp playwright 의 DPR 0.333 viewport scale 이슈로
# 디바이스 캡쳐를 22% 작게 렌더 → 우회 위해 System.Drawing 직접 합성.
# 5장 (today/stamps/calendar/timer/eval) 의 카피·디바이스 캡쳐를 받아
# 1080x2418 PNG 로 만든다.

Add-Type -AssemblyName System.Drawing

function New-StoreScreenshot {
    param(
        [string]$DeviceImg,    # 디바이스 캡쳐 path
        [string]$Eyebrow,      # 상단 lime 칩 텍스트
        [string[]]$TitleLines, # 큰 타이틀 라인 배열
        [string[]]$DescLines,  # 작은 디스크립션 라인 배열
        [string]$OutPath       # 출력 PNG path
    )

    $W = 1080
    $H = 2418
    $bmp = New-Object System.Drawing.Bitmap $W, $H
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality

    # Wise 톤: sage 캔버스 #E8EBE6
    $sage = [System.Drawing.Color]::FromArgb(232, 235, 230)
    $sageBrush = New-Object System.Drawing.SolidBrush $sage
    $g.FillRectangle($sageBrush, 0, 0, $W, $H)

    # Lime 칩 + 짙은 lime 텍스트 (Eyebrow)
    $lime = [System.Drawing.Color]::FromArgb(159, 232, 112)        # #9FE870
    $limeBrush = New-Object System.Drawing.SolidBrush $lime
    $eyeColor = [System.Drawing.Color]::FromArgb(5, 77, 40)         # #054D28
    $eyeBrush = New-Object System.Drawing.SolidBrush $eyeColor
    $eyeFont = New-Object System.Drawing.Font 'Malgun Gothic', 18, ([System.Drawing.FontStyle]::Bold)

    $padX = 72
    $y = 56

    # 칩 width 측정 + pill rect 그리기
    $eyeSize = $g.MeasureString($Eyebrow, $eyeFont)
    $chipH = 60
    $chipW = [int]($eyeSize.Width + 50)
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc($padX, $y, $chipH, $chipH, 90, 180)
    $path.AddArc($padX + $chipW - $chipH, $y, $chipH, $chipH, 270, 180)
    $path.CloseFigure()
    $g.FillPath($limeBrush, $path)
    $eyeY = $y + ($chipH - $eyeSize.Height) / 2
    $g.DrawString($Eyebrow, $eyeFont, $eyeBrush, ($padX + 24), $eyeY)

    $y += $chipH + 28

    # Title (큰 굵은 ink)
    $titleColor = [System.Drawing.Color]::FromArgb(14, 15, 12)      # #0E0F0C
    $titleBrush = New-Object System.Drawing.SolidBrush $titleColor
    $titleFont = New-Object System.Drawing.Font 'Malgun Gothic', 52, ([System.Drawing.FontStyle]::Bold)
    foreach ($line in $TitleLines) {
        $g.DrawString($line, $titleFont, $titleBrush, $padX, $y)
        $y += 88
    }
    $y += 12

    # Desc (Regular body)
    $descColor = [System.Drawing.Color]::FromArgb(69, 71, 69)       # #454745
    $descBrush = New-Object System.Drawing.SolidBrush $descColor
    $descFont = New-Object System.Drawing.Font 'Malgun Gothic', 22, ([System.Drawing.FontStyle]::Regular)
    foreach ($line in $DescLines) {
        $g.DrawString($line, $descFont, $descBrush, $padX, $y)
        $y += 46
    }

    $headerEnd = [int]($y + 40)

    # 디바이스 캡쳐 (1080 width fit, status bar 90px 잘라내기).
    # PowerShell 변수는 case-insensitive — param $DeviceImg 와 충돌 피하려고 $devBmp 사용.
    $devBmp = [System.Drawing.Image]::FromFile($DeviceImg)
    $availH = $H - $headerEnd
    $srcStart = 90
    $srcH = [Math]::Min($devBmp.Height - $srcStart, $availH)
    $destRect = New-Object System.Drawing.Rectangle 0, $headerEnd, $W, $srcH
    $srcRect = New-Object System.Drawing.Rectangle 0, $srcStart, $devBmp.Width, $srcH
    $g.DrawImage($devBmp, $destRect, $srcRect, [System.Drawing.GraphicsUnit]::Pixel)
    $devBmp.Dispose()

    $g.Dispose()
    $bmp.Save($OutPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()

    Write-Output "$OutPath : OK"
}

# 5장 카피 정의
# 입력: 원본 디바이스 캡처(_screenshots, 유지). 출력: deploy/assets(이동된 새 위치).
$ScreenshotDir = "D:\bhs-project\self-check-study\doc\design\_screenshots"
$OutDir = "D:\bhs-project\self-check-study\doc\deploy\assets"

$specs = @(
    @{ Key='today';    Eyebrow='집중할 일';   Title=@('Today 한눈에 보기');         Desc=@('지금 할 일 + 다음 할 일을', '한 카드로 정리');    Img='device-today.png' }
    @{ Key='stamps';   Eyebrow='쌓이는 보상'; Title=@('컬렉션이 채워진다');         Desc=@('완료한 만큼 늘어나는', '도장 그리드');           Img='device-stamps.png' }
    @{ Key='calendar'; Eyebrow='한 달의 흐름'; Title=@('무지개 달력');               Desc=@('만족도 × 도달도가', '셀 색의 진하기로');         Img='device-calendar-03.jpg' }
    @{ Key='timer';    Eyebrow='몰입 모드';   Title=@('초록 링 + 카운트다운');      Desc=@('시작 한 번에 곧장 집중');                        Img='device-timer.png' }
    @{ Key='eval';     Eyebrow='어땠어?';     Title=@('한 번의 탭으로', '자기평가 끝'); Desc=@('만족·보통·힘들었어 3단계,', '도달률은 자동 계산'); Img='device-now.png' }
)

foreach ($s in $specs) {
    $imgPath = Join-Path $ScreenshotDir $s.Img
    if (-not (Test-Path $imgPath)) {
        Write-Output "SKIP $($s.Key) : missing $($s.Img)"
        continue
    }
    $out = Join-Path $OutDir "screenshot-$($s.Key).png"
    New-StoreScreenshot -DeviceImg $imgPath -Eyebrow $s.Eyebrow -TitleLines $s.Title -DescLines $s.Desc -OutPath $out
}
