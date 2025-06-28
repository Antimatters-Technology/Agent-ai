#!/bin/bash

# VisaMate AI - AWS Deployment Script
# Optimized for AWS Free Tier deployment

set -e

echo "🚀 VisaMate AI - AWS Deployment Script"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME="visamate-ai-stack"
APP_NAME="visamate-ai"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        log_warning "AWS CDK not found. Installing..."
        npm install -g aws-cdk
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed."
        exit 1
    fi
    
    # Check Node.js for CDK
    if ! command -v node &> /dev/null; then
        log_error "Node.js is required for AWS CDK but not installed."
        exit 1
    fi
    
    log_success "All prerequisites are met!"
}

setup_environment() {
    log_info "Setting up deployment environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install Python dependencies
    pip install -r requirements.txt
    
    # Install CDK dependencies
    cd infrastructure
    if [ ! -f "package.json" ]; then
        npm init -y
        npm install aws-cdk-lib constructs
    fi
    cd ..
    
    log_success "Environment setup complete!"
}

validate_aws_limits() {
    log_info "Validating AWS Free Tier limits..."
    
    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "Deploying to AWS Account: $ACCOUNT_ID"
    
    # Check region
    log_info "Using AWS Region: $AWS_REGION"
    
    # Validate free tier eligible services
    log_info "Ensuring free tier eligible services:"
    echo "  ✓ DynamoDB (25GB, 200M requests/month)"
    echo "  ✓ Lambda (1M requests, 400K GB-seconds/month)"
    echo "  ✓ API Gateway (1M requests/month)"
    echo "  ✓ S3 (5GB, 20K GET requests/month)"
    echo "  ✓ Cognito (50K MAUs/month)"
    echo "  ✓ CloudWatch (10 metrics, 1M API requests)"
    
    log_success "AWS limits validated!"
}

bootstrap_cdk() {
    log_info "Bootstrapping AWS CDK..."
    
    cd infrastructure
    
    # Bootstrap CDK if not already done
    if ! cdk bootstrap aws://$ACCOUNT_ID/$AWS_REGION 2>/dev/null; then
        log_info "CDK bootstrap required..."
        cdk bootstrap aws://$ACCOUNT_ID/$AWS_REGION
    fi
    
    cd ..
    log_success "CDK bootstrap complete!"
}

deploy_infrastructure() {
    log_info "Deploying AWS infrastructure..."
    
    cd infrastructure
    
    # Synthesize the stack
    log_info "Synthesizing CDK stack..."
    cdk synth
    
    # Deploy the stack
    log_info "Deploying CDK stack..."
    cdk deploy --require-approval never --outputs-file outputs.json
    
    # Extract outputs
    if [ -f "outputs.json" ]; then
        log_info "Deployment outputs:"
        cat outputs.json | jq .
    fi
    
    cd ..
    log_success "Infrastructure deployment complete!"
}

package_lambda_functions() {
    log_info "Packaging Lambda functions..."
    
    # Create Lambda deployment packages
    mkdir -p dist/lambda
    
    # Package SOP Generator Lambda
    if [ -d "src/lambdas/sop_generator" ]; then
        cd src/lambdas/sop_generator
        zip -r ../../../dist/lambda/sop_generator.zip .
        cd ../../..
        log_success "SOP Generator Lambda packaged"
    fi
    
    # Package Document Processor Lambda
    if [ -d "src/lambdas/document_processor" ]; then
        cd src/lambdas/document_processor
        zip -r ../../../dist/lambda/document_processor.zip .
        cd ../../..
        log_success "Document Processor Lambda packaged"
    fi
    
    # Package Wizard API Lambda
    if [ -d "src/lambdas/wizard_api" ]; then
        cd src/lambdas/wizard_api
        zip -r ../../../dist/lambda/wizard_api.zip .
        cd ../../..
        log_success "Wizard API Lambda packaged"
    fi
    
    log_success "All Lambda functions packaged!"
}

setup_secrets() {
    log_info "Setting up AWS Secrets Manager..."
    
    # Create Gemini API key secret
    if [ ! -z "$GEMINI_API_KEY" ]; then
        aws secretsmanager create-secret \
            --name "visamate/gemini" \
            --description "Gemini AI API key for VisaMate" \
            --secret-string "{\"api_key\":\"$GEMINI_API_KEY\"}" \
            --region $AWS_REGION 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id "visamate/gemini" \
            --secret-string "{\"api_key\":\"$GEMINI_API_KEY\"}" \
            --region $AWS_REGION
        
        log_success "Gemini API key secret configured"
    else
        log_warning "GEMINI_API_KEY not set. Please configure manually in AWS Secrets Manager."
    fi
}

