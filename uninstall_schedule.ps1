$taskName = 'HermesAI-News-Briefing'
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Output "Scheduled task removed: $taskName"