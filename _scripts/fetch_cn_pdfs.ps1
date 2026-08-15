# 下载中文论文：期刊官网直链 PDF 直接下载，知网/万方付费页标记需手动
$ErrorActionPreference = 'Continue'
$t = Get-Content -Raw -Encoding UTF8 'F:\deepseek harness\中美欧日中近岸养殖政策文献总目.md'
$cnIds = 1..32 | ForEach-Object { 'CN-{0:D2}' -f $_ }
$cnIds += @('CN-54','CN-56','CN-58','CN-59','CN-61','CN-62','CN-63','CN-64','CN-65','CN-68','CN-69','CN-71','CN-73','CN-74','CN-75','CN-76','CN-77','JP-31','JP-37','KR-02')
$outDir = 'F:\deepseek harness\pdfs_cn'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

$rows = @()
foreach ($id in $cnIds) {
  $m = [regex]::Match($t, '(?m)^\| ' + [regex]::Escape($id) + ' \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|')
  $lit = ''; $linkCol = ''
  if ($m.Success) { $lit = ($m.Groups[1].Value -replace '\[([^\]]*)\]\([^)]*\)', '$1').Trim(); $linkCol = $m.Groups[3].Value }
  $urls = [regex]::Matches($linkCol, 'https?://[^\s\)\]]+') | ForEach-Object { $_.Value }
  $file = Join-Path $outDir ($id + '.pdf')
  $status = 'no_link'; $used = ''
  foreach ($u in $urls) {
    $isPdfLike = ($u -match 'create_pdf') -or ($u -match '\.pdf') -or ($u -match 'sciengine') -or ($u -match '/CN/PDF/') -or ($u -match 'pdfpreview') -or ($u -match 'open\.pdf')
    $isPaid = ($u -match 'cnki') -or ($u -match 'wanfang') -or ($u -match 'cqvip')
    if ($isPdfLike) {
      try {
        Invoke-WebRequest -Uri $u -OutFile $file -TimeoutSec 70 -MaximumRedirection 12 -UseBasicParsing -Headers @{'User-Agent'=$UA;'Referer'='https://www.baidu.com/'}
        $len = (Get-Item $file -ErrorAction SilentlyContinue).Length
        if ($len -and $len -gt 20000) { $status = 'downloaded'; $used = $u; break }
        else { $status = 'small_or_error'; Remove-Item $file -ErrorAction SilentlyContinue }
      } catch { $status = 'download_failed'; $used = $u }
    } elseif (-not $isPaid) {
      # 其他链接（期刊官网摘要页）尝试解析 PDF
      try {
        $html = (Invoke-WebRequest -Uri $u -TimeoutSec 50 -UseBasicParsing -Headers @{'User-Agent'=$UA}).Content
        $pm = [regex]::Match($html, 'href="([^"]*(?:create_pdf|\.pdf|CN/PDF)[^"]*)"', 'IgnoreCase')
        if ($pm.Success) {
          $pdfUrl = $pm.Groups[1].Value
          if ($pdfUrl -notmatch '^https?://') { $pdfUrl = ([uri]$u).GetLeftPart([uri]::Authority) + $pdfUrl }
          Invoke-WebRequest -Uri $pdfUrl -OutFile $file -TimeoutSec 70 -MaximumRedirection 12 -UseBasicParsing -Headers @{'User-Agent'=$UA}
          $len = (Get-Item $file -ErrorAction SilentlyContinue).Length
          if ($len -and $len -gt 20000) { $status = 'downloaded'; $used = $pdfUrl; break }
          else { $status = 'small_or_error'; Remove-Item $file -ErrorAction SilentlyContinue }
        } else { $status = 'page_no_pdf_link' }
      } catch { if ($status -ne 'small_or_error') { $status = 'page_fetch_failed' } }
    } else { $status = 'needs_subscription'; $used = $u }
  }
  $rows += [pscustomobject]@{ Id = $id; Title = $lit; Status = $status; Source = $used }
  Start-Sleep -Milliseconds 400
}
$rows | Export-Csv -Path 'F:\deepseek harness\pdfs_cn\download_report.csv' -NoTypeInformation -Encoding UTF8
$dl = ($rows | Where-Object Status -eq 'downloaded').Count
"SUMMARY downloaded=$dl / $($rows.Count)"
$rows | Where-Object Status -eq 'downloaded' | ForEach-Object { "  $($_.Id)  $($_.Status)" }