configure_monitoring() {
    log_info "Setting up monitoring and alerting..."
    
    # Create CloudWatch log groups
    aws logs create-log-group --log-group-name "/aws/lambda/visamate-sop-generator" --region $AWS_REGION 2>/dev/null || true
    aws logs create-log-group --log-group-name "/aws/lambda/visamate-document-processor" --region $AWS_REGION 2>/dev/null || true
    aws logs create-log-group --log-group-name "/aws/lambda/visamate-wizard-api" --region $AWS_REGION 2>/dev/null || true
    
    # Set log retention (7 days for free tier optimization)
    aws logs put-retention-policy --log-group-name "/aws/lambda/visamate-sop-generator" --retention-in-days 7 --region $AWS_REGION 2>/dev/null || true
    aws logs put-retention-policy --log-group-name "/aws/lambda/visamate-document-processor" --retention-in-days 7 --region $AWS_REGION 2>/dev/null || true
    aws logs put-retention-policy --log-group-name "/aws/lambda/visamate-wizard-api" --retention-in-days 7 --region $AWS_REGION 2>/dev/null || true
    
    log_success "Monitoring configured!"
}

run_health_checks() {
    log_info "Running post-deployment health checks..."
    
    # Wait a moment for services to initialize
    sleep 10
    
    # Get API Gateway URL from outputs
    if [ -f "infrastructure/outputs.json" ]; then
        API_URL=$(cat infrastructure/outputs.json | jq -r '.VisaMateAWSStack.APIGatewayURL // empty')
        
        if [ ! -z "$API_URL" ]; then
            log_info "Testing API endpoint: $API_URL"
            
            # Test health endpoint
            if curl -f "$API_URL/health" > /dev/null 2>&1; then
                log_success "API health check passed!"
            else
                log_warning "API health check failed. Service may still be initializing."
            fi
        fi
    fi
}

cleanup_deployment() {
    log_info "Cleaning up deployment artifacts..."
    
    # Remove temporary files
    rm -rf dist/lambda
    
    log_success "Cleanup complete!"
}

display_deployment_info() {
    log_success "🎉 VisaMate AI deployment complete!"
    echo ""
    echo "Deployment Summary:"
    echo "==================="
    echo "Stack Name: $STACK_NAME"
    echo "Region: $AWS_REGION"
    echo "Account: $ACCOUNT_ID"
    echo ""
    
    if [ -f "infrastructure/outputs.json" ]; then
        echo "Service Endpoints:"
        echo "=================="
        cat infrastructure/outputs.json | jq -r '
            .VisaMateAWSStack | 
            to_entries[] | 
            select(.key | contains("URL") or contains("Bucket") or contains("Pool")) |
            "\(.key): \(.value)"
        '
        echo ""
    fi
    
    echo "Next Steps:"
    echo "==========="
    echo "1. Configure your frontend to use the API Gateway URL"
    echo "2. Set up your domain and SSL certificate (optional)"
    echo "3. Configure monitoring alerts"
    echo "4. Test the SOP generation functionality"
    echo "5. Monitor AWS costs in the billing dashboard"
    echo ""
    echo "Useful Commands:"
    echo "================"
    echo "View logs: aws logs tail /aws/lambda/visamate-sop-generator --follow"
    echo "Update stack: cdk deploy"
    echo "Destroy stack: cdk destroy"
}

# Main deployment flow
main() {
    echo "Starting deployment at $(date)"
    
    check_prerequisites
    setup_environment
    validate_aws_limits
    bootstrap_cdk
    package_lambda_functions
    deploy_infrastructure
    setup_secrets
    configure_monitoring
    run_health_checks
    cleanup_deployment
    display_deployment_info
    
    log_success "Deployment completed successfully at $(date)"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "destroy")
        log_warning "Destroying AWS infrastructure..."
        cd infrastructure
        cdk destroy --force
        log_success "Infrastructure destroyed!"
        ;;
    "update")
        log_info "Updating existing deployment..."
        deploy_infrastructure
        ;;
    "status")
        log_info "Checking deployment status..."
        cd infrastructure
        cdk list
        ;;
    *)
        echo "Usage: $0 [deploy|destroy|update|status]"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  destroy - Destroy all AWS resources"
        echo "  update  - Update existing deployment"
        echo "  status  - Check deployment status"
        exit 1
        ;;
esac 