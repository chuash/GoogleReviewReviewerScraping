# Import necessary libraries
import csv
import os
import pandas as pd
import re
import time
import Utils
from dateutil.relativedelta import relativedelta
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Declaring variables
# Filepath for file containing google reviews related to business entity.
bizreviewfilepath = r".\entityreviews.csv"
# Filepath for file containing google contributors and their contribution summary.
contrisumfilepath = r".\contributorsummary.csv"
# Filepath for file containing google contributors and their detailed contributions.
contridetailfilepath = r".\contributordetails.csv"
# Base url for GoogleMaps Contributor page
baseurl = "https://google.com/maps/contrib/"
# Field names for contribution summary file
contrisumcols = [
    "Reviewer_ID",
    "Name",
    "Localguide",
    "ScrapedDate",
    "Reviews",
    "Ratings",
    "Photos",
    "Videos",
    "Captions",
    "Answers",
    "Edits",
    "Reported",
    "Places",
    "Roads",
    "Facts",
    "Q&A",
]
# Field names for contribution details file
contridetailcols = [
    "Reviewer_ID",
    "ContributionType",
    "BusinessName",
    "BusinessAddress",
    "Ratings",
    "ContributionDate",
    "ScrapedDate",
    "Reviews",
]
# Use these with read_ID function
target = []
idx = ""


