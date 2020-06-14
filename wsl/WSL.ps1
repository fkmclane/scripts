Get-Process -Name Xming -ErrorAction SilentlyContinue > $null
if (-Not $?) {
    Start-Process "$Env:ProgramFiles\Xming\Xming.exe" :0,-clipboard,-multiwindow,-nolisten,inet6 -NoNewWindow
}

$env:DISPLAY=':0'

while (-Not (& "$Env:ProgramFiles\Xming\xprop.exe" -root)) {
    Start-Sleep -Milliseconds 500
}

& "$Env:ProgramFiles\Xming\xhost.exe" +(& wsl -e hostname -I) > $null

Start-Process wsl '-e',bash,-c,'"cd ~; export DISPLAY=`ip route list default | head -n1 | sed -e ''s/^default via \([0-9a-f.:]\+\) .*$/\1/''`:0; exec alacritty -e fish"' -NoNewWindow