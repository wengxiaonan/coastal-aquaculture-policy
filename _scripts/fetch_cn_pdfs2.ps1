# Download CN journal PDFs: extract URLs from list files by ID, then fetch open PDFs
$ErrorActionPreference = 'Continue'
$work = 'F:\deepseek harness'
$ids = @()
1..32 | ForEach-Object { $ids += ('CN-{0:D2}' -f $_) }
$ids += @('CN-54','CN-56','CN-58','CN-59','CN-61','CN-62','CN-63','CN-64','CN-65','CN-68','CN-69','CN-71','CN-73','CN-74','CN-75','CN-76','CN-77','JP-31','JP-37','KR-02')

$files = Get-ChildItem -Path $work -Filter '*.md' | Where-Object { $_.Name -ne '中美欧日中近岸养殖政策文献总目.md' }
$outDir = Join-Path $work 'pdfs_cn'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

$rows = @()
foreach ($id in $ids) {
  $found = $false
  $urls = @()
  foreach ($f in $files) {
    $lines = Get-Content -Encoding UTF8 $f.FullName
    for ($i = 0; $i -lt $lines.Count; $i++) {
      if ($lines[$i] -match [regex]::Escape("($id)")) {
        $found = $true
        $seg = $lines[$i]
        if ($i + 1 -lt $lines.Count) { $seg += ' ' + $lines[$i + 1] }
        $urls = [regex]::Matches($seg, 'https?://[^\s\)\]]+') | ForEach-Object { $_.Value } | Select-Object -Unique
        break
      }
    }
    if ($found) { break }
  }
  $file = Join-Path $outDir ($id + '.pdf')
  $status = if ($found) { 'no_url_found' } else { 'id_not_found' }
  $used = ''
  foreach ($u in $urls) {
    $isPdfLike = ($u -match 'create_pdf|\.pdf|sciengine|/CN/PDF/|pdfpreview|open\.pdf|abstract/.*pdf')
    $isPaid = ($u -match 'cnki|wanfang|cqvip|webvpn|read\.cnki|wap\.cnki')
    if ($isPdfLike -and $status -ne 'downloaded') {
      try {
        Invoke-WebRequest -Uri $u -OutFile $file -TimeoutSec 70 -MaximumRedirection 12 -UseBasicParsing -Headers @{'User-Agent' = $UA}
        $len = (Get-Item $file -ErrorAction SilentlyContinue).Length
        if ($len -and $len -gt 20000) { $status = 'downloaded'; $used = $u }
        else { $status = 'small_or_error'; Remove-Item $file -ErrorAction SilentlyContinue }
      } catch { $status = 'download_failed'; $used = $u }
    } elseif (-not $isPaid -and $status -eq 'no_url_found' -or $status -eq 'download_failed' -or $status -eq 'id_not_found') {
      # try page then find pdf link
      try {
        $html = (Invoke-WebRequest -Uri $u -TimeoutSec 50 -UseBasicParsing -Headers @{'User-Agent' = $UA}).Content
        $pm = [regex]::Match($html, 'href="([^"]*(?:create_pdf|\.pdf|CN/PDF)[^"]*)"', 'IgnoreCase')
        if ($pm.Success) {
          $pdfUrl = $pm.Groups[1].Value
          if ($pdfUrl -notmatch '^https?://') { $pdfUrl = ([uri]$u).GetLeftPart([uri]::Authority) + $pdfUrl }
          Invoke-WebRequest -Uri $pdfUrl -OutFile $file -TimeoutSec 70 -MaximumRedirection 12 -UseBasicParsing -Headers @{'User-Agent' = $UA}
          $len = (Get-Item $file -ErrorAction SilentlyContinue).Length
          if ($len -and $len -gt 20000) { $status = 'downloaded'; $used = $pdfUrl }
          else { $status = 'small_or_error'; Remove-Item $file -ErrorAction SilentlyContinue }
        } else { if ($status -eq 'no_url_found') { $status = 'page_no_pdf_link' } }
      } catch { if ($status -eq 'no_url_found') { $status = 'page_fetch_failed' } }
    } elseif ($isPaid -and $status -eq 'no_url_found') {
      $status = 'needs_subscription'; $used = $u
    }
  }
  $rows += [pscustomobject]@{ Id = $id; Status = $status; Source = $used }
  Start-Sleep -Milliseconds 300
}
$rows | Export-Csv -Path (Join-Path $outDir 'download_report.csv') -NoTypeInformation -Encoding UTF8
$dl = ($rows | Where-Object Status -eq 'downloaded').Count
"SUMMARY downloaded=$dl / $($rows.Count)"
$rows | Group-Object Status | ForEach-Object { "  $($_.Name): $($_.Count)" }
