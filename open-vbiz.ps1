# Mở Vbiz Café và nhờ GitHub cập nhật tin (dùng `gh` đã đăng nhập sẵn trên máy, không cần token riêng).
# Shortcut "Vbiz Café" trên Desktop chạy file này.
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "HarryyNgg/vbiz-cafe"

# Lượt gần nhất mới chạy trong 20 phút thì thôi, tránh mở trang nhiều lần là chạy dồn
$last = & $gh run list --repo $repo --workflow vbiz.yml --limit 1 --json createdAt -q ".[0].createdAt" 2>$null
if (-not $last -or ((Get-Date).ToUniversalTime() - [datetime]::Parse($last).ToUniversalTime()).TotalMinutes -gt 20) {
    & $gh workflow run vbiz.yml --repo $repo 2>$null | Out-Null
}

Start-Process "https://harryyngg.github.io/vbiz-cafe/"
