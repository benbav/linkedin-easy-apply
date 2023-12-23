import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import re
import time
import csv
import subprocess
import os
import sys

# https://github.com/reddy-hari/automate-linkedin-easy-apply-jobs/blob/master/openTest.js built using this as reference

# change these to match your search / what will be filled in forms / where the jobs are saved

# search_term = "data science internship"
# year_of_experience = "1"
# csv_save_name = "chichi_jobs.csv"

# linkedin_username = "chi.sanyika@gmail.com"
# linkedin_password = ""  # chichi needs to make linkeidn password

# search_terms = ["data analyst", "data scientist", "financial analyst"]
search_terms = ["data analyst"]
year_of_experience = "3"
csv_save_name = "benbav_jobs.csv"

linkedin_username = "benbav@berkeley.edu"
linkedin_password = "sally1234"

total_applied_jobs = 0


def update_playwright():
    try:
        result = subprocess.run(["playwright", "install"], capture_output=True, text=True)
    except Exception as e:
        print(f"Error checking Playwright version: {e}")


async def finish_apply(page, job_text):
    global total_applied_jobs
    await page.get_by_role("button", name="Submit application").click()  # timeout=2600
    print("Suessfully applied to position: " + job_text[:20] + "...")

    # write to csv
    today = time.strftime("%Y-%m-%d")

    # Write job details to the CSV file
    with open(csv_save_name, "a", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)

        # Write header if the file is empty
        if csv_file.tell() == 0:
            csv_writer.writerow(["Title", "Date"])

        # Write job details
        csv_writer.writerow([job_text, today])

    # wait for exit window to popup
    time.sleep(2)
    # exit
    await page.get_by_role("button", name="Dismiss").click()
    total_applied_jobs += 1


async def get_to_submit_page(page):
    time.sleep(1)
    # need to fix the number form quetsions
    review_button = await page.query_selector('button[aria-label="Review your application"]')
    next_button = await page.query_selector('button[aria-label="Continue to next step"]')

    number_inputs = await page.query_selector_all('input.artdeco-text-input--input[type="text"]')
    drop_downs = await page.query_selector_all('//select[starts-with(@id, "text-entity-list-form-component-formElement")]')
    radio_buttons = await page.query_selector_all('//label[starts-with(@class, "t-14")]')

    if review_button:
        print("found review button")
        # I think error is that it isnt findin review button
        await review_button.click()
    if next_button:
        await next_button.click()

    print("radio buttons: " + str(len(radio_buttons)))
    print("number inputs: " + str(len(number_inputs)))
    print("drop downs: " + str(len(drop_downs)))
    if radio_buttons or number_inputs or drop_downs:
        print("looking for form buttons")
        try:
            if radio_buttons:
                print("found radio buttons: " + str(len(radio_buttons)))
                for label in radio_buttons:
                    try:
                        text = await label.inner_text()
                        if "Yes" in text:
                            await label.click(timeout=1000)
                            if next_button:
                                await next_button.click()
                    except Exception as e:
                        print("Error: " + str(e))
            if number_inputs:
                print("found number inputs: " + str(len(number_inputs)))
                for text_input in number_inputs:
                    print("trying to fill number input: " + str(text_input))
                    try:
                        # error is it cant fill number input here for some reason
                        await text_input.fill(year_of_experience)
                        print("filled number input: " + str(text_input))
                        if next_button:
                            await next_button.click()
                    except Exception as e:
                        # await text_input.fill("a")
                        print("Error: " + str(e))
                        # time.sleep(20)
                        # a = input("asdf")
            if drop_downs:
                print("found drop downs: " + str(len(drop_downs)))
                # select yes from any drop downs
                time.sleep(1)
                drop_downs = await page.query_selector_all('//select[starts-with(@id, "text-entity-list-form-component-formElement")]')
                for drop_down in drop_downs:
                    try:
                        dropdown_options = await drop_down.inner_text()
                        option1 = dropdown_options[0]
                        if "Yes" in dropdown_options:
                            print("found yes in dropdowns")
                            await drop_down.select_option(value="Yes", timeout=3000)
                            print("selected yes in dropdowns")
                            # p = input("asdf")
                            if next_button:
                                await next_button.click()
                            elif review_button:
                                print("review button click")
                                await review_button.click()

                        else:
                            print("filling in with " + option1)
                            await drop_down.select_option(value=option1)
                            if next_button:
                                await next_button.click()
                            break
                    except Exception as e:
                        # print("dropdown error: " + str(e))
                        if next_button:
                            await next_button.click()
                        elif review_button:
                            await review_button.click()
                        else:
                            print("Error3: " + str(e))

            review_button = await page.query_selector('button[aria-label="Review your application"]')
            next_button = await page.query_selector('button[aria-label="Continue to next step"]')
            if next_button:
                await next_button.click()
            elif review_button:
                await review_button.click()
            else:
                print("Error4: " + str(e))
        except Exception as e:
            if next_button:
                await next_button.click()
            elif review_button:
                await review_button.click()
            else:
                print("Error5: " + str(e))


