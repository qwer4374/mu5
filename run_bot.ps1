# Advanced Telegram Bot - PowerShell Runner
# =====================================
# Script to run the Telegram bot on Windows 11 with VS Code
# Author: Advanced Bot Developer
# Version: 2.0.0

param(
    [switch]$Install,
    [switch]$Update,
    [switch]$Clean,
    [switch]$Debug,
    [switch]$Help
)

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$InfoColor = "Cyan"
$WarningColor = "Yellow"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Show-Help {
    Write-ColorOutput "🤖 Advanced Telegram Bot - PowerShell Runner" $InfoColor
    Write-ColorOutput "=============================================" $InfoColor
    Write-Host ""
    Write-ColorOutput "Usage:" $InfoColor
    Write-ColorOutput "  .\run_bot.ps1                 # Run the bot" $InfoColor
    Write-ColorOutput "  .\run_bot.ps1 -Install        # Install dependencies" $InfoColor
    Write-ColorOutput "  .\run_bot.ps1 -Update         # Update dependencies" $InfoColor
    Write-ColorOutput "  .\run_bot.ps1 -Clean          # Clean cache and temp files" $InfoColor
    Write-ColorOutput "  .\run_bot.ps1 -Debug          # Run in debug mode" $InfoColor
    Write-ColorOutput "  .\run_bot.ps1 -Help           # Show this help" $InfoColor
    Write-Host ""
    Write-ColorOutput "Requirements:" $WarningColor
    Write-ColorOutput "  - Python 3.8 or higher" $WarningColor
    Write-ColorOutput "  - pip package manager" $WarningColor
    Write-ColorOutput "  - Internet connection" $WarningColor
    Write-Host ""
}

function Test-PythonInstallation {
    Write-ColorOutput "🔍 Checking Python installation..." $InfoColor
    
    try {
        $pythonVersion = python3 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Python found: $pythonVersion" $SuccessColor
            return $true
        }
    }
    catch {
        Write-ColorOutput "❌ Python not found in PATH" $ErrorColor
        Write-ColorOutput "Please install Python 3.8+ from https://python.org" $WarningColor
        return $false
    }
    
    return $false
}

function Test-PipInstallation {
    Write-ColorOutput "🔍 Checking pip installation..." $InfoColor
    
    try {
        $pipVersion = pip3 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ pip found: $pipVersion" $SuccessColor
            return $true
        }
    }
    catch {
        Write-ColorOutput "❌ pip not found" $ErrorColor
        Write-ColorOutput "Please ensure pip is installed with Python" $WarningColor
        return $false
    }
    
    return $false
}

function Install-Dependencies {
    Write-ColorOutput "📦 Installing Python dependencies..." $InfoColor
    
    if (-not (Test-Path "requirements.txt")) {
        Write-ColorOutput "❌ requirements.txt not found!" $ErrorColor
        return $false
    }
    
    try {
        Write-ColorOutput "Installing packages from requirements.txt..." $InfoColor
        pip3 install -r requirements.txt --upgrade
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Dependencies installed successfully!" $SuccessColor
            return $true
        } else {
            Write-ColorOutput "❌ Failed to install dependencies" $ErrorColor
            return $false
        }
    }
    catch {
        Write-ColorOutput "❌ Error installing dependencies: $_" $ErrorColor
        return $false
    }
}

function Update-Dependencies {
    Write-ColorOutput "🔄 Updating Python dependencies..." $InfoColor
    
    try {
        pip3 install -r requirements.txt --upgrade --force-reinstall
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Dependencies updated successfully!" $SuccessColor
            return $true
        } else {
            Write-ColorOutput "❌ Failed to update dependencies" $ErrorColor
            return $false
        }
    }
    catch {
        Write-ColorOutput "❌ Error updating dependencies: $_" $ErrorColor
        return $false
    }
}

function Clean-Environment {
    Write-ColorOutput "🧹 Cleaning environment..." $InfoColor
    
    # Clean Python cache
    if (Test-Path "__pycache__") {
        Remove-Item -Recurse -Force "__pycache__"
        Write-ColorOutput "✅ Removed __pycache__" $SuccessColor
    }
    
    # Clean .pyc files
    Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
    Write-ColorOutput "✅ Removed .pyc files" $SuccessColor
    
    # Clean logs (keep recent ones)
    if (Test-Path "data\logs") {
        $oldLogs = Get-ChildItem "data\logs" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
        $oldLogs | Remove-Item -Force
        Write-ColorOutput "✅ Cleaned old log files" $SuccessColor
    }
    
    # Clean temporary downloads
    if (Test-Path "data\downloads") {
        $tempFiles = Get-ChildItem "data\downloads" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddHours(-24) }
        $tempFiles | Remove-Item -Force
        Write-ColorOutput "✅ Cleaned temporary download files" $SuccessColor
    }
    
    Write-ColorOutput "✅ Environment cleaned successfully!" $SuccessColor
}

