#!/bin/bash

# Kyuaar Vercel Deployment Script
# This script handles progressive deployment from staging to production

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="kyuaar-01"
STAGING_BRANCH="staging"
PRODUCTION_BRANCH="main"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[DEPLOY]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Vercel CLI is installed
    if ! command -v vercel &> /dev/null; then
        print_error "Vercel CLI not found. Installing..."
        npm install -g vercel
    fi
    
    # Check if git is initialized
    if [ ! -d .git ]; then
        print_error "Git not initialized"
        exit 1
    fi
    
    # Check if required files exist
    required_files=("wsgi.py" "requirements.txt" "vercel.json")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Required file missing: $file"
            exit 1
        fi
    done
    
    print_status "Prerequisites check passed"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    if [ -f "pytest.ini" ] || [ -d "tests" ]; then
        python -m pytest tests/ -v --cov=app --cov-report=term-missing || {
            print_error "Tests failed"
            exit 1
        }
    else
        print_warning "No tests found, skipping test phase"
    fi
}

# Function to deploy to staging
deploy_staging() {
    print_status "Deploying to staging environment..."
    
    # Ensure we're on staging branch
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "$STAGING_BRANCH" ]; then
        print_warning "Not on staging branch. Switching to staging..."
        git checkout -b "$STAGING_BRANCH" 2>/dev/null || git checkout "$STAGING_BRANCH"
    fi
    
    # Deploy to Vercel staging
    print_status "Deploying to Vercel staging..."
    vercel --prod --env-file .env.staging --scope kyuaar --confirm || {
        print_error "Staging deployment failed"
        exit 1
    }
    
    # Get deployment URL
    STAGING_URL=$(vercel --prod --env-file .env.staging --scope kyuaar --confirm --no-clipboard | tail -n 1)
    print_status "Staging deployed to: $STAGING_URL"
    
    # Update comms.md
    echo -e "\n## Deployment Update - $(date)\n" >> comms.md
    echo "To All: Staging deployment completed - $STAGING_URL" >> comms.md
    echo "Please review and test before production deployment." >> comms.md
    
    git add comms.md
    git commit -m "Update deployment status in comms.md" || true
}

# Function to deploy to production
deploy_production() {
    print_status "Deploying to production environment..."
    
    # Confirm production deployment
    read -p "Are you sure you want to deploy to production? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Production deployment cancelled"
        exit 1
    fi
    
    # Ensure we're on main branch
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "$PRODUCTION_BRANCH" ]; then
        print_warning "Not on main branch. Switching to main..."
        git checkout "$PRODUCTION_BRANCH"
        
        # Merge staging into main
        print_status "Merging staging changes..."
        git merge "$STAGING_BRANCH" --no-ff -m "Merge staging into production"
    fi
    
    # Deploy to Vercel production
    print_status "Deploying to Vercel production..."
    vercel --prod --env-file .env.production --scope kyuaar --confirm || {
        print_error "Production deployment failed"
        exit 1
    }
    
    # Get deployment URL
    PROD_URL=$(vercel --prod --env-file .env.production --scope kyuaar --confirm --no-clipboard | tail -n 1)
    print_status "Production deployed to: $PROD_URL"
    
    # Update comms.md
    echo -e "\n## Production Deployment - $(date)\n" >> comms.md
    echo "To All: Production deployment completed - $PROD_URL" >> comms.md
    echo "Deployment successful. Site is now live!" >> comms.md
    
    git add comms.md
    git commit -m "Update production deployment status" || true
    git push origin "$PRODUCTION_BRANCH"
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Create environment file templates if they don't exist
    if [ ! -f .env.staging ]; then
        cat > .env.staging << EOF
# Staging Environment Variables
FLASK_ENV=staging
FIREBASE_CREDENTIALS=
SECRET_KEY=
DATABASE_URL=
EOF
        print_warning "Created .env.staging template. Please fill in the values."
    fi
    
    if [ ! -f .env.production ]; then
        cat > .env.production << EOF
# Production Environment Variables
FLASK_ENV=production
FIREBASE_CREDENTIALS=
SECRET_KEY=
DATABASE_URL=
EOF
        print_warning "Created .env.production template. Please fill in the values."
    fi
}

# Function to rollback deployment
rollback() {
    print_status "Rolling back deployment..."
    
    # Get list of deployments
    vercel ls --scope kyuaar
    
    read -p "Enter deployment ID to rollback to: " deployment_id
    
    vercel rollback "$deployment_id" --scope kyuaar --confirm || {
        print_error "Rollback failed"
        exit 1
    }
    
    print_status "Rollback completed"
}

# Main script logic
case "${1:-help}" in
    staging)
        check_prerequisites
        setup_environment
        run_tests
        deploy_staging
        ;;
    production)
        check_prerequisites
        setup_environment
        run_tests
        deploy_production
        ;;
    rollback)
        rollback
        ;;
    setup)
        setup_environment
        ;;
    test)
        run_tests
        ;;
    *)
        echo "Usage: $0 {staging|production|rollback|setup|test}"
        echo ""
        echo "Commands:"
        echo "  staging     - Deploy to staging environment"
        echo "  production  - Deploy to production environment"
        echo "  rollback    - Rollback to a previous deployment"
        echo "  setup       - Setup environment files"
        echo "  test        - Run tests only"
        exit 1
        ;;
esac