# pylint: disable=unused-wildcard-import
# If dow is 5,1,2 and MTM is below -1% then no order to be placed that day and wait for next day
# Get file contents from gdrive shareable link 
# URL = <Go to Drive --> choose the file --> choose 'Get Link' --> paste it here>
# path = 'https://drive.google.com/uc?export=download&id='+URL.split('/')[-2]
# Gdrive files are slow to read, takes at least 2 seconds

# Google Sheets API
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
# https://developers.google.com/sheets/api/quickstart/python

###### STRATEGY / TRADE PLAN #####
# Trading Style     : Intraday. Positional if MTM is negative.
# Trade Timing      : Regular Market hours 
# Trading Capital   : Rs 6,60,000 approx
# Trading Qty       : Min upto 6 lots
# Premarket Routine : TBD
# Trading Goals     : Short max Nifty OTM Call/Put < 100   
# Time Frame        : 2 min
# Entry Criteria    : Entry post 10.30 AM / Price Action = Sell CE; Price Action SELL PE
# Exit Criteria     : Book 75% at 30 ponts gain/nearest Pivot Level-10pts (Whichever is earliest), rest based on Nearest Pivot Level - 10pts  
# Risk Capacity     : TBD. Always use next week expiry to be safe and if price goes above 150, switch to next expiry
# Order Management  : Only target orders set; Manually manage -ve MTM (Use Mean reversion/Adjust to next strikes)

# Supertrend Buy signal will trigger ATM CE buy
# Supertrend Sell signal will trigger ATM PE buy 
# Existing positions to be closed before order trigger
# For option price, ATM ltp CE and ATM ltp PE to be subscribed dynamically and stored in global variables
# Nifty option order trigger to be based on Nifty50 Index movement hence nifty50 dataframe required 
# BankNifty option order trigger to be based on BankNifty Index movement hence banknifty dataframe required to be maintained seperately

# bg process
# 2020-09-01 09:59:18.152555|1|chat_id=670221062 text=Cmd ls
# exception= list index out of range
# 2020-09-01 10:00:18.565516|1|chat_id= text=Cmd ls
# exception= list index out of range

# Open issues/tasks:
# Check use of float in buy_signal() as it is working in ab.py without it
# Instead of check_trade_time_zone() plan for no_trade_zone() 
# Update Contract Symbol ab.update_contract_symbol(). If last friday is holiday this code dosent run and the symbol is not updated and the program fails
# Consider seperate sl_buffer for nifty and bank in get_trade_price()
# Check if order parameters like order type and others can be paramterised
# Look at close pending orders, my not be efficient, exception handling and all
# WebSocket disconnection and subscription/tick loss issue. Upgraded the package  
# Option of MIS orders for bank to be added, maybe for nifty as well. Can test with nifty 
# check_MTM_Limit() limitation : if other nifty or bank scrips are traded this will messup the position
# trade_limit_reached() moved before check_pending_orders(). Need to check if this is the correct approach
# get_trade_price bo_level to be parameterised from .ini 0 , 1 (half of atr), 2 (~atr)
# If ATR > 10 or something activate BO3
# In ST up/down if ST_MEDIUM is down/Up - If high momentum (check rate of change) chances are it will break medium SL 
# Look at 3 min to 6 min crossover points , compare ST values of low and medium for possible override
# Retun/Exit function after Postion check in buy/sell function fails 
# Look at df_nifty.STX.values; Can we use tail to get last n values in the list
# Can have few tasks to be taken care/check each min like MTM/Tradefalg check/set. This is apart from interval
# Delay of 146 secs, 57 secs, 15 secs etc seen. Check and Need to handle 
# Look at 5/10 mins trend, dont take positions against the trend
# Keep limit price at 10% from ST and Sl beyond 10% from ST
# Relook at supertrend multiplier=2.5 option instead of current 3
# NSE Premarket method values may not be current as bank open time is considered . Need to fetch this realtime around 915 
# May need try/catch in reading previous day datafile due to copy of ini file or failed runs
# Can look at frequency of data export through parameter, say 60,120,240 etc.. 

# Guidelines:
# TSL to be double of SL (Otherwise mostly SLs are hit as they tend to )
# SL will be hit in high volatility. SL may be set to ATR*3 or medium df Supertrend Value
# Always buy market, in case SL reverse and get out cost to cost. Market has to come up, but mind expiry :)  
# SLs are usually hit in volatile market, so see if you can use less qty and no SLs, especially bank.
# Dont go against the trend in any case. 
# Avoid manual trades

# To Manually run program use following command
# python3 ab_options_sell.py &


# To do
# Source list of NSE holidays from public url file like on github 


# from pandas.core.indexing import is_label_like
# import ab_lib
# from ab_lib import *
from pya3 import *
import sys
import datetime
import time
# import threading
import configparser

# For Autologin
import requests
import json
from Crypto import Random
from Crypto.Cipher import AES
import hashlib
import base64
import pyotp
from dateutil.relativedelta import relativedelta, TH



# from nsepy import get_history


INI_FILE = __file__[:-3]+".ini"   
# Load parameters from the config file
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)
log_to_file = int(cfg.get("tokens", "log_to_file"))



# Manual Activities to be performed
# ---------------------------------
# Frequency - Yearly, Update [Info] -> weekly_expiry_holiday_dates in .ini

# Enable logging to file
# If log folder is not present create it
if not os.path.exists("./log") : os.makedirs("./log")
if log_to_file : sys.stdout = sys.stderr =  open(r"./log/ab_options_sell_" + datetime.datetime.now().strftime("%Y%m%d") +".log" , "a") 

# sys.stdout = sys.stderr = open(LOG_FILE, "a")
###################################
#      Logging method
###################################
# Custom logging: Default Info=1, data =0
def iLog(strLogText,LogType=1,sendTeleMsg=False):
    '''0=data, 1=Info, 2-Warning, 3-Error, 4-Abort, 5-Signal(Buy/Sell) ,6-Activity/Task done

        sendTelegramMsg=True - Send Telegram message as well. 
        Do not use special characters like #,& etc  
    '''
    #0- Data format TBD; symbol, price, qty, SL, Tgt, TSL
    
    print("{}|{}|{}".format(datetime.datetime.now(),LogType,strLogText),flush=True)
    
    if sendTeleMsg :
        try:
            requests.get("https://api.telegram.org/"+strBotToken+"/sendMessage?chat_id="+strChatID+"&text="+strLogText)
        except:
            iLog("Telegram message failed."+strLogText)



######################################
#       Initialise variables
######################################
strChatID = cfg.get("tokens", "chat_id")
strBotToken = cfg.get("tokens", "bot_token")    #Bot include "bot" prefix in the token

read_settings_from_url = int(cfg.get("tokens", "read_settings_from_url"))
settings_url = cfg.get("tokens", "settings_url")

BASE_URL = cfg.get("tokens", "BASE_URL") 

# Session id and related parameters tobe removed from the config file and below as well post testing for sometime
# session_id = cfg.get("tokens", "session_id")
# session_dt = cfg.get("tokens", "session_dt")
# if session_dt == datetime.date.today().isoformat():
#     iLog("Existing session will be reused.")
# else:
#     session_id = ""


# read_settings_from_url = 'https://raw.githubusercontent.com/RajeshSivadasan/mysettings/main/ab_options_sell.ini'
# read_settings_from_url = ''

iLog(f"Initialising : {__file__}",sendTeleMsg=True)
# iLog(f"Logging info into : {LOG_FILE}")

# # crontabed this at 9.00 am instead of 8.59 
# # Set initial sleep time to match the bank market opening time of 9:00 AM to avoid previous junk values
# init_sleep_seconds = int(cfg.get("info", "init_sleep_seconds"))
# iLog(f"Setting up initial sleep time of {init_sleep_seconds} seconds.",sendTeleMsg=True)
# time.sleep(init_sleep_seconds)

# susername = cfg.get("tokens", "uid")
# spassword = cfg.get("tokens", "pwd")
# twofa = cfg.get("tokens", "twofa")
# api_key = cfg.get("tokens", "api_key")


