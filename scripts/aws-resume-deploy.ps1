# CloudMLOps — resume AWS deployment from Step 6 (VPC connector onward).
#
# Prerequisites (one-time on your PC):
#   1. AWS CLI v2: https://aws.amazon.com/cli/
#   2. aws configure  (region us-east-2, access key from My security credentials)
#   3. Docker Desktop running
#
# Usage:
#   cd D:\CloudMLOps
#   .\scripts\aws-resume-deploy.ps1 -Action verify
#   .\scripts\aws-resume-deploy.ps1 -Action vpc-connector
#   .\scripts\aws-resume-deploy.ps1 -Action push-backend
#   .\scripts\aws-resume-deploy.ps1 -Action push-frontend -BackendUrl https://xxxxx.us-east-2.awsapprunner.com

param(
    [ValidateSet("verify", "vpc-connector", "push-backend", "push-frontend", "print-github-secrets")]
    [string]$Action = "verify",
    [string]$BackendUrl = "",
    [string]$Region = "us-east-2",
    [string]$AccountId = "569486438576",
    [string]$DbClusterId = "database-1",
    [string]$S3Bucket = "cloudmlops-uploads-569486438576",
    [string]$VpcConnectorName = "cloudmlops-connector",
    [string]$ConnectorSgName = "cloudmlops-connector-sg"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Require-AwsCli {
    $aws = Get-Command aws -ErrorAction SilentlyContinue
    if (-not $aws) {
        Write-Host "AWS CLI not found. Install from https://aws.amazon.com/cli/ then run: aws configure" -ForegroundColor Red
        exit 1
    }
    aws sts get-caller-identity | Out-Null
    Write-Host "AWS credentials OK" -ForegroundColor Green
}

function Require-Docker {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker is not running. Start Docker Desktop." -ForegroundColor Red
        exit 1
    }
}

function Invoke-Verify {
    Require-AwsCli
    Write-Host "`n=== Verify AWS resources ($Region) ===" -ForegroundColor Cyan

    Write-Host "`n-- RDS cluster --"
    aws rds describe-db-clusters --db-cluster-identifier $DbClusterId --region $Region `
        --query "DBClusters[0].{Status:Status,Endpoint:Endpoint,VpcId:VpcSecurityGroups[0].VpcSecurityGroupId}" `
        --output table 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "RDS cluster '$DbClusterId' not found or not accessible." -ForegroundColor Yellow
    }

    Write-Host "`n-- Secrets Manager --"
    aws secretsmanager list-secrets --region $Region `
        --query "SecretList[?starts_with(Name, 'cloudmlops/')].Name" --output table

    Write-Host "`n-- S3 bucket --"
    aws s3api head-bucket --bucket $S3Bucket --region $Region 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "Bucket $S3Bucket exists" -ForegroundColor Green }
    else { Write-Host "Bucket $S3Bucket missing" -ForegroundColor Yellow }

    Write-Host "`n-- ECR repositories --"
    aws ecr describe-repositories --region $Region `
        --query "repositories[?contains(repositoryName, 'cloudmlops')].repositoryName" --output table

    Write-Host "`n-- IAM roles --"
    foreach ($role in @("AppRunnerECRAccessRole", "CloudMLOpsInstanceRole", "GitHubActionsDeployRole")) {
        aws iam get-role --role-name $role --query "Role.RoleName" --output text 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Host "  OK: $role" -ForegroundColor Green }
        else { Write-Host "  MISSING: $role" -ForegroundColor Yellow }
    }

    Write-Host "`n-- VPC connectors --"
    aws apprunner list-vpc-connectors --region $Region `
        --query "VpcConnectors[?VpcConnectorName=='$VpcConnectorName'].{Name:VpcConnectorName,Status:Status,Arn:VpcConnectorArn}" `
        --output table 2>$null

    Write-Host "`n-- App Runner services --"
    aws apprunner list-services --region $Region `
        --query "ServiceSummaryList[?contains(ServiceName, 'cloudmlops')].{Name:ServiceName,Status:Status,Url:ServiceUrl}" `
        --output table 2>$null

    Write-Host "`nNext: .\scripts\aws-resume-deploy.ps1 -Action vpc-connector" -ForegroundColor Cyan
}

