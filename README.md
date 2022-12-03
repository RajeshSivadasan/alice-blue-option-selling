# (Work In Progress) Fully automated Alice Blue Algo Trading program with Python on NSE for Nifty / Banknifty Options Selling
Please use this only for reference and at your own risk. This repository contains python code to perform algo trading on India, NSE through AliceBlue broker. 
You need to have a valid AliceBlue client ID, password, 2FA authentication password set and API enabled (ask aliceblue support) to get this working.
This program is developed on Windows 10 and tested on both Windows and AWS linux (ubuntu) platform. This program can be scheduled using crontab in AWS linux free tier to run daily at 9.14 AM. <a href="https://github.com/RajeshSivadasan/AWSScripts">AWS lambda functions</a> can be used to start and stop AWS instances as per the market timings. 

1. (WIP) Usage : > python ab_options_sell.py

You can read through the comments in the ab_options_selling.py for detailed understanding. 

2. The program uses ab_options_sell.ini file which is the key configuration file through which we can control all the parameters of this program, even at realtime using Telegram chats. 

Feel free to use/distribute this code freely so that new algo developers can get started easily.  

For folks who are interested in learning Algo Programming for Indian Stock exchanges can join this informative, valuable and highly active Telegram Group
https://t.me/AlgoTradeAnalysis
(Please note this is not my Telegram Group)
