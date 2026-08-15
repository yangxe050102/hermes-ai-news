# 安装每日 08:00 的 Windows 计划任务（通过 ai-news-briefing 技能运行）
$taskName = 'HermesAI-News-Briefing'
$skillScript = Join-Path $env:USERPROFILE '.codex\skills\ai-news-briefing\scripts\run.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$skillScript`""
$trigger = New-ScheduledTaskTrigger -Daily -At 8am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
  -Description 'AI daily briefing: run via ai-news-briefing skill' -Force | Out-Null
Write-Output "Scheduled task installed: $taskName (daily 08:00, skill entry)"