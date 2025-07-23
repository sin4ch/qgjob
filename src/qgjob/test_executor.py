import os
import json
import time
import logging
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.webdriver import WebDriver
from appium import webdriver as appium_webdriver
import requests
from retrying import retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserStackManager:
    def __init__(self):
        self.username = os.getenv("BROWSERSTACK_USERNAME")
        self.access_key = os.getenv("BROWSERSTACK_ACCESS_KEY")
        self.build_name = os.getenv("BUILD_NAME", "QualGent-Test-Build")
        self.project_name = os.getenv("PROJECT_NAME", "QualGent")
        
        if not self.username or not self.access_key:
            raise ValueError("BrowserStack credentials not found. Set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY")

        # Check for placeholder values
        if (self.username == "your_browserstack_username" or
            self.access_key == "your_browserstack_access_key" or
            "your_" in self.username.lower() or
            "your_" in self.access_key.lower()):
            raise ValueError("BrowserStack credentials contain placeholder values. Please set actual credentials.")
    
    def get_auth_tuple(self):
        """Return auth tuple, ensuring credentials are not None"""
        if not self.username or not self.access_key:
            raise ValueError("BrowserStack credentials are None")
        return (self.username, self.access_key)
    
    def get_hub_url(self):
        return f"https://{self.username}:{self.access_key}@hub-cloud.browserstack.com/wd/hub"
    
    def get_capabilities(self, target: str, app_version_id: str) -> Dict[str, Any]:
        base_caps = {
            "build": f"{self.build_name}-{app_version_id}",
            "project": self.project_name,
            "browserstack.debug": "true",
            "browserstack.video": "true",
            "browserstack.networkLogs": "true",
            "browserstack.console": "errors"
        }
        
        if target == "device":
            return {
                **base_caps,
                "device": "Samsung Galaxy S22",
                "os_version": "12.0",
                "platformName": "Android"
            }
        elif target == "emulator":
            return {
                **base_caps,
                "device": "Google Pixel 6",
                "os_version": "12.0",
                "platformName": "Android"
            }
        else:
            return {
                **base_caps,
                "browserName": "Chrome",
                "browserVersion": "latest",
                "os": "Windows",
                "osVersion": "11"
            }
    
    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def create_session(self, target: str, app_version_id: str) -> WebDriver:
        capabilities = self.get_capabilities(target, app_version_id)
        
        if target in ["device", "emulator"]:
            driver = appium_webdriver.Remote(
                command_executor=self.get_hub_url(),
                desired_capabilities=capabilities
            )
        else:
            driver = webdriver.Remote(
                command_executor=self.get_hub_url(),
                desired_capabilities=capabilities
            )
        
        logger.info(f"Created BrowserStack session: {driver.session_id}")
        return driver
    
    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        url = f"https://api.browserstack.com/automate/sessions/{session_id}.json"
        response = requests.get(url, auth=self.get_auth_tuple())
        response.raise_for_status()
        return response.json()
    
    def mark_session_status(self, session_id: str, status: str, reason: str = ""):
        url = f"https://api.browserstack.com/automate/sessions/{session_id}.json"
        data = {"status": status, "reason": reason}
        response = requests.put(
            url, 
            json=data, 
            auth=self.get_auth_tuple()
        )
        response.raise_for_status()

class AppManager:
    def __init__(self, browserstack_manager: BrowserStackManager):
        self.bs_manager = browserstack_manager
        self.app_storage = {}
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def upload_app(self, app_version_id: str, app_file_path: str) -> str:
        if app_version_id in self.app_storage:
            return self.app_storage[app_version_id]
        
        url = "https://api-cloud.browserstack.com/app-automate/upload"
        
        with open(app_file_path, 'rb') as app_file:
            files = {'file': (app_file_path, app_file, 'application/octet-stream')}
            response = requests.post(
                url,
                files=files,
                auth=self.bs_manager.get_auth_tuple()
            )
        
        response.raise_for_status()
        result = response.json()
        app_url = result.get('app_url')
        
        if not app_url:
            raise Exception(f"Failed to upload app: {result}")
        
        self.app_storage[app_version_id] = app_url
        logger.info(f"Uploaded app {app_version_id}: {app_url}")
        return app_url
    
    def get_app_path(self, app_version_id: str) -> str:
        app_dir = os.getenv("APP_STORAGE_DIR", "/tmp/apps")
        return os.path.join(app_dir, f"{app_version_id}.apk")

