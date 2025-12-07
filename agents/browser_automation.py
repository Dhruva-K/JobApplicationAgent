"""
Browser automation module for job application form filling.
Uses Playwright for automated form detection and submission.
NOT FUNCTIONAL
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import (
        async_playwright,
        Page,
        Browser,
        BrowserContext,
        TimeoutError as PlaywrightTimeout,
    )
except ImportError:
    async_playwright = None
    Page = None
    Browser = None
    BrowserContext = None
    PlaywrightTimeout = Exception

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """Handles browser automation for job applications."""

    def __init__(self, headless: bool = True, screenshot_dir: Optional[str] = None):
        """
        Initialize browser automation.

        Args:
            headless: Run browser in headless mode
            screenshot_dir: Directory to save screenshots (for debugging)
        """
        if async_playwright is None:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        self.headless = headless
        self.screenshot_dir = (
            Path(screenshot_dir) if screenshot_dir else Path("outputs/screenshots")
        )
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start the browser."""
        logger.info("Starting browser automation...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        logger.info("Browser started successfully")

    async def close(self):
        """Close the browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")

    async def create_page(self) -> Page:
        """Create a new page."""
        if not self.context:
            await self.start()
        return await self.context.new_page()

    async def screenshot(self, page: Page, name: str):
        """Take a screenshot for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.screenshot_dir / f"{name}_{timestamp}.png"
            await page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None

    async def detect_form_fields(self, page: Page) -> Dict[str, Any]:
        """
        Detect form fields on the page.

        Returns:
            Dictionary of detected fields with their selectors
        """
        logger.info("Detecting form fields...")

        try:
            # Wait for page to load
            await page.wait_for_load_state("networkidle", timeout=10000)

            fields = {
                "text_inputs": [],
                "textareas": [],
                "selects": [],
                "checkboxes": [],
                "radio_buttons": [],
                "file_uploads": [],
                "buttons": [],
            }

            # Detect input fields
            inputs = await page.query_selector_all("input")
            for input_elem in inputs:
                input_type = await input_elem.get_attribute("type") or "text"
                input_name = await input_elem.get_attribute("name") or ""
                input_id = await input_elem.get_attribute("id") or ""
                input_placeholder = await input_elem.get_attribute("placeholder") or ""

                field_info = {
                    "type": input_type,
                    "name": input_name,
                    "id": input_id,
                    "placeholder": input_placeholder,
                    "element": input_elem,
                }

                if input_type in ["text", "email", "tel", "url", "number"]:
                    fields["text_inputs"].append(field_info)
                elif input_type == "checkbox":
                    fields["checkboxes"].append(field_info)
                elif input_type == "radio":
                    fields["radio_buttons"].append(field_info)
                elif input_type == "file":
                    fields["file_uploads"].append(field_info)
                elif input_type in ["submit", "button"]:
                    fields["buttons"].append(field_info)

            # Detect textareas
            textareas = await page.query_selector_all("textarea")
            for textarea in textareas:
                fields["textareas"].append(
                    {
                        "name": await textarea.get_attribute("name") or "",
                        "id": await textarea.get_attribute("id") or "",
                        "placeholder": await textarea.get_attribute("placeholder")
                        or "",
                        "element": textarea,
                    }
                )

            # Detect select dropdowns
            selects = await page.query_selector_all("select")
            for select in selects:
                options = await select.query_selector_all("option")
                option_values = []
                for option in options:
                    value = await option.get_attribute("value")
                    text = await option.text_content()
                    option_values.append({"value": value, "text": text})

                fields["selects"].append(
                    {
                        "name": await select.get_attribute("name") or "",
                        "id": await select.get_attribute("id") or "",
                        "options": option_values,
                        "element": select,
                    }
                )

            # Detect buttons
            buttons = await page.query_selector_all("button")
            for button in buttons:
                button_type = await button.get_attribute("type") or "button"
                button_text = await button.text_content() or ""
                fields["buttons"].append(
                    {
                        "type": button_type,
                        "text": button_text.strip(),
                        "element": button,
                    }
                )

            logger.info(
                f"Detected: {len(fields['text_inputs'])} text inputs, "
                f"{len(fields['textareas'])} textareas, "
                f"{len(fields['selects'])} selects, "
                f"{len(fields['file_uploads'])} file uploads, "
                f"{len(fields['buttons'])} buttons"
            )

            return fields

        except Exception as e:
            logger.error(f"Error detecting form fields: {e}")
            return {}

    async def fill_form_field(
        self, page: Page, field: Dict[str, Any], value: Any
    ) -> bool:
        """
        Fill a form field with the given value.

        Args:
            page: Playwright page
            field: Field information from detect_form_fields
            value: Value to fill

        Returns:
            True if successful, False otherwise
        """
        try:
            element = field["element"]
            field_type = field.get("type", "text")

            if field_type in ["text", "email", "tel", "url", "number"]:
                await element.fill(str(value))
                logger.debug(
                    f"Filled {field.get('name', field.get('id'))} with '{value}'"
                )

            elif field_type == "checkbox":
                if value:
                    await element.check()
                else:
                    await element.uncheck()
                logger.debug(f"Set checkbox {field.get('name')} to {value}")

            elif field_type == "file":
                if isinstance(value, (str, Path)):
                    await element.set_input_files(str(value))
                    logger.debug(f"Uploaded file to {field.get('name')}: {value}")

            elif "element" in field and field.get("name"):
                # Handle select dropdowns
                await element.select_option(value=str(value))
                logger.debug(f"Selected option '{value}' in {field.get('name')}")

            return True

        except Exception as e:
            logger.error(f"Error filling field {field.get('name', 'unknown')}: {e}")
            return False

    async def click_button(
        self, page: Page, button_text: str = None, button_selector: str = None
    ) -> bool:
        """
        Click a button on the page.

        Args:
            page: Playwright page
            button_text: Text content of button to click
            button_selector: CSS selector for button

        Returns:
            True if successful, False otherwise
        """
        try:
            if button_selector:
                button = await page.query_selector(button_selector)
            elif button_text:
                # Try multiple selectors
                button = await page.query_selector(f"button:has-text('{button_text}')")
                if not button:
                    button = await page.query_selector(
                        f"input[type='submit'][value*='{button_text}']"
                    )
                if not button:
                    button = await page.query_selector(f"a:has-text('{button_text}')")
            else:
                logger.error("Must provide either button_text or button_selector")
                return False

            if button:
                await button.click()
                logger.info(f"Clicked button: {button_text or button_selector}")
                await page.wait_for_load_state("networkidle", timeout=5000)
                return True
            else:
                logger.warning(f"Button not found: {button_text or button_selector}")
                return False

        except Exception as e:
            logger.error(f"Error clicking button: {e}")
            return False

    async def wait_for_navigation(self, page: Page, timeout: int = 30000):
        """Wait for page navigation."""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except PlaywrightTimeout:
            logger.warning("Navigation timeout")
            return False

    async def get_page_text(self, page: Page) -> str:
        """Get all text content from the page."""
        try:
            return await page.inner_text("body")
        except Exception as e:
            logger.error(f"Error getting page text: {e}")
            return ""

    async def check_for_errors(self, page: Page) -> Optional[str]:
        """
        Check for error messages on the page.

        Returns:
            Error message if found, None otherwise
        """
        error_selectors = [
            ".error",
            ".alert-danger",
            ".error-message",
            '[role="alert"]',
            ".validation-error",
            ".field-error",
            ".form-error",
        ]

        for selector in error_selectors:
            try:
                error_elem = await page.query_selector(selector)
                if error_elem and await error_elem.is_visible():
                    error_text = await error_elem.text_content()
                    if error_text and error_text.strip():
                        logger.warning(f"Error found on page: {error_text}")
                        return error_text.strip()
            except:
                continue

        return None

    async def check_for_confirmation(self, page: Page) -> Tuple[bool, Optional[str]]:
        """
        Check if application was successfully submitted.

        Returns:
            (success, confirmation_message) tuple
        """
        # Check for success indicators
        success_patterns = [
            "application submitted",
            "thank you for applying",
            "successfully submitted",
            "application received",
            "confirmation",
            "we received your application",
        ]

        page_text = (await self.get_page_text(page)).lower()

        for pattern in success_patterns:
            if pattern in page_text:
                # Try to find confirmation number
                confirmation_selectors = [
                    ".confirmation-number",
                    ".reference-number",
                    ".application-id",
                    '[data-testid*="confirmation"]',
                ]

                for selector in confirmation_selectors:
                    try:
                        elem = await page.query_selector(selector)
                        if elem:
                            conf_text = await elem.text_content()
                            logger.info(f"Application confirmed: {conf_text}")
                            return True, conf_text.strip()
                    except:
                        continue

                logger.info("Application appears successful")
                return True, "Application submitted successfully"

        # Check for common error indicators
        if any(err in page_text for err in ["error", "failed", "could not submit"]):
            error = await self.check_for_errors(page)
            return False, error

        return False, None

    async def handle_login(
        self, page: Page, platform: str, credentials: Dict[str, str]
    ) -> bool:
        """
        Handle login for platforms that require authentication.

        Args:
            page: Playwright page
            platform: Platform name (linkedin, indeed, etc.)
            credentials: Dictionary with 'email' and 'password'

        Returns:
            True if login successful
        """
        logger.info(f"Attempting login for {platform}...")

        try:
            if platform == "linkedin":
                # Check if already logged in
                if "feed" in page.url or "mynetwork" in page.url:
                    logger.info("Already logged in to LinkedIn")
                    return True

                # Navigate to login page
                await page.goto("https://www.linkedin.com/login")
                await page.wait_for_load_state("networkidle")

                # Fill login form
                await page.fill("#username", credentials.get("email", ""))
                await page.fill("#password", credentials.get("password", ""))
                await page.click('button[type="submit"]')

                await page.wait_for_load_state("networkidle", timeout=10000)

                # Check if login successful
                if "feed" in page.url or "mynetwork" in page.url:
                    logger.info("LinkedIn login successful")
                    return True
                else:
                    logger.error("LinkedIn login failed")
                    return False

            elif platform == "indeed":
                # Indeed login logic
                if "indeed.com/account" in page.url:
                    logger.info("Already logged in to Indeed")
                    return True

                await page.goto("https://secure.indeed.com/account/login")
                await page.wait_for_load_state("networkidle")

                await page.fill("#login-email-input", credentials.get("email", ""))
                await page.fill(
                    "#login-password-input", credentials.get("password", "")
                )
                await page.click("#login-submit-button")

                await page.wait_for_load_state("networkidle", timeout=10000)
                return True

            else:
                logger.warning(f"Login not implemented for {platform}")
                return False

        except Exception as e:
            logger.error(f"Login error for {platform}: {e}")
            return False


class PlatformHandler:
    """Base class for platform-specific application handlers."""

    def __init__(self, browser: BrowserAutomation):
        self.browser = browser

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply to a job on the platform.

        Args:
            job_url: URL of the job posting
            application_data: Dictionary containing application details

        Returns:
            Result dictionary with status and details
        """
        raise NotImplementedError("Subclasses must implement apply()")


class LinkedInHandler(PlatformHandler):
    """Handler for LinkedIn Easy Apply applications."""

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply to LinkedIn job with Easy Apply."""
        page = await self.browser.create_page()

        try:
            logger.info(f"Starting LinkedIn Easy Apply: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state("networkidle")

            # Take initial screenshot
            await self.browser.screenshot(page, "linkedin_job_page")

            # Check if login required
            if "login" in page.url or "authwall" in page.url:
                logger.info("LinkedIn login required")
                credentials = application_data.get("credentials", {})
                if not await self.browser.handle_login(page, "linkedin", credentials):
                    return {
                        "status": "failed",
                        "reason": "Login required but credentials not provided or login failed",
                    }
                # Navigate back to job
                await page.goto(job_url)
                await page.wait_for_load_state("networkidle")

            # Look for Easy Apply button
            easy_apply_button = await page.query_selector("button.jobs-apply-button")
            if not easy_apply_button:
                easy_apply_button = await page.query_selector(
                    "button:has-text('Easy Apply')"
                )

            if not easy_apply_button:
                logger.warning("Easy Apply button not found")
                return {
                    "status": "requires_manual",
                    "reason": "Easy Apply button not found - may require external application",
                }

            # Click Easy Apply
            await easy_apply_button.click()
            await asyncio.sleep(2)  # Wait for modal to open

            # Take screenshot of application form
            await self.browser.screenshot(page, "linkedin_application_modal")

            # Fill out application form (multi-step)
            max_steps = 5
            for step in range(max_steps):
                logger.info(f"Processing application step {step + 1}")

                # Detect fields
                fields = await self.browser.detect_form_fields(page)

                # Fill text inputs
                for field in fields.get("text_inputs", []):
                    field_name = field.get("name", "").lower()
                    field_id = field.get("id", "").lower()

                    # Map common fields
                    if "phone" in field_name or "phone" in field_id:
                        if "phone" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["phone"]
                            )
                    elif "email" in field_name or "email" in field_id:
                        if "email" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["email"]
                            )

                # Upload resume if needed
                for field in fields.get("file_uploads", []):
                    if "resume" in application_data.get("documents", {}):
                        resume_path = application_data["documents"]["resume"]
                        await self.browser.fill_form_field(page, field, resume_path)

                # Take screenshot of filled form
                await self.browser.screenshot(page, f"linkedin_step_{step + 1}_filled")

                # Look for Next or Submit button
                next_button = await page.query_selector("button:has-text('Next')")
                submit_button = await page.query_selector("button:has-text('Submit')")
                review_button = await page.query_selector("button:has-text('Review')")

                if submit_button or review_button:
                    # Final step - submit application
                    logger.info("Submitting application...")
                    button_to_click = submit_button or review_button
                    await button_to_click.click()
                    await asyncio.sleep(3)

                    # Check for confirmation
                    success, confirmation = await self.browser.check_for_confirmation(
                        page
                    )

                    await self.browser.screenshot(page, "linkedin_confirmation")

                    if success:
                        return {
                            "status": "submitted",
                            "confirmation_number": confirmation,
                            "platform": "linkedin",
                        }
                    else:
                        # Check for errors
                        error = await self.browser.check_for_errors(page)
                        return {
                            "status": "failed",
                            "reason": error or "Unknown error during submission",
                        }

                elif next_button:
                    # Continue to next step
                    await next_button.click()
                    await asyncio.sleep(2)
                else:
                    # No more buttons - might be done or stuck
                    logger.warning("No next/submit button found")
                    break

            return {"status": "failed", "reason": "Could not complete application flow"}

        except Exception as e:
            logger.error(f"LinkedIn application error: {e}")
            await self.browser.screenshot(page, "linkedin_error")
            return {"status": "failed", "reason": f"Error: {str(e)}"}
        finally:
            await page.close()


