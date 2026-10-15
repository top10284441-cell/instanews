# =====================================================
# InstaBonus 텔레그램 자동 발송 — 스케줄러 재등록 스크립트
# 반드시 PowerShell을 "관리자 권한으로 실행"해서 사용하세요.
# =====================================================

$batPath = "d:\사용자파일\바탕화면\antigravity\instagrm_Auto\run_schedule.bat"

# 현재 로그인한 사용자 이름 자동 감지
$currentUser = "$env:USERDOMAIN\$env:USERNAME"

# 비밀번호 입력 (PC가 잠금 상태여도 실행되려면 필요)
$password = Read-Host "🔑 Windows 로그인 비밀번호를 입력하세요 (PC 잠금 상태에서도 실행됨)" -AsSecureString
$plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
)

# 실행 설정: 배터리 차단 해제, 로그온 없이 실행 가능
$settings = New-ScheduledTaskSettingsSet `
    -DisallowStartIfOnBatteries:$false `
    -StopIfGoingOnBatteries:$false `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

$action = New-ScheduledTaskAction -Execute $batPath

$triggerMorning = New-ScheduledTaskTrigger -Daily -At "09:00"
$triggerEvening = New-ScheduledTaskTrigger -Daily -At "18:00"

# 기존 태스크 삭제 후 재등록 (비밀번호 포함 → 로그온 없이 실행 가능)
Unregister-ScheduledTask -TaskName "InstaBonus_Morning_09" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "InstaBonus_Evening_18" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "InstaBonus_Morning_09" `
    -Action $action `
    -Trigger $triggerMorning `
    -Settings $settings `
    -User $currentUser `
    -Password $plainPassword `
    -RunLevel Highest `
    -Force

Register-ScheduledTask `
    -TaskName "InstaBonus_Evening_18" `
    -Action $action `
    -Trigger $triggerEvening `
    -Settings $settings `
    -User $currentUser `
    -Password $plainPassword `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "✅ [Windows 작업 스케줄러 등록 완료]" -ForegroundColor Green
Write-Host "   - 매일 오전 09:00 자동 실행 (InstaBonus_Morning_09)"
Write-Host "   - 매일 오후 18:00 자동 실행 (InstaBonus_Evening_18)"
Write-Host "   - PC 잠금/절전 상태에서도 자동 실행됩니다."
Write-Host ""
Write-Host "📋 로그 확인 위치:"
Write-Host "   d:\사용자파일\바탕화면\antigravity\instagrm_Auto\telegram_schedule.log"
Write-Host ""

# 즉시 테스트 실행 여부 확인
$test = Read-Host "지금 바로 테스트 실행 해볼까요? (y/n)"
if ($test -eq "y" -or $test -eq "Y") {
    Write-Host "▶ 테스트 실행 중..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName "InstaBonus_Morning_09"
    Start-Sleep -Seconds 5
    $result = (Get-ScheduledTaskInfo -TaskName "InstaBonus_Morning_09").LastTaskResult
    Write-Host "실행 결과 코드: $result"
    if ($result -eq 0) {
        Write-Host "✅ 성공!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  코드 $result — 로그 파일을 확인하세요." -ForegroundColor Yellow
    }
}
