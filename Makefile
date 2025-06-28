# VisaMate AI - Production-Ready Makefile
# Optimized for AWS Free Tier and Gemini AI integration

.PHONY: help install dev test lint format clean build deploy setup-aws setup-gemini run-local run-prod

# Default target
help:
	@echo "VisaMate AI - Canada Study Visa Platform"
	@echo ""
	@echo "Available commands:"
	@echo "  setup-env        - Set up development environment"
	@echo "  setup-aws        - Configure AWS services (free tier)"
	@echo "  setup-gemini     - Configure Gemini AI service"
	@echo "  install          - Install dependencies"
	@echo "  dev              - Run development server with hot reload"
	@echo "  run-local        - Run local server"
	@echo "  run-prod         - Run production server"
	@echo "  test             - Run all tests"
	@echo "  test-unit        - Run unit tests only"
	@echo "  test-integration - Run integration tests"
	@echo "  lint             - Run linting checks"
	@echo "  format           - Format code"
	@echo "  type-check       - Run type checking"
	@echo "  security-check   - Run security checks"
	@echo "  build            - Build Docker image"
	@echo "  deploy-aws       - Deploy to AWS (CDK)"
	@echo "  deploy-local     - Deploy locally with Docker"
	@echo "  db-migrate       - Run database migrations"
	@echo "  db-seed          - Seed database with test data"
	@echo "  logs             - View application logs"
	@echo "  clean            - Clean up generated files"

# Environment setup
setup-env:
	@echo "Setting up development environment..."
	cp .env.example .env 2>/dev/null || echo "Please create .env file manually"
	python -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

# AWS Setup (Free Tier)
setup-aws:
	@echo "Setting up AWS services (Free Tier)..."
	@echo "Please ensure AWS CLI is configured with your credentials"
	aws sts get-caller-identity
	@echo "Creating AWS resources..."
	cd infrastructure && cdk bootstrap
	cd infrastructure && cdk deploy --require-approval never
	@echo "AWS setup complete!"

# Gemini AI Setup
setup-gemini:
	@echo "Setting up Gemini AI service..."
	@echo "Please ensure GEMINI_API_KEY is set in your .env file"
	@echo "Get your API key from: https://makersuite.google.com/app/apikey"
	python -c "import os; print('✓ Gemini API key configured' if os.getenv('GEMINI_API_KEY') else '✗ Please set GEMINI_API_KEY in .env')"

# Dependencies
install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "Dependencies installed successfully!"

# Development
dev:
	@echo "Starting development server with hot reload..."
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

run-local:
	@echo "Starting local server..."
	python -m src.main

run-prod:
	@echo "Starting production server..."
	gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --log-level info

# Testing
test:
	@echo "Running all tests..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

test-sop:
	@echo "Testing SOP generation..."
	python -m pytest tests/unit/test_sop_generator.py -v

test-questionnaire:
	@echo "🧪 Testing complete IRCC questionnaire flow..."
	python scripts/test_questionnaire_flow.py

test-forms:
	@echo "📋 Testing form auto-filling..."
	python -m pytest tests/unit/test_form_service.py -v

test-full-flow:
	@echo "🚀 Testing complete application flow..."
	make test-questionnaire
	make test-forms
	make test-sop

# Code Quality
lint:
	@echo "Running linting checks..."
	flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/
	@echo "Code formatted successfully!"

type-check:
	@echo "Running type checks..."
	mypy src/ --ignore-missing-imports

security-check:
	@echo "Running security checks..."
	bandit -r src/ -f json -o security-report.json || true
	safety check --json --output safety-report.json || true
	@echo "Security check complete. Check reports for details."

# Docker
build:
	@echo "Building Docker image..."
	docker build -t visamate-ai:latest .
	@echo "Docker image built successfully!"

build-prod:
	@echo "Building production Docker image..."
	docker build -f Dockerfile.prod -t visamate-ai:prod .

# Deployment
deploy-aws:
	@echo "Deploying to AWS..."
	@echo "Building and deploying Lambda functions..."
	cd infrastructure && cdk deploy --require-approval never
	@echo "Deployment complete!"

deploy-local:
	@echo "Deploying locally with Docker Compose..."
	docker-compose up -d --build
	@echo "Local deployment complete! Visit http://localhost:8000"

# Database operations
db-migrate:
	@echo "Running database migrations..."
	alembic upgrade head

db-seed:
	@echo "Seeding database with test data..."
	python scripts/seed_questions.py

db-reset:
	@echo "Resetting database..."
	alembic downgrade base
	alembic upgrade head
	python scripts/seed_questions.py

# AWS DynamoDB operations
dynamodb-create-tables:
	@echo "Creating DynamoDB tables..."
	python scripts/create_dynamodb_tables.py

dynamodb-seed:
	@echo "Seeding DynamoDB with test data..."
	python scripts/seed_dynamodb.py

# Monitoring and Logs
logs:
	@echo "Viewing application logs..."
	docker-compose logs -f app || tail -f app.log

logs-aws:
	@echo "Viewing AWS CloudWatch logs..."
	aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/visamate"

# Performance testing
load-test:
	@echo "Running load tests..."
	locust -f tests/load/locustfile.py --host=http://localhost:8000

# API testing
test-api:
	@echo "Testing API endpoints..."
	python scripts/test_api.py

# SOP generation testing
test-sop-generation:
	@echo "Testing SOP generation with sample data..."
	python scripts/test_sop_generation.py

# Documentation
docs:
	@echo "Generating documentation..."
	mkdocs build
	@echo "Documentation generated in site/ directory"

docs-serve:
	@echo "Serving documentation..."
	mkdocs serve

# Maintenance
clean:
	@echo "Cleaning up generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -f security-report.json safety-report.json
	@echo "Cleanup complete!"

# Environment variables check
check-env:
	@echo "Checking environment variables..."
	python -c "
import os
required_vars = ['GEMINI_API_KEY', 'AWS_REGION', 'COGNITO_USER_POOL_ID']
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print(f'❌ Missing: {missing}')
    exit(1)
else:
    print('✅ All required environment variables are set')
"

# Health check
health-check:
	@echo "Checking application health..."
	curl -f http://localhost:8000/health || echo "Application not running or unhealthy"

# Full setup for new developers
setup-dev: setup-env install setup-gemini check-env
	@echo "Development environment setup complete!"
	@echo "Run 'make dev' to start the development server"

# Production deployment pipeline
deploy-prod: lint test security-check build-prod deploy-aws
	@echo "Production deployment complete!"

# Quick development start
quick-start: install dev

# Emergency rollback
rollback-aws:
	@echo "Rolling back AWS deployment..."
	cd infrastructure && cdk deploy --previous-version

# Backup operations
backup-dynamodb:
	@echo "Backing up DynamoDB tables..."
	python scripts/backup_dynamodb.py

restore-dynamodb:
	@echo "Restoring DynamoDB tables..."
	python scripts/restore_dynamodb.py

# Monitoring setup
setup-monitoring:
	@echo "Setting up monitoring and alerting..."
	aws logs create-log-group --log-group-name /aws/lambda/visamate-monitoring
	@echo "Monitoring setup complete!"

# Cost optimization
optimize-aws-costs:
	@echo "Optimizing AWS costs..."
	@echo "Checking for unused resources..."
	python scripts/optimize_aws_costs.py 