
# 修复ScanManagement.vue中的反斜杠转义问题
$file = "c:\Users\ranma\CodeGeeXProjects\media-service\frontend\src\views\ScanManagement.vue"
$content = Get-Content $file -Raw -Encoding UTF8

# 替换错误的反斜杠转义
$content = $content -replace "path\.includes\(''\)", "path.includes('\\')"
$content = $content -replace " \? ''", " ? '\\'"

Set-Content $file $content -Encoding UTF8
Write-Host "修复完成"
