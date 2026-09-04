# Cotygodniowy bieg inv-adv: pelny cykl (run.py) + lokalny dashboard.
# Log: reports/logs/run-YYYY-MM-DD.log. Blad = wpis w logu; punkt historii
# NIE jest dopisywany przy bledzie (lepsza luka niz zly punkt).
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
$logDir = Join-Path $project "reports\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("run-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

"=== inv-adv weekly run: {0} ===" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss") *>> $log

python run.py *>> $log
if ($LASTEXITCODE -ne 0) {
    "BLAD: run.py zakonczyl sie kodem $LASTEXITCODE - punkt historii NIE zostal dopisany" *>> $log
    exit 1
}

python -m inv_adv.publish *>> $log
if ($LASTEXITCODE -ne 0) {
    "BLAD: publish zakonczyl sie kodem $LASTEXITCODE (protokol OK, dashboard nieodswiezony)" *>> $log
    exit 1
}

"ZAKONCZONO OK" *>> $log
exit 0