# Settings can also be read from url except for token settings
if read_settings_from_url:
    iLog(f"Reading settings from url file {settings_url}")
    cfg.read_string(requests.get(settings_url).text)
else:
    iLog(f"Reading settings from local file {INI_FILE}")



# Realtime variables also loaded in get_realtime_config()
trade_nifty = int(cfg.get("realtime", "trade_nifty"))                 # Trade Nifty options. True = 1 (or non zero) False=0
trade_banknifty = int(cfg.get("realtime", "trade_banknifty"))                 # Trade Bank Nifty options. True = 1 (or non zero) False=0

nifty_sl = float(cfg.get("realtime", "nifty_sl"))               #15.0 ?
bank_sl = float(cfg.get("realtime", "bank_sl"))                     #30.0 ?

mtm_sl = int(cfg.get("realtime", "mtm_sl"))                     #amount below which program exit all positions 
mtm_target = int(cfg.get("realtime", "mtm_target"))             #amount above which program exit all positions and not take new positions

nifty_limit_price_offset = float(cfg.get("realtime", "nifty_limit_price_offset"))
bank_limit_price_offset = float(cfg.get("realtime", "bank_limit_price_offset"))

nifty_strike_ce_offset = float(cfg.get("realtime", "nifty_strike_ce_offset"))
nifty_strike_pe_offset = float(cfg.get("realtime", "nifty_strike_pe_offset"))
bank_strike_ce_offset = float(cfg.get("realtime", "bank_strike_ce_offset"))
bank_strike_pe_offset = float(cfg.get("realtime", "bank_strike_pe_offset"))

strategy1_HHMM  = int(cfg.get("realtime", "strategy1_HHMM"))    # If set to 0 , strategy is disabled
strategy2_HHMM  = int(cfg.get("realtime", "strategy2_HHMM"))    # If set to 0 , strategy is disabled



# nifty_lot_size = int(cfg.get("info", "nifty_lot_size"))

#List NSE holidays, hence reduce 1 day to get expiry date if it falls on thurshday 
holiday_dates = cfg.get("info", "holiday_dates").split(",")


interval_seconds = int(cfg.get("info", "interval_seconds"))   #3
# nifty_sqoff_time = int(cfg.get("info", "nifty_sqoff_time")) #1512 time after which orders not to be processed and open orders to be cancelled
# bank_sqoff_time = int(cfg.get("info", "bank_sqoff_time")) #2310 time after which orders not to be processed and open orders to be cancelled


premarket_advance = int(cfg.get("info", "premarket_advance"))
premarket_decline = int(cfg.get("info", "premarket_decline"))
premarket_flag = int(cfg.get("info", "premarket_flag"))          # whether premarket trade enabled  or not 1=yes


# Below 2 Are Base Flag For nifty /bank nifty trading_which is used to reset daily(realtime) flags(trade_nifty,trade_banknifty) as 
# they might have been changed during the day in realtime 
enable_bank = int(cfg.get("info", "enable_bank"))               # 1=Original flag for BANKNIFTY trading. Daily(realtime) flag to be reset eod based on this.  
enable_NFO = int(cfg.get("info", "enable_NFO"))                 # 1=Original flag for Nifty trading. Daily(realtime) flag to be reset eod based on this.


nifty_opt_per_lot_qty = int(cfg.get("info", "nifty_opt_per_lot_qty"))

# List of days in number for which next week expiry needs to be selected, else use current week expiry
next_week_expiry_days = list(map(int,cfg.get("info", "next_week_expiry_days").split(",")))


# all_variables = f"susername={susername}, trade_nifty={trade_nifty}"

# iLog("Settings used : " + all_variables)


# while True:
#     iLog("reading from url")
#     cfg.read_string(requests.get(settings_url).text)
#     iLog(cfg.get("realtime", "mtm_sl"))  
#     time.sleep(5) 


# sys.exit(0)

# # Run autologin for the day
# autologin_date = cfg.get("tokens", "autologin_date")
# if autologin_date == datetime.date.today().isoformat():
#     iLog("Ant portal autologin already run for the day.")
# else:
#     iLog("Running Ant portal autologin.")
#     # import ab_auto_login_totp

# Lists to store ltp ticks from websocket
lst_nifty_ltp = []
lst_bank_ltp = []


socket_opened = False

# Counters for dataframe indexes
df_nifty_cnt = 0           
df_bank_cnt = 0


df_cols = ["cur_HHMM","open","high","low","close","signal","sl"]  # v1.1 added signal column

df_nifty = pd.DataFrame(data=[],columns=df_cols)        # Low - to store 3 mins level OHLC data for nifty
df_bank = pd.DataFrame(data=[],columns=df_cols)         # Low - to store 3 mins level OHLC data for banknifty

dict_ltp = {}                   # Will contain dictionary of token and ltp pulled from websocket
dict_sl_orders = {}             # Dictionary to store SL Order ID: token,target price, instrument, quantity; if ltp > target price then update the SL order limit price.

# lst_nifty = []  
cur_min = 0
flg_min = 0

MTM = 0.0                       # Float
pos_bank_ce = 0                 # current banknifty CE position 
pos_nifty_ce = 0                # current nifty CE position
pos_bank_pe = 0                 # current banknifty PE position 
pos_nifty_pe = 0                # current nifty PE position


processNiftyEOD = False         # Process pending Nifty order cancellation and saving of df data; Flag to run procedure only once


token_nifty_ce = 1111           # Set by get instrument later in the code
token_nifty_pe = 2222
token_bank_ce = 1111           
token_bank_pe = 2222


ltp_nifty_ATM_CE = 0            # Last traded price for Nifty ATM CE
ltp_nifty_ATM_PE = 0            # Last traded price for Nifty ATM PE
ltp_bank_ATM_CE = 0             # Last traded price for BankNifty ATM CE
ltp_bank_ATM_PE = 0             # Last traded price for BankNifty ATM PE

subscribe_list = []             # List of instruments currently being subscribed

dict_nifty_ce = {}
dict_nifty_pe = {}
dict_nifty_opt_selected = {} # for storing the details of existing older option position which needs reversion


# Get current/next week expiry 
# ----------------------------
# if today is tue or wed then use next expiry else use current expiry. .isoweekday() 1 = Monday, 2 = Tuesday
dow = datetime.date.today().isoweekday()    # Also used in placing orders 
if dow  in (next_week_expiry_days):  # next_week_expiry_days = 2,3,4 
    expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7)+7 )
else:
    expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7))

if str(expiry_date) in holiday_dates :
    expiry_date = expiry_date - datetime.timedelta(days=1)




# Get last thursday of next month for getting Next month Nifty Future Contract  
dt_next_exp = ((datetime.date.today()+ relativedelta(months=1)) + relativedelta(day=31, weekday=TH(-1)))
if str(dt_next_exp) in holiday_dates :
    dt_next_exp = dt_next_exp - datetime.timedelta(days=1)





# Get the trading levels and quantity multipliers to be followed for the day .e.g on Friday only trade reversion 3rd or 4th levels to be safe
lst_ord_lvl_reg =  eval(cfg.get("info", "ord_sizing_lvls_reg"))[dow]
lst_ord_lvl_mr =  eval(cfg.get("info", "ord_sizing_lvls_mr"))[dow]
lst_qty_multiplier_reg = eval(cfg.get("info", "qty_multiplier_per_lvls_reg"))[dow]
lst_qty_multiplier_mr = eval(cfg.get("info", "qty_multiplier_per_lvls_mr"))[dow]

nifty_avg_margin_req_per_lot =  int(cfg.get("info", "nifty_avg_margin_req_per_lot"))
# option_sell_type = cfg.get("info", "option_sell_type")  # CE/PE/BOTH
# nifty_opt_base_lot = int(cfg.get("info", "nifty_opt_base_lot"))

iLog(f"expiry_date = {expiry_date} dow={dow} lst_ord_lvl_reg={lst_ord_lvl_reg} lst_ord_lvl_mr={lst_ord_lvl_mr}")





