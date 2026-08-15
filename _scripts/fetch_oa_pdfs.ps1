# 批量检测 138 个 DOI 的 OA 状态并下载 OA PDF（Unpaywall）
$ErrorActionPreference = 'Continue'
$dois = Get-Content -Encoding UTF8 'F:\deepseek harness\zotero_doi_list.txt' | Where-Object { $_ -match '^10\.' } | Sort-Object -Unique
$outDir = 'F:\deepseek harness\pdfs'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$rows = @()
$i = 0
foreach ($d in $dois) {
  $i++
  $safe = ($d -replace '[^A-Za-z0-9._-]', '_')
  $file = Join-Path $outDir ($safe + '.pdf')
  $status = 'no_oa'; $pdfUrl = ''
  try {
    $r = Invoke-RestMethod -Uri ("https://api.unpaywall.org/v2/" + $d + "?email=test@mail.com") -TimeoutSec 40
    if ($r.is_oa) {
      $loc = $r.best_oa_location
      if ($loc -and $loc.url_for_pdf) { $pdfUrl = $loc.url_for_pdf }
      elseif ($loc -and $loc.url) { $pdfUrl = $loc.url }
      if ($pdfUrl) {
        try {
          Invoke-WebRequest -Uri $pdfUrl -OutFile $file -TimeoutSec 70 -MaximumRedirection 12 -UseBasicParsing
          $len = (Get-Item $file -ErrorAction SilentlyContinue).Length
          if ($len -and $len -gt 20000) { $status = 'downloaded' } else { $status = 'small_or_error'; Remove-Item $file -ErrorAction SilentlyContinue }
        } catch { $status = 'download_failed' }
      } else { $status = 'oa_no_pdf_url' }
    }
  } catch { $status = 'api_error' }
  $rows += [pscustomobject]@{ No = $i; DOI = $d; Status = $status; PdfUrl = $pdfUrl; File = if ($status -eq 'downloaded') { $file } else { '' } }
  Start-Sleep -Milliseconds 900
}
$rows | Export-Csv -Path 'F:\deepseek harness\unpaywall_report.csv' -NoTypeInformation -Encoding UTF8
$dl = ($rows | Where-Object Status -eq 'downloaded').Count
$no = ($rows | Where-Object Status -eq 'no_oa').Count
$other = $rows.Count - $dl - $no
"SUMMARY downloaded=$dl no_oa=$no other=$other total=$($rows.Count)"
