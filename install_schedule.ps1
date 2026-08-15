# 安装每日 08:00 的 Windows 计划任务
$taskName = 'HermesAI-News-Briefing'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$here\run.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 8am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
  -Description 'AI 热点日报：抓取→翻译→GitHub Pages 部署→飞书推送' -Force | Out-Null
Write-Output "已安装计划任务 $taskName（每日 08:00）"