class GreenhouseHandler(PlatformHandler):
    """Handler for Greenhouse applications."""

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply to Greenhouse job."""
        page = await self.browser.create_page()

        try:
            logger.info(f"Starting Greenhouse application: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state("networkidle")

            await self.browser.screenshot(page, "greenhouse_job_page")

            # Look for Apply button
            apply_button = await page.query_selector("#apply_button")
            if not apply_button:
                apply_button = await page.query_selector(
                    "a:has-text('Apply for this job')"
                )

            if apply_button:
                await apply_button.click()
                await asyncio.sleep(2)

            # Detect and fill form
            fields = await self.browser.detect_form_fields(page)

            # Map fields
            field_mapping = {
                "first_name": application_data.get("first_name", ""),
                "last_name": application_data.get("last_name", ""),
                "email": application_data.get("email", ""),
                "phone": application_data.get("phone", ""),
            }

            # Fill text inputs
            for field in fields.get("text_inputs", []):
                field_name = field.get("name", "").lower()
                for key, value in field_mapping.items():
                    if key in field_name and value:
                        await self.browser.fill_form_field(page, field, value)

            # Upload resume
            for field in fields.get("file_uploads", []):
                if "resume" in application_data.get("documents", {}):
                    await self.browser.fill_form_field(
                        page, field, application_data["documents"]["resume"]
                    )

            await self.browser.screenshot(page, "greenhouse_filled")

            # Submit
            if await self.browser.click_button(page, button_text="Submit Application"):
                await asyncio.sleep(3)
                success, confirmation = await self.browser.check_for_confirmation(page)

                await self.browser.screenshot(page, "greenhouse_result")

                if success:
                    return {
                        "status": "submitted",
                        "confirmation_number": confirmation,
                        "platform": "greenhouse",
                    }

            error = await self.browser.check_for_errors(page)
            return {
                "status": "failed",
                "reason": error or "Could not submit application",
            }

        except Exception as e:
            logger.error(f"Greenhouse application error: {e}")
            await self.browser.screenshot(page, "greenhouse_error")
            return {"status": "failed", "reason": f"Error: {str(e)}"}
        finally:
            await page.close()


class GenericHandler(PlatformHandler):
    """Generic handler for unknown platforms."""

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt generic application submission."""
        page = await self.browser.create_page()

        try:
            logger.info(f"Starting generic application: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state("networkidle")

            await self.browser.screenshot(page, "generic_job_page")

            # Try to detect and fill form
            fields = await self.browser.detect_form_fields(page)

            if not fields.get("text_inputs") and not fields.get("textareas"):
                logger.warning("No form fields detected")
                return {
                    "status": "requires_manual",
                    "reason": "No application form detected on page",
                }

            # Fill common fields
            filled_count = 0
            for field in fields.get("text_inputs", []):
                field_name = field.get("name", "").lower()
                field_placeholder = field.get("placeholder", "").lower()

                if "email" in field_name or "email" in field_placeholder:
                    if "email" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["email"]
                        )
                        filled_count += 1
                elif "phone" in field_name or "phone" in field_placeholder:
                    if "phone" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["phone"]
                        )
                        filled_count += 1
                elif "name" in field_name or "name" in field_placeholder:
                    if "first" in field_name or "first" in field_placeholder:
                        if "first_name" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["first_name"]
                            )
                            filled_count += 1
                    elif "last" in field_name or "last" in field_placeholder:
                        if "last_name" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["last_name"]
                            )
                            filled_count += 1

            # Upload resume if found
            for field in fields.get("file_uploads", []):
                if "resume" in application_data.get("documents", {}):
                    await self.browser.fill_form_field(
                        page, field, application_data["documents"]["resume"]
                    )
                    filled_count += 1

            await self.browser.screenshot(page, "generic_filled")

            if filled_count == 0:
                return {
                    "status": "requires_manual",
                    "reason": "Could not automatically fill any fields",
                }

            # Try to find and click submit button
            submit_clicked = False
            for button_text in [
                "Submit",
                "Apply",
                "Send Application",
                "Submit Application",
            ]:
                if await self.browser.click_button(page, button_text=button_text):
                    submit_clicked = True
                    break

            if not submit_clicked:
                return {
                    "status": "requires_manual",
                    "reason": f"Filled {filled_count} fields but could not find submit button",
                }

            await asyncio.sleep(3)
            success, confirmation = await self.browser.check_for_confirmation(page)

            await self.browser.screenshot(page, "generic_result")

            if success:
                return {
                    "status": "submitted",
                    "confirmation_number": confirmation,
                    "platform": "generic",
                }

            error = await self.browser.check_for_errors(page)
            return {
                "status": "pending",
                "reason": error
                or f"Filled {filled_count} fields and clicked submit - manual review recommended",
            }

        except Exception as e:
            logger.error(f"Generic application error: {e}")
            await self.browser.screenshot(page, "generic_error")
            return {"status": "failed", "reason": f"Error: {str(e)}"}
        finally:
            await page.close()