###########################################
#    Class for Autologin into AliceBlue web
###########################################
class CryptoJsAES:
  @staticmethod
  def __pad(data):
    BLOCK_SIZE = 16
    length = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + (chr(length) * length).encode()

  @staticmethod
  def __unpad(data):
    return data[:-(data[-1] if type(data[-1]) == int else ord(data[-1]))]

  def __bytes_to_key(data, salt, output=48):
    assert len(salt) == 8, len(salt)
    data += salt
    key = hashlib.md5(data).digest()
    final_key = key
    while len(final_key) < output:
      key = hashlib.md5(key + data).digest()
      final_key += key
    return final_key[:output]

  @staticmethod
  def encrypt(message, passphrase):
    salt = Random.new().read(8)
    key_iv = CryptoJsAES.__bytes_to_key(passphrase, salt, 32 + 16)
    key = key_iv[:32]
    iv = key_iv[32:]
    aes = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(b"Salted__" + salt + aes.encrypt(CryptoJsAES.__pad(message)))

  @staticmethod
  def decrypt(encrypted, passphrase):
    encrypted = base64.b64decode(encrypted)
    assert encrypted[0:8] == b"Salted__"
    salt = encrypted[8:16]
    key_iv = CryptoJsAES.__bytes_to_key(passphrase, salt, 32 + 16)
    key = key_iv[:32]
    iv = key_iv[32:]
    aes = AES.new(key, AES.MODE_CBC, iv)
    return CryptoJsAES.__unpad(aes.decrypt(encrypted[16:]))



############################################################################
#     Define Functions
############################################################################

def auto_login_totp(user):

    userId = user['userid']
    password = user['password'] 
    twofa = user['twofa']
    totp_encrypt_key = user['totp_key']
    ret_val = False

    try:
        totp = pyotp.TOTP(totp_encrypt_key)

        url = BASE_URL+"/customer/getEncryptionKey"
        payload = json.dumps({"userId": userId})
        headers = {'Content-Type': 'application/json'}
        response = requests.request("POST", url, headers=headers, data=payload,verify=True)
        encKey = response.json()["encKey"]
        checksum = CryptoJsAES.encrypt(password.encode(), encKey.encode()).decode('UTF-8')


        url = BASE_URL+"/customer/webLogin"
        payload = json.dumps({"userId": userId,"userData": checksum})
        headers = {'Content-Type': 'application/json'}

        response = requests.request("POST", url, headers=headers, data=payload,verify=True)
        response_data = response.json()


        url = BASE_URL+"/sso/2fa"

        payload = json.dumps({
        "answer1": twofa,
        "userId": userId,
        "sCount": str(response_data['sCount']),
        "sIndex": response_data['sIndex']
        })

        headers = {'Content-Type': 'application/json'}

        response = requests.request("POST", url, headers=headers, data=payload,verify=True)

        # print("response.json():")
        # print(response.json())


        if response.json()["loPreference"] == "TOTP" and response.json()["totpAvailable"]:
            url = BASE_URL+"/sso/verifyTotp"
            payload = json.dumps({"tOtp": totp.now(),"userId": userId})
            headers = {'Authorization': 'Bearer '+userId+' '+response.json()['us'],'Content-Type': 'application/json'}
            response = requests.request("POST", url, headers=headers, data=payload,verify=True)


        if response.json()["userSessionID"]:
            # print("Login Successfully",flush=True)
            iLog(f"Login Successful. SessionID: {response.json()['userSessionID']}")
            ret_val = True
        # else:
        #     # print("User is not TOTP enabled! Please enable TOTP through mobile or web",flush=True)
        #     return False

    except Exception as ex:
        iLog(f"[{userId}] Exception occured: {ex}")
    
    return ret_val

def get_realtime_config():
    '''This procedure can be called during execution to get realtime values from the .ini file'''

    global trade_nifty, trade_banknifty, nifty_limit_price_offset,bank_limit_price_offset\
    ,mtm_sl,mtm_target, cfg, nifty_sl, bank_sl, export_data, sl_buffer, nifty_ord_type, bank_ord_type\
    ,nifty_strike_ce_offset, nifty_strike_pe_offset, bank_strike_ce_offset, bank_strike_pe_offset\
    ,strategy1_HHMM,strategy2_HHMM

    cfg.read(INI_FILE)
    
    trade_nifty = int(cfg.get("realtime", "trade_nifty"))                   # True = 1 (or non zero) False=0
    trade_banknifty = int(cfg.get("realtime", "trade_banknifty"))           # True = 1 (or non zero) False=0
    

    
    mtm_sl = float(cfg.get("realtime", "mtm_sl"))
    mtm_target  = float(cfg.get("realtime", "mtm_target"))
    sl_buffer = int(cfg.get("realtime", "sl_buffer"))
    
    nifty_limit_price_offset = float(cfg.get("realtime", "nifty_limit_price_offset"))
    bank_limit_price_offset = float(cfg.get("realtime", "bank_limit_price_offset"))

    nifty_strike_ce_offset = float(cfg.get("realtime", "nifty_strike_ce_offset"))
    nifty_strike_pe_offset = float(cfg.get("realtime", "nifty_strike_pe_offset"))
    bank_strike_ce_offset = float(cfg.get("realtime", "bank_strike_ce_offset"))
    bank_strike_pe_offset = float(cfg.get("realtime", "bank_strike_pe_offset"))

    strategy1_HHMM  = int(cfg.get("realtime", "strategy1_HHMM"))    # If set to 0 , strategy is disabled
    strategy2_HHMM  = int(cfg.get("realtime", "strategy2_HHMM")) 

def place_order(user, ins_scrip, qty, limit_price=0.0, buy_sell = TransactionType.Sell, order_type = OrderType.Limit, order_tag = "ab_options_sell"):
    '''
    Used for placing orders. Default is buy market orders for squareoff short positions 
    buy_sell = TransactionType.Buy/TransactionType.Sell
    order_type = Default is limit order
    limit_price = limit price in case SL order needs to be placed 
    '''
    # global alice
    alice_ord = user['broker_object'] 
    ord_obj = {}

    if limit_price > 1 : 
        trigger_price = limit_price
    else:
        trigger_price = None

    if user['virtual_trade']:
        iLog(f"[{user['userid']}] place_order(): *** Viratual trade {ins_scrip.name} {qty} {buy_sell} {limit_price}")    
    else:
        iLog(f"[{user['userid']}] place_order(): {ins_scrip.name} {qty} {buy_sell} {limit_price}")

        try:
            ord_obj = alice_ord.place_order(transaction_type = buy_sell,
                            instrument = ins_scrip,
                            quantity = qty,
                            order_type = order_type,
                            product_type = ProductType.Normal,
                            price = limit_price,
                            trigger_price = trigger_price,
                            stop_loss = None,
                            square_off = None,
                            trailing_sl = None,
                            is_amo = False,
                            order_tag = order_tag)

        except Exception as ex:
            iLog(f"[{user['userid']}] place_order(): Exception occured {ex}",3)

    return ord_obj