if __name__ == "__main__":
    try:
        # Read in list of google contributor IDs
        IDlist = Utils.read_ID(bizreviewfilepath, target, idx)

        # Initialise the Chrome driver
        driver = Utils.initialise_driver(Utils.chromedriverfilepath)

        # Initialise the contribution summary file, if it has yet to exist
        if not os.path.exists(contrisumfilepath):
            # setting newline parameter to '' so that no unnecessary newline is created by csv writer
            with open(contrisumfilepath, "w", newline="") as f:
                contrisum_write = csv.writer(f)
                contrisum_write.writerow(contrisumcols)

        # Initialise the contribution details file, if it has yet to exist
        if not os.path.exists(contridetailfilepath):
            # setting newline parameter to '' so that no unnecessary newline is created by csv writer
            with open(contridetailfilepath, "w", newline="") as f:
                contridetail_write = csv.writer(f)
                contridetail_write.writerow(contridetailcols)

        # Extracting information by google contributor ID
        # Get the date of extraction
        scrapedatestr, scrapedate = (
            datetime.now().date().strftime("%d %b %Y"),
            datetime.now().date(),
        )
        with open(contrisumfilepath, "a", newline="", encoding="utf-8") as f1, open(
            contridetailfilepath, "a", newline="", encoding="utf-8"
        ) as f2:
            contrisum_append = csv.writer(f1)
            contridetail_append = csv.writer(f2)
            for ix in IDlist:
                # Navigate to page of Contributor ID
                driver.get(baseurl + ix)
                time.sleep(1)

                # 1)Extract the name
                name = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "geAzIe"))).text

                # 2a)Get the breakdown of contributions. First, click to show the contributions
                entry = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "FNyx3"))
                )
                # Check if contributor has attained status of local guide
                localguide = "Yes" if "local guide" in entry.text.lower() else "No"
                entry.click()

                # 2b) Then extract the contribution types, followed by the corresponding counts
                CT = WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CLASS_NAME, "FM5HI"))
                )
                contribtype = [ele.text for ele in CT]
                CC = WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CLASS_NAME, "AyEQdd"))
                )
                contribcount = [ele.text for ele in CC]

                # 2c) Confirm that the contribution types correspond to the fieldnames in the contribution summary file
                if [item.lower() for item in contrisumcols[4:]] == [
                    itemz.lower().split()[0] for itemz in contribtype
                ]:

                    # 2d) Write to contribution summary file
                    contrisum_append.writerow(
                        [[ix], name, localguide, scrapedatestr] + contribcount
                    )
                else:
                    raise Utils.MyError(
                        "Mismatch in contribution types. Cross-check contribution summary file field names with website."
                    )

                # 2e) Click to close the contribution dialog box
                driver.find_element(
                    By.XPATH, '//*[@id="modal-dialog"]/div/div[2]/div/button/span'
                ).click()

                # 3) Click on the "Reviews" button to access the reviews
                tabs = driver.find_elements(By.CLASS_NAME, "Gpq6kf")
                # Ensure that the correct button is being clicked. Both the reviews and photos buttons are of class "Gpq6kf"
                if len(tabs) == 2 and tabs[0].text == 'Reviews':
                    tabs[0].click()
                else:
                    raise Utils.MyError(
                        "Check the class names for the reviews and photos elements"
                    )

                # 4) First check if there is any review, if no, skip else proceed with scraping
                reviewsection = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "[aria-label='Reviews']")
                    )
                )
                if "OEnQgb" not in [
                    ele.get_attribute("class").strip()
                    for ele in reviewsection.find_elements(By.XPATH, "*")
                ]:
                    # 4a) Scroll to bottom of reviews page so as to show all reviews and capture the max scrollheight of review section
                    eleheight = Utils.scroll_to_bottom(reviewsection, driver) 

                    # 4b) Click on "More" ,if present, for each review so as to show the entire review
                    if "See more" in driver.page_source:
                        More = WebDriverWait(driver, 10).until(
                            EC.visibility_of_all_elements_located(
                                (By.CSS_SELECTOR, "[aria-label='See more']")
                            )
                        )
                        _ = [button.click() for button in More]

                    # 4c) Get the business names and address of the business entities reviewed by contributor
                    bizname_add = [
                        ele.text.split("\n")
                        for ele in driver.find_elements(By.CLASS_NAME, "WNxzHc ")
                    ]
                    biznames = [ele[0] for ele in bizname_add]
                    bizadd = [
                        " ".join(ele[1:]) if len(ele) > 1 else "" for ele in bizname_add
                    ]

                    # 4d) Get the business ratings and review dates for each review made by contributor
                    rating_date_ele = [
                        ele.find_elements(By.XPATH, "*")
                        for ele in driver.find_elements(By.CLASS_NAME, "DU9Pgb")
                    ]
                    rating_date = [
                        [item.get_attribute("class").strip() for item in ele]
                        for ele in rating_date_ele
                    ]
                    ratings = []
                    reviewdate = []
                    for i in range(len(rating_date_ele)):
                        [
                            (
                                ratings.append(
                                    rating_date_ele[i][0].get_attribute("aria-label")
                                )
                                if "kvMYJc" in rating_date[i]
                                else ratings.append("")
                            )
                        ]
                        [
                            (
                                reviewdate.append(rating_date_ele[i][1].text)
                                if "rsqaWe" in rating_date[i]
                                else reviewdate.append("")
                            )
                        ]

                    # 4e) Get the reviews
                    reviews = [
                        ele.text
                        for ele in driver.find_elements(
                            By.XPATH, "//div[@class='DU9Pgb']/following-sibling::div[1]"
                        )
                    ]

                    # 4f) Write to contribution details file
                    for i in range(len(biznames)):
                        contridetail_append.writerow(
                            [
                                [ix],
                                "Review",
                                biznames[i],
                                bizadd[i],
                                ratings[i],
                                Utils.datediff(scrapedate, reviewdate[i]),
                                scrapedatestr,
                                reviews[i],
                            ]
                        )
                else:
                    contridetail_append.writerow(
                        [[ix], "Review", "", "", "", "", scrapedatestr, ""]
                    )

                # 5) Click on the "Photos" button to access the photos if there are photos
                if tabs[1].text == 'Photos':
                    tabs[1].click()
                else:
                    raise Utils.MyError(
                        "Photos section seems to be non-existent, please check."
                    )
                
                # 5a) Check if there is any photo, if no, skip else proceed with scraping
                photosection = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "[aria-label='Photos']")
                    )
                )
                if "OEnQgb" not in [
                    ele.get_attribute("class").strip()
                    for ele in photosection.find_elements(By.XPATH, "*")
                ]:

                    # 5b) Scroll to bottom of photos page so as to show all photos and capture the max scrollheight of review section
                    Utils.scroll_to_bottom(photosection, driver)
                    # 5c) Get the business names and address
                    bizname_add = [
                        ele.text.split("\n")
                        for ele in driver.find_elements(By.CLASS_NAME, "UwKPnd")
                    ]
                    biznames = [ele[0] for ele in bizname_add]
                    bizadd = [
                        " ".join(ele[1:]) if len(ele) > 1 else "" for ele in bizname_add
                    ]
                    # 5d) Write to contribution details file
                    for i in range(len(biznames)):
                        contridetail_append.writerow(
                            [
                                [ix],
                                "Photos",
                                biznames[i],
                                bizadd[i],
                                "",
                                "",
                                scrapedatestr,
                                "",
                            ]
                        )
                else:
                    contridetail_append.writerow(
                        [[ix], "Photos", "", "", "", "", scrapedatestr, ""]
                    )

        print("Google Contributor scrapper program successfully run.")

    except TimeoutException:
        print(f"Error detected: {Utils.MyError('10 sec time out trying to wait for element to be visible, please troubleshoot the relevant elements')}")

    except NoSuchElementException as e:
        print(f"Error detected: {Utils.MyError('Unable to locate element. See error msg for affected element(s). ' + str(e))}")

    except (Utils.MyError, Exception, BaseException) as e:
        print(f"Error detected: {Utils.MyError(str(e))}")

    finally:
        # Close the browser regardless whether scraping is successfully completed
        driver.quit()
