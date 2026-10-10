$batPath = "d:\사용자파일\바탕화면\antigravity\instagrm_Auto\run_schedule.bat"
$action = New-ScheduledTaskAction -Execute $batPath
$triggerMorning = New-ScheduledTaskTrigger -Daily -At 9:00am
$triggerEvening = New-ScheduledTaskTrigger -Daily -At 6:00pm

Register-ScheduledTask -TaskName "InstaBonus_Morning_09" -Action $action -Trigger $triggerMorning -Force
Register-ScheduledTask -TaskName "InstaBonus_Evening_18" -Action $action -Trigger $triggerEvening -Force

Write-Host "✅ [Windows 작업 스케줄러 등록 완료]"
Write-Host "- 매일 오전 09:00 (InstaBonus_Morning_09)"
Write-Host "- 매일 오후 18:00 (InstaBonus_Evening_18)"
