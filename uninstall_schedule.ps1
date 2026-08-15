$taskName = 'HermesAI-News-Briefing'
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Output "已移除计划任务 $taskName"