def place_option_orders_pivot(user,flgMeanReversion,dict_opt):
    '''
    Called from place_option_orders(). All arguments are mandatory.
    This procedure is used for putting regular or mean reversion (position sizing) orders based on pivot levels 
    '''
    # iLog(f"[{user['userid']}] place_option_orders_pivot(): flgMeanReversion = {flgMeanReversion} dict_opt = {dict_opt}")
    iLog(f"[{user['userid']}] place_option_orders_pivot(): flgMeanReversion={flgMeanReversion}")    

    last_price = dict_opt["last_price"]
    ins_opt = dict_opt["instrument"]
    qty = user['nifty_opt_base_lot'] * nifty_opt_per_lot_qty


    # level 0 = immediate resistance level, level 1 = Next resistance level and so on  
    if flgMeanReversion :
        #Put orders for mean reversion for existing positions while addding new positions 
        # rng = (dict_nifty_ce["r2"] - dict_nifty_ce["r1"])/2
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            # S/R to Level Mapping: s1=0, pp=1, r1=2, r2=3, r3=4, r4=5
            # place_order(user,ins_opt,qty,float(dict_opt["s1"]))
            
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["pp"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r1"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r2"]))
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r3"]))
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            # S/R to Level Mapping: pp=0, r1=1, r2=2, r3=3, r4=4
            # place_order(user,ins_opt,qty,float(dict_opt["pp"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r1"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r2"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r3"]))
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]))
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            # S/R to Level Mapping: r1=0, r2=1, r3=2, r4=3
            # place_order(user,ins_opt,qty,float(dict_opt["r1"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r2"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r3"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]))
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            # S/R to Level Mapping: r2=0, r3=1, r4=2
            # place_order(user,ins_opt,qty,float(dict_opt["r2"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r3"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r4"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 3*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            # S/R to Level Mapping: r3=0, r4=1
            # place_order(user,ins_opt,qty,float(dict_opt["r3"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r4"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + 3*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 4*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        else:
            iLog(f"[{user['userid']}] place_option_orders_pivot(): flgMeanReversion=True, Unable to find pivots and place order for {ins_opt}")

    else:
        # Regular orders for fresh positions or new position for next strike for mean reversion
        if dict_opt["s3"] <= last_price < dict_opt["s2"] : 
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["s2"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["s1"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["pp"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r1"]))
            if 4 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[4],float(dict_opt["r2"]))
            if 5 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[5],float(dict_opt["r3"]))
        
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["s1"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["pp"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r1"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r2"]))
            if 4 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[4],float(dict_opt["r3"]))
            if 5 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[5],float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["pp"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r1"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r2"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r3"]))
            if 4 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[4],float(dict_opt["r4"]))

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["r1"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r2"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r3"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r4"]))

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["r2"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r3"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r4"]))

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["r3"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r4"]))

        else:
            iLog(f"[{user['userid']}] place_option_orders_pivot(): flgMeanReversion=False, Unable to find pivots and place order for {ins_opt}")


def place_option_orders_fixed(user,flgMeanReversion,dict_opt):
    '''
    Called from place_option_orders(). All arguments are mandatory.
    This procedure is used for putting regular or mean reversion (position sizing) orders based on pivot levels 
    '''
    # iLog(f"[{user['userid']}] place_option_orders_pivot(): flgMeanReversion = {flgMeanReversion} dict_opt = {dict_opt}")
    iLog(f"[{user['userid']}] place_option_orders_fixed(): flgMeanReversion={flgMeanReversion}")    

    last_price = dict_opt["last_price"]
    ins_opt = dict_opt["instrument"]
    qty = user['nifty_opt_base_lot'] * nifty_opt_per_lot_qty


    # level 0 = immediate resistance level, level 1 = Next resistance level and so on  
    if flgMeanReversion :
        #Put orders for mean reversion for existing positions while addding new positions 
        # rng = (dict_nifty_ce["r2"] - dict_nifty_ce["r1"])/2
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            # S/R to Level Mapping: s1=0, pp=1, r1=2, r2=3, r3=4, r4=5
            # place_order(user,ins_opt,qty,float(dict_opt["s1"]))
            
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["pp"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r1"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r2"]))
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r3"]))
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            # S/R to Level Mapping: pp=0, r1=1, r2=2, r3=3, r4=4
            # place_order(user,ins_opt,qty,float(dict_opt["pp"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r1"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r2"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r3"]))
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]))
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            # S/R to Level Mapping: r1=0, r2=1, r3=2, r4=3
            # place_order(user,ins_opt,qty,float(dict_opt["r1"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r2"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r3"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]))
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            # S/R to Level Mapping: r2=0, r3=1, r4=2
            # place_order(user,ins_opt,qty,float(dict_opt["r2"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r3"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r4"]))
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 3*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            # S/R to Level Mapping: r3=0, r4=1
            # place_order(user,ins_opt,qty,float(dict_opt["r3"]))
            if 1 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[1],float(dict_opt["r4"]))
            if 2 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[2],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 3 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 4 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + 3*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(user,ins_opt,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 4*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        else:
            iLog(f"[{user['userid']}] place_option_orders_pivot(): flgMeanReversion=True, Unable to find pivots and place order for {ins_opt}")

    else:
        # Regular orders for fresh positions or new position for next strike for mean reversion
        if dict_opt["s3"] <= last_price < dict_opt["s2"] : 
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["s2"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["s1"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["pp"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r1"]))
            if 4 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[4],float(dict_opt["r2"]))
            if 5 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[5],float(dict_opt["r3"]))
        
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["s1"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["pp"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r1"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r2"]))
            if 4 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[4],float(dict_opt["r3"]))
            if 5 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[5],float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["pp"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r1"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r2"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r3"]))
            if 4 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[4],float(dict_opt["r4"]))

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["r1"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r2"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r3"]))
            if 3 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[3],float(dict_opt["r4"]))

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["r2"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r3"]))
            if 2 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[2],float(dict_opt["r4"]))

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            if 0 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[0],float(dict_opt["r3"]))
            if 1 in lst_ord_lvl_reg: place_order(user,ins_opt,qty*lst_qty_multiplier_reg[1],float(dict_opt["r4"]))

        else:
            iLog(f"[{user['userid']}] place_option_orders_fixed(): flgMeanReversion=False, Unable to find pivots and place order for {ins_opt}")



def close_all_orders(opt_index="ALL",buy_sell="ALL",ord_open_time=0):
    '''Cancel pending orders. opt_index=ALL/BANKN/NIFTY , buy_sell = ALL/BUY/SELL'''
    # print(datetime.datetime.now(),"In close_all_orders().",opt_index,flush=True)

    # Check orders to clear any non pending orders 
    # check_orders()

    #Square off (trigger SL orders to Market) for any Calls/Puts
    if opt_index in ['NIFTY_CE','NIFTY_PE','BANKN_CE','BANKN_PE']:
        for oms_order_id, value in dict_sl_orders.items():
            if value[2][2][:5]+"_"+value[2][2][-2:] == opt_index:
                # dict_sl_orders => key=order ID : value = [0-token, 1-target price, 2-instrument, 3-quantity, 4-SL Price]
                alice.modify_order(TransactionType.Sell,value[2],ProductType.Delivery,oms_order_id,OrderType.Market,value[3], 0.0)
                iLog(f"close_all_orders(): Squareoff - Triggered market order for {opt_index} with order id = {oms_order_id}")

        return

    # #Square off MIS Positions if any
    # if (opt_index[:5]=='NIFTY' or opt_index=='ALL') and nifty_ord_type == "MIS":
    #     if pos_nifty_ce > 0 :
    #         #update dict with SL order ID : [0-token, 1-target price, 2-instrument, 3-quantity, 4-SL Price]

    #         iLog(f"Closing Nifty Open Positions pos_nifty={pos_nifty_ce} - Execution Commented",2,sendTeleMsg=True)   
    #         #squareOff_MIS(TransactionType.Sell, ins_nifty_opt,pos_nifty)
    #         # needs to be managed with SL orders and cap on number of trades and MTM limit
    #     if pos_nifty_pe > 0 :
    #         iLog(f"Option position cannot be negative pos_nifty={pos_nifty_pe}",2,sendTeleMsg=True)
    #         # squareOff_MIS(TransactionType.Buy, ins_nifty_opt, abs(pos_nifty))

    # if (opt_index[:4]=='BANK'  or opt_index=='ALL') and nifty_ord_type == "MIS":
    #     if pos_bank_ce > 0 :
    #         iLog(f"Closing BankNifty Open Positions pos_bank={pos_bank_ce} - Execution Commented",2,sendTeleMsg=True)   
    #         # squareOff_MIS(TransactionType.Sell, ins_bank_opt ,pos_bank)
    #         # needs to be managed with SL orders and cap on number of trades and MTM limit
    #     if pos_bank_pe > 0 :
    #         iLog(f"Option position cannot be negative pos_bank={pos_bank}",2,sendTeleMsg=True)


    # Get pending orders and cancel them
    try:
        orders = alice.get_order_history()  #['data']['pending_orders'] #Get all orders
        if orders:
            iLog("Listing of Open orders. No orders cancelled here:")
            for ord in orders:
                if ord['Status']=='open':
                    iLog( f"ord['Trsym']={ord['Trsym']},ord['Nstordno']={ord['Nstordno']},ord['Status']={ord['Status']},ord['Qty']={ord['Qty']}")
        else:
            # print(datetime.datetime.now(),"In close_all_orders(). No Pending Orders found.",opt_index,flush=True)
            iLog("close_all_orders(): No Pending Orders found for "+ str(opt_index))
            return    
        
    except Exception as ex:
        orders = None
        # print("In close_all_orders(). Exception="+ str(ex),flush=True)
        iLog("close_all_orders(): Exception="+ str(ex),3)
        return

    if opt_index == "ALL":
        # If this proc is called in each interval, Check for order open time and leg indicator is blank for main order
        if ord_open_time > 0 :
            today = datetime.datetime.now()
            
            for c_order in orders:
                diff =  today - datetime.datetime.fromtimestamp(c_order['order_entry_time'])
                # print("diff.total_seconds()=",diff.total_seconds(), "c_order['leg_order_indicator']=",c_order['leg_order_indicator'], flush=True)
                
                if (c_order['leg_order_indicator'] == '') and  (diff.total_seconds() / 60) > ord_open_time :
                    iLog("close_all_orders(): Cancelling order due to order open limit time crossed for Ord. no. : " + c_order['oms_order_id'],sendTeleMsg=True)
                    alice.cancel_order(c_order['oms_order_id'])

        else:
            #Cancel all open orders
            iLog("close_all_orders(): Cancelling all orders now diabled temporarily.") #+ c_order['oms_order_id'])
            # alice.cancel_all_orders()
    else:
        for c_order in orders:
            #if c_order['leg_order_indicator']=='' then its actual pending order not leg order
            if opt_index == c_order['trading_symbol'][:5]:
                if buy_sell == "ALL" :
                    iLog("close_all_orders(): Cancelling order "+c_order['oms_order_id'])
                    alice.cancel_order(c_order['oms_order_id'])    

                elif buy_sell == c_order['transaction_type']:
                    iLog("close_all_orders(): Cancelling order "+c_order['oms_order_id'])
                    alice.cancel_order(c_order['oms_order_id'])


    iLog("close_all_orders(): opt_index={},buy_sell={},ord_open_time={}".format(opt_index,buy_sell,ord_open_time)) #6 = Activity/Task done

