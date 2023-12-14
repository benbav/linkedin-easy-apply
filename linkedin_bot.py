import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import re
import time
import csv

# https://github.com/reddy-hari/automate-linkedin-easy-apply-jobs/blob/master/openTest.js built using this as reference

# change these to match your search / what will be filled in forms / where the jobs are saved

# search_term = "data science internship"
# year_of_experience = "1"
# csv_save_name = "chichi_jobs.csv"

# linkedin_username = "chi.sanyika@gmail.com"
# linkedin_password = ""  # chichi needs to make linkeidn password

search_terms = ["data analyst", "data scientist"]
year_of_experience = "3"
csv_save_name = "benbav_jobs.csv"

linkedin_username = "benbav@berkeley.edu"
linkedin_password = "sally1234"


async def finish_apply(page, job_text):
    global applied_jobs
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
    applied_jobs += 1


async def fill_questions_exists(page):
    radio_buttons = await page.query_selector_all('//label[starts-with(@class, "t-14")]')
    number_inputs = await page.query_selector_all('//div[starts-with(@class, "artdeco-text-input--container ember-view")]//input[@type="text"]')
    drop_downs = await page.query_selector_all('//select[starts-with(@id, "text-entity-list-form-component-formElement")]')
    if radio_buttons or number_inputs or drop_downs:
        return True
    else:
        return False


async def fill_questions(page):
    radio_buttons = await page.query_selector_all('//label[starts-with(@class, "t-14")]')
    if radio_buttons:
        for label in radio_buttons:
            try:
                text = await label.inner_text()
                if "Yes" in text:
                    await label.click(timeout=1000)
            except Exception as e:
                print("Error: " + str(e))

        # fill any text boxes with 3 lol
    number_inputs = await page.query_selector_all('//div[starts-with(@class, "artdeco-text-input--container ember-view")]//input[@type="text"]')
    if number_inputs:
        for text_input in number_inputs:
            try:
                await text_input.fill(year_of_experience, timeout=1000)
            except Exception as e:
                print("filling with text")
                await text_input.fill("a", timeout=1000)
                print("Error: " + str(e))

    # select yes from any drop downs
    drop_downs = await page.query_selector_all('//select[starts-with(@id, "text-entity-list-form-component-formElement")]')
    if drop_downs:
        for drop_down in drop_downs:
            if "Yes" in await drop_down.inner_text():
                await drop_down.select_option(value="Yes", timeout=1000)
            elif "Native or bilingual" in await drop_down.inner_text():  # for the english question
                await drop_down.select_option(value="Native or bilingual", timeout=1000)


total_applied_jobs = 0


async def run(playwright: Playwright) -> None:
    # global search_terms # fix later
    global applied_jobs
    global total_applied_jobs
    # loop over the search terms twice
    for _ in range(2):
        for search_term in search_terms:
            print("Searching for " + search_term + "jobs...")
            browser = await playwright.chromium.launch(headless=True)
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

            # chichi login

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

            # test later with the last few pages
            # result_pages = result_pages[0:1]

            # Loop through result pages and apply to jobs
            # result_pages = 100

            for i in range(len(result_pages)):
                await page.click(f'//button[starts-with(@aria-label, "Page {i + 1}")]')

                # get all positions (jobs on each page)

                # jobs = await page.query_selector_all('//div[starts-with(@class, "job-card-list__entity-lockup artdeco-entity-lockup artdeco-entity-lockup--size-4 ember-view")]')
                jobs = await page.query_selector_all('//div[starts-with(@class, "full-width artdeco-entity-lockup__title ember-view")]')

                # there are like 20 on the page - how to get all of them?
                print("found " + str(len(jobs)) + " jobs on page " + str(i + 1))

                try:
                    for job_count, job in enumerate(jobs):
                        print(f"working on job {job_count + 1} on page {i + 1}")
                        job_text = await job.inner_text()  # Get text of the position
                        await job.click()  # click job
                        await job.click()
                        # print("CLICKED JOB: " + job_text[:20] + "...")
                        time.sleep(1)  # wait for easy apply to become blue

                        try:
                            # click easy apply
                            await page.click('//div[starts-with(@class, "jobs-apply-button--top-card")]', timeout=1001)  # timeout=2000
                            # sometimes it goes straight to review

                            try:
                                count = 0
                                while True:
                                    if await page.query_selector('//span[text()="Submit application"]'):
                                        # print("found submit application button")
                                        await finish_apply(page, job_text)
                                        break

                                    elif await fill_questions_exists(page):
                                        print("found fill questions")
                                        count += 1
                                        try:
                                            await fill_questions(page)
                                            if count == 5:
                                                print("exiting...")
                                                await page.get_by_role("button", name="Dismiss").click()
                                                await page.get_by_role("button", name="Discard").click()
                                                break
                                            elif await page.query_selector('button[aria-label="Review your application"]'):
                                                print("found review button")
                                                await page.get_by_role("button", name="Review").click()
                                            else:
                                                count += 1
                                                if count == 5:
                                                    print("exiting...")
                                                    await page.get_by_role("button", name="Dismiss").click()
                                                    await page.get_by_role("button", name="Discard").click()
                                                    break
                                                # print("hit next button1")
                                                try:
                                                    await page.get_by_role("button", name="Next").click()
                                                except Exception as e:
                                                    # print("exiting...")
                                                    await page.get_by_role("button", name="Dismiss").click()
                                                    await page.get_by_role("button", name="Discard").click()
                                                    break
                                        except Exception as e:
                                            print("exiting...")
                                            await page.get_by_role("button", name="Dismiss").click()
                                            await page.get_by_role("button", name="Discard").click()

                                    elif await page.query_selector('//span[text()="Review"]'):
                                        # print("found review button")
                                        await page.get_by_role("button", name="Review").click()
                                    else:
                                        # print("count: " + str(count))
                                        count += 1
                                        if count == 5:
                                            print("exiting...")
                                            await page.get_by_role("button", name="Dismiss").click()
                                            await page.get_by_role("button", name="Discard").click()
                                            break
                                        # print("hit next button2")
                                        await page.get_by_role("button", name="Next").click()
                            except Exception as e:
                                print("Error in while loop: " + str(e))
                                print("exiting...")
                                await page.get_by_role("button", name="Dismiss").click()
                                await page.get_by_role("button", name="Discard").click()
                                print(e)

                        except Exception as e:
                            print("already applied to job")
                            time.sleep(1)
                except Exception as e:
                    print("Error: " + str(e))
                    print(e)
                    # exit
                    print("exiting...")
                    await page.get_by_role("button", name="Dismiss").click()
                    await page.get_by_role("button", name="Discard").click()
                    print("applied to " + str(applied_jobs) + " jobs")

            # track number of applied jobs for each search term
            print("applied to " + str(applied_jobs) + " jobs for " + search_term)
            print()
            print("overall applied to " + str(total_applied_jobs) + " jobs")


async def main() -> None:
    async with async_playwright() as playwright:
        await asyncio.gather(run(playwright))


# Run the asyncio event loop directly
asyncio.run(main())
