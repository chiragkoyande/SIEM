# SentinelWatch SIEM Deployment Script for Windows
# This script handles both development and production deployments

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [switch]$Clean,
    
    [Parameter(Mandatory=$false)]
    [switch]$Build
)

Write-Host "SentinelWatch SIEM Deployment Script" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow

# Function to check if Docker is installed
function Test-DockerInstalled {
    try {
        docker --version | Out-Null
        return $true
    }
    catch {
        Write-Host "Docker is not installed or not running!" -ForegroundColor Red
        Write-Host "Please install Docker Desktop for Windows." -ForegroundColor Red
        return $false
    }
}

# Function to check if docker-compose is available
function Test-DockerCompose {
    try {
        docker-compose --version | Out-Null
        return $true
    }
    catch {
        Write-Host "docker-compose is not available!" -ForegroundColor Red
        return $false
    }
}

# Function to clean up existing containers
function Invoke-Cleanup {
    Write-Host "Cleaning up existing containers and images..." -ForegroundColor Yellow
    docker-compose down -v --remove-orphans
    docker system prune -f
    Write-Host "Cleanup completed." -ForegroundColor Green
}

# Function to setup environment file
function Initialize-Environment {
    if (-not (Test-Path ".env")) {
        Write-Host "Creating .env file from template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "Please edit .env file with your configuration before running in production!" -ForegroundColor Yellow
    }
}

# Function to create necessary directories
function Initialize-Directories {
    $directories = @("logs", "ssl")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "Created directory: $dir" -ForegroundColor Green
        }
    }
}

# Main deployment function
function Start-Deployment {
    # Check prerequisites
    if (-not (Test-DockerInstalled)) {
        exit 1
    }
    
    if (-not (Test-DockerCompose)) {
        exit 1
    }

    # Initialize environment
    Initialize-Environment
    Initialize-Directories

    # Cleanup if requested
    if ($Clean) {
        Invoke-Cleanup
    }

    # Build and run
    Write-Host "Starting deployment..." -ForegroundColor Green
    
    if ($Environment -eq "prod") {
        Write-Host "Starting production deployment with nginx..." -ForegroundColor Yellow
        docker-compose --profile production up --build -d
        Write-Host "Production deployment started!" -ForegroundColor Green
        Write-Host "Application available at: http://localhost" -ForegroundColor Cyan
    }
    else {
        Write-Host "Starting development deployment..." -ForegroundColor Yellow
        docker-compose up --build -d
        Write-Host "Development deployment started!" -ForegroundColor Green
        Write-Host "Application available at: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "API documentation: http://localhost:8000/docs" -ForegroundColor Cyan
    }
}

# Function to show status
function Show-Status {
    Write-Host "Container status:" -ForegroundColor Yellow
    docker-compose ps
    
    Write-Host "`nHealth check:" -ForegroundColor Yellow
    try {
        if ($Environment -eq "prod") {
            $response = Invoke-WebRequest -Uri "http://localhost/health" -TimeoutSec 5
        } else {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
        }
        Write-Host "Application is healthy!" -ForegroundColor Green
    }
    catch {
        Write-Host "Health check failed. Application may still be starting..." -ForegroundColor Yellow
    }
}

# Execute deployment
try {
    Start-Deployment
    
    # Wait a moment for containers to start
    Start-Sleep -Seconds 5
    
    Show-Status
    
    Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
    Write-Host "Use 'docker-compose logs -f' to view logs" -ForegroundColor Cyan
    Write-Host "Use 'docker-compose down' to stop the application" -ForegroundColor Cyan
}
catch {
    Write-Host "Deployment failed: $_" -ForegroundColor Red
    exit 1
}
