param(
    [string]$Ip = "",
    [string]$Dns = "localhost"
)

$ErrorActionPreference = "Stop"

$certDir = Join-Path $PSScriptRoot "certs"
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

$certFile = Join-Path $certDir "server.pem"
$keyFile = Join-Path $certDir "server.key"

$san = "DNS:$Dns,IP:127.0.0.1"
if ($Ip) {
    $san = "$san,IP:$Ip"
}

$mkcert = Get-Command mkcert -ErrorAction SilentlyContinue
if ($mkcert) {
    $names = @($Dns, "127.0.0.1")
    if ($Ip) {
        $names += $Ip
    }

    & $mkcert.Source -install
    & $mkcert.Source -cert-file $certFile -key-file $keyFile @names
    if ($LASTEXITCODE -ne 0) {
        throw "mkcert no pudo generar el certificado."
    }
    Write-Host "Certificado generado con mkcert en $certDir"
    return
}

$openssl = (Get-Command openssl -ErrorAction SilentlyContinue).Source
if (-not $openssl) {
    $candidates = @(
        (Join-Path $env:ProgramFiles "Git\usr\bin\openssl.exe"),
        (Join-Path $env:ProgramFiles "Git\mingw64\bin\openssl.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $openssl = $candidate
            break
        }
    }
}

if ($openssl) {
    & $openssl req -x509 -nodes -newkey rsa:2048 -days 365 `
        -keyout $keyFile -out $certFile `
        -subj "/CN=$Dns" -addext "subjectAltName=$san"
    if ($LASTEXITCODE -ne 0) {
        throw "openssl no pudo generar el certificado."
    }
    Write-Host "Certificado autofirmado generado en $certDir"
    Write-Host "El navegador mostrara un aviso; es normal en local."
    return
}

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    throw "Instala mkcert, OpenSSL o Docker para generar el certificado local."
}

docker run --rm --mount "type=bind,source=$certDir,target=/certs" alpine:3.20 sh -c "apk add --no-cache openssl >/dev/null && openssl req -x509 -nodes -newkey rsa:2048 -days 365 -keyout /certs/server.key -out /certs/server.pem -subj '/CN=$Dns' -addext 'subjectAltName=$san'"
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo generar el certificado con Docker."
}

Write-Host "Certificado autofirmado generado en $certDir"
Write-Host "El navegador mostrara un aviso; es normal en local."