class LeverHandler(PlatformHandler):
    """Handler for Lever applications."""

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply to Lever job."""
        page = await self.browser.create_page()

        try:
            logger.info(f"Starting Lever application: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state("networkidle")

            await self.browser.screenshot(page, "lever_job_page")

            # Look for Apply button
            apply_button = await page.query_selector("a.template-btn-submit")
            if not apply_button:
                apply_button = await page.query_selector(
                    "a:has-text('Apply for this position')"
                )

            if apply_button:
                await apply_button.click()
                await asyncio.sleep(2)

            # Fill application form
            fields = await self.browser.detect_form_fields(page)

            # Map common Lever fields
            field_mapping = {
                "name": application_data.get("first_name", "")
                + " "
                + application_data.get("last_name", ""),
                "email": application_data.get("email", ""),
                "phone": application_data.get("phone", ""),
                "org": application_data.get("company", ""),
                "urls[LinkedIn]": application_data.get("linkedin_url", ""),
            }

            # Fill text inputs
            for field in fields.get("text_inputs", []):
                field_name = field.get("name", "")
                if field_name in field_mapping and field_mapping[field_name]:
                    await self.browser.fill_form_field(
                        page, field, field_mapping[field_name]
                    )

            # Upload resume
            for field in fields.get("file_uploads", []):
                field_name = field.get("name", "").lower()
                if "resume" in field_name and "resume" in application_data.get(
                    "documents", {}
                ):
                    await self.browser.fill_form_field(
                        page, field, application_data["documents"]["resume"]
                    )
                elif "cover" in field_name and "cover_letter" in application_data.get(
                    "documents", {}
                ):
                    await self.browser.fill_form_field(
                        page, field, application_data["documents"]["cover_letter"]
                    )

            await self.browser.screenshot(page, "lever_filled")

            # Submit
            if await self.browser.click_button(page, button_text="Submit application"):
                await asyncio.sleep(3)
                success, confirmation = await self.browser.check_for_confirmation(page)

                await self.browser.screenshot(page, "lever_result")

                if success:
                    return {
                        "status": "submitted",
                        "confirmation_number": confirmation,
                        "platform": "lever",
                    }

            error = await self.browser.check_for_errors(page)
            return {
                "status": "failed",
                "reason": error or "Could not submit application",
            }

        except Exception as e:
            logger.error(f"Lever application error: {e}")
            await self.browser.screenshot(page, "lever_error")
            return {"status": "failed", "reason": f"Error: {str(e)}"}
        finally:
            await page.close()


class WorkdayHandler(PlatformHandler):
    """Handler for Workday applications."""

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply to Workday job."""
        page = await self.browser.create_page()

        try:
            logger.info(f"Starting Workday application: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state("networkidle")

            await self.browser.screenshot(page, "workday_job_page")

            # Look for Apply button
            apply_button = await page.query_selector("a[data-automation-id='apply']")
            if not apply_button:
                apply_button = await page.query_selector("a:has-text('Apply')")

            if apply_button:
                await apply_button.click()
                await asyncio.sleep(3)

            # Workday has multi-step process
            max_steps = 10
            for step in range(max_steps):
                logger.info(f"Processing Workday step {step + 1}")

                await self.browser.screenshot(page, f"workday_step_{step + 1}")

                # Detect fields
                fields = await self.browser.detect_form_fields(page)

                # Fill text inputs
                for field in fields.get("text_inputs", []):
                    field_id = field.get("id", "").lower()
                    field_name = field.get("name", "").lower()

                    if "email" in field_id or "email" in field_name:
                        if "email" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["email"]
                            )
                    elif "phone" in field_id or "phone" in field_name:
                        if "phone" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["phone"]
                            )
                    elif "firstname" in field_id or "firstname" in field_name:
                        if "first_name" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["first_name"]
                            )
                    elif "lastname" in field_id or "lastname" in field_name:
                        if "last_name" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["last_name"]
                            )
                    elif "address" in field_id or "address" in field_name:
                        if "address" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["address"]
                            )
                    elif "city" in field_id or "city" in field_name:
                        if "city" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["city"]
                            )
                    elif "zipcode" in field_id or "postal" in field_id:
                        if "zipcode" in application_data:
                            await self.browser.fill_form_field(
                                page, field, application_data["zipcode"]
                            )

                # Upload documents
                for field in fields.get("file_uploads", []):
                    if "resume" in application_data.get("documents", {}):
                        await self.browser.fill_form_field(
                            page, field, application_data["documents"]["resume"]
                        )

                # Look for Next or Submit button
                next_button = await page.query_selector(
                    "button[data-automation-id='bottom-navigation-next-button']"
                )
                submit_button = await page.query_selector(
                    "button[data-automation-id='bottom-navigation-submit-button']"
                )

                if submit_button:
                    logger.info("Submitting Workday application...")
                    await submit_button.click()
                    await asyncio.sleep(5)

                    success, confirmation = await self.browser.check_for_confirmation(
                        page
                    )
                    await self.browser.screenshot(page, "workday_confirmation")

                    if success:
                        return {
                            "status": "submitted",
                            "confirmation_number": confirmation,
                            "platform": "workday",
                        }
                    else:
                        error = await self.browser.check_for_errors(page)
                        return {
                            "status": "failed",
                            "reason": error or "Unknown error during submission",
                        }

                elif next_button:
                    await next_button.click()
                    await asyncio.sleep(2)
                else:
                    logger.warning("No next/submit button found in Workday")
                    break

            return {
                "status": "requires_manual",
                "reason": "Workday application requires manual completion - complex workflow",
            }

        except Exception as e:
            logger.error(f"Workday application error: {e}")
            await self.browser.screenshot(page, "workday_error")
            return {"status": "failed", "reason": f"Error: {str(e)}"}
        finally:
            await page.close()


