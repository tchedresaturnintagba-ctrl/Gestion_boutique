param(
    [string]$PostgresBin = "C:\Program Files\PostgreSQL\18\bin",
    [string]$DatabaseName = "gestion_boutiques",
    [string]$DatabaseUser = "gestion_boutiques"
)

$ErrorActionPreference = "Stop"
$psql = Join-Path $PostgresBin "psql.exe"
if (-not (Test-Path $psql)) {
    throw "psql.exe introuvable dans $PostgresBin"
}

function New-SecureValue([int]$ByteCount) {
    $bytes = New-Object byte[] $ByteCount
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
        return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    } finally {
        $generator.Dispose()
    }
}

$adminPassword = Read-Host "Mot de passe de l'utilisateur PostgreSQL postgres" -AsSecureString
$adminPasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPassword)

try {
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($adminPasswordPointer)
    $databasePassword = New-SecureValue 32
    $jwtSecret = New-SecureValue 48

    $roleExists = & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc `
        "SELECT 1 FROM pg_roles WHERE rolname = '$DatabaseUser'"
    if ($LASTEXITCODE -ne 0) { throw "Impossible de vérifier le rôle PostgreSQL." }

    if (-not $roleExists) {
        & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
            "CREATE ROLE $DatabaseUser LOGIN PASSWORD '$databasePassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;"
    } else {
        & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
            "ALTER ROLE $DatabaseUser WITH LOGIN PASSWORD '$databasePassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;"
    }
    if ($LASTEXITCODE -ne 0) { throw "Impossible de préparer le rôle PostgreSQL." }

    $databaseExists = & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc `
        "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName'"
    if ($LASTEXITCODE -ne 0) { throw "Impossible de vérifier la base PostgreSQL." }

    if (-not $databaseExists) {
        & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
            "CREATE DATABASE $DatabaseName OWNER $DatabaseUser;"
    } else {
        & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
            "ALTER DATABASE $DatabaseName OWNER TO $DatabaseUser;"
    }
    if ($LASTEXITCODE -ne 0) { throw "Impossible de préparer la base PostgreSQL." }

    $envPath = Join-Path $PSScriptRoot "..\apps\api\.env"
    $envContent = @(
        "GB_ENVIRONMENT=development"
        'GB_CORS_ORIGINS=["http://localhost:5173"]'
        "GB_DATABASE_URL=postgresql+asyncpg://${DatabaseUser}:${databasePassword}@127.0.0.1:5432/${DatabaseName}"
        "GB_JWT_SECRET_KEY=${jwtSecret}"
    ) -join [Environment]::NewLine
    [IO.File]::WriteAllText($envPath, $envContent + [Environment]::NewLine)

    Write-Host "Base, rôle applicatif et fichier apps/api/.env préparés." -ForegroundColor Green
} finally {
    $env:PGPASSWORD = $null
    if ($adminPasswordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($adminPasswordPointer)
    }
}