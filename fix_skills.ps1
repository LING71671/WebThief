# 批量修复技能文件的 frontmatter
$skillsDir = "$env:USERPROFILE\.trae\skills"
$categories = @('ai_engineering', 'architecture', 'backend', 'code_management', 'devops', 'documentation', 'frontend', 'mobile', 'security', 'testing')

$totalFixed = 0
$success = 0

foreach ($category in $categories) {
    $categoryDir = Join-Path $skillsDir $category
    if (-not (Test-Path $categoryDir)) { continue }
    
    $skillDirs = Get-ChildItem $categoryDir -Directory
    foreach ($skillDir in $skillDirs) {
        $skillFile = Join-Path $skillDir.FullName "SKILL.md"
        if (-not (Test-Path $skillFile)) { continue }
        
        $totalFixed++
        try {
            $content = Get-Content $skillFile -Raw -Encoding UTF8
            $lines = $content -split "`n"
            
            $name = ""
            $oldDesc = ""
            
            $inFrontmatter = $false
            foreach ($line in $lines) {
                if ($line.Trim() -eq "---") {
                    if (-not $inFrontmatter) {
                        $inFrontmatter = $true
                        continue
                    } else {
                        break
                    }
                }
                
                if ($inFrontmatter) {
                    if ($line.Trim().StartsWith('name:')) {
                        $name = $line.Trim().Split(':', 2)[1].Trim().Trim('"')
                    } elseif ($line.Trim().StartsWith('description:')) {
                        $oldDesc = $line.Trim().Split(':', 2)[1].Trim().Trim('"')
                    }
                }
            }
            
            $newDesc = $oldDesc
            $newDesc = $newDesc -replace '\s*当用户需要.*$', ''
            $newDesc = $newDesc -replace '\s*当用户询问相关主题时调用此技能\.', ''
            $newDesc = $newDesc.Trim().Trim('.')
            
            if ($newDesc.Length -gt 180) {
                $newDesc = $newDesc.Substring(0, 177) + "..."
            }
            
            $newFrontmatter = "---`nname: `"$name`"`ndescription: `"$newDesc`"`n---`n`n"
            
            $secondTripleDash = $content.IndexOf("---", 3)
            if ($secondTripleDash -ne -1) {
                $remainingContent = $content.Substring($secondTripleDash + 4)
                $newContent = $newFrontmatter + $remainingContent
                Set-Content -Path $skillFile -Value $newContent -Encoding UTF8 -NoNewline
                Write-Host "✓ 修复: $($skillDir.Name)/$($category)"
                $success++
            }
        } catch {
            Write-Host "✗ 失败: $($skillDir.Name)/$($category): $_"
        }
    }
}

Write-Host "`n修复完成!"
Write-Host "总计: $totalFixed"
Write-Host "成功: $success"
Write-Host "失败: $($totalFixed - $success)"
