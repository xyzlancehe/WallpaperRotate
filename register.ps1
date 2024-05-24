
$python = Get-Command "pythonw.exe" | Select-Object -ExpandProperty Source
Write-Host "Use python: $python" -ForegroundColor Green
$launchScript = Get-Item -Path "start.ps1" | Select-Object -ExpandProperty FullName
$pythonScript = Get-Item -Path "WallpaperRotate.py" | Select-Object -ExpandProperty FullName
$psArgString = "-File $launchScript $python $pythonScript"
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument $psArgString -WorkingDirectory $pwd.Path
$trigger = New-ScheduledTaskTrigger -AtLogon -User $env:UserName
Register-ScheduledTask -Force -TaskName "WallpaperRotate for $env:UserName" -Action $action -Trigger $trigger -TaskPath "\Custom\"