function Initialize-Environment {
    Write-ColorOutput "🚀 Initializing bot environment..." $InfoColor
    
    # Create necessary directories
    $directories = @("data", "data\logs", "data\downloads", "data\backups", "data\cache")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-ColorOutput "✅ Created directory: $dir" $SuccessColor
        }
    }
    
    # Check config file
    if (-not (Test-Path "config.py")) {
        Write-ColorOutput "❌ config.py not found!" $ErrorColor
        return $false
    }
    
    Write-ColorOutput "✅ Environment initialized successfully!" $SuccessColor
    return $true
}

function Start-Bot {
    param([bool]$DebugMode = $false)
    
    Write-ColorOutput "🤖 Starting Advanced Telegram Bot..." $InfoColor
    Write-Host ""
    
    if ($DebugMode) {
        Write-ColorOutput "🐛 Debug mode enabled" $WarningColor
        $env:LOG_LEVEL = "DEBUG"
    }
    
    try {
        # Set environment variables for Windows
        $env:PYTHONPATH = $PWD
        $env:PYTHONIOENCODING = "utf-8"
        
        # Start the bot
        python3 main.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Bot stopped gracefully" $SuccessColor
        } else {
            Write-ColorOutput "❌ Bot stopped with error code: $LASTEXITCODE" $ErrorColor
        }
    }
    catch {
        Write-ColorOutput "❌ Error starting bot: $_" $ErrorColor
    }
}

function Show-BotInfo {
    Write-ColorOutput "🤖 Advanced Telegram Bot v2.0.0" $InfoColor
    Write-ColorOutput "================================" $InfoColor
    Write-Host ""
    Write-ColorOutput "Features:" $InfoColor
    Write-ColorOutput "  ✅ Advanced file downloading" $SuccessColor
    Write-ColorOutput "  ✅ User management and analytics" $SuccessColor
    Write-ColorOutput "  ✅ Admin panel and controls" $SuccessColor
    Write-ColorOutput "  ✅ Scheduled tasks and automation" $SuccessColor
    Write-ColorOutput "  ✅ Backup and security features" $SuccessColor
    Write-ColorOutput "  ✅ Multi-language support" $SuccessColor
    Write-ColorOutput "  ✅ Rate limiting and spam protection" $SuccessColor
    Write-ColorOutput "  ✅ Interactive UI with inline keyboards" $SuccessColor
    Write-Host ""
    Write-ColorOutput "Bot Token: 1862186312:AAEgq9cIQDbf2MitTjDMjYKPgdD9eGCPSlI" $InfoColor
    Write-ColorOutput "Owner ID: 697852646" $InfoColor
    Write-Host ""
}

# Main execution
Clear-Host
Show-BotInfo

if ($Help) {
    Show-Help
    exit 0
}

# Check system requirements
if (-not (Test-PythonInstallation)) {
    exit 1
}

if (-not (Test-PipInstallation)) {
    exit 1
}

# Handle command line arguments
if ($Install) {
    if (Install-Dependencies) {
        Write-ColorOutput "🎉 Installation completed successfully!" $SuccessColor
        Write-ColorOutput "You can now run the bot with: .\run_bot.ps1" $InfoColor
    }
    exit 0
}

if ($Update) {
    Update-Dependencies
    exit 0
}

if ($Clean) {
    Clean-Environment
    exit 0
}

# Initialize environment
if (-not (Initialize-Environment)) {
    Write-ColorOutput "❌ Failed to initialize environment" $ErrorColor
    exit 1
}

# Check if dependencies are installed
try {
    python3 -c "import telegram; import sqlalchemy; import aiohttp" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ Dependencies not installed. Run with -Install flag first." $ErrorColor
        Write-ColorOutput "Example: .\run_bot.ps1 -Install" $WarningColor
        exit 1
    }
}
catch {
    Write-ColorOutput "❌ Dependencies check failed. Please install dependencies first." $ErrorColor
    exit 1
}

# Start the bot
Write-ColorOutput "Press Ctrl+C to stop the bot" $WarningColor
Write-Host ""

Start-Bot -DebugMode $Debug

Write-ColorOutput "👋 Thank you for using Advanced Telegram Bot!" $InfoColor