async def dismiss_job(page):
    # first press escape
    await page.keyboard.press("Escape")
    time.sleep(1)
    print("pressing escape")
    discard_buttons = await page.query_selector_all('//button[contains(@data-control-name, "discard")]')
    if discard_buttons:
        print("clicking discard")
        await discard_buttons[0].click()
    else:
        print("No 'close' or 'discard' button found.")


async def run(playwright: Playwright) -> None:
    global applied_jobs
    global total_applied_jobs
    for search_term in search_terms:
        print("Searching for " + search_term + " jobs...")
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        applied_jobs = 0

        # login
        await page.goto("https://www.linkedin.com/")
        await page.get_by_label("Email or phone").click()
        await page.get_by_label("Email or phone").fill(linkedin_username)
        await page.get_by_label("Email or phone").press("Tab")
        await page.get_by_label("Password", exact=True).fill(linkedin_password)
        await page.get_by_role("button", name="Sign in").click()

        await page.get_by_placeholder("Search").click()
        await page.get_by_placeholder("Search").fill(search_term)
        await page.get_by_placeholder("Search").press("Enter")
        await page.get_by_role("button", name="Jobs").click()

        await page.get_by_label("Easy Apply filter.").click()

        # job filters on easy apply and remote
        await page.get_by_label("Remote filter. Clicking this button displays all Remote filter options.").click()
        await page.locator("label").filter(has_text="Remote Filter by Remote").click()
        await page.get_by_role("button", name="Apply current filter to show").click()

        # gets count of all pages at the bottom
        result_pages = await page.query_selector_all('//li[starts-with(@class, "artdeco-pagination")]')

        # get all positions (jobs on each page)
        time.sleep(1)

        for i in range(len(result_pages)):
            await page.click(f'//button[starts-with(@aria-label, "Page {i + 1}")]')

            time.sleep(2)

            jobs = await page.query_selector_all('//div[starts-with(@class, "full-width artdeco-entity-lockup__title ember-view")]')
            hide_job_buttons = await page.query_selector_all('//button[starts-with(@aria-label, "Dismiss job")]')
            zipped_jobs = zip(jobs, hide_job_buttons)

            print("found " + str(len(jobs)) + " jobs on  page " + str(i + 1))

            try:
                for job_count, (job, hide_job_button) in enumerate(zipped_jobs):
                    print(f"working on job {job_count + 1}")
                    job_text = await job.inner_text()  # Get text of the position
                    await job.click()
                    time.sleep(1)  # wait for easy apply to become blue

                    try:
                        # click easy apply
                        await page.click('//div[starts-with(@class, "jobs-apply-button--top-card")]', timeout=1001)  # timeout=2000

                        try:
                            count = 0
                            while True:
                                # check if submit button exists finish the loop
                                if await page.query_selector('//span[text()="Submit application"]'):
                                    await finish_apply(page, job_text)
                                    # hide job
                                    time.sleep(1)
                                    print("hiding job...")
                                    await hide_job_button.click()
                                    time.sleep(1)
                                    break

                                # if non submit pages exist
                                else:
                                    count += 1
                                    try:
                                        await get_to_submit_page(page)
                                        if count > 5:
                                            # time.sleep(4)
                                            # p = input("pause")
                                            await dismiss_job(page)
                                            print("exiting after 5 tries")
                                            break
                                    except Exception as e:
                                        print("Error: " + str(e))
                                        print("exiting1...")
                                        await dismiss_job(page)

                        except Exception as e:
                            print("Error in while loop: " + str(e))
                            print("exiting2...")
                            await dismiss_job(page)
                            print(e)

                    except Exception as e:
                        # hide job if already applied
                        print("already applied to job")
                        print("hiding job...")
                        await hide_job_button.click()

                        time.sleep(1)
            except Exception as e:
                print("Error: " + str(e))
                # take screenshot
                await page.screenshot(path="error2.png")
                time.sleep(20)
                print(e)
                # exit
                print("exiting...")
                await dismiss_job(page)
                await dismiss_job(page)


update_playwright()


async def main() -> None:
    async with async_playwright() as playwright:
        await asyncio.gather(run(playwright))


# Run the asyncio event loop directly
asyncio.run(main())


# play sound at the end
os.system("afplay /System/Library/Sounds/Glass.aiff")
print("applied to " + str(total_applied_jobs) + " jobs")

# ok just need to spot test the forms on some jobs to fill out more
# just sleep on the next error to get the job title that isn't working
