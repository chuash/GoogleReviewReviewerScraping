# Import necessary libraries
import csv
import os
import re
import time
import Utils
from dateutil.relativedelta import relativedelta
from datetime import datetime
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
#from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 

# Declaring variables
# Filepath for file containing summary information related to business entity
bizsummaryfilepath = r'.\entitysummary.csv'
# Filepath for file containing google reviews related to business entity
bizreviewfilepath = r'.\entityreviews.csv'
# Filepath for folder containing review screenshot images
imagefilepath = r'.\images'
# Base url for GoogleMaps
baseurl = 'https://google.com/maps/'
# Field names for business entity summary file
summarycols = ['BusinessName', 'BusinessAddress', 'Category', 'Ratings',
               '#Reviews', 'ScrapedDate']
# Field names for business entity reviews file
reviewcols = ['BusinessName', 'BusinessAddress', 'Reviewer_ID', 'Name',
              'Ratings', 'ContributionDate', 'ScrapedDate',
              'Reviews']

if __name__ == "__main__":
    try:
        # Initialise the business entity summary file, if it has yet to exist
        if not os.path.exists(bizsummaryfilepath):
            # setting newline parameter to '' so that no unnecessary newline is created by csv writer
            with open(bizsummaryfilepath, 'w', newline='') as f:
                bizsum_write = csv.writer(f)
                bizsum_write.writerow(summarycols)

        # Initialise the business entity reviews file, if it has yet to exist
        if not os.path.exists(bizreviewfilepath):
            # setting newline parameter to '' so that no unnecessary newline is created by csv writer
            with open(bizreviewfilepath, 'w', newline='') as f:
                bizreview_write = csv.writer(f)
                bizreview_write.writerow(reviewcols)

        # Get user input on the target business
        biz = input('Please input the business name you want reviews to be scraped from : \n ')

        # Initialise the Chrome driver and access the GoogleMaps url
        driver = Utils.initialise_driver(Utils.chromedriverfilepath)
        driver.get(baseurl)

        # 1) Click on "Search Google Maps" searchbar and enter business name
        input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME,"xiQnY")))
        input.send_keys(biz.lower())

        # 2) Select the first search option returned by Google Maps
        option = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CLASS_NAME,"ZHeE1b")))
        option[0].click()

        # 3a) Extract the business name and check that it tallies with the search query
        name = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME,"lfPIob"))).text
        # if doesn't tally, raises error and stops scrapping to prevent scraping from wrong business entity
        if name.lower() != biz.lower():
            raise Utils.MyError("Name of business entity returned from search is incorrect")
        # 3b) Extract the business address
        add = [ele.text for ele in driver.find_elements(By.CLASS_NAME, 'Io6YTe')][0]
        # 3c) Extract the business category
        category = driver.find_element(By.CLASS_NAME, 'DkEaL ').text
        # 3d) Extract the average ratings and total number of reviews for the business
        temp = driver.find_element(By.CLASS_NAME, 'F7nice').text.split('\n')
        avgrating = temp[0]
        totreviews = re.sub('[()]', '', temp[1])

        # 4) Write to business summary file
        scrapedatestr, scrapedate = datetime.now().date().strftime('%d %b %Y'), datetime.now().date()
        with open(bizsummaryfilepath, 'a', newline='', encoding='utf-8') as f:
            bizsum_append = csv.writer(f)
            bizsum_append.writerow([name, add, category, avgrating, totreviews, scrapedatestr])

        # 5) Extracting the reviews
        # 5a) Click on the "Reviews" button to access the reviews page
        tabs = driver.find_elements(By.CLASS_NAME, "Gpq6kf")
        # Ensure that the correct button is being clicked. The Overview, Reviews and About buttons are of class "Gpq6kf"
        if len(tabs) == 3 and tabs[1].text == 'Reviews':
            tabs[1].click()
        else:
            raise Utils.MyError("Check the class names for the reviews button or review button might be missing")
        
        with open(bizreviewfilepath, 'a', newline='', encoding='utf-8') as f1:
            bizreview_append = csv.writer(f1)
        # 5b) look for the main section of the review page
            main = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[role= 'main']")))
            # Then check if there is a review section within the main section. If cannot be found, raise error
            reviewsection = main.find_elements(By.XPATH, '*')[1]
            # Allow time for elements to load
            time.sleep(1)
            reviewsectionparts = reviewsection.find_elements(By.XPATH, "*")
            if not(len(reviewsectionparts) == 10 and [ele.get_attribute('class').strip() for ele in reviewsectionparts][8] == 'm6QErb XiKgde'):
                raise Utils.MyError("No review section detected, pleaee check")
            # confirm that there are reviews in the review section
            if len(reviewsectionparts[8].find_elements(By.XPATH, "*"))>0:   # stop here
        # 5c) Scroll to bottom of reviews page so as to show all reviews and capture the max scrollheight of review section
                Utils.scroll_to_bottom(reviewsection, driver)
        # 5d) Click on "More" ,if present, for each review so as to show the entire review
                if 'See more' in driver.page_source:
                    More = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "[aria-label='See more']")))
                    _ = [button.click() for button in More]
        # 5e) Get the reviewer ID and name
                # extract the reviewer ID from the google maps contributor links
                reviewer_ID = [re.search(r'\d+',ele.get_attribute('data-href')) for ele in driver.find_elements(By.CLASS_NAME, "al6Kxe")]
                reviewer_ID = [ele[0] if ele is not None else ele for ele in reviewer_ID]
                # raise error if there is no reviewer ID detected
                if None in reviewer_ID:
                    raise Utils.MyError("No reviewer ID detected for at least one of the reviewers, please check.")
                reviewer_name = [ele.text for ele in driver.find_elements(By.CLASS_NAME, "d4r55")]
        # 5f) Get the business ratings
                ratings = [ele.get_attribute("aria-label") for ele in driver.find_elements(By.CLASS_NAME, "kvMYJc")]
        # 5g) Get the review dates
                reviewdate = [ele.text for ele in driver.find_elements(By.CLASS_NAME, "rsqaWe")]
        # 5h) Get the reviews
                reviews = [ele.text for ele in driver.find_elements(By.XPATH, "//div[@class='DU9Pgb']/following-sibling::div[1]")]
        # 5i) Write to business reviews file
                for i in range(len(reviewer_name)):
                    bizreview_append.writerow([name, add, [reviewer_ID[i]], reviewer_name[i],
                                              ratings[i], Utils.datediff(scrapedate,reviewdate[i]),
                                              scrapedatestr,reviews[i]])
            else:
                bizreview_append.writerow([name, add,'','','','',scrapedatestr,''])
                
        
        print(f"Google Reviews for {name} successfully scraped. Waiting to take screenshots.")
        
        # 6) Scroll to top of the review page, then take screenshots from top to bottom, saving the screenshots
        Utils.scroll_screenshot(element=reviewsection, driver=driver, imagefilepath=imagefilepath, stitchflg=True)
                
        print("Google Reviews scrapper program successfully run.")
                
    except TimeoutException:
        print(f"Error detected: {Utils.MyError('10 sec time out trying to wait for element to be visible, please troubleshoot the relevant elements')}")
    except NoSuchElementException as e:
        print(f"Error detected: {Utils.MyError('Unable to locate element. See error msg for affected element(s). ' + str(e))}")
    except (Utils.MyError, Exception, BaseException) as e:
        print(f"Error detected: {Utils.MyError(str(e))}")
    finally:
        # Close the browser regardless whether scraping is successfully completed
        driver.quit()
