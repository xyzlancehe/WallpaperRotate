
$python = Get-Command "pythonw.exe" | Select-Object -ExpandProperty Source
Write-Host "Use python: $python" -ForegroundColor Green
$action = New-ScheduledTaskAction -Execute $python -Argument "WallpaperRotate.py" -WorkingDirectory $pwd.Path
$trigger = New-ScheduledTaskTrigger -AtLogon -User $env:UserName
Register-ScheduledTask -Force -TaskName "WallpaperRotate" -Action $action -Trigger $trigger -TaskPath "\Custom\"