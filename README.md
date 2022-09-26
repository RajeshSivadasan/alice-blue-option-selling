# (Work In Progress) Fully automated Alice Blue Algo Trading program with Python on NSE for Nifty / Banknifty Options Selling
Please use this only for reference and at your own risk. This repository contains python code to perform algo trading on India, NSE through AliceBlue broker. 
You need to have a valid AliceBlue client ID, password, 2FA authentication password set and API enabled (ask aliceblue support) to get this working.
This program is developed on AWS linux (ubuntu) platform
1. (WIP) Usage : > python ab_options_sell.py

You can read through the comments in the ab_options_selling.py for detailed understanding. 

2. The program uses ab_options_sell.ini file which is the key configuration file through which we can control all the parameters of this program, even at realtime using Telegram chats. 

3. As a onetime setup, please create log and data folder in the same path where the program files are copied.

4. Please run/schedule the ab_auto_login.py daily once at morning around 9:00 AM IST to log into the AliceBlue portal which is a mandatory requirement for connecting through the AliceBlue API V2.

Feel free to use/distribute this code freely so that new algo developers can get started easily.  

For folks who are interested in learning Algo Programming for Indian Stock exchanges can join this informative, valuable and highly active Telegram Group
https://t.me/AlgoTradeAnalysis
(Please note this is not my Telegram Group)
