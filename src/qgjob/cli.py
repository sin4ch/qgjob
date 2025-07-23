import click
import requests
import json
import time
import os
import sys
from typing import Optional

API_BASE_URL = os.getenv("QGJOB_API_URL", "http://localhost:8000")
TIMEOUT = 30

def handle_api_error(response):
    try:
        error_detail = response.json().get("detail", "Unknown error")
    except:
        error_detail = f"HTTP {response.status_code}"
    return error_detail

@click.group()
def cli():
    """QualGent Job Queue CLI - Submit and manage test jobs"""
    pass

@cli.command()
@click.option("--org-id", required=True, help="Organization ID")
@click.option("--app-version-id", required=True, help="App version ID")
@click.option("--test", required=True, help="Test file path")
@click.option("--priority", default=5, help="Job priority (1-10, lower = higher priority)")
@click.option("--target", default="browserstack", 
              type=click.Choice(["emulator", "device", "browserstack"]), 
              help="Target platform")
def submit(org_id, app_version_id, test, priority, target):
    """Submit a new test job"""
    payload = {
        "org_id": org_id,
        "app_version_id": app_version_id,
        "test_path": test,
        "priority": priority,
        "target": target
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/jobs", json=payload, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            click.echo(click.style("✓ Job submitted successfully!", fg="green"))
            click.echo(f"Job ID: {click.style(result['job_id'], fg='blue')}")
            click.echo(f"Status: {result['status']}")
            
            if result.get('message'):
                click.echo(f"Message: {result['message']}")
        else:
            error_detail = handle_api_error(response)
            click.echo(click.style(f"✗ Error submitting job: {error_detail}", fg="red"), err=True)
            sys.exit(1)
            
    except requests.exceptions.Timeout:
        click.echo(click.style("✗ Request timed out", fg="red"), err=True)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"✗ Cannot connect to API server at {API_BASE_URL}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.option("--job-id", required=True, help="Job ID to check")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def status(job_id, verbose):
    """Check job status"""
    try:
        response = requests.get(f"{API_BASE_URL}/jobs/{job_id}", timeout=TIMEOUT)
        
        if response.status_code == 200:
            job = response.json()
            
            status_color = {
                "queued": "yellow",
                "processing": "blue", 
                "completed": "green",
                "failed": "red"
            }.get(job['status'], "white")
            
            click.echo(f"Job ID: {click.style(job['job_id'], fg='blue')}")
            click.echo(f"Status: {click.style(job['status'].upper(), fg=status_color)}")
            click.echo(f"Org ID: {job['org_id']}")
            click.echo(f"App Version: {job['app_version_id']}")
            click.echo(f"Test: {job['test_path']}")
            click.echo(f"Priority: {job['priority']}")
            click.echo(f"Target: {job['target']}")
            click.echo(f"Created: {job['created_at']}")
            click.echo(f"Updated: {job['updated_at']}")
            
            if verbose or job['status'] in ['completed', 'failed']:
                if job.get('result'):
                    result = job['result']
                    click.echo(f"\nResult Details:")
                    if result.get('video_url'):
                        click.echo(f"  Video URL: {click.style(result['video_url'], fg='blue')}")
                    if result.get('browserstack_url'):
                        click.echo(f"  BrowserStack Session: {click.style(result['browserstack_url'], fg='blue')}")
                    if result.get('execution_time'):
                        click.echo(f"  Execution Time: {result['execution_time']:.2f}s")
                    if result.get('test_results'):
                        click.echo(f"  Test Results: {result['test_results']}")
                
                if job.get('error_message'):
                    click.echo(f"\nError: {click.style(job['error_message'], fg='red')}")
        
        elif response.status_code == 404:
            click.echo(click.style(f"✗ Job {job_id} not found", fg="red"), err=True)
            sys.exit(1)
        else:
            error_detail = handle_api_error(response)
            click.echo(click.style(f"✗ Error getting job status: {error_detail}", fg="red"), err=True)
            sys.exit(1)
            
    except requests.exceptions.Timeout:
        click.echo(click.style("✗ Request timed out", fg="red"), err=True)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"✗ Cannot connect to API server at {API_BASE_URL}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.option("--org-id", help="Filter by organization ID")
@click.option("--status", help="Filter by job status")
@click.option("--app-version-id", help="Filter by app version ID")
@click.option("--limit", default=20, help="Maximum number of jobs to show")
def list(org_id, status, app_version_id, limit):
    """List jobs with optional filters"""
    try:
        params = {"limit": limit}
        if org_id:
            params["org_id"] = org_id
        if status:
            params["status"] = status
        if app_version_id:
            params["app_version_id"] = app_version_id
            
        response = requests.get(f"{API_BASE_URL}/jobs", params=params, timeout=TIMEOUT)
        
        if response.status_code == 200:
            jobs = response.json()
            
            if not jobs:
                click.echo("No jobs found")
                return
            
            click.echo(f"{'Job ID':<36} {'Status':<12} {'Org':<15} {'App Version':<15} {'Target':<12} {'Created'}")
            click.echo("-" * 110)
            
            for job in jobs:
                status_color = {
                    "queued": "yellow",
                    "processing": "blue",
                    "completed": "green", 
                    "failed": "red"
                }.get(job['status'], "white")
                
                created_time = job['created_at'][:16].replace('T', ' ')
                
                status_formatted = click.style(job['status'].upper(), fg=status_color)
                
                click.echo(f"{job['job_id']:<36} "
                          f"{status_formatted:<12} "
                          f"{job['org_id']:<15} "
                          f"{job['app_version_id']:<15} "
                          f"{job['target']:<12} "
                          f"{created_time}")
        else:
            error_detail = handle_api_error(response)
            click.echo(click.style(f"✗ Error listing jobs: {error_detail}", fg="red"), err=True)
            sys.exit(1)
            
    except requests.exceptions.Timeout:
        click.echo(click.style("✗ Request timed out", fg="red"), err=True)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"✗ Cannot connect to API server at {API_BASE_URL}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.option("--job-id", required=True, help="Job ID to wait for")
@click.option("--timeout", default=300, help="Timeout in seconds")
@click.option("--poll-interval", default=5, help="Polling interval in seconds")
def wait(job_id, timeout, poll_interval):
    """Wait for job completion"""
    start_time = time.time()
    
    with click.progressbar(length=timeout, label="Waiting for job completion") as bar:
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{API_BASE_URL}/jobs/{job_id}", timeout=TIMEOUT)
                
                if response.status_code == 200:
                    job = response.json()
                    status = job['status']
                    
                    if status == 'completed':
                        bar.finish()
                        click.echo(f"\n✓ Job {job_id} completed successfully!")
                        
                        if job.get('result', {}).get('video_url'):
                            click.echo(f"Video URL: {job['result']['video_url']}")
                        
                        return
                    elif status == 'failed':
                        bar.finish()
                        error_msg = job.get('error_message', 'Unknown error')
                        click.echo(f"\n✗ Job {job_id} failed: {error_msg}", err=True)
                        sys.exit(1)
                    
                    elapsed = int(time.time() - start_time)
                    bar.update(elapsed)
                    
                elif response.status_code == 404:
                    bar.finish()
                    click.echo(f"\n✗ Job {job_id} not found", err=True)
                    sys.exit(1)
                else:
                    error_detail = handle_api_error(response)
                    click.echo(f"\n✗ Error checking job status: {error_detail}", err=True)
                
                time.sleep(poll_interval)
                
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                click.echo(f"\n✗ Connection lost to API server", err=True)
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                bar.finish()
                click.echo(f"\n✗ Wait cancelled by user")
                sys.exit(1)
    
    bar.finish()
    click.echo(f"\n✗ Timeout waiting for job {job_id}", err=True)
    sys.exit(1)

@cli.command()
@click.option("--job-id", required=True, help="Job ID to retry")
def retry(job_id):
    """Retry a failed job"""
    try:
        response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/retry", timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            click.echo(click.style("✓ Job queued for retry!", fg="green"))
            if result.get('message'):
                click.echo(f"Message: {result['message']}")
        else:
            error_detail = handle_api_error(response)
            click.echo(click.style(f"✗ Error retrying job: {error_detail}", fg="red"), err=True)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"✗ Cannot connect to API server at {API_BASE_URL}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.option("--job-id", required=True, help="Job ID to cancel")
def cancel(job_id):
    """Cancel a queued or processing job"""
    try:
        response = requests.delete(f"{API_BASE_URL}/jobs/{job_id}", timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            click.echo(click.style("✓ Job cancelled successfully!", fg="green"))
            if result.get('message'):
                click.echo(f"Message: {result['message']}")
        else:
            error_detail = handle_api_error(response)
            click.echo(click.style(f"✗ Error cancelling job: {error_detail}", fg="red"), err=True)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"✗ Cannot connect to API server at {API_BASE_URL}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
def metrics():
    """Show system metrics"""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=TIMEOUT)
        
        if response.status_code == 200:
            metrics = response.json()
            
            click.echo(click.style("QualGent System Metrics", fg="blue", bold=True))
            click.echo(f"Total Jobs: {metrics['total_jobs']}")
            click.echo(f"Queued: {click.style(str(metrics['queued_jobs']), fg='yellow')}")
            click.echo(f"Processing: {click.style(str(metrics['processing_jobs']), fg='blue')}")
            click.echo(f"Completed: {click.style(str(metrics['completed_jobs']), fg='green')}")
            click.echo(f"Failed: {click.style(str(metrics['failed_jobs']), fg='red')}")
            click.echo(f"Queue Size: {metrics['queue_size']}")
            click.echo(f"Success Rate: {metrics['success_rate']:.1f}%")
        else:
            error_detail = handle_api_error(response)
            click.echo(click.style(f"✗ Error getting metrics: {error_detail}", fg="red"), err=True)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"✗ Cannot connect to API server at {API_BASE_URL}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()