def check_MTM_Limit(user):
    ''' Checks and returns the current MTM and sets the trading flag based on the limit specified in the 
    .ini. This needs to be called before buy/sell signal generation in processing. 
    Also updates the postion counter for Nifty and bank which are used in buy/sell procs.'''
    
    global trade_banknifty, trade_nifty, pos_nifty_ce, pos_nifty_pe, pos_bank_ce, pos_bank_pe

    alice_ord = user['broker_object']
    trading_symbol = ""
    mtm = 0.0
    pos_bank_ce = 0
    pos_bank_pe = 0
    pos_nifty_ce = 0
    pos_nifty_pe = 0
    ce_pe = ""

    # Get position and mtm
    try:    # Get netwise postions (MTM)
        pos = alice_ord.get_netwise_positions()
        if pos:
            for p in  pos:
                mtm = mtm + float(p['MtoM'].replace(",",""))
                # print("get_position()",p['trading_symbol'],p['net_quantity'],flush=True)
                trading_symbol = p['Tsym'][:5]
                ce_pe = p['Tsym'][-2:]
                if trading_symbol == 'NIFTY':
                    if ce_pe == 'CE':
                        pos_nifty_ce = pos_nifty_ce + int(p['Netqty'])
                    elif ce_pe == 'PE':
                        pos_nifty_pe = pos_nifty_pe + int(p['Netqty'])

                elif trading_symbol == 'BANKN':
                    if ce_pe == 'CE':
                        pos_bank_ce = pos_bank_ce + int(p['Netqty'])
                    elif ce_pe == 'PE':
                        pos_bank_pe = pos_bank_pe + int(p['Netqty'])

                # below to be commented
                # iLog(f"check_MTM_Limit(): pos_nifty_CE={pos_nifty_ce}, pos_nifty_PE={pos_nifty_pe}, pos_bank_CE={pos_bank_ce}, pos_bank_PE={pos_bank_pe}")

    
    except Exception as ex:
        mtm = -1.0  # To ignore in calculations in case of errors
        print("check_MTM_Limit(): Exception=",ex, flush = True)
    
    # print(mtm,mtm_sl,mtm_target,flush=True)

    # Enable trade flags based on MTM limits set
    if (mtm < mtm_sl or mtm > mtm_target) and (trade_banknifty==1 or trade_nifty==1): # or mtm>mtm_target:
        trade_banknifty = 0
        trade_nifty = 0
        # Stop further trading and set both the trading flag to 0
        cfg.set("realtime","trade_nifty","0")
        cfg.set("realtime","trade_banknifty","0")

        try:
            with open(INI_FILE, 'w') as configfile:
                cfg.write(configfile)
                configfile.close()
            
            strMsg = "check_MTM_Limit(): Trade flags set to false. MTM={}, trade_nifty={}, trade_banknifty={}".format(mtm,trade_nifty,trade_banknifty)
            iLog(strMsg,6)  # 6 = Activity/Task done
            
        except Exception as ex:
            strMsg = "check_MTM_Limit(): Trade flags set to false. May be overwritten. Could not update ini file. Ex="+str(ex)
            iLog(strMsg,3)

        iLog("check_MTM_Limit(): MTM {} out of SL or Target range. Squareoff will be triggered for MIS orders...".format(mtm),2,sendTeleMsg=True)

        close_all_orders("ALL")

    return mtm

def set_config_value(section,key,value):
    '''Set the config file (.ini) value. Applicable for setting only one parameter value. 
    All parameters are string

    section=info/realtime,key,value
    '''
    cfg.set(section,key,value)
    try:
        with open(INI_FILE, 'w') as configfile:
            cfg.write(configfile)
            configfile.close()
    except Exception as ex:
        iLog("Exception writing to config. section={},key={},value={},ex={}".format(section,key,value,ex),2)

