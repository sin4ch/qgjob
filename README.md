# QualGent Job Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/qualgent/qgjob/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/qualgent/qgjob/actions/workflows/ci-cd.yml)

A production-ready job orchestration system for managing and executing AppWright automated tests on BrowserStack. Provides complete job queuing, processing, and monitoring for web and mobile app testing.

## Features

- **Job Queue Management**: Redis-based queuing with priority support
- **BrowserStack Integration**: Web and mobile testing on real devices
- **REST API & CLI**: Complete interfaces for job management
- **Worker Processes**: Background test execution with retry logic
- **Database Persistence**: PostgreSQL job tracking and results
- **Production Ready**: Comprehensive logging, monitoring, and CI/CD integration

## Architecture

```
CLI/API → FastAPI Server → Redis Queue → Workers → BrowserStack
                ↓
          PostgreSQL Database
```

## Quick Start

### How It Works

1. **Deploy Apps**: Place mobile apps in `/tmp/apps/{version}.apk` or configure web URLs in tests
2. **Submit Jobs**: Use CLI or API to queue AppWright tests for execution
3. **Automatic Execution**: Workers run tests on BrowserStack with real devices/browsers
4. **Monitor Results**: Get execution videos, pass/fail status, and detailed logs

### Application Types

**Web Applications:**
```bash
# Test file specifies URL: await device.goto('https://myapp.com')
qgjob submit --org-id "myorg" --app-version-id "v1.0" \
  --test "web-test.spec.js" --target browserstack
```

**Mobile Applications:**
```bash
# 1. Deploy app with version-based naming
cp builds/myapp.apk /tmp/apps/v1.0.apk

# 2. Submit test (system finds and uploads app automatically)
qgjob submit --org-id "myorg" --app-version-id "v1.0" \
  --test "mobile-test.spec.js" --target device
```

## Prerequisites

- Python 3.8+
- PostgreSQL 12+ (running and accessible)
- Redis 6+ (running and accessible)
- BrowserStack Account with Automate plan

**Important:** This is a production application that requires all dependencies. The application will fail to start if any component is missing.

## Installation & Setup

### 1. Basic Setup
```bash
git clone <repository-url>
cd qgjob
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Infrastructure Setup

**PostgreSQL:**
```bash
# Install (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Create database
createdb qgjob
createuser qgjob_user
```

**Redis:**
```bash
# Install and start
sudo apt-get install redis-server
redis-server
```

**BrowserStack:**
1. Create account at https://www.browserstack.com/
2. Get credentials from Account → Settings → Automate

### 3. Environment Configuration

Create `.env` file:
```env
# Database (Required)
DATABASE_URL=postgresql://qgjob_user:secure_password@localhost:5432/qgjob

# Redis (Required)
REDIS_URL=redis://localhost:6379

# BrowserStack Credentials (Required)
BROWSERSTACK_USERNAME=your_actual_username
BROWSERSTACK_ACCESS_KEY=your_actual_access_key

# Application Settings
APP_STORAGE_DIR=/tmp/apps
LOG_LEVEL=INFO
```

### 4. Initialize & Run

```bash
# Initialize database
python -c "from src.qgjob.database import create_tables; create_tables()"

# Start services (both required)
python -m src.qgjob.main &      # API Server
python -m src.qgjob.worker &    # Worker Process
```

## Mobile App Testing

### App Deployment Model

Mobile apps use a **pre-deployment model**: apps must be placed in the storage directory before submitting tests.

**App Storage Convention:**
```bash
# Naming: APP_STORAGE_DIR/{app_version_id}.apk
/tmp/apps/v1.2.3.apk          # For --app-version-id "v1.2.3"
/tmp/apps/release-2024.apk    # For --app-version-id "release-2024"
```

**Workflow:**
```bash
# 1. Deploy app with version-based naming
mkdir -p /tmp/apps
cp builds/myapp-v1.2.3.apk /tmp/apps/v1.2.3.apk

# 2. Submit test (system finds and uploads app automatically)
qgjob submit --org-id "myorg" --app-version-id "v1.2.3" \
  --test "mobile-test.spec.js" --target device

