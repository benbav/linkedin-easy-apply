import asyncio
from playwright.async_api import Playwright, async_playwright
import time
import csv
import os
import random
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SEARCH_TERMS = ["data analyst"]
random.shuffle(SEARCH_TERMS)
YEAR_OF_EXPERIENCE = "4"
CSV_SAVE_NAME = "benbav_jobs.csv"
LINKEDIN_USERNAME = os.getenv("username")
LINKEDIN_PASSWORD = os.getenv("password")
HEADLESS = False

# Global variable to count total applied jobs
total_applied_jobs = 0

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_playwright():
    os.system("playwright install")


async def finish_apply(page, job_text):
    global total_applied_jobs
    await page.get_by_role("button", name="Submit application").click()
    logger.info(f"Successfully applied to position: {job_text[:20]}...")

    today = time.strftime("%Y-%m-%d")
    with open(CSV_SAVE_NAME, "a", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            csv_writer.writerow(["Title", "Date", "Source"])
        csv_writer.writerow([job_text, today, "linkedin"])

    time.sleep(2)

    await page.get_by_role("button", name="Dismiss").click()
    total_applied_jobs += 1


async def click_review(page):
    review_button = await page.query_selector('button[aria-label="Review your application"]')
    if review_button:
        await review_button.click()


async def handle_form_elements(page):
    number_inputs = await page.query_selector_all('input.artdeco-text-input--input[type="text"]')
    drop_downs = await page.query_selector_all('//select[starts-with(@id, "text-entity-list-form-component-formElement")]')
    radio_buttons = await page.query_selector_all('input:has-text("Value")')

    if number_inputs:
        for text_input in number_inputs:
            try:
                await text_input.fill(YEAR_OF_EXPERIENCE)
            except Exception as e:
                logger.error(f"Error filling number input: {e}")

    if drop_downs:
        for drop_down in drop_downs:
            try:
                options = await drop_down.inner_text()
                if "Yes" in options:
                    await drop_down.select_option(value="Yes")
                else:
                    await drop_down.select_option(index=0)
            except Exception as e:
                logger.error(f"Error selecting dropdown option: {e}")

    if radio_buttons:
        for button in radio_buttons:
            try:
                text = await button.inner_text()
                if "Yes" in text:
                    await button.click()
            except Exception as e:
                logger.error(f"Error clicking radio button: {e}")


async def get_to_submit_page(page):
    review_button = await page.query_selector('button[aria-label="Review your application"]')
    next_button = await page.query_selector('button[aria-label="Continue to next step"]')

    if review_button:
        await review_button.click()
    if next_button:
        await next_button.click()

    await handle_form_elements(page)

    review_button = await page.query_selector('button[aria-label="Review your application"]')
    next_button = await page.query_selector('button[aria-label="Continue to next step"]')
    if next_button:
        await next_button.click()
    elif review_button:
        await review_button.click()


async def dismiss_job(page):
    await page.keyboard.press("Escape")
    time.sleep(1)
    discard_buttons = await page.query_selector_all('//button[contains(@data-control-name, "discard")]')
    if discard_buttons:
        await discard_buttons[0].click()
    else:
        logger.info("No 'close' or 'discard' button found.")


async def login_to_linkedin(page):
    await page.goto("https://www.linkedin.com/")
    await page.get_by_label("Email or phone").fill(LINKEDIN_USERNAME)
    await page.get_by_label("Password", exact=True).fill(LINKEDIN_PASSWORD)
    await page.get_by_role("button", name="Sign in").click()


async def search_jobs(page, search_term):
    await page.get_by_placeholder("Search").fill(search_term)
    await page.get_by_placeholder("Search").press("Enter")
    await page.get_by_role("button", name="Jobs").click()
    await page.get_by_label("Easy Apply filter.").click()
    await page.get_by_label("Remote filter. Clicking this button displays all Remote filter options.").click()
    await page.locator("label").filter(has_text="Remote Filter by Remote").click()
    await page.get_by_role("button", name="Apply current filter to show").click()


async def process_job(page, job, hide_job_button):
    job_text = await job.inner_text()
    await job.click()
    time.sleep(1)

    applied = await page.query_selector('//div[contains(@class, "artdeco-inline-feedback") and contains(@class, "artdeco-inline-feedback--success")]')

    if applied:
        logger.info("Already applied to this job.")
        return
    try:
        await page.click('//div[starts-with(@class, "jobs-apply-button--top-card")]', timeout=3000)
        logger.info("Clicked easy apply...")

        count = 0
        while True:
            if await page.query_selector('//span[text()="Submit application"]'):
                await finish_apply(page, job_text)
                # await hide_job_button.click()
                break
            else:
                count += 1
                await get_to_submit_page(page)
                if count > 5:
                    await dismiss_job(page)
                    break
    except Exception as e:
        logger.error(f"Error processing job: {e}")
        pause = input("Press Enter to continue...")
        await dismiss_job(page)


async def run(playwright: Playwright):
    global total_applied_jobs
    for search_term in SEARCH_TERMS:
        browser = await playwright.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()

        await login_to_linkedin(page)
        await search_jobs(page, search_term)

        time.sleep(2)
        result_pages = await page.query_selector_all('//li[starts-with(@class, "artdeco-pagination")]')
        logger.info(f"Found {len(result_pages)} pages.")

        for i in range(len(result_pages)):
            await page.click(f'//button[starts-with(@aria-label, "Page {i + 1}")]')
            time.sleep(3)

            jobs = await page.query_selector_all('//div[starts-with(@class, "full-width artdeco-entity-lockup__title ember-view")]')
            hide_job_buttons = await page.query_selector_all('//button[starts-with(@aria-label, "Dismiss")]')
            zipped_jobs = zip(jobs, hide_job_buttons)

            logger.info(f"Found {len(jobs)} jobs on page {i + 1}")
            for job, hide_job_button in zipped_jobs:
                await process_job(page, job, hide_job_button)


async def linkedin_bot_main():
    async with async_playwright() as playwright:
        await run(playwright)


if __name__ == "__main__":
    update_playwright()
    try:
        asyncio.run(linkedin_bot_main())
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        asyncio.run(linkedin_bot_main())
    os.system("afplay /System/Library/Sounds/Glass.aiff")
    logger.info(f"Applied to {total_applied_jobs} jobs")


# this actually works better I just want it to go through more forms with it - that's the next step
# isolate a form that doesn't work with a pause first
# then try and fill that form or see what type of form it is
