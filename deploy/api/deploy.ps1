# Package and deploy the CloudGuard API (CloudFormation + Lambda + API Gateway HTTP API).
#
#   cd deploy/api ;  .\deploy.ps1            # deploy/update the stack
#   cd deploy/api ;  .\deploy.ps1 -Destroy   # tear everything down
#
# Linux deps (pydantic-core is compiled) are built inside the Lambda python3.12 image via Docker,
# so the zip runs on Lambda. AGENTCORE_ARN is read from submission/deployment.json; nothing secret
# is needed (the API only invokes the runtime; the decider key lives in the deployed agent, not here).

param([switch]$Destroy)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$repo = Resolve-Path "$here\..\.."
$stack = "cloudguard-api"
$region = "us-east-1"

$account = (aws sts get-caller-identity --query Account --output text)
$bucket = "cloudguard-api-artifacts-$account-$region"

if ($Destroy) {
  Write-Host "[api] deleting stack $stack ..."
  aws cloudformation delete-stack --stack-name $stack --region $region
  aws cloudformation wait stack-delete-complete --stack-name $stack --region $region
  Write-Host "[api] stack deleted. (S3 artifact bucket $bucket left in place; delete manually if you want.)"
  exit 0
}

$arn = (Get-Content "$repo\submission\deployment.json" | ConvertFrom-Json).runtime_arn
if (-not $arn) { throw "AGENTCORE_ARN not found in submission/deployment.json - deploy the agent first." }
Write-Host "[api] account=$account region=$region arn=$arn"

# --- 1. build the deps for Linux/python3.12 and stage app.py into build/ ---
$build = "$here\build"
Remove-Item -Recurse -Force $build -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $build | Out-Null
Copy-Item "$here\app.py" "$build\app.py"

Write-Host "[api] building Linux deps in the Lambda python3.12 image (Docker)..."
# Mount build/ as /var/task and pip install the deps into it; the image is Amazon Linux + py3.12.
docker run --rm --entrypoint /bin/sh `
  -v "${build}:/var/task" -v "${here}:/src" `
  public.ecr.aws/lambda/python:3.12 `
  -c "pip install --no-cache-dir -r /src/requirements.txt -t /var/task" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "dependency build failed" }

# --- 2. zip ---
$zip = "$here\cloudguard-api.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path "$build\*" -DestinationPath $zip
$key = "cloudguard-api-$(Get-Date -Format yyyyMMddHHmmss).zip"

# --- 3. upload to S3 (create the bucket if needed) ---
# Native stderr must not halt the script, so check existence via the bucket list (not head-bucket).
$eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$buckets = (aws s3api list-buckets --query "Buckets[].Name" --output text 2>$null)
if ($buckets -notmatch [regex]::Escape($bucket)) {
  Write-Host "[api] creating artifact bucket $bucket ..."
  if ($region -eq "us-east-1") { aws s3api create-bucket --bucket $bucket --region $region 2>&1 | Out-Null }
  else { aws s3api create-bucket --bucket $bucket --region $region --create-bucket-configuration LocationConstraint=$region 2>&1 | Out-Null }
}
aws s3 cp $zip "s3://$bucket/$key" --region $region 2>&1 | Out-Null
$ErrorActionPreference = $eap

# --- 4. deploy the stack ---
Write-Host "[api] deploying CloudFormation stack $stack ..."
aws cloudformation deploy `
  --stack-name $stack --region $region `
  --template-file "$here\template.yaml" `
  --capabilities CAPABILITY_IAM `
  --parameter-overrides AgentRuntimeArn=$arn CodeS3Bucket=$bucket CodeS3Key=$key

$url = (aws cloudformation describe-stacks --stack-name $stack --region $region --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
Write-Host ""
Write-Host "[api] DONE. Public API: $url"
Write-Host "[api] test: $url/api/info"
Write-Host "[api] point the frontend at it: set VITE_API_BASE=$url and rebuild, or add an Amplify rewrite /api/<*> -> $url/api/<*>"