# 3. System automatically:
# - Finds /tmp/apps/v1.2.3.apk
# - Uploads to BrowserStack (cached for future tests)
# - Creates mobile session with app installed
# - Runs AppWright test on real device
```

**Benefits:** Performance (cached uploads), CI/CD friendly, secure, clear version management.

## CI/CD Integration

The project includes comprehensive GitHub Actions workflow with automated testing.

**Setup:**
1. Configure GitHub Secrets:
   ```
   BROWSERSTACK_USERNAME: your_browserstack_username
   BROWSERSTACK_ACCESS_KEY: your_browserstack_access_key
   ```

2. Pipeline runs on: push to `main`/`develop`, pull requests, manual dispatch

**CI/CD Example:**
```yaml
- name: Run AppWright Tests
  run: |
    qgjob submit --org-id "$ORG" --app-version-id "$VERSION" \
      --test "regression.spec.js" --priority 1 --target browserstack > job_output.txt

    JOB_ID=$(grep "Job ID:" job_output.txt | awk '{print $3}')
    qgjob wait --job-id "$JOB_ID" --timeout 300
    qgjob status --job-id "$JOB_ID" --verbose
```

## Usage

### CLI Commands

```bash
# Submit jobs
qgjob submit --org-id "my-org" --app-version-id "v1.0.0" --test "test.spec.js" --target browserstack
qgjob submit --org-id "my-org" --app-version-id "v1.0.0" --test "mobile.spec.js" --target device

# Monitor jobs
qgjob status --job-id "job-uuid" [--verbose]
qgjob list --org-id "my-org" [--status failed]
qgjob wait --job-id "job-uuid" --timeout 300

# Manage jobs
qgjob retry --job-id "job-uuid"
qgjob cancel --job-id "job-uuid"
qgjob metrics
```

### REST API

```bash
# Submit job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"org_id": "my-org", "app_version_id": "v1.0.0", "test_path": "test.spec.js", "priority": 1, "target": "browserstack"}'

# Health check
curl http://localhost:8000/health
```

### Supported Targets

- **browserstack**: Web testing on BrowserStack
- **device**: Mobile app testing on real devices via BrowserStack
- **emulator**: Mobile app testing on emulators via BrowserStack

## Example AppWright Test

Sample test file (`tests/wikipedia.spec.js`):

```javascript
import { test, expect } from "appwright";

test("Open Playwright on Wikipedia and verify Microsoft is visible", async ({ device }) => {
  await device.getByText("Skip").tap();

  const searchInput = device.getByText("Search Wikipedia", { exact: true });
  await searchInput.tap();
  await searchInput.fill("playwright");

  await device.getByText("Playwright (software)").tap();
  await expect(device.getByText("Microsoft")).toBeVisible();
});
```

**Key Features:** AppWright framework, device context for mobile-first testing, touch interactions (`.tap()`, `.fill()`), content-based element selection, visual assertions.

**Execution Results:** Creates BrowserStack session, records video, provides detailed results, integrates with CI/CD.

## Production Deployment

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

### Production Considerations

- **Scalability**: Multiple workers, load balancing, database optimization
- **Security**: Secure credential management, network security, API authentication
- **Monitoring**: Application metrics, infrastructure monitoring, alerting
- **Backup**: Database backups, configuration version control, disaster recovery

## Troubleshooting

### Common Issues

**Database Connection Failed:**
```
RuntimeError: Database connection failed: connection to server at "localhost" (127.0.0.1), port 5432 failed
```
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL format: `postgresql://user:password@host:port/database`

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

**App File Not Found:**
```
Error: App file not found for v1.2.3 at path: /tmp/apps/v1.2.3.apk
```
- Check naming: `--app-version-id "v1.2.3"` requires `/tmp/apps/v1.2.3.apk`
- Verify file exists: `ls -la /tmp/apps/`
- Check permissions: `chmod 644 /tmp/apps/*.apk`

**Worker Not Processing Jobs:**
- Check worker logs: `qgjob-worker.log`
- Verify environment variables are set
- Ensure BrowserStack account has available sessions

### Monitoring

**Log Files:** `qgjob.log` (API), `qgjob-worker.log` (Worker)
**Health Checks:** `GET /health`, `GET /metrics`

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
- `GET /jobs` - List jobs with filters (supports org_id, status, app_version_id, limit, offset)
- `DELETE /jobs/{job_id}` - Cancel job
- `GET /jobs/{job_id}/retry` - Retry failed job
- `GET /health` - Health check
- `GET /metrics` - System metrics

## License

This project is licensed under the MIT License.
