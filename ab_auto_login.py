import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import configparser
import ab_lib
from ab_lib import *
import sys


# import os
# print("Current dir:", os.getcwd())

# Enable logging to file
LOG_FILE =  r"./log/ab_auto_login_" + datetime.datetime.now().strftime("%Y%m%d") +".log"
sys.stdout = sys.stderr = open(LOG_FILE, "a")


INI_FILE = "ab_options_sell.ini"              # Set .ini file name used for storing config info.
# Load parameters from the config file
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)


# Set user profile; Access token and other user specific info from .ini will be pulled from this section
ab_lib.strChatID = cfg.get("tokens", "chat_id")
ab_lib.strBotToken = cfg.get("tokens", "options_bot_token")    #Bot include "bot" prefix in the token

iLog(f"Initialising : {__file__}",sendTeleMsg=True)
iLog(f"Logging info into : {LOG_FILE}")


app_url = 'https://a3.aliceblueonline.com'

client_code = cfg.get("tokens", "uid")
password = cfg.get("tokens", "pwd")
twofa = cfg.get("tokens", "twofa")
mpin = cfg.get("tokens", "mpin")

# iLog(f"client_code={client_code}, password={password}, twofa={twofa}, mpin={mpin}")

chromedriver_path = r'./chromedriver.exe'
# chromedriver_path = r'C:\Users\rajes\venv_alice_blue\code\chromedriver.exe'

# Options for headless chrome execution
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--headless')
options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36')

iLog(f"Running chromedriver in headless mode from path : {chromedriver_path}")
s=Service(chromedriver_path)
chrome_driver = webdriver.Chrome(service=s,options=options)
chrome_driver.get(app_url)
chrome_driver.delete_all_cookies()

form_user_id = chrome_driver.find_element(By.CSS_SELECTOR,"#app > div > div > div > div > div.rounded.custom-Card.pa-6.w-344 > div:nth-child(2) > form > div > input")
form_user_id.send_keys(client_code)
form_user_id.send_keys(Keys.RETURN)
time.sleep(1)


mpin_xpath = '//*[@id="app"]/div/div/div/div/div[1]/div[2]/form/div/div[1]/span[1]/input'

label_val = chrome_driver.find_element(By.XPATH,'//*[@id="app"]/div/div/div/div/div[1]/div[2]/form/div/label').text.strip()

iLog(f"Login Page label value={label_val}")

form_mpin = chrome_driver.find_element(By.XPATH,mpin_xpath)

iLog(f"Checking M-Pin element. id={form_mpin.id}")

# Check if M-Pin or password is asked
if label_val == 'M-Pin':
    iLog("M-Pin element found")
    form_mpin.send_keys(mpin)
    form_mpin.send_keys(Keys.RETURN)
    time.sleep(3)
else:
    iLog("M-Pin element not found. Using password element.")
    
    # Find password element and enter the password
    form_password = chrome_driver.find_element(By.CSS_SELECTOR,"#app > div > div > div > div > div.rounded.custom-Card.pa-6.w-344 > div:nth-child(2) > form > div > div.pswborder.rounded.d-flex.align-center.justify-space-between.w-100.h-40 > span.inputWithImg.cursor > input")
    form_password.send_keys(password)
    form_password.send_keys(Keys.RETURN)
    
    time.sleep(1)

    # Find twofa element and enter twofa
    form_twofa = chrome_driver.find_element(By.CSS_SELECTOR,"#app > div > div > div > div > div.rounded.custom-Card.pa-6.w-344 > div:nth-child(2) > form > div > div.pswborder.rounded.d-flex.align-center.justify-space-between.w-100.h-40 > span.inputWithImg.cursor > input")
    form_twofa.send_keys(twofa)
    form_twofa.send_keys(Keys.RETURN)
    time.sleep(3)

chrome_driver.delete_all_cookies()
chrome_driver.quit()
iLog("Login completed")