function Invoke-VpcConnector {
    Require-AwsCli

    $cluster = aws rds describe-db-clusters --db-cluster-identifier $DbClusterId --region $Region --output json | ConvertFrom-Json
    $clusterObj = $cluster.DBClusters[0]
    $rdsSgId = $clusterObj.VpcSecurityGroups[0].VpcSecurityGroupId

    $subnetGroup = aws rds describe-db-subnet-groups --region $Region `
        --query "DBSubnetGroups[?DBSubnetGroupName=='$($clusterObj.DBSubnetGroup)'].Subnets[].SubnetIdentifier" `
        --output json | ConvertFrom-Json
    if (-not $subnetGroup -or $subnetGroup.Count -lt 2) {
        # Fallback: default VPC subnets
        $vpcId = aws ec2 describe-subnets --region $Region `
            --filters "Name=default-for-az,Values=true" `
            --query "Subnets[].SubnetId" --output json | ConvertFrom-Json
        $subnetGroup = @($vpcId | Select-Object -First 2)
    }
    if ($subnetGroup.Count -lt 2) {
        throw "Need at least 2 subnet IDs for the VPC connector."
    }

    $existing = aws apprunner list-vpc-connectors --region $Region --output json | ConvertFrom-Json
    $found = $existing.VpcConnectors | Where-Object { $_.VpcConnectorName -eq $VpcConnectorName }
    if ($found) {
        Write-Host "VPC connector already exists: $($found.VpcConnectorArn)" -ForegroundColor Green
        Write-Host "`nNext: .\scripts\aws-resume-deploy.ps1 -Action push-backend" -ForegroundColor Cyan
        return
    }

    # Create connector security group in same VPC as RDS SG
    $rdsSg = aws ec2 describe-security-groups --group-ids $rdsSgId --region $Region --output json | ConvertFrom-Json
    $vpcId = $rdsSg.SecurityGroups[0].VpcId

    $connectorSg = aws ec2 describe-security-groups --region $Region `
        --filters "Name=group-name,Values=$ConnectorSgName" "Name=vpc-id,Values=$vpcId" `
        --query "SecurityGroups[0].GroupId" --output text 2>$null
    if ($connectorSg -eq "None" -or -not $connectorSg) {
        Write-Host "Creating security group $ConnectorSgName ..."
        $connectorSg = aws ec2 create-security-group --group-name $ConnectorSgName `
            --description "CloudMLOps App Runner VPC connector" --vpc-id $vpcId --region $Region `
            --query "GroupId" --output text
    }
    Write-Host "Connector SG: $connectorSg"

    # Allow connector -> RDS on 5432
    aws ec2 authorize-security-group-ingress --group-id $rdsSgId --protocol tcp --port 5432 `
        --source-group $connectorSg --region $Region 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "Added RDS inbound rule (5432 from connector SG)" -ForegroundColor Green }
    else { Write-Host "RDS inbound rule may already exist (OK)" -ForegroundColor Yellow }

    if (-not $found) {
        $subnets = ($subnetGroup | Select-Object -First 2) -join " "
        Write-Host "Creating VPC connector $VpcConnectorName ..."
        $result = aws apprunner create-vpc-connector --region $Region `
            --vpc-connector-name $VpcConnectorName `
            --subnets ($subnetGroup | Select-Object -First 2) `
            --security-groups $connectorSg --output json | ConvertFrom-Json
        Write-Host "Created: $($result.VpcConnector.VpcConnectorArn)" -ForegroundColor Green
    }

    Write-Host "`nNext: .\scripts\aws-resume-deploy.ps1 -Action push-backend" -ForegroundColor Cyan
}

function Invoke-EcrLogin {
    $reg = "$AccountId.dkr.ecr.$Region.amazonaws.com"
    aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $reg 2>&1 | Out-Null
    Write-Output $reg
}

function Invoke-PushBackend {
    Require-AwsCli
    Require-Docker
    $reg = Invoke-EcrLogin
    Write-Host "Building backend (FLAN-T5, ~15-20 min)..." -ForegroundColor Cyan
    docker build --platform linux/amd64 `
        --build-arg INSTALL_AI=true `
        --build-arg PREFETCH_MODEL=true `
        -t "${reg}/cloudmlops-backend:latest" "$RepoRoot\backend"
    docker push "${reg}/cloudmlops-backend:latest"
    Write-Host "`nBackend image pushed. Create App Runner service in console (see docs/aws-resume-checklist.md Step 8)." -ForegroundColor Green
}

function Invoke-PushFrontend {
    Require-AwsCli
    Require-Docker
    if (-not $BackendUrl) {
        throw "Pass -BackendUrl https://your-backend.us-east-2.awsapprunner.com"
    }
    $reg = Invoke-EcrLogin
    Write-Host "Building frontend with VITE_API_BASE_URL=$BackendUrl ..."
    docker build --platform linux/amd64 `
        --build-arg "VITE_API_BASE_URL=$BackendUrl" `
        -t "${reg}/cloudmlops-frontend:latest" "$RepoRoot\frontend"
    docker push "${reg}/cloudmlops-frontend:latest"
    Write-Host "`nFrontend image pushed. Create App Runner frontend service (Step 9)." -ForegroundColor Green
}

function Invoke-PrintGitHubSecrets {
    Require-AwsCli
    Write-Host "`n=== GitHub production environment ===" -ForegroundColor Cyan
    Write-Host "AWS_ACCOUNT_ID (secret): $AccountId"
    Write-Host "AWS_REGION (variable): $Region"
    $services = aws apprunner list-services --region $Region --output json | ConvertFrom-Json
    foreach ($s in $services.ServiceSummaryList) {
        if ($s.ServiceName -match "cloudmlops") {
            $arn = $s.ServiceArn
            $url = $s.ServiceUrl
            Write-Host "$($s.ServiceName): $url"
            Write-Host "  ARN: $arn"
        }
    }
    Write-Host "`nSet BACKEND_PUBLIC_URL (variable) to the backend ServiceUrl (https://...)."
}

switch ($Action) {
    "verify" { Invoke-Verify }
    "vpc-connector" { Invoke-VpcConnector }
    "push-backend" { Invoke-PushBackend }
    "push-frontend" { Invoke-PushFrontend }
    "print-github-secrets" { Invoke-PrintGitHubSecrets }
}