class iCIMSHandler(PlatformHandler):
    """Handler for iCIMS applications."""

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply to iCIMS job."""
        page = await self.browser.create_page()

        try:
            logger.info(f"Starting iCIMS application: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state("networkidle")

            await self.browser.screenshot(page, "icims_job_page")

            # Look for Apply button
            apply_button = await page.query_selector("a.iCIMS_Button")
            if not apply_button:
                apply_button = await page.query_selector("a:has-text('Apply Now')")

            if apply_button:
                await apply_button.click()
                await asyncio.sleep(3)

            # Fill form
            fields = await self.browser.detect_form_fields(page)

            # Map fields
            for field in fields.get("text_inputs", []):
                field_id = field.get("id", "").lower()

                if "firstname" in field_id:
                    if "first_name" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["first_name"]
                        )
                elif "lastname" in field_id:
                    if "last_name" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["last_name"]
                        )
                elif "email" in field_id:
                    if "email" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["email"]
                        )
                elif "phone" in field_id:
                    if "phone" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["phone"]
                        )

            # Upload resume
            for field in fields.get("file_uploads", []):
                if "resume" in application_data.get("documents", {}):
                    await self.browser.fill_form_field(
                        page, field, application_data["documents"]["resume"]
                    )

            await self.browser.screenshot(page, "icims_filled")

            # Submit
            if await self.browser.click_button(
                page, button_selector="button[type='submit']"
            ):
                await asyncio.sleep(3)
                success, confirmation = await self.browser.check_for_confirmation(page)

                await self.browser.screenshot(page, "icims_result")

                if success:
                    return {
                        "status": "submitted",
                        "confirmation_number": confirmation,
                        "platform": "icims",
                    }

            error = await self.browser.check_for_errors(page)
            return {
                "status": "failed",
                "reason": error or "Could not submit application",
            }

        except Exception as e:
            logger.error(f"iCIMS application error: {e}")
            await self.browser.screenshot(page, "icims_error")
            return {"status": "failed", "reason": f"Error: {str(e)}"}
        finally:
            await page.close()


class IndeedHandler(PlatformHandler):
    """Handler for Indeed applications."""

    async def apply(
        self, job_url: str, application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply to Indeed job."""
        page = await self.browser.create_page()

        try:
            logger.info(f"Starting Indeed application: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state("networkidle")

            await self.browser.screenshot(page, "indeed_job_page")

            # Check if login required
            if "account/login" in page.url:
                logger.info("Indeed login required")
                credentials = application_data.get("credentials", {})
                if not await self.browser.handle_login(page, "indeed", credentials):
                    return {
                        "status": "failed",
                        "reason": "Login required but credentials not provided or login failed",
                    }
                await page.goto(job_url)
                await page.wait_for_load_state("networkidle")

            # Look for Apply button
            apply_button = await page.query_selector("button.ia-BaseLinkButton")
            if not apply_button:
                apply_button = await page.query_selector("button:has-text('Apply now')")
            if not apply_button:
                apply_button = await page.query_selector(
                    "a:has-text('Apply on company site')"
                )
                if apply_button:
                    return {
                        "status": "requires_manual",
                        "reason": "Indeed redirects to external company site",
                    }

            if apply_button:
                await apply_button.click()
                await asyncio.sleep(2)

            # Fill application form
            fields = await self.browser.detect_form_fields(page)

            # Map fields
            for field in fields.get("text_inputs", []):
                field_name = field.get("name", "").lower()
                field_id = field.get("id", "").lower()

                if "email" in field_name or "email" in field_id:
                    if "email" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["email"]
                        )
                elif "phone" in field_name or "phone" in field_id:
                    if "phone" in application_data:
                        await self.browser.fill_form_field(
                            page, field, application_data["phone"]
                        )

            # Upload resume if not already on Indeed
            for field in fields.get("file_uploads", []):
                if "resume" in application_data.get("documents", {}):
                    await self.browser.fill_form_field(
                        page, field, application_data["documents"]["resume"]
                    )

            await self.browser.screenshot(page, "indeed_filled")

            # Submit
            submit_button_texts = [
                "Submit your application",
                "Submit application",
                "Continue",
                "Apply",
            ]
            submitted = False
            for button_text in submit_button_texts:
                if await self.browser.click_button(page, button_text=button_text):
                    submitted = True
                    break

            if submitted:
                await asyncio.sleep(3)
                success, confirmation = await self.browser.check_for_confirmation(page)

                await self.browser.screenshot(page, "indeed_result")

                if success:
                    return {
                        "status": "submitted",
                        "confirmation_number": confirmation,
                        "platform": "indeed",
                    }

            error = await self.browser.check_for_errors(page)
            return {
                "status": "failed",
                "reason": error or "Could not submit application",
            }

        except Exception as e:
            logger.error(f"Indeed application error: {e}")
            await self.browser.screenshot(page, "indeed_error")
            return {"status": "failed", "reason": f"Error: {str(e)}"}
        finally:
            await page.close()