def get_option_tokens(nifty_bank="ALL"):
    '''This procedure sets the current option tokens ins_nifty_ce, ins_nifty_pe to the latest ATM tokens
    nifty_bank="NIFTY" | "BANK" | "ALL"
    '''

    iLog(f"In get_option_tokens():{nifty_bank}")

    #WIP
    global token_nifty_ce, token_nifty_pe, ins_nifty_ce, ins_nifty_pe, \
        token_bank_ce, token_bank_pe, ins_bank_ce, ins_bank_pe,\
        dict_nifty_ce, dict_nifty_pe

    # print("expiry_date=",expiry_date,flush=True)
    # print("weekly_expiry_holiday_dates=",weekly_expiry_holiday_dates,flush=True)


    if nifty_bank=="NIFTY" or nifty_bank=="ALL":
        if len(lst_nifty_ltp)>0:
          
            nifty50 = lst_nifty_ltp[-1]
            # print("nifty50=",nifty50,flush=True)

            nifty_atm = round(int(nifty50),-2)
            iLog(f"nifty_atm={nifty_atm}")

            strike_ce = float(nifty_atm + nifty_strike_ce_offset)   #OTM Options
            strike_pe = float(nifty_atm - nifty_strike_pe_offset)

            tmp_ce = alice.get_instrument_for_fno(exch="NFO",symbol='NIFTY', expiry_date=expiry_date.isoformat() , is_fut=False,strike=strike_ce, is_CE=True)
            tmp_pe = alice.get_instrument_for_fno(exch="NFO",symbol='NIFTY', expiry_date=expiry_date.isoformat() , is_fut=False,strike=strike_pe, is_CE=False)

            # Reuse if current and new ce/pe is same 
            if ins_nifty_ce!=tmp_ce:
            
                ins_nifty_ce = tmp_ce
                ins_nifty_pe = tmp_pe

                alice.subscribe([ins_nifty_ce,ins_nifty_pe])


                iLog(f"ins_nifty_ce={ins_nifty_ce}, ins_nifty_pe={ins_nifty_pe}")

                token_nifty_ce = ins_nifty_ce[1]
                token_nifty_pe = ins_nifty_pe[1]

                # print("token_nifty_ce=",token_nifty_ce,flush=True)
                # print("token_nifty_pe=",token_nifty_pe,flush=True)

                # Calculate pivot points for nitfy option CE and PE
                dict_nifty_ce = get_pivot_points(ins_nifty_ce,strike_ce)
                dict_nifty_pe = get_pivot_points(ins_nifty_pe,strike_pe)

        else:
            iLog(f"len(lst_nifty_ltp)={len(lst_nifty_ltp)}")

    if nifty_bank=="BANK" or nifty_bank=="ALL":
        if len(lst_bank_ltp)>0:
            bank50 = int(lst_bank_ltp[-1])
            # print("Bank50=",bank50,flush=True)

            bank_atm = round(int(bank50),-2)
            iLog(f"bank_atm={bank_atm}")

            strike_ce = float(bank_atm - bank_strike_ce_offset) #ITM Options
            strike_pe = float(bank_atm + bank_strike_pe_offset)

            ins_bank_ce = alice.get_instrument_for_fno(symbol = 'BANKNIFTY', expiry_date=expiry_date, is_fut=False, strike=strike_ce, is_CE = True)
            ins_bank_pe = alice.get_instrument_for_fno(symbol = 'BANKNIFTY', expiry_date=expiry_date, is_fut=False, strike=strike_pe, is_CE = False)

            alice.subscribe(ins_bank_ce, LiveFeedType.COMPACT)
            alice.subscribe(ins_bank_pe, LiveFeedType.COMPACT)
            
            iLog(f"ins_bank_ce={ins_bank_ce}, ins_bank_pe={ins_bank_pe}")

            token_bank_ce = int(ins_bank_ce[1])
            token_bank_pe = int(ins_bank_pe[1])

            # print("token_bank_ce=",token_bank_ce,flush=True)
            # print("token_bank_pe=",token_bank_pe,flush=True)
            
            # Calculate pivot points for nitfy option CE and PE
            # dict_nifty_ce = get_pivot_points(ins_nifty_ce,strike_ce)
            # dict_nifty_pe = get_pivot_points(ins_nifty_pe,strike_pe)

        else:
            iLog(f"len(lst_bank_ltp)={len(lst_bank_ltp)}")

    time.sleep(2)
    
    if nifty_bank=="NIFTY" or nifty_bank=="ALL":
        iLog(f"ltp_nifty_ATM_CE={ltp_nifty_ATM_CE}, ltp_nifty_ATM_PE={ltp_nifty_ATM_PE}")
        
        if ltp_nifty_ATM_CE<1:
            print(f"Waiting for 3 more seconds to refresh the LTP")
            time.sleep(3)
            iLog(f"ltp_nifty_ATM_CE={ltp_nifty_ATM_CE}, ltp_nifty_ATM_PE={ltp_nifty_ATM_PE}")

        dict_nifty_ce["last_price"] = ltp_nifty_ATM_CE
        dict_nifty_pe["last_price"] = ltp_nifty_ATM_PE

    if nifty_bank=="BANK" or nifty_bank=="ALL":
        iLog(f"ltp_bank_ATM_CE={ltp_bank_ATM_CE}, ltp_bank_ATM_PE={ltp_bank_ATM_PE}")  

def check_positions(user):
    '''
    1. Check positions
    2. If position exists, check overall MTM and squareoff the trade that has reached its target
    3. If position does not exist do nothing as order punching is done by strategy code
    '''
    strMsgSuffix = f"[{user['userid']}] check_positions():"

    alice_ord = user['broker_object'] 

    pos = alice_ord.get_netwise_positions() # Returns list of dicts if position is there else returns dict {'emsg': 'No Data', 'stat': 'Not_Ok'}
    if type(pos)==list:
        df_pos = pd.DataFrame(pos)[['Symbol','Tsym','Netqty','MtoM']]
        print(f"{strMsgSuffix}df_pos:=\n{df_pos}",flush=True)
        
        df_pos['mtm'] = df_pos.MtoM.str.replace(",","").astype(float)
        mtm = sum(df_pos['mtm'])
        pos_nifty = sum(pd.to_numeric(df_pos[df_pos.Symbol=='NIFTY'].Netqty))
        pos_bank = sum(pd.to_numeric(df_pos[df_pos.Symbol=='BANKNIFTY'].Netqty))

        pos_total = sum(abs(df_pos.Netqty.astype(int)))

        # ----------- Need changes for Banknifty as the lot size is 25
        net_margin_utilised = abs(pos_total/50) * nifty_avg_margin_req_per_lot
        profit_target = round(net_margin_utilised * (user['profit_target_perc']/100))

        print(f"{strMsgSuffix} net_margin_utilised={net_margin_utilised} mtm={mtm} pos_nifty={pos_nifty} pos_bank={pos_bank}")

        # Aliceblue.squareoff_positions()
        if mtm > profit_target:
            for opt in df_pos.itertuples():
                # Check if instrument options and position is sell and its mtm is greater than profit target amt
                tradingsymbol = opt.Tsym
                qty = opt.Netqty
                MtoM = float(opt.MtoM.replace(",",""))
                # # Get the partial profit booking quantity
                
                # Aliceblue.squareoff_positions('NFO',)

                # iLog(f"{strMsgSuffix} tradingsymbol={tradingsymbol} qty={qty} MtoM={MtoM} opt.ltp={opt.ltp}")
                # # Need to provision for partial profit booking
                # if (tradingsymbol[-2:] in ('CE','PE')) and (qty < 0) and (opt.mtm > opt.profit_target_amt) :
                #     # iLog(strMsgSuffix + f" Placing Squareoff order for tradingsymbol={tradingsymbol}, qty={qty}",True)
                #     place_order(kiteuser,tradingsymbol=tradingsymbol,qty=qty, transaction_type=kite.TRANSACTION_TYPE_BUY, order_type=kite.ORDER_TYPE_MARKET)
                #     kiteuser["partial_profit_booked_flg"]=1
    else:
        iLog(f"{strMsgSuffix} {pos['emsg']}",2)

def get_pivot_points(instrument,strike_price):
    '''Calculates and returns the pivot points as dict for the given instrument'''

    iLog(f"In get_pivot_points(): symbol={instrument.name}, strike_price={strike_price}")
    
    
    # from_date = datetime.date.today()-datetime.timedelta(days=25)
    # to_date = datetime.date.today()-datetime.timedelta(days=1)
    # iLog(f" from_date={from_date}, to_date={to_date}")

    from_date = datetime.datetime.now() - datetime.timedelta(days=7)
    to_date = datetime.datetime.now() - datetime.timedelta(days=1)

    try:
        dict_ohlc = pd.DataFrame(alice.get_historical(instrument, from_date, to_date, "D", False)).iloc[-1].to_dict()

    # symbol="NIFTY" symbol="BANKNIFTY"
    # df_hist_ce = get_history(symbol=symbol, start=from_date, end=to_date, index=True, option_type='CE', strike_price=strike_price,
                # expiry_date=expiry_date)[['Open','High','Low','Close']]
        # print("dict_ohlc:\n",dict_ohlc)

        # Calculate Pivot Points and update the dictionary
        last_high = dict_ohlc["high"]
        last_low = dict_ohlc["low"]
        last_close = dict_ohlc["close"]

        range = last_high - last_low
        dict_ohlc["pp"] = pp = round((last_high + last_low + last_close)/3)
        dict_ohlc["r1"] = r1 = round((2 * pp) - last_low)
        dict_ohlc["r2"] = r2 = round(pp + range)
        dict_ohlc["r3"] = r3 = round(pp + 2 * range)
        dict_ohlc["r4"] = r4 = r3 + (r3 - r2)   # ???? For r4 Check if we need to divide / 2 and then round
        dict_ohlc["s1"] = s1 = round((2 * pp) - last_high)
        dict_ohlc["s2"] = s2 = round(pp - (r1 - s1))
        dict_ohlc["s3"] = s3 = round(pp - 2 * (last_high - last_low))

        dict_ohlc["symbol"] = instrument.name
        dict_ohlc["instrument"] = instrument

        iLog(f"Pivot Points for {instrument.name} :  {s3}(s3) {s2}(s2) {s1}(s1) {pp}(pp) {r1}(r1) {r2}(r2) {r3}(r3) {r4}(r4)")

        return dict_ohlc

    except Exception as ex:
        iLog(f"Unable to fetch pivor points for token {instrument.name}. Error : {ex}")
        return {}

