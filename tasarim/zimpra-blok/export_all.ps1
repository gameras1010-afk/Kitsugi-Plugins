$ErrorActionPreference = 'Stop'
$openscad = (Get-Command openscad -ErrorAction SilentlyContinue).Source
if (-not $openscad) {
    Write-Error 'OpenSCAD CLI bulunamadi. OpenSCAD kurulum klasorunu PATH degiskenine ekleyip tekrar deneyin.'
    exit 1
}
Set-Location $PSScriptRoot
foreach ($sz in @('S','M','L')) {
    foreach ($piece in @('base','pivot','grip')) {
        $out = "${piece}_${sz}.stl"
        & $openscad -o $out -D ('size="{0}"' -f $sz) -D ('part="{0}"' -f $piece) .\zimpra_blok.scad
        if ($LASTEXITCODE -ne 0) { throw "STL export failed: $out" }
    }
}
Write-Host 'Bitti: 9 STL dosyasi olusturuldu. Slicerda olculeri ve montaji kontrol edin.'