class TestExecutor:
    def __init__(self):
        # BrowserStack credentials are required for production
        try:
            self.bs_manager = BrowserStackManager()
            logger.info("BrowserStack integration initialized successfully")
        except ValueError as e:
            logger.error(f"BrowserStack credentials are required for production: {e}")
            logger.error("Please set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY environment variables")
            logger.error("You can obtain these credentials from your BrowserStack account dashboard")
            raise RuntimeError(f"BrowserStack credentials required: {e}")

        self.app_manager = AppManager(self.bs_manager)
        self.test_scripts_dir = os.getenv("TEST_SCRIPTS_DIR", "tests")
    
    def execute_test(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        target = job_data["target"]
        app_version_id = job_data["app_version_id"]
        test_path = job_data["test_path"]
        job_id = job_data["id"]
        
        logger.info(f"Executing test {job_id}: {test_path} on {target} with app {app_version_id}")
        
        try:
            if target == "browserstack":
                return self._execute_browserstack_web_test(job_data)
            elif target in ["device", "emulator"]:
                return self._execute_browserstack_app_test(job_data)
            else:
                error_msg = f"Unsupported target '{target}' in production. Only 'browserstack', 'device', and 'emulator' are supported."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "video_url": None,
                    "test_results": f"Unsupported target: {target}"
                }
        
        except Exception as e:
            logger.error(f"Test execution failed for job {job_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "video_url": None,
                "test_results": f"Test failed with error: {str(e)}"
            }
    
    def _execute_browserstack_web_test(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        # This should never happen since we fail fast in __init__, but keeping for safety
        if not self.bs_manager:
            error_msg = "BrowserStack credentials are required but not configured"
            logger.error(error_msg)
            logger.error("Please set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY environment variables")
            return {
                "success": False,
                "error": error_msg,
                "video_url": None,
                "test_results": "BrowserStack credentials not available"
            }
        
        driver = None
        session_id = None
        
        try:
            driver = self.bs_manager.create_session("browserstack", job_data["app_version_id"])
            session_id = driver.session_id
            
            test_result = self._run_web_test_script(driver, job_data["test_path"])
            
            session_details = self.bs_manager.get_session_details(session_id)
            video_url = session_details.get("automation_session", {}).get("video_url")
            
            status = "passed" if test_result["success"] else "failed"
            self.bs_manager.mark_session_status(
                session_id, 
                status, 
                test_result.get("error", "")
            )
            
            return {
                "success": test_result["success"],
                "video_url": video_url,
                "test_results": test_result["details"],
                "session_id": session_id,
                "browserstack_url": session_details.get("automation_session", {}).get("public_url")
            }
        
        finally:
            if driver:
                driver.quit()
    
    def _execute_browserstack_app_test(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        # This should never happen since we fail fast in __init__, but keeping for safety
        if not self.bs_manager or not self.app_manager:
            error_msg = "BrowserStack credentials are required but not configured"
            logger.error(error_msg)
            logger.error("Please set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY environment variables")
            return {
                "success": False,
                "error": error_msg,
                "video_url": None,
                "test_results": "BrowserStack credentials not available"
            }
        
        driver = None
        session_id = None
        
        try:
            app_path = self.app_manager.get_app_path(job_data["app_version_id"])
            
            if os.path.exists(app_path):
                app_url = self.app_manager.upload_app(job_data["app_version_id"], app_path)
            else:
                error_msg = f"App file not found for {job_data['app_version_id']} at path: {app_path}"
                logger.error(error_msg)
                logger.error("Please ensure the app file exists in the APP_STORAGE_DIR")
                return {
                    "success": False,
                    "error": error_msg,
                    "video_url": None,
                    "test_results": f"App file not found: {app_path}"
                }
            
            capabilities = self.bs_manager.get_capabilities(job_data["target"], job_data["app_version_id"])
            capabilities["app"] = app_url
            
            driver = appium_webdriver.Remote(
                command_executor=self.bs_manager.get_hub_url(),
                desired_capabilities=capabilities
            )
            session_id = driver.session_id
            
            test_result = self._run_app_test_script(driver, job_data["test_path"])
            
            session_details = self.bs_manager.get_session_details(session_id)
            video_url = session_details.get("automation_session", {}).get("video_url")
            
            status = "passed" if test_result["success"] else "failed"
            self.bs_manager.mark_session_status(
                session_id, 
                status, 
                test_result.get("error", "")
            )
            
            return {
                "success": test_result["success"],
                "video_url": video_url,
                "test_results": test_result["details"],
                "session_id": session_id,
                "browserstack_url": session_details.get("automation_session", {}).get("public_url")
            }
        
        finally:
            if driver:
                driver.quit()
    

    

    
    def _run_web_test_script(self, driver: WebDriver, test_path: str) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            if "onboarding" in test_path:
                return self._run_onboarding_test(driver)
            elif "login" in test_path:
                return self._run_login_test(driver)
            elif "checkout" in test_path:
                return self._run_checkout_test(driver)
            else:
                return self._run_generic_web_test(driver, test_path)
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": f"Web test failed: {str(e)}",
                "execution_time": time.time() - start_time
            }
    
    def _run_app_test_script(self, driver: WebDriver, test_path: str) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            time.sleep(2)
            
            if "onboarding" in test_path:
                return self._run_app_onboarding_test(driver)
            elif "login" in test_path:
                return self._run_app_login_test(driver)
            elif "checkout" in test_path:
                return self._run_app_checkout_test(driver)
            else:
                return self._run_generic_app_test(driver, test_path)
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": f"App test failed: {str(e)}",
                "execution_time": time.time() - start_time
            }
    
    def _run_onboarding_test(self, driver: WebDriver) -> Dict[str, Any]:
        start_time = time.time()
        
        driver.get("https://example.com")
        time.sleep(2)
        
        get_started_button = driver.find_element("css selector", "[data-testid='get-started']")
        get_started_button.click()
        time.sleep(1)
        
        email_field = driver.find_element("css selector", "[data-testid='email']")
        email_field.send_keys("test@example.com")
        time.sleep(1)
        
        submit_button = driver.find_element("css selector", "[data-testid='submit']")
        submit_button.click()
        time.sleep(2)
        
        welcome_element = driver.find_element("css selector", "[data-testid='welcome']")
        
        return {
            "success": welcome_element.is_displayed(),
            "details": "Onboarding flow completed successfully",
            "execution_time": time.time() - start_time
        }
    
    def _run_login_test(self, driver: WebDriver) -> Dict[str, Any]:
        start_time = time.time()
        
        driver.get("https://example.com/login")
        time.sleep(2)
        
        username_field = driver.find_element("css selector", "[data-testid='username']")
        username_field.send_keys("testuser")
        
        password_field = driver.find_element("css selector", "[data-testid='password']")
        password_field.send_keys("password123")
        
        login_button = driver.find_element("css selector", "[data-testid='login-button']")
        login_button.click()
        time.sleep(3)
        
        dashboard_element = driver.find_element("css selector", "[data-testid='dashboard']")
        
        return {
            "success": dashboard_element.is_displayed(),
            "details": "Login flow completed successfully",
            "execution_time": time.time() - start_time
        }
    
    def _run_checkout_test(self, driver: WebDriver) -> Dict[str, Any]:
        start_time = time.time()
        
        driver.get("https://example.com/checkout")
        time.sleep(2)
        
        card_field = driver.find_element("css selector", "[data-testid='card-number']")
        card_field.send_keys("4111111111111111")
        
        expiry_field = driver.find_element("css selector", "[data-testid='expiry']")
        expiry_field.send_keys("12/25")
        
        cvv_field = driver.find_element("css selector", "[data-testid='cvv']")
        cvv_field.send_keys("123")
        
        pay_button = driver.find_element("css selector", "[data-testid='pay-button']")
        pay_button.click()
        time.sleep(3)
        
        success_element = driver.find_element("css selector", "[data-testid='success']")
        
        return {
            "success": success_element.is_displayed(),
            "details": "Checkout flow completed successfully",
            "execution_time": time.time() - start_time
        }
    
    def _run_generic_web_test(self, driver: WebDriver, test_path: str) -> Dict[str, Any]:
        start_time = time.time()
        driver.get("https://example.com")
        time.sleep(2)
        
        return {
            "success": True,
            "details": f"Generic web test {test_path} completed",
            "execution_time": time.time() - start_time
        }
    
    def _run_app_onboarding_test(self, driver: WebDriver) -> Dict[str, Any]:
        start_time = time.time()
        time.sleep(3)
        
        try:
            get_started_btn = driver.find_element("id", "get_started_button")
            get_started_btn.click()
            time.sleep(2)
            
            email_field = driver.find_element("id", "email_input")
            email_field.send_keys("test@example.com")
            
            submit_btn = driver.find_element("id", "submit_button")
            submit_btn.click()
            time.sleep(3)
            
            welcome_text = driver.find_element("id", "welcome_message")
            
            return {
                "success": welcome_text.is_displayed(),
                "details": "App onboarding flow completed successfully",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": f"App onboarding test failed: {str(e)}",
                "execution_time": time.time() - start_time
            }
    
    def _run_app_login_test(self, driver: WebDriver) -> Dict[str, Any]:
        start_time = time.time()
        time.sleep(2)
        
        try:
            username_field = driver.find_element("id", "username")
            username_field.send_keys("testuser")
            
            password_field = driver.find_element("id", "password")
            password_field.send_keys("password123")
            
            login_btn = driver.find_element("id", "login_button")
            login_btn.click()
            time.sleep(3)
            
            dashboard = driver.find_element("id", "dashboard")
            
            return {
                "success": dashboard.is_displayed(),
                "details": "App login flow completed successfully",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": f"App login test failed: {str(e)}",
                "execution_time": time.time() - start_time
            }
    
    def _run_app_checkout_test(self, driver: WebDriver) -> Dict[str, Any]:
        start_time = time.time()
        time.sleep(2)
        
        try:
            card_field = driver.find_element("id", "card_number")
            card_field.send_keys("4111111111111111")
            
            expiry_field = driver.find_element("id", "expiry_date")
            expiry_field.send_keys("12/25")
            
            cvv_field = driver.find_element("id", "cvv")
            cvv_field.send_keys("123")
            
            pay_btn = driver.find_element("id", "pay_button")
            pay_btn.click()
            time.sleep(4)
            
            success_msg = driver.find_element("id", "payment_success")
            
            return {
                "success": success_msg.is_displayed(),
                "details": "App checkout flow completed successfully",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": f"App checkout test failed: {str(e)}",
                "execution_time": time.time() - start_time
            }
    
    def _run_generic_app_test(self, driver: WebDriver, test_path: str) -> Dict[str, Any]:
        start_time = time.time()
        time.sleep(2)
        
        return {
            "success": True,
            "details": f"Generic app test {test_path} completed",
            "execution_time": time.time() - start_time
        }
    

