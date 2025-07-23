# QualGent Job Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready job orchestration system for managing and executing AppWright automated tests on BrowserStack. This system provides a complete solution for queuing, processing, and monitoring AppWright test jobs with support for web and mobile app testing.

## Features

- **Job Queue Management**: Redis-based job queuing with priority support
- **BrowserStack Integration**: Seamless integration with BrowserStack for web and mobile testing
- **REST API**: Complete API for job submission, monitoring, and management
- **CLI Tool**: Command-line interface for easy job management
- **Worker Process**: Background workers for job execution
- **Database Persistence**: PostgreSQL support for job tracking
- **Production Logging**: Comprehensive logging and monitoring
- **Error Handling**: Robust error handling with retry logic

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Client    │    │   REST API      │    │   Web Client    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     FastAPI Server        │
                    │   (Job Orchestrator)      │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      Redis Queue          │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │    Worker Processes       │
                    │  (Test Executors)         │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │    BrowserStack API       │
                    │   (Test Execution)        │
                    └───────────────────────────┘
```

## Prerequisites

**Required Infrastructure:**
- Python 3.8+
- PostgreSQL 12+ (running and accessible)
- Redis 6+ (running and accessible)
- BrowserStack Account with valid credentials

**Important:** This is a production application that requires all dependencies to be properly configured. The application will fail to start if any required component is missing.

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd qgjob
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Setup (PostgreSQL)

**Install PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Windows - Download from https://www.postgresql.org/download/windows/
```

**Create Database:**
```sql
CREATE DATABASE qgjob;
CREATE USER qgjob_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE qgjob TO qgjob_user;
```

### 3. Redis Setup

**Install Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Docker (alternative)
docker run -d -p 6379:6379 --name redis redis:alpine
```

**Start Redis:**
```bash
redis-server
```

### 4. BrowserStack Setup

1. Create account at https://www.browserstack.com/
2. Get credentials from Account → Settings → Automate
3. Note your username and access key

### 5. Environment Configuration

**Create `.env` file:**
```env
# Database (Required)
DATABASE_URL=postgresql://qgjob_user:secure_password@localhost:5432/qgjob

# Redis (Required)
REDIS_URL=redis://localhost:6379

# API Configuration
QGJOB_API_URL=http://localhost:8000

# BrowserStack Credentials (Required)
BROWSERSTACK_USERNAME=your_actual_username
BROWSERSTACK_ACCESS_KEY=your_actual_access_key

# Application Settings
BUILD_NAME=QualGent-Test-Build
PROJECT_NAME=QualGent
APP_STORAGE_DIR=/tmp/apps
TEST_SCRIPTS_DIR=tests
MAX_JOB_RETRIES=3
WORKER_TIMEOUT_HOURS=1
LOG_LEVEL=INFO
```

**⚠️ Important:** Replace placeholder values with actual credentials. The application will not start with default placeholder values.

### 6. Initialize Database

```bash
python -c "from src.qgjob.database import create_tables; create_tables()"
```

## Running the Application

### Start API Server
```bash
python -m src.qgjob.main
```

### Start Worker Process
```bash
python -m src.qgjob.worker
```

**Note:** Both processes must be running for the system to function properly.

## Continuous Integration/Continuous Deployment (CI/CD)

This project includes a comprehensive GitHub Actions workflow that automatically tests the entire application stack.

### CI/CD Features

- **Automated Testing**: Full end-to-end testing with PostgreSQL and Redis
- **BrowserStack Integration**: Production testing with real BrowserStack credentials
- **Service Validation**: Comprehensive validation of all application components
- **Artifact Collection**: Automatic collection of logs and test reports

### Workflow Triggers

The CI/CD pipeline runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` branch
- Manual workflow dispatch

### Setting Up CI/CD

1. **Configure GitHub Secrets** (required):
   ```
   BROWSERSTACK_USERNAME: your_browserstack_username
   BROWSERSTACK_ACCESS_KEY: your_browserstack_access_key
   ```

2. **View Workflow Status**:
   - Check the badge above for current build status
   - Visit the Actions tab in your GitHub repository

3. **Review Test Results**:
   - Workflow generates comprehensive test reports
   - Application logs are automatically collected as artifacts


### For Contributors

When contributing to this project:
1. **All pull requests** trigger the CI/CD pipeline
2. **Tests must pass** before merging
3. **Review artifacts** if tests fail for debugging information
4. **Follow the workflow** for consistent development practices

The CI/CD pipeline ensures that all changes are thoroughly tested in a production-like environment before deployment.

## Usage

