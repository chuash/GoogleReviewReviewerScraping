# Import necessary libraries
import csv
import os
import pandas as pd
import re
import time
from dateutil.relativedelta import relativedelta
from datetime import datetime
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Exception handling
class MyError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def initialise_driver(chromedriverfilepath, headlessflg = False):
    """
    This function takes in the filepath pointing to the chromedriver.exe file 
    and initialise the chromium web driver, taking into consideration whether
    headless or otherwise

    Args:
    ----------
    chromedriverfilepath (str) : absolute file path pointing to the chromedriver.exe file
    headlessflg (boolean) : determines whether driver is initialised in headless
                            mode. The default is False.

    Raises
    ------
    MyError : Inform user that Chrome Webdriver file path cannot be located
    
    Returns
    -------
    driver (object) : webdriver
    """
    if os.path.exists(chromedriverfilepath):
        # Tune setup options
        options = Options()
        options.headless = headlessflg  # Decides whether headless mode or not
            #options.add_argument("--window-size=1920,1080")  # Define the window size of the browser 1920x1080 px
        options.add_argument("--start-maximized")  #maximise the browser window
        cService = webdriver.ChromeService(executable_path=chromedriverfilepath)
        driver = webdriver.Chrome(options=options, service = cService)
        return driver
    else:
        raise MyError("Unable to locate Chrome Webdriver filepath")
    
def scroll_to_bottom(element, driver):
    """
    When given a scrollable Selenium element and Selenium Chrome Webdriver, 
    this function scrolls to the bottom of the element.
    
    Args:
    ----------
    element(object): Selenium element
    driver(object): Selenium Chrome Webdriver
    
    Returns:
    -------
    None

    """
    ht0 = 0
    # get the element's initial visible scrollable height
    ht1 = driver.execute_script("return arguments[0].scrollHeight", element)
    while ht0 < ht1:
        # scroll to the bottom of the element's visible scrollable height
        driver.execute_script('arguments[0].scrollTo(0,arguments[1])', element, ht1)
        # stop running the script for 1sec to allow time for elements to load
        time.sleep(1)
        ht0 = ht1
        # extract the element's current visible scrollable height
        ht1 = driver.execute_script("return arguments[0].scrollHeight", element)

def datediff(scrapedate, durdiff):
    """
    This function takes in a date and duration difference and calculates a date that is 
    relative to the input date by the duration difference

    Args:
    ----------
    scrapedate(datetime object) : input date, in this case, is the date of scraping
    durdiff(str) : duration difference, e.g. 'a month ago', '3 weeks ago'

    Returns
    -------
    datetime object converted to date string 

    """
    if durdiff == '':
        contributiondate = scrapedate - relativedelta()
    else:
        numdiff = 1 if durdiff.split()[0] == 'a' else int(durdiff.split()[0])
        perioddiff = durdiff.split()[1]+'s' if durdiff.split()[1][-1]!='s' else durdiff.split()[1]
        contributiondate = scrapedate - relativedelta(**{perioddiff:numdiff})
    
    return contributiondate.strftime('%d %b %Y')

def read_ID(reviewfilepath, target=[], idx=''):
    """
    This function takes in the filepath pointing to the file containing google reviews 
    related to business entity. It then reads in the file and extracts the list of
    reviewer IDs. As the file may contain different business entities, this function
    allows user to select reviews corresponding to certain target businesses. Instead of 
    selecting all the reviewer IDs, this function allows the user to subset the reviewer
    IDs list from certain reviewer ID onwards

    # target business (use only when need to subset and target contributors for specific business)
    target = 'Queen Beauty Toa Payoh'
    # target contributorID (use this only when program fails halfway and you want to start from certain contributor onwards)

    Args:
    ----------
    reviewfilepath (str) : absolute filepath pointing to the google review file
    target (list) : list of target businesses to extract reviewer IDs from. The default is [].
    idx (str) : reviewer ID to subset list of reviewer IDs from. The default is ''.

    Raises
    ------
    MyError: Refer to the script for the error messages

    Returns
    -------
    IDlist(list): list of reviewer IDs

    """
    # Read in list of google contributor IDs
    if os.path.exists(reviewfilepath):
        df = pd.read_csv(reviewfilepath)
        if set(['Reviewer_ID', 'BusinessName']).issubset(df.columns):
            # If target businesses specified
            if len(target) > 0:
                df= df[df['BusinessName'].isin(target)]
                IDlist= df.Reviewer_ID.apply(lambda x: re.search(r'\d+', x)[0]).tolist()
            # else consider all businesses
            else:
                IDlist= df.Reviewer_ID.apply(lambda x: re.search(r'\d+', x)[0]).tolist()
            if idx != '':
                IDlist= IDlist[IDlist.index(idx):]
            return IDlist
        else:
            raise MyError("Reviewer_ID and BusinessName field names expected, but cannot be found in Google reviews file, please check.")
    else:
        raise MyError("Google reviews file containing list of google contributor IDs not available, please check.")


def scroll_screenshot(element, driver, imagefilepath, stitchflg=True):
    """
    This function scrolls through the target element from top to bottom and takes
    screenshots of the element along the way. It also saves the images as well as the 
    stitched images into one long image, if applied.

    Parameters
    ----------
    element(object) : Scrollable selenium object to apply the scrolling and screenshots to
    driver(object) : Selenium Chrome Webdriver
    imagefilepath(str) : Filepath for folder containing review screenshot images
    stitchflg(boolean) : Whether to stitch the images into one long image.The default is True.

    Returns
    -------
    None.

    """
    slices = []  # to store image fragment
    offset = 0  # where to start
    # create the folder to store images, if it does not yet exist
    if not os.path.exists(imagefilepath):
        os.makedirs(imagefilepath)
        
    # Scroll to top of element so as to take screenshot from top to bottom
    driver.execute_script('arguments[0].scrollTo(0,arguments[1])', element, 0)
    
    # Get the max scroll height of the element
    finalscrollht = driver.execute_script("return arguments[0].scrollHeight", element)
    
    # As long as element max height is not reach, keep scrolling and take screenshots along the way
    while offset < finalscrollht:
        # Scrolling element
        driver.execute_script('arguments[0].scrollTo(0,arguments[1])', element, offset)
        # Take screenshot image of visible real estate
        img = Image.open(BytesIO(element.screenshot_as_png))
        offset += img.size[1]
        # storing each screenshot as bytes to a list, for stitching if activated
        slices.append(img)
        # Take screenshot image of visible real estate and store as png format
        element.screenshot(imagefilepath + f'\screen_{offset}.png')
        print (offset, finalscrollht)
    print('Screenshots of all reviews taken.')
    
    # To trim off duplicated portion from the last image
    extra_height = offset - finalscrollht
    if extra_height > 0 and len(slices) > 1:
       pixel_ratio = driver.execute_script("return window.devicePixelRatio")
       extra_height *= pixel_ratio
       last_image = slices[-1]
       width, height = last_image.size
       box = (0, extra_height, width, height)
       slices[-1] = last_image.crop(box)
    
    if stitchflg:
        # Stitch all images into one long image
        print('Stitching all images into one big image')
        img_frame_height = sum([img_frag.size[1] for img_frag in slices])
        img_frame = Image.new("RGB", (slices[0].size[0], img_frame_height))
        offset = 0
        for img_frag in slices:
            img_frame.paste(img_frag, (0, offset))
            offset += img_frag.size[1]
        img_frame.save(imagefilepath + '\stitchedimage.png')
        
        print('Screenshots of all reviews stitched into one long image.')