def strategy1_old(user):
    global strategy1_HHMM
    strategy1_HHMM = 0
    '''
    order tag = ST1
    Pivot levels based CE sell strategy
    Put trades based on the option type and strike selection and its pivots (now only for NIFTY)
    1. Check positions
    2. If position already exists
        2.1 Check if orders exists for those position , if yes do nothing
        2.2 Else get pivot points for this position symbol and place orders
    3. If position does not exist
        3.1 Place order for the current option
    '''
    iLog("In strategy1(): ")
    alice_ord = user['broker_object'] 
    option_sell_type = user['option_sell_type']

    pos = alice_ord.get_netwise_positions() # Returns list of dicts if position is there else returns dict {'emsg': 'No Data', 'stat': 'Not_Ok'}
    if type(pos)==list:
        # Existing Positions present
        iLog("strategy1(): Existing Positions found! No Order will be placed.")
        pass
    
    else:
        iLog("strategy1(): Existing Positions not found. Checking for existing Orders...")
        
        orders = alice_ord.get_order_history('')
        if type(orders)==list:
            iLog("strategy1(): Existing Orders found! No Order will be placed.")
            pass
        
        else:
            iLog("strategy1(): Existing Orders not found. New Orders will be placed...")
            get_option_tokens("NIFTY")
            if option_sell_type=='CE' or option_sell_type=='BOTH':
                print(f"dict_nifty_ce:=\n{dict_nifty_ce}",flush=True)
                iLog("strategy1(): Placing CE orders...")
                place_option_orders_pivot(user,False,dict_nifty_ce)

            if option_sell_type=='PE' or option_sell_type=='BOTH':
                print(f"dict_nifty_pe:=\n{dict_nifty_pe}",flush=True)
                iLog("strategy1(): Placing PE orders...")
                place_option_orders_pivot(user,False,dict_nifty_pe)

def strategy1(user):
    global strategy1_HHMM
    strategy1_HHMM = 0
    '''
    order tag = ST1
    Peg levels based CE sell strategy ( MO for <20 30,60,90,120,150,180)
    Put trades based on the option type and strike selection and above price levels (now only for NIFTY)
    1. Check positions
    2. If position already exists
        2.1 Check if orders exists for those position , if yes do nothing
        2.2 Else get pivot points for this position symbol and place orders
    3. If position does not exist
        3.1 Place order for the current option
    '''
    iLog("In strategy1(): ")
    alice_ord = user['broker_object'] 
    option_sell_type = user['option_sell_type']

    pos = alice_ord.get_netwise_positions() # Returns list of dicts if position is there else returns dict {'emsg': 'No Data', 'stat': 'Not_Ok'}
    if type(pos)==list:
        # Existing Positions present
        iLog("strategy1(): Existing Positions found! No Order will be placed.")
        pass
    
    else:
        iLog("strategy1(): Existing Positions not found. Checking for existing Orders...")
        
        orders = alice_ord.get_order_history('')
        if type(orders)==list:
            iLog("strategy1(): Existing Orders found! No Order will be placed.")
            pass
        
        else:
            iLog("strategy1(): Existing Orders not found. New Orders will be placed...")
            get_option_tokens("NIFTY")
            if option_sell_type=='CE' or option_sell_type=='BOTH':
                print(f"dict_nifty_ce:=\n{dict_nifty_ce}",flush=True)
                iLog("strategy1(): Placing CE orders...")
                place_option_orders_pivot(user,False,dict_nifty_ce)

            if option_sell_type=='PE' or option_sell_type=='BOTH':
                print(f"dict_nifty_pe:=\n{dict_nifty_pe}",flush=True)
                iLog("strategy1(): Placing PE orders...")
                place_option_orders_pivot(user,False,dict_nifty_pe)



def strategy2(user):
    # Do a strangle for price ~200 and keep SL of 70, add position to opposite leg when 50 SL is reached 
    global strategy2_HHMM
    strategy2_HHMM=0

    iLog("In strategy1(): ")
    # alice_ord = user['broker_object']
    # print(alice_ord) 



########################################################################
#       Alice Blue Socket Events
########################################################################
def event_handler_quote_update(message):
    global dict_ltp, lst_bank_ltp,ltp_bank_ATM_CE,ltp_bank_ATM_PE, lst_nifty_ltp, ltp_nifty_ATM_CE, ltp_nifty_ATM_PE


    feed_message = json.loads(message)
    if feed_message["t"]=='tf': 
        if(feed_message["tk"]==str(token_nifty_ce)):
            ltp_nifty_ATM_CE = float(feed_message['lp'] if 'lp' in feed_message else ltp_nifty_ATM_CE)

        if(feed_message["tk"]==str(token_nifty_pe)):
            ltp_nifty_ATM_PE = float(feed_message['lp'] if 'lp' in feed_message else ltp_nifty_ATM_PE)

        #For Nifty 50,
        if(feed_message["tk"]=="26000"):
            lst_nifty_ltp.append(float(feed_message['lp'] if 'lp' in feed_message else lst_nifty_ltp[-1]))
    
    # print(feed_message)
    
    # print(f"token_nifty_ce={token_nifty_ce}")

        # ltp_nifty_ATM_CE = float(feed_message["lp"])
        # iLog(f"ltp_nifty_ATM_CE={ltp_nifty_ATM_CE}")

    # if(message['token']==token_nifty_ce):
    #     ltp_nifty_ATM_CE=message['ltp']


    # if(message['token']==token_nifty_pe):
    #     ltp_nifty_ATM_PE=message['ltp']

    # if(message['token']==token_bank_ce):
    #     ltp_bank_ATM_CE=message['ltp']

    # if(message['token']==token_bank_pe):
    #     ltp_bank_ATM_PE=message['ltp']


            # print("len(lst_nifty_ltp)=",len(lst_nifty_ltp))
            # print(lst_nifty_ltp[-1])
            # lst_nifty_ltp.append(float(feed_message["lp"]))
            # print(lst_nifty_ltp)

    # #For BankNifty 50,
    # if(message["tk"]=="26009"):
    #     lst_bank_ltp.append(message["lp"])

    # #Update the ltp for all the tokens
    # dict_ltp.update({message['token']:message['ltp']})

def open_callback():
    global socket_opened
    socket_opened = True
    iLog("In open_callback().")
    # Call the instrument subscription
    # subscribe_ins()   # Can move to main program in case of tick discontinuation issue is not noticed
    
def error_callback(error):
    iLog(f"In error_callback().error={error}",3)
  
def close_callback():
    iLog("In close_callback().")




# Main program starts from here...

# To reuse pya3 session
# session_id = 'FjpN4X03GyLL8XUGNFhJuNJ0Cqqr3Zj765b9XqRDzJult9ThGs6OXi2VQgT3otybKyX8Ja0WMVXlxmXjYCsnMygFepe55me3hkVD7843GfnJxu6Ep7BCq9SZtE1slvU51zSCQCVoXEyWPAQyEr7VGyu2m6VI0WiT6OkAJe8JKXtdsVdyLClvK8zcQmzvm2ztenY57bFeG9oogn1I2yG2Yz1xkYBxh2yDyJbHvOGVmXXMYXi5XGvHytnck0ZuxGpj'
# alice = Aliceblue(user_id=susername,api_key=api_key,session_id=session_id)

users=[]

# Load multiple users from the .ini file, login to ant portal and maintain a userlist
for section in cfg.sections():
    user={}
    if section[0:5]=='user-':
        if  cfg.get(section, "active")=='Y':
            user['userid'] = cfg.get(section, "uid")
            user['password'] = cfg.get(section, "pwd")
            user['twofa'] = cfg.get(section, "twofa")
            user['totp_key'] = cfg.get(section, "totp_key")
            user['api_key'] = cfg.get(section, "api_key")
            user['nifty_opt_base_lot'] = int(cfg.get(section, "nifty_opt_base_lot")) 
            user['option_sell_type'] = cfg.get(section, "option_sell_type")
            user['profit_target_perc'] = int(cfg.get(section, "profit_target_perc"))
            user['loss_limit_perc'] = int(cfg.get(section, "loss_limit_perc"))
            user['profit_booking_qty_perc'] = int(cfg.get(section, "profit_booking_qty_perc"))
            user['virtual_trade'] = int(cfg.get(section, "virtual_trade"))
           

            if auto_login_totp(user):
                alice_user = Aliceblue(user_id=user['userid'], api_key=user['api_key'])
                session_id = alice_user.get_session_id()
                iLog(f"Login Successful for user {user['userid']}")
                user['broker_object'] = alice_user   # aliceblue, zerodha, kotak, icici, upstock etc
                user['broker'] = "aliceblue"
                
                users.append(user)
            else:
                iLog(f"Autologin failed for {user['userid']}")
            
            
            
# Exit if user logins failed
if len(users)==0:
    iLog(f"All user Logins failed !")
    sys.exit(0)

# print("users:")
# print(users)

# Assign alice object to the first logged in user
alice = users[0]['broker_object']


################################
# Wait till start of the market
################################
print(float(datetime.datetime.now().strftime("%H%M%S.%f")[:-3]))
while float(datetime.datetime.now().strftime("%H%M%S.%f")[:-3]) < 91459.900:
    pass


########################################################
# Code block to place orders at immediate market opening
########################################################
if int(datetime.datetime.now().strftime("%H%M")) < 916:
    # -- Temp code to sell option at a particular strike at market opening at market price
    # PUT
    strike = 24500
    qty = 75
    is_CE = False   # if CE or PE
    exp_dt = datetime.date(2025, 5, 15)
    tmp_ins = alice.get_instrument_for_fno(exch="NFO",symbol='NIFTY', expiry_date=exp_dt.isoformat() , is_fut=False,strike=strike, is_CE=is_CE)

    iLog(f"tmp_ins={tmp_ins}, exp_dt={exp_dt}")

    alice.place_order(transaction_type = TransactionType.Sell, instrument = tmp_ins,quantity = qty,order_type = OrderType.Market,
        product_type = ProductType.Normal,price = 0.0,trigger_price = None,stop_loss = None,square_off = None,trailing_sl = None,is_amo = False)

    # CALL
    strike = 25000
    qty = 75
    is_CE = True   # if CE or PE
    tmp_ins = alice.get_instrument_for_fno(exch="NFO",symbol='NIFTY', expiry_date=exp_dt.isoformat() , is_fut=False,strike=strike, is_CE=is_CE)

    iLog(f"tmp_ins={tmp_ins}")

    alice.place_order(transaction_type = TransactionType.Sell, instrument = tmp_ins,quantity = qty,order_type = OrderType.Market,
        product_type = ProductType.Normal,price = 0.0,trigger_price = None,stop_loss = None,square_off = None,trailing_sl = None,is_amo = False)


# -- Temp code
# sys.exit(0)


# cfg.set("tokens","session_id",session_id)
# with open(INI_FILE, 'w') as configfile:
#     cfg.write(configfile)
#     configfile.close()
print(f"Updated session_id at {datetime.datetime.now()}",flush=True)


# Download contracts
alice.get_contract_master("INDICES")
alice.get_contract_master("NSE")
alice.get_contract_master("NFO")

# For testing
# alice.get_contract_master("MCX")


# Get Nifty and BankNifty spot instrument object
ins_nifty = alice.get_instrument_by_symbol('INDICES', 'NIFTY 50')
ins_bank = alice.get_instrument_by_symbol('INDICES', 'NIFTY BANK')

ins_nifty_fut = alice.get_instrument_for_fno(exch="NFO",symbol='NIFTY', expiry_date=dt_next_exp.isoformat(), is_fut=True,strike=None, is_CE=False)

# ins_crude = alice.get_instrument_by_symbol('MCX', 'CRUDEOIL22NOVFUT')

# iLog(f"ins_nifty={ins_nifty}")
# iLog(f"ins_bank={ins_bank}")


# Start Websocket
iLog("Starting Websocket.",sendTeleMsg=True)

alice.start_websocket(socket_open_callback=open_callback, socket_close_callback=close_callback,
        socket_error_callback=error_callback, subscription_callback=event_handler_quote_update, run_in_background=True)


# Check with Websocket open status
while(socket_opened==False):
    pass


# Later add bank nifty support
subscribe_list = [ins_nifty]
# print("subscribe_list=",subscribe_list)

alice.subscribe(subscribe_list)
print("subscribed to subscribe_list")



# sucessfully tested order execution on multiple users below 1-July-2024
# ins_goldm=alice.get_instrument_by_symbol('MCX','GOLDM')
# place_order(users[0],ins_goldm,1,1.5)
#place_order(users[1],ins_goldm,1,1.5)


# sys.exit(0)

# alice.subscribe(ins_crude, LiveFeedType.TICK_DATA)
# print("subscried to crude")

#Temp assignment for CE/PE instrument tokens
ins_nifty_ce = ins_nifty
ins_nifty_pe = ins_nifty
ins_nifty_opt = ins_nifty

ins_bank_ce = ins_bank
ins_bank_pe = ins_bank
ins_bank_opt = ins_bank



# subscribe_ins()


# Get ATM /(+-offset) option tokens for Nifty and BankNifty
get_option_tokens("NIFTY")

iLog("Waiting for 5 seconds till websocket refreshes LTPs")
time.sleep(5)   # Sleep so that tick for the ltp gets accumulated


iLog("Starting tick processing.",sendTeleMsg=True)

strategy1_executed=0
strategy2_executed=0


# Test Area
# get_realtime_config()
# strategy1(user)
# sys.exit(0)

########################################################
####            MAIN PROGRAM START HERE ...         ####
########################################################  
# Process tick data/indicators and generate buy/sell and execute orders
cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))
while cur_HHMM > 914 and cur_HHMM<2332: # 1732
    t1 = time.time()
    
    # 1. Get realtime config changes from .ini file and reload variables
    get_realtime_config()
    
    
    # 2. Execute Strategy1
    if strategy1_HHMM==cur_HHMM and strategy1_executed==0:
        iLog(f"Triggering Strategy1 (CE and PE Sell) at {cur_HHMM}",1,True)
        for user in users:
            strategy1(user)
        strategy1_executed=1
    
    elif strategy1_HHMM != cur_HHMM:
        strategy1_executed=0

    
    # 3. Execute Strategy2
    if strategy2_HHMM==cur_HHMM and strategy2_executed==0:
        iLog(f"Triggering Strategy2 (Strangle) at {cur_HHMM}",1,True)
        for user in users:
            strategy2(user)
        strategy2_executed=1
    
    elif strategy2_HHMM != cur_HHMM:
        strategy2_executed=0
    
    
    
    # 4. Check position, MTM and square off positions if applicable 
    for user in users:
        # MTM = check_MTM_Limit(user)   # Check the logic if any can be reused, or else discard
        check_positions(user)


    # 5. Find processing time and Log only if processing takes more than 2 seconds
    t2 = time.time() - t1
    if t2 > 2.0: 
        strMsg="Processing time(secs)= {0:.2f}".format(t2)
        iLog(strMsg,2)

    # 6. Wait for the specified time interval before processing
    time.sleep(interval_seconds)   # Default 30 Seconds
    cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))