### CLI Commands

**Submit a Job:**
```bash
qgjob submit --org-id "my-org" --app-version-id "v1.0.0" --test "login.spec.js" --priority 1 --target browserstack
```

**Check Job Status:**
```bash
qgjob status --job-id "job-uuid"
```

**List Jobs:**
```bash
qgjob list --org-id "my-org"
qgjob list --status failed
```

**System Metrics:**
```bash
qgjob metrics
```

### REST API

**Submit Job:**
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "my-org",
    "app_version_id": "v1.0.0", 
    "test_path": "login.spec.js",
    "priority": 1,
    "target": "browserstack"
  }'
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

## Supported Targets

- **browserstack**: Web testing on BrowserStack
- **device**: Mobile app testing on real devices via BrowserStack
- **emulator**: Mobile app testing on emulators via BrowserStack

All targets require valid BrowserStack credentials.

## Example AppWright Test Files

The project includes sample AppWright test files for demonstration:

- `tests/onboarding.spec.js` - User onboarding flow test
- `tests/login.spec.js` - Login functionality test
- `tests/checkout.spec.js` - Checkout process test
- `tests/wikipedia.spec.js` - Wikipedia search and verification test (AppWright reference implementation)

These test files demonstrate the expected format for AppWright tests that can be submitted to the job orchestrator.

## Production Deployment

### Environment Requirements

1. **PostgreSQL Database**
   - Dedicated database instance
   - Proper backup strategy
   - Connection pooling for high load

2. **Redis Instance**
   - Persistent Redis configuration
   - Memory allocation based on queue size
   - High availability setup for critical systems

3. **BrowserStack Account**
   - Sufficient parallel testing limits
   - Valid subscription with required features

### Docker Deployment

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: qgjob
      POSTGRES_USER: qgjob_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://qgjob_user:${DB_PASSWORD}@postgres:5432/qgjob
      - REDIS_URL=redis://redis:6379
      - BROWSERSTACK_USERNAME=${BS_USERNAME}
      - BROWSERSTACK_ACCESS_KEY=${BS_ACCESS_KEY}
    depends_on:
      - postgres
      - redis

  worker:
    build: .
    command: python -m src.qgjob.worker
    environment:
      - DATABASE_URL=postgresql://qgjob_user:${DB_PASSWORD}@postgres:5432/qgjob
      - REDIS_URL=redis://redis:6379
      - BROWSERSTACK_USERNAME=${BS_USERNAME}
      - BROWSERSTACK_ACCESS_KEY=${BS_ACCESS_KEY}
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
```

## Troubleshooting

### Application Won't Start

**Database Connection Failed:**
```
RuntimeError: Database connection failed: connection to server at "localhost" (127.0.0.1), port 5432 failed
```
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL format: `postgresql://user:password@host:port/database`
- Ensure database exists and user has permissions

**Redis Connection Failed:**
```
RuntimeError: Redis connection failed: Error 111 connecting to localhost:6379. Connection refused.
```
- Verify Redis is running: `redis-cli ping`
- Check REDIS_URL format: `redis://localhost:6379`

**BrowserStack Credentials Required:**
```
RuntimeError: BrowserStack credentials required: BrowserStack credentials not found
```
- Set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY
- Verify credentials are not placeholder values
- Test credentials on BrowserStack dashboard

### Worker Issues

**Worker Not Processing Jobs:**
- Check worker logs in `qgjob-worker.log`
- Verify all environment variables are set
- Ensure BrowserStack account has available parallel sessions

**Jobs Failing:**
- Check BrowserStack account limits
- Verify app files exist in APP_STORAGE_DIR
- Review job error messages in database

### Monitoring

**Log Files:**
- API: `qgjob.log`
- Worker: `qgjob-worker.log`

**Health Checks:**
- API: `GET /health`
- Metrics: `GET /metrics`

## API Reference

### Job Object
```json
{
  "id": "uuid",
  "org_id": "string",
  "app_version_id": "string", 
  "test_path": "string",
  "priority": 1,
  "target": "browserstack|device|emulator",
  "status": "queued|processing|completed|failed",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z",
  "result": "string",
  "error_message": "string"
}
```

### Endpoints
- `POST /jobs` - Submit new job
- `GET /jobs/{job_id}` - Get job details
- `GET /jobs` - List jobs with filters
- `DELETE /jobs/{job_id}` - Cancel job
- `POST /jobs/{job_id}/retry` - Retry failed job
- `GET /health` - Health check
- `GET /metrics` - System metrics

## License

This project is licensed under the MIT License.
