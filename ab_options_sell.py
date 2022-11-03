# pylint: disable=unused-wildcard-import
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
# Risk Capacity     : Not applicable :-) . Always use next week expiry to be safe and if price goes above 150, switch to next expiry
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
import ab_lib
from ab_lib import *
from pya3 import *
import sys
import datetime
import time
# import threading

from nsepy import get_history






# Manual Activities to be performed
# ---------------------------------
# Frequency - Yearly, Update [Info] -> weekly_expiry_holiday_dates in .ini

# Enable logging to file
LOG_FILE = r"./log/ab_options_sell_" + datetime.datetime.now().strftime("%Y%m%d") +".log"
# sys.stdout = sys.stderr = open(LOG_FILE, "a")


######################################
#       Initialise variables
######################################
INI_FILE = "ab_options_sell.ini"              # Set .ini file name used for storing config info.
# Load parameters from the config file
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)

# read_settings_from_url = cfg.get("tokens", "read_settings_from_url").strip()
read_settings_from_url = 'https://raw.githubusercontent.com/RajeshSivadasan/mysettings/main/ab_options_sell.ini'
read_settings_from_url = ''

if len(read_settings_from_url) > 5:
    print(f"Reading settings from url file")
    pass
else:
    print(f"Reading settings from local file {INI_FILE}")
    # Set user profile; Access token and other user specific info from .ini will be pulled from this section
    ab_lib.strChatID = cfg.get("tokens", "chat_id")
    ab_lib.strBotToken = cfg.get("tokens", "options_bot_token")    #Bot include "bot" prefix in the token

    iLog(f"Initialising : {__file__}",sendTeleMsg=True)
    iLog(f"Logging info into : {LOG_FILE}")


    # crontabed this at 9.00 am instead of 8.59 
    # Set initial sleep time to match the bank market opening time of 9:00 AM to avoid previous junk values
    init_sleep_seconds = int(cfg.get("info", "init_sleep_seconds"))
    iLog(f"Setting up initial sleep time of {init_sleep_seconds} seconds.",sendTeleMsg=True)
    time.sleep(init_sleep_seconds)

    susername = cfg.get("tokens", "uid")
    spassword = cfg.get("tokens", "pwd")
    twofa = cfg.get("tokens", "twofa")
    api_secret = cfg.get("tokens", "api_secret")
    api_code = cfg.get("tokens", "api_code")
    api_key = cfg.get("tokens", "api_key")

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

    # nifty_lot_size = int(cfg.get("info", "nifty_lot_size"))

    #List of thursdays when its NSE holiday, hence reduce 1 day to get expiry date 
    weekly_expiry_holiday_dates = cfg.get("info", "weekly_expiry_holiday_dates").split(",")


    olhc_duration = int(cfg.get("info", "olhc_duration"))   #3
    # nifty_sqoff_time = int(cfg.get("info", "nifty_sqoff_time")) #1512 time after which orders not to be processed and open orders to be cancelled
    # bank_sqoff_time = int(cfg.get("info", "bank_sqoff_time")) #2310 time after which orders not to be processed and open orders to be cancelled

    nifty_tsl = int(cfg.get("info", "nifty_tsl"))   #Trailing Stop Loss for Nifty
    bank_tsl = int(cfg.get("info", "bank_tsl"))     #Trailing Stop Loss for BankNifty

    premarket_advance = int(cfg.get("info", "premarket_advance"))
    premarket_decline = int(cfg.get("info", "premarket_decline"))
    premarket_flag = int(cfg.get("info", "premarket_flag"))          # whether premarket trade enabled  or not 1=yes


    # Below 2 Are Base Flag For nifty /bank nifty trading_which is used to reset daily(realtime) flags(trade_nifty,trade_banknifty) as 
    # they might have been changed during the day in realtime 
    enable_bank = int(cfg.get("info", "enable_bank"))               # 1=Original flag for BANKNIFTY trading. Daily(realtime) flag to be reset eod based on this.  
    enable_NFO = int(cfg.get("info", "enable_NFO"))                 # 1=Original flag for Nifty trading. Daily(realtime) flag to be reset eod based on this.
    
    
    no_of_trades_limit = int(cfg.get("info", "no_of_trades_limit"))         # 2 BOs trades per order; 6 trades for 3 orders
    
    # pending_ord_limit_mins = int(cfg.get("info", "pending_ord_limit_mins")) # Close any open orders not executed beyond the set limit


    # nifty_trade_start_time = int(cfg.get("info", "nifty_trade_start_time"))
    # nifty_trade_end_time = int(cfg.get("info", "nifty_trade_end_time"))

    # sl_wait_time = int(cfg.get("info", "sl_wait_time"))
    # nifty_limit_price_low = int(cfg.get("info", "nifty_limit_price_low"))
    # nifty_limit_price_high = int(cfg.get("info", "nifty_limit_price_high"))
    # bank_limit_price_low = int(cfg.get("info", "bank_limit_price_low"))
    # bank_limit_price_high = int(cfg.get("info", "bank_limit_price_high"))



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


interval = olhc_duration        # Time interval of candles in minutes; 3 
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


############################################################################
#       Define Functions
############################################################################
def get_realtime_config():
    '''This procedure can be called during execution to get realtime values from the .ini file'''

    global trade_nifty, trade_banknifty, nifty_limit_price_offset,bank_limit_price_offset\
    ,mtm_sl,mtm_target, cfg, nifty_sl, bank_sl, export_data, sl_buffer, nifty_ord_type, bank_ord_type\
    ,nifty_strike_ce_offset, nifty_strike_pe_offset, bank_strike_ce_offset, bank_strike_pe_offset

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

def place_sl_order(main_order_id, nifty_bank, ins_opt):
    ''' 1. This procedure checks if the main_order_id is executed till the wait time is over
        2. If the main order is executed then places a StopLoss Order
        3. Checks if SL2 (enableBO2_*) is enabled, if yes places the second SL order
    nifty_bank = NIFTY | BANK '''

    iLog(f"In place_sl_order():main_order_id={main_order_id}, nifty_bank={nifty_bank}")

    lt_price = 0.0
    wait_time = sl_wait_time      # Currently set to 100 * 2 (sleep) = 200 seconds(~3 mins).  
    order_executed = False
    strMsg = ""
    
    while wait_time > 0:
        print(f"wait_time={wait_time}",flush=True)
        try:
            orders = alice.get_order_history()["data"]["completed_orders"]
            for ord in orders:
                if ord["oms_order_id"]==main_order_id:
                    # print(f"In place_sl_order(): Order Details =",ord, flush=True)
                    # Order may be rejected as well
                    if ord["order_status"]=="complete": 
                        lt_price = ord["price"]
                        order_executed = True
                        break   #break for loop
                    elif ord["order_status"]=="rejected":
                        iLog(f"Order {main_order_id} rejected. Please check funds or any other issue.",sendTeleMsg=True)
                        return   #Exit out of the procedure

        except Exception as ex:
            iLog(f"In place_sl_order(): Exception = {ex}")
        
        if order_executed : break   #break while loop

        time.sleep(2)

        wait_time = wait_time - 1

    if order_executed:
        time.sleep(2)  #As order might not be completely filled / alice blue takes time to recognise margin.
        
        if nifty_bank == "NIFTY": 
            # ins_opt =  ins_bank_opt
            bo1_qty = nifty_bo1_qty
            sl = nifty_sl
            tgt1 = nifty_tgt1
            tgt2 = nifty_tgt2
        
        elif nifty_bank == "BANK":
            # ins_opt =  ins_nifty_opt
            bo1_qty = bank_bo1_qty
            sl = bank_sl
            tgt1 = bank_tgt1
            tgt2 = bank_tgt2

        sl_price = float(lt_price-sl)
        
        #place SL order
        #---- Intraday order (MIS) , SL Order
        order = squareOff_MIS(TransactionType.Sell, ins_opt, bo1_qty, OrderType.StopLossLimit, sl_price)
        if order['status'] == 'success':
            strMsg = f"In place_sl_order(1): MIS SL1 order_id={order['data']['oms_order_id']}, StopLoss Price={sl_price}"
            #update dict with SL order ID : [0-token, 1-target price, 2-instrument, 3-quantity, 4-SL Price]
            dict_sl_orders.update({order['data']['oms_order_id']:[ins_opt[1], lt_price+tgt1, ins_opt, bo1_qty, sl_price] } )
            print("place_sl_order(1): dict_sl_orders=",dict_sl_orders, flush=True)
        else:
            strMsg = f"In place_sl_order(1): MIS SL1 Order Failed.={order['message']}" 
        
        #If second/medium range target (BO2) order is enabled then execute that
        
        if (nifty_bank == "NIFTY" and enableBO2_nifty ) or (nifty_bank == "BANK" and enableBO2_bank) :
            order = squareOff_MIS(TransactionType.Sell, ins_opt, bo1_qty, OrderType.StopLossLimit, sl_price)
            if order['status'] == 'success':
                strMsg = f"In place_sl_order(2): MIS SL2 order_id={order['data']['oms_order_id']}, StopLoss Price={sl_price}"
                #update dict with SL order ID : [0-token, 1-target price, 2-instrument, 3-quantity, 4-SL Price]
                dict_sl_orders.update({order['data']['oms_order_id']:[ins_opt[1], lt_price+tgt2, ins_opt, bo1_qty, sl_price] } )
                print("place_sl_order(2): dict_sl_orders=",dict_sl_orders, flush=True)
            else:
                strMsg = f"In place_sl_order(2): MIS SL2 Order Failed.={order['message']}"



    else:
        #cancel main order
        ret = alice.cancel_order(main_order_id)
        print("place_sl_order(): ret=alice.cancel_order()=>",ret, flush=True)
        strMsg = "place_sl_order(): main order= not executed within the wait time of 120 seconds, hence cancelled the order " + main_order_id

    iLog(strMsg,sendTeleMsg=True)

def squareOff_MIS(buy_sell,ins_scrip,qty, order_type = OrderType.Market, limit_price=0.0,order_tag= None):
    '''Square off MIS positions at EoD or when mtm limit is reached. Also used for placing Market orders. 
    buy_sell = TransactionType.Buy/TransactionType.Sell

    order_type = OrderType.StopLossLimit Default is Market order

    limit_price = limit price in case SL order needs to be placed 
    '''
    global alice

    ord_obj = {}

    if limit_price > 1 : 
        trigger_price = limit_price
    else:
        trigger_price = None

    try:
        ord_obj=alice.place_order(transaction_type = buy_sell,
                         instrument = ins_scrip,
                         quantity = qty,
                         order_type = order_type,
                         product_type = ProductType.Intraday,
                         price = limit_price,
                         trigger_price = trigger_price,
                         stop_loss = None,
                         square_off = None,
                         trailing_sl = None,
                         is_amo = False,
                         order_tag = order_tag)

        # strMsg = "In squareOff_MIS(): buy_sell={},ins_scrip={},qty={},order_type={},limit_price={}".format(buy_sell,ins_scrip,qty,order_type,limit_price)
        # iLog(strMsg,6,sendTeleMsg=True)
    
    except Exception as ex:
        iLog("Exception occured in squareOff_MIS():"+str(ex),3)

    return ord_obj

def buy_signal(ins_scrip,qty,limit_price,stop_loss_abs,target_abs,trailing_sl_abs,product_type=ProductType.Delivery):
    global alice
    #ord=
    #{'status': 'success', 'message': 'Order placed successfully', 'data': {'oms_order_id': '200416000176487'}}
    #{'status': 'error', 'message': 'Error Occurred :Trigger price cannot be greater than Limit Price', 'data': {}}
    #ord1['status']=='success'
    #print(ord['data']['oms_order_id'])
    try:
        ord_obj=alice.place_order(transaction_type = TransactionType.Buy,
                         instrument = ins_scrip,
                         quantity = qty,
                         order_type = OrderType.Limit,
                         product_type = product_type,
                         price = float(limit_price),
                         trigger_price = float(limit_price),
                         stop_loss = float(stop_loss_abs),
                         square_off = target_abs,
                         trailing_sl = trailing_sl_abs,
                         is_amo = False)
    except Exception as ex:
            # print("Exception occured in buy_signal():",ex,flush=True)
            #ord_obj={'status': 'error'} not required as api gives this in case of actual error
    #print("buy_signal():ins_scrip,qty,limit_price,stop_loss_abs,target_abs,trailing_sl_abs:",ins_scrip,qty,limit_price,stop_loss_abs,target_abs,trailing_sl_abs,flush=True)
            iLog("Exception occured in buy_signal():"+str(ex),3)

    return ord_obj

def sell_signal(ins_scrip,qty,limit_price,stop_loss_abs,target_abs,trailing_sl_abs,product_type=ProductType.Delivery):
    global alice
    try:
        ord_obj=alice.place_order(transaction_type = TransactionType.Sell,
                         instrument = ins_scrip,
                         quantity = qty,
                         order_type = OrderType.Limit,
                         product_type = product_type,
                         price = limit_price,
                         trigger_price = limit_price,
                         stop_loss = stop_loss_abs,
                         square_off = target_abs,
                         trailing_sl = trailing_sl_abs,
                         is_amo = False)
          
    except Exception as ex:
            # print("Exception occured in sell_signal():",ex,flush=True)
            iLog(f"Exception occured in sell_signal(): {ex}",3)
    #print("sell_signal():ins_scrip,qty,limit_price,stop_loss_abs,target_abs,trailing_sl_abs:",ins_scrip,qty,limit_price,stop_loss_abs,target_abs,trailing_sl_abs,flush=True)
    
    return ord_obj

def buy_nifty_options(strMsg):
   
    global df_nifty
    option_type = ""

    df_nifty.iat[-1,5] = "B"  # v1.1 set signal column value


    # strMsg == NIFTY_CE | NIFTY_PE 
    lt_price, nifty_sl = get_trade_price_options(strMsg)   # Get trade price and SL for BO1 
   
    df_nifty.iat[-1,6] = nifty_sl  # v3.7 set sl column value. This is only for BO1; rest BOs will different SLs 

    # iLog(strMsg)    #can be commented later
   
    #Warning: No initialisation done
    if strMsg == "NIFTY_CE" :
        ins_nifty_opt = ins_nifty_ce
        option_type = "CE"
    elif strMsg == "NIFTY_PE" :
        ins_nifty_opt = ins_nifty_pe
        option_type = "PE"

    strMsg = strMsg + f" {ins_nifty_opt[2]}" + " Limit Price=" + str(lt_price) + " SL=" + str(nifty_sl)

    
    if lt_price<nifty_limit_price_low or lt_price>nifty_limit_price_high :
        strMsg = strMsg + " buy_nifty(): Limit Price not in buying range."
        iLog(strMsg,2,sendTeleMsg=True)
        return
    
    if not trade_nifty:
        strMsg = strMsg + " buy_nifty(): trade_nifty=0. Order not initiated."
        iLog(strMsg,2,sendTeleMsg=True)
        return

    if not check_trade_time_zone("NIFTY"):
        strMsg = strMsg + " buy_nifty(): No trade time zone. Order not initiated."
        iLog(strMsg,2,sendTeleMsg=True)
        return
        
    if option_type == 'CE':
        if pos_nifty_pe > 0:    #Check if PE position exists and squareoff if it exits.
            close_all_orders("NIFTY_PE")

        if pos_nifty_ce > 0:
            strMsg = f"buy_nifty(): Position already exists={pos_nifty_ce}. " + strMsg    #do not buy if position already exists; 
            iLog(strMsg,sendTeleMsg=True)
            return
        
    elif option_type == 'PE':
        if pos_nifty_ce > 0:    #Check if CE position exists and squareoff if it exits.
            close_all_orders("NIFTY_CE")

        if pos_nifty_pe > 0:
            strMsg = f"buy_nifty(): Position already exists={pos_nifty_pe}. " + strMsg    #do not buy if position already exists; 
            iLog(strMsg,sendTeleMsg=True)
            return


    if trade_limit_reached("NIFTY"):
        strMsg = strMsg + "buy_nifty(): NIFTY Trade limit reached."
        iLog(strMsg,2,sendTeleMsg=True)
        return

    # Cancel pending buy orders and close existing sell orders if any
    #close_all_orders("NIFTY")  #Not required or SL can be updated to be market order
        
    if nifty_ord_type == "MIS" : 
        #---- Intraday order (MIS) , Market Order
        # order = squareOff_MIS(TransactionType.Buy, ins_nifty_opt,nifty_bo1_qty)
        # order_tag = datetime.datetime.now().strftime("NF_%H%M%S")
        
        bo1_qty = nifty_bo1_qty
        if enableBO2_nifty: 
            bo1_qty = nifty_bo1_qty*2
        
        
        order = squareOff_MIS(TransactionType.Buy, ins_nifty_opt, bo1_qty, OrderType.Limit, lt_price)
        if order['status'] == 'success':
            strMsg = strMsg + " buy_nifty(): Initiating place_sl_order(). main_order_id==" +  str(order['data']['oms_order_id'])
            iLog(strMsg,sendTeleMsg=True)   # Can be commented later
            t = threading.Thread(target=place_sl_order,args=(order['data']['oms_order_id'],"NIFTY",ins_nifty_opt,))
            t.start()

        else:
            strMsg = strMsg + ' buy_nifty(): MIS Order Failed.' + order['message']
            iLog(strMsg,sendTeleMsg=True)

    elif nifty_ord_type == "BO" :
        #---- First Bracket order for initial target
        order = buy_signal(ins_nifty_opt,nifty_bo1_qty,lt_price,nifty_sl,nifty_tgt1,nifty_tsl)    #SL to be float; 
        if order['status'] == 'success' :
            # buy_order1_nifty = order['data']['oms_order_id']
            strMsg = strMsg + " 1st BO order_id=" + str(order['data']['oms_order_id'])
        else:
            strMsg = strMsg + ' buy_nifty() 1st BO Failed.' + order['message']

        #---- Second Bracket order for open target
        if enableBO2_nifty:
            # lt_price, nifty_sl = get_trade_price("NIFTY","BUY",nifty_ord_exec_level2)   # Get trade price and SL for BO2
            order = buy_signal(ins_nifty_opt,nifty_bo2_qty,lt_price,nifty_sl,nifty_tgt2,nifty_tsl)
            strMsg = strMsg + " BO2 Limit Price=" + str(lt_price) + " SL=" + str(nifty_sl)
            if order['status'] == 'success':
                # buy_order2_nifty = order['data']['oms_order_id']
                strMsg = strMsg + " 2nd BO order_id=" + str(order['data']['oms_order_id'])
            else:
                strMsg=strMsg + ' buy_nifty() 2nd BO Failed.' + order['message']

        #---- Third Bracket order for open target
        if enableBO3_nifty:  
            # lt_price, nifty_sl = get_trade_price("NIFTY","BUY",nifty_ord_exec_level3)   # Get trade price and SL for BO3
            order = buy_signal(ins_nifty_opt,nifty_bo3_qty,lt_price,nifty_sl,nifty_tgt3,nifty_tsl)
            strMsg = strMsg + " BO3 Limit Price=" + str(lt_price) + " SL=" + str(nifty_sl)
            if order['status']=='success':
                # buy_order3_nifty = order['data']['oms_order_id']
                strMsg = strMsg + " 3rd BO order_id=" + str(order['data']['oms_order_id'])
            else:
                strMsg=strMsg + ' buy_nifty() 3rd BO Failed.' + order['message']

        iLog(strMsg,sendTeleMsg=True)

def buy_bank_options(strMsg):
    '''Buy Banknifty options '''
    global df_bank
    option_type = ""

    df_bank.iat[-1,5] = "B"  # v1.1 set signal column value


    # strMsg == CE | PE 
    lt_price, bank_sl = get_trade_price_options(strMsg)   # Get trade price and SL for BO1 
   
    df_bank.iat[-1,6] = bank_sl  # v3.7 set sl column value. This is only for BO1; rest BOs will different SLs 

    # iLog(strMsg)    #can be commented later

    #Warning: No initialisation done
    if strMsg == "BANK_CE" :
        ins_bank_opt = ins_bank_ce
        option_type = "CE"

    elif strMsg == "BANK_PE" :
        ins_bank_opt = ins_bank_pe
        option_type = "PE"
    

    strMsg = strMsg + f" {ins_bank_opt[2]}" + " Limit Price=" + str(lt_price) + " SL=" + str(bank_sl)

    
    if lt_price<bank_limit_price_low or lt_price>bank_limit_price_high :
        strMsg = strMsg + " buy_bank(): Limit Price not in buying range."
        iLog(strMsg,2,sendTeleMsg=True)
        return

    if not trade_banknifty :
        strMsg = strMsg + " buy_bank(): trade_banknifty=0. Order not initiated."
        iLog(strMsg,2,sendTeleMsg=True)
        return

    if not check_trade_time_zone("NIFTY"):
        strMsg = strMsg + " buy_bank(): No trade time zone. Order not initiated."
        iLog(strMsg,2,sendTeleMsg=True)
        return
    
    if option_type == 'CE':
        if pos_bank_ce > 0:   # Position updates in MTM check
            strMsg = f"buy_bank(): Position already exists={pos_bank_ce}. " + strMsg    #do not buy if position already exists; 
            iLog(strMsg,sendTeleMsg=True)
            return

    elif option_type == 'PE':
            if pos_bank_pe > 0:   # Position updates in MTM check
                strMsg = f"buy_bank(): Position already exists={pos_bank_pe}. " + strMsg    #do not buy if position already exists; 
                iLog(strMsg,sendTeleMsg=True)
                return


    if trade_limit_reached("BANKN"):
        strMsg = strMsg + "buy_bank(): BankNIFTY Trade limit reached."
        iLog(strMsg,2,sendTeleMsg=True)
        return

    # Cancel pending buy orders and close existing sell orders if any
    #close_all_orders("BANKN_CE")   #Not required or SL can be updated to be market order
    
    if bank_ord_type == "MIS" : 
        #---- Intraday order (MIS) , Market Order
        # order = squareOff_MIS(TransactionType.Buy, ins_bank_opt,bank_bo1_qty)
        # order_tag = datetime.datetime.now().strftime("BN_%H%M%S")
        # IF BO2 is enabled then trade quantity needs to be doubled. Two SL/TGT Orders will be placed with the below quantity 
        bo1_qty = bank_bo1_qty
        if enableBO2_bank: 
            bo1_qty = bank_bo1_qty*2
        
        order = squareOff_MIS(TransactionType.Buy, ins_bank_opt, bo1_qty, OrderType.Limit, lt_price)
        if order['status'] == 'success':
            strMsg = strMsg + " buy_bank(): Initiating place_sl_order(). main_order_id=" + str(order['data']['oms_order_id']) 
            iLog(strMsg,sendTeleMsg=True)   # Can be commented later
            t = threading.Thread(target=place_sl_order,args=(order['data']['oms_order_id'],"BANK",ins_bank_opt,))
            t.start()

        else:
            strMsg = strMsg + ' buy_bank(): MIS Order Failed.' + order['message']
            iLog(strMsg,sendTeleMsg=True)

    # BO option may not work as usually BO is disabled in alice blue for options, hence not updating the below code for BO
    elif bank_ord_type == "BO" :
        #---- First Bracket order for initial target
        order = buy_signal(ins_bank_opt,bank_bo1_qty,lt_price,bank_sl,bank_tgt1,bank_tsl)    #SL to be float; 
        if order['status'] == 'success' :
            # buy_order1_bank = order['data']['oms_order_id']
            strMsg = strMsg + " 1st BO order_id=" + str(order['data']['oms_order_id'])
        else:
            strMsg = strMsg + ' buy_bank() 1st BO Failed.' + order['message']

        #---- Second Bracket order for open target
        if enableBO2_bank:
            # lt_price, bank_sl = get_trade_price("NIFTY","BUY",bank_ord_exec_level2)   # Get trade price and SL for BO2
            order = buy_signal(ins_bank_opt,bank_bo2_qty,lt_price,bank_sl,bank_tgt2,bank_tsl)
            strMsg = strMsg + " BO2 Limit Price=" + str(lt_price) + " SL=" + str(bank_sl)
            if order['status'] == 'success':
                # buy_order2_bank = order['data']['oms_order_id']
                strMsg = strMsg + " 2nd BO order_id=" + str(order['data']['oms_order_id'])
            else:
                strMsg=strMsg + ' buy_bank() 2nd BO Failed.' + order['message']

        #---- Third Bracket order for open target
        if enableBO3_bank:  
            # lt_price, bank_sl = get_trade_price("NIFTY","BUY",bank_ord_exec_level3)   # Get trade price and SL for BO3
            order = buy_signal(ins_bank_opt,bank_bo3_qty,lt_price,bank_sl,bank_tgt3,bank_tsl)
            strMsg = strMsg + " BO3 Limit Price=" + str(lt_price) + " SL=" + str(bank_sl)
            if order['status']=='success':
                # buy_order3_bank = order['data']['oms_order_id']
                strMsg = strMsg + " 3rd BO order_id=" + str(order['data']['oms_order_id'])
            else:
                strMsg=strMsg + ' buy_bank() 3rd BO Failed.' + order['message']

        iLog(strMsg,sendTeleMsg=True)

def subscribe_ins():
    try:
        if trade_nifty : 
            alice.subscribe(ins_nifty, LiveFeedType.TICK_DATA)
            alice.subscribe(ins_nifty_ce, LiveFeedType.TICK_DATA)
            alice.subscribe(ins_nifty_pe, LiveFeedType.TICK_DATA)
            iLog(f"subscribed to {ins_nifty}, {ins_nifty_ce}, {ins_nifty_pe} ")

        if trade_banknifty : 
            alice.subscribe(ins_bank, LiveFeedType.TICK_DATA)
            alice.subscribe(ins_bank_ce, LiveFeedType.TICK_DATA)
            alice.subscribe(ins_bank_pe, LiveFeedType.TICK_DATA)
            iLog(f"subscribed to {ins_bank}, {ins_bank_ce}, {ins_bank_pe} ")

    except Exception as ex:
        iLog("subscribe_ins(): Exception="+ str(ex),3)

    iLog("subscribe_ins().")

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

def check_MTM_Limit():
    ''' Checks and returns the current MTM and sets the trading flag based on the limit specified in the 
    .ini. This needs to be called before buy/sell signal generation in processing. 
    Also updates the postion counter for Nifty and bank which are used in buy/sell procs.'''
    
    global trade_banknifty, trade_nifty, pos_nifty_ce, pos_nifty_pe, pos_bank_ce, pos_bank_pe

    trading_symbol = ""
    mtm = 0.0
    pos_bank_ce = 0
    pos_bank_pe = 0
    pos_nifty_ce = 0
    pos_nifty_pe = 0
    ce_pe = ""

    # Get position and mtm
    try:    # Get netwise postions (MTM)
        pos = alice.get_netwise_positions()
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

def get_trade_price_options(bank_nifty):
    '''Returns the trade price and stop loss abs value for bank/nifty=CRUDE/NIFTY
    buy_sell=BUY/SELL, bo_level or Order execution level = 1(default means last close),2,3 and 0 for close -1 for market order
    '''

    iLog(f"In get_trade_price_options():{bank_nifty}")

    lt_price = 0.0

    # atr = 0
    sl = nifty_sl

    # Refresh the tokens and ltp
    if bank_nifty == "NIFTY_CE" or bank_nifty == "NIFTY_PE":
        get_option_tokens("NIFTY")
    elif bank_nifty == "BANK_CE" or bank_nifty == "BANK_PE":
        get_option_tokens("BANK")

    # 1. Set default limit price, below offset can be parameterised
    if bank_nifty == "NIFTY_CE" :
        lt_price = int(ltp_nifty_ATM_CE) + nifty_limit_price_offset # Set Default trade price
    elif bank_nifty == "NIFTY_PE" :
        lt_price = int(ltp_nifty_ATM_PE) + nifty_limit_price_offset # Set Default trade price
    elif bank_nifty == "BANK_CE" :
        lt_price = int(ltp_bank_ATM_CE) + bank_limit_price_offset
    elif bank_nifty == "BANK_PE" :
        lt_price = int(ltp_bank_ATM_PE) + bank_limit_price_offset
    else:
        print("get_trade_price_options1",flush=True)
    
    lt_price = float(lt_price)
    print("get_trade_price_options(): lt_price={}".format(lt_price),flush=True)
    
    return lt_price, sl

def trade_limit_reached(bank_nifty="NIFTY"):
    # Check if completed order can work here
    '''Check if number of trades reached/crossed the parameter limit . Return true if reached or crossed else false.
     Dont process the Buy/Sell order if returns true
     bank_nifty=CRUDE/NIFTY '''
    
    trades_cnt = 0  # Number of trades, needs different formula in case of nifty / bank
    buy_cnt = 0
    sell_cnt = 0

    try:
        trade_book = alice.get_trade_book()
        if len(trade_book['data']) == 0 :
            return False        # No Trades
        else:
            trades = trade_book['data']['trades'] #Get all trades
    
    except Exception as ex:
        iLog("trade_limit_reached(): Exception="+ str(ex),3)
        return True     # To be safe in case of exception

    if not trades:
        iLog("trade_limit_reached(): No Trades found for "+ str(bank_nifty))
        return False        # No trades, hence go ahead

    for c_trade in trades:
        if bank_nifty == c_trade['trading_symbol'][:5]:
            if c_trade['transaction_type'] == "BUY" :
                buy_cnt = buy_cnt + 1
            elif c_trade['transaction_type'] == "SELL" :
                 sell_cnt = sell_cnt + 1

    iLog(f"trade_limit_reached(): buy_cnt={buy_cnt}, sell_cnt={sell_cnt}")            
    
    if buy_cnt > sell_cnt:
        trades_cnt = buy_cnt
    else:
        trades_cnt = sell_cnt

    if trades_cnt >= no_of_trades_limit:
        return True
    else:
        return False

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

def check_trade_time_zone(bank_nifty="NIFTY"):
    result = False

    cur_time = int(datetime.datetime.now().strftime("%H%M"))

    # if bank_nifty=="CRUDE" and (cur_time > curde_trade_start_time and cur_time < curde_trade_end_time) :
    #     result = True

    if bank_nifty=="NIFTY" and (cur_time > nifty_trade_start_time and cur_time < nifty_trade_end_time) :
        result = True

    return result

def get_option_tokens(nifty_bank="ALL"):
    '''This procedure sets the current option tokens to the latest ATM tokens
    nifty_bank="NIFTY" | "BANK" | "ALL"
    '''

    iLog(f"In get_option_tokens():{nifty_bank}")

    #WIP
    global token_nifty_ce, token_nifty_pe, ins_nifty_ce, ins_nifty_pe, \
        token_bank_ce, token_bank_pe, ins_bank_ce, ins_bank_pe



    # print("expiry_date=",expiry_date,flush=True)
    # print("weekly_expiry_holiday_dates=",weekly_expiry_holiday_dates,flush=True)



    if nifty_bank=="NIFTY" or nifty_bank=="ALL":
        if len(lst_nifty_ltp)>0:
          
            nifty50 = lst_nifty_ltp[-1]
            # print("nifty50=",nifty50,flush=True)

            nifty_atm = round(int(nifty50),-2)
            iLog(f"nifty_atm={nifty_atm}")

            strike_ce = float(nifty_atm - nifty_strike_ce_offset)   #ITM Options
            strike_pe = float(nifty_atm + nifty_strike_pe_offset)

            ins_nifty_ce = alice.get_instrument_for_fno(exch="NFO",symbol='NIFTY', expiry_date=expiry_date.isoformat() , is_fut=False,strike=strike_ce, is_CE=True)
            ins_nifty_pe = alice.get_instrument_for_fno(exch="NFO",symbol='NIFTY', expiry_date=expiry_date.isoformat() , is_fut=False,strike=strike_pe, is_CE=False)

            alice.subscribe([ins_nifty_ce,ins_nifty_pe])

           
            iLog(f"ins_nifty_ce={ins_nifty_ce}, ins_nifty_pe={ins_nifty_pe}")

            token_nifty_ce = ins_nifty_ce[1]
            token_nifty_pe = ins_nifty_pe[1]

            # print("token_nifty_ce=",token_nifty_ce,flush=True)
            # print("token_nifty_pe=",token_nifty_pe,flush=True)

            # Calculate pivot points for nitfy option CE and PE
            calculate_pivot('NIFTY',strike_ce)

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

        else:
            iLog(f"len(lst_bank_ltp)={len(lst_bank_ltp)}")

    time.sleep(2)
    
    if nifty_bank=="NIFTY" or nifty_bank=="ALL":
        iLog(f"ltp_nifty_ATM_CE={ltp_nifty_ATM_CE}, ltp_nifty_ATM_PE={ltp_nifty_ATM_PE}")        
    
    if nifty_bank=="BANK" or nifty_bank=="ALL":
        iLog(f"ltp_bank_ATM_CE={ltp_bank_ATM_CE}, ltp_bank_ATM_PE={ltp_bank_ATM_PE}")  

def check_orders():
    ''' 1. Checks for pending SL orders and update/maintain local sl order dict 
        2. Updates SL order to target price if reached
        2.1 Update SL order target price and trigger price to TSL, ltp - tsl used to find new SL price and not ltp - (tsl+sl)
    '''
    # iLog("In check_orders()")   # can be disabled later to reduce logging  

    #1 Remove completed orders/keep only pending orders from the SL orders dict
    try:
        orders = alice.get_order_history()['data']['pending_orders']
        if orders:
            # iLog(f"check_orders():orders={orders}\n dict_sl_orders={dict_sl_orders}")   #To be commented later
            # loop through Sl orders dict and check if its in the pending order list 
            for key, value in dict_sl_orders.items():
                order_found = False
                for order in orders:
                    if key == order['oms_order_id']:
                        order_found = True
                        break
                
                # remove the order from sl dict which is not pending
                if not order_found:
                    dict_sl_orders.pop(key)
                    iLog(f"In check_orders(): Removed order {key} from dict_sl_orders")
        
        else:
            dict_sl_orders.clear()
        
    except:
        pass
    
    
    # print("dict_ltp=",dict_ltp,flush=True)

    #2. Check the current price of the SL orders and if they are above tgt modify them to target price
    # dict_sl_orders => key=order ID : value = [0-token, 1-target price, 2-instrument, 3-quantity, 4-SL Price]
    tsl = bank_tsl  #+ bank_sl
    # iLog(f"tsl={tsl}")
    for oms_order_id, value in dict_sl_orders.items():
        
        ltp = dict_ltp[value[0]]
        if value[2][2][:5]=="BANKN":    #Check if the instrument is nifty or banknifty and get the tsl accordingly
            tsl = bank_tsl
        else:
            tsl = nifty_tsl
        
        iLog(f"In check_orders(): oms_order_id={oms_order_id}, ltp={ltp}, Target={float(value[1])}, bank_tsl={bank_tsl}, SL Price={float(value[4])}")
        #Set Target Price : current ltp > target price
        if ltp > value[1] :
            try:
                alice.modify_order(TransactionType.Sell,value[2],ProductType.Intraday,oms_order_id,OrderType.Limit,value[3], price=float(value[1]))
                iLog(f"In check_orders(): BullsEye! Target price for OrderID {oms_order_id} modified to {value[1]}")
            
            except Exception as ex:
                iLog("In check_orders(): Exception occured during Target price modification = " + str(ex),3)

        #Set StopLoss(TargetPrice) to Trailing SL
        elif (ltp - value[4]) > tsl :
            tsl_price = float(int(ltp - tsl))
            try:
                alice.modify_order(TransactionType.Sell,value[2],ProductType.Intraday,oms_order_id,OrderType.StopLossLimit,value[3], tsl_price,tsl_price )
                #Update dictionary with the new SL price
                dict_sl_orders.update({oms_order_id:[value[0], value[1], value[2], value[3],tsl_price]} )
                iLog(f"In check_orders(): TSL for OrderID {oms_order_id} modified to {tsl_price}")
                # \n dict_sl_orders={dict_sl_orders}
            except Exception as ex:
                iLog("In check_orders(): Exception occured during TSL modification = " + str(ex),3)

def calculate_pivot(symbol,strike_price):
    '''Calculates and sets the pivot points for Nifty'''

    iLog(f"symbol,strike_price={symbol},{strike_price}")

    from_date = datetime.date.today()-datetime.timedelta(days=5)
    to_date = datetime.date.today()-datetime.timedelta(days=1)

    # symbol="NIFTY" symbol="BANKNIFTY"
    df_hist_ce = get_history(symbol=symbol, start=from_date, end=to_date, index=True, option_type='CE', strike_price=strike_price,
                expiry_date=expiry_date)[['Open','High','Low','Close']]

    iLog("df_hist_ce=")
    iLog(df_hist_ce)
    
    nifty_opt_ce_last_high = df_hist_ce.iloc[-1].High
    nifty_opt_ce_last_low = df_hist_ce.iloc[-1].Low
    nifty_opt_ce_last_close = df_hist_ce.iloc[-1].Close

    nifty_opt_ce_range = nifty_opt_ce_last_high - nifty_opt_ce_last_low
    nifty_opt_ce_pp = round((nifty_opt_ce_last_high + nifty_opt_ce_last_low + nifty_opt_ce_last_close)/3)
    nifty_opt_ce_r1 = round((2 * nifty_opt_ce_pp) - nifty_opt_ce_last_low)
    nifty_opt_ce_r2 = round(nifty_opt_ce_pp + nifty_opt_ce_range)
    nifty_opt_ce_r3 = round(nifty_opt_ce_pp + 2 * nifty_opt_ce_range)
    # ???? Check if we need to divide / 2 and then round
    nifty_opt_ce_r4 = nifty_opt_ce_r3 + round((nifty_opt_ce_r3 - nifty_opt_ce_r2))  

    iLog(f"Pivot Points for {symbol}{strike_price}:")
    iLog(f"{nifty_opt_ce_pp}, {nifty_opt_ce_r1}, {nifty_opt_ce_r2}, {nifty_opt_ce_r3}, {nifty_opt_ce_r4}")

########################################################################
#       Alice Blue Socket Events
########################################################################
def event_handler_quote_update(message):
    global dict_ltp, lst_bank_ltp,ltp_bank_ATM_CE,ltp_bank_ATM_PE, lst_nifty_ltp, ltp_nifty_ATM_CE, ltp_nifty_ATM_PE


    feed_message = json.loads(message)
    # print(feed_message)
    
    # print(f"token_nifty_ce={token_nifty_ce}")
    if(feed_message["tk"]==str(token_nifty_ce)):
        print(feed_message)
        ltp_nifty_ATM_CE = float(feed_message['lp'] if 'lp' in feed_message else ltp_nifty_ATM_CE)
        # ltp_nifty_ATM_CE = float(feed_message["lp"])
        iLog(f"ltp_nifty_ATM_CE={ltp_nifty_ATM_CE}")

    # if(message['token']==token_nifty_ce):
    #     ltp_nifty_ATM_CE=message['ltp']


    # if(message['token']==token_nifty_pe):
    #     ltp_nifty_ATM_PE=message['ltp']

    # if(message['token']==token_bank_ce):
    #     ltp_bank_ATM_CE=message['ltp']

    # if(message['token']==token_bank_pe):
    #     ltp_bank_ATM_PE=message['ltp']

    #For Nifty 50, 
    if(feed_message["tk"]=="26000"):
        print("len(lst_nifty_ltp)=",len(lst_nifty_ltp))
        # print(lst_nifty_ltp[-1])
        lst_nifty_ltp.append(float(feed_message['lp'] if 'lp' in feed_message else lst_nifty_ltp[-1]))
        # lst_nifty_ltp.append(float(feed_message["lp"]))
        print(lst_nifty_ltp)

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
iLog("User = " + susername)
#print(str(datetime.datetime.now().strftime("%H:%M:%S")) + ' : '+susername,flush=True)

# pya3
alice = Aliceblue(user_id=susername,api_key=api_key)
session_id = alice.get_session_id() # Get Session ID

# To reuse pya3 session
# session_id = 'FjpN4X03GyLL8XUGNFhJuNJ0Cqqr3Zj765b9XqRDzJult9ThGs6OXi2VQgT3otybKyX8Ja0WMVXlxmXjYCsnMygFepe55me3hkVD7843GfnJxu6Ep7BCq9SZtE1slvU51zSCQCVoXEyWPAQyEr7VGyu2m6VI0WiT6OkAJe8JKXtdsVdyLClvK8zcQmzvm2ztenY57bFeG9oogn1I2yG2Yz1xkYBxh2yDyJbHvOGVmXXMYXi5XGvHytnck0ZuxGpj'
# alice = Aliceblue(user_id=susername,api_key=api_key,session_id=session_id)

# Krishnavelu
# Get session id
# session_id = AliceBlue.login_and_get_sessionID(username=susername, password=spassword, twoFA = twofa,app_id = api_code,api_secret = api_secret)
# session_id='pb23iGBuPeCntXLvZUBkjiE9ODYuMLPhR2YHCuDtEMgaIte2OKWoV56peXCr3g5vug6YYd1ESuIeUEzfWLZEicPmH3sPZENyvxQotDMSgIyszrg8FKDRv54aGzpLI4nhdrAQtpm2TbajetoFd45vptTkFqVSQUyAye8pqnaRsa4Z8sI3TZ253mac9qW2JW47IxGsWY9gJqsL82kdk44Rx4XPGYaj0H1ycsBRiYQHoMaCTQlCaShITB1Zj9xhsf4R'

# use session id to create alice object, Connect to AliceBlue and download contracts
# alice = AliceBlue(username = susername,session_id = session_id, master_contracts_to_download=['NFO','NSE','MCX'])
# alice = AliceBlue(username = susername,session_id = session_id)


iLog(f"session_id={session_id}")

alice.get_contract_master("INDICES")
alice.get_contract_master("NSE")
alice.get_contract_master("NFO")


# Get Nifty and BankNifty spot instrument object
ins_nifty = alice.get_instrument_by_symbol('INDICES', 'NIFTY 50')
ins_bank = alice.get_instrument_by_symbol('INDICES', 'NIFTY BANK')

# ins_crude = alice.get_instrument_by_symbol('MCX', 'CRUDEOIL22NOVFUT')

iLog(f"ins_nifty={ins_nifty}")
iLog(f"ins_bank={ins_bank}")


# Start Websocket
iLog("Starting Websocket.",sendTeleMsg=True)


alice.start_websocket(socket_open_callback=open_callback, socket_close_callback=close_callback,
                      socket_error_callback=error_callback, subscription_callback=event_handler_quote_update, run_in_background=True)

# alice.start_websocket(subscribe_callback=event_handler_quote_update,
#                     socket_open_callback=open_callback,
#                     socket_close_callback=close_callback,
#                     socket_error_callback=error_callback)


# alice.start_websocket(subscribe_callback=event_handler_quote_update,socket_open_callback=open_callback)

# Check with Websocket open status
while(socket_opened==False):
    pass



subscribe_list = [ins_nifty]
print("subscribe_list=",subscribe_list)

alice.subscribe(subscribe_list)
print("subscried to nifty")

# alice.subscribe(ins_crude, LiveFeedType.TICK_DATA)
# print("subscried to crude")

#Temp assignment for CE/PE instrument tokens
ins_nifty_ce = ins_nifty
ins_nifty_pe = ins_nifty
ins_nifty_opt = ins_nifty

ins_bank_ce = ins_bank
ins_bank_pe = ins_bank
ins_bank_opt = ins_bank



# Subscribe to Nifty50
# alice.subscribe(ins_nifty,LiveFeedType.TICK_DATA)

# # Get instrument of Nifty ATM Option
# ins_nifty50 = alice.get_instrument_by_symbol('NSE', 'Nifty 50')     #Instead of futures get Nifty 50 Index price 
# print(ins_nifty50,flush=True)
# alice.subscribe(ins_nifty50, LiveFeedType.COMPACT)

time.sleep(5)   # Sleep so that tick for the ltp gets accumulated

# subscribe_ins()

# Get next week Expiry date
expiry_date = datetime.date.today() + datetime.timedelta(((3-datetime.date.today().weekday()) % 7)+7)
# Reduce one day if thurshday is a holiday
if str(expiry_date) in weekly_expiry_holiday_dates :
    expiry_date = expiry_date - datetime.timedelta(days=1)


iLog(f"expiry_date={expiry_date}")

# Get ATM /(+-offset) option tokens for Nifty and BankNifty
get_option_tokens("NIFTY")

# iLog("Done")
# close_all_orders('NIFTY_CE')
# sys.exit(0)


iLog("Starting tick processing.",sendTeleMsg=True)




########################################################
####            MAIN PROGRAM START HERE ...         ####
########################################################  
# Process tick data/indicators and generate buy/sell and execute orders
while True:
    # Process as per start of market timing
    cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))
    print("cur_HHMM=",cur_HHMM,flush=True)

    if cur_HHMM > 914:

        cur_min = datetime.datetime.now().minute 

        # Below if block will run after every time interval specified in the .ini file
        if( cur_min % interval == 0 and flg_min != cur_min):

            flg_min = cur_min     # Set the minute flag to run the code only once post the interval
            t1 = time.time()      # Set timer to record the processing time of all the indicators
            
            # Can include the below code to work in debug mode only
            strMsg = "BN=" + str(len(lst_bank_ltp))
            # if len(df_bank.index) > 0 : strMsg = strMsg + " "+str(df_bank.close.iloc[-1]) 

            strMsg = strMsg +  " N="+ str(len(lst_nifty_ltp))
            # if len(df_nifty.index) > 0 : strMsg = strMsg + " "+str(df_nifty.close.iloc[-1]) 


            # Check MTM and stop trading if limit reached; This can be parameterised to % gain/loss
            MTM = check_MTM_Limit()
           
            
            if len(lst_bank_ltp) > 1:       # BANKNIFTY Candle
                tmp_lst = lst_bank_ltp.copy()  # Copy the ticks to a temp list
                lst_bank_ltp.clear()           # Reset the ticks list; There can be gap in the ticks during this step ???
                #print(f"CRUDE: cur_min = {cur_min},len(tmp_lst)={len(tmp_lst)},i={i}",flush=True)
                #Formation of candle
                df_bank.loc[df_bank_cnt, df_cols]=[cur_HHMM, tmp_lst[0], max(tmp_lst), min(tmp_lst), tmp_lst[-1],"",0]
                df_bank_cnt = df_bank_cnt + 1 
                # open = df_bank.close.tail(3).head(1)  # First value  
                strMsg = strMsg + " " + str(round(tmp_lst[-1]))      #Crude close 

                    
            if len(lst_nifty_ltp) > 1:       # Nifty Candle
                tmp_lst = lst_nifty_ltp.copy()  # Copy the ticks to a temp list
                lst_nifty_ltp.clear()           # Reset the ticks list
                # print(f"NIFTY: cur_min = {cur_min},len(tmp_lst)={len(tmp_lst)}",flush=True)
                # Formation of candle
                df_nifty.loc[df_nifty_cnt,df_cols] = [cur_HHMM,tmp_lst[0],max(tmp_lst),min(tmp_lst),tmp_lst[-1],"",0]
                df_nifty_cnt = df_nifty_cnt + 1
                strMsg = strMsg + " " + str(round(tmp_lst[-1]))      #Nifty close

            # Get realtime config changes from .ini file and reload variables
            get_realtime_config()

            strMsg = strMsg + f" POS(n,bn)=({pos_nifty_ce+pos_nifty_pe}, {pos_bank_ce+pos_bank_pe}), MTM={MTM}" 
            iLog(strMsg,sendTeleMsg=True)



            # ############## BANKNIFTY Order Generation #########################
            if df_bank_cnt > 6 : 

                # Logic for Buy/Sell will go here
                strMsg=f"BankNifty: #={df_bank_cnt}, ltp_bank_ATM_CE={ltp_bank_ATM_CE}, ltp_bank_ATM_PE={ltp_bank_ATM_PE}"
                iLog(strMsg)

      
            # ////////////// NIFTY Order Generation //////////////////////////
            if df_nifty_cnt > 6 : 

                strMsg=f"Nifty: #={df_nifty_cnt}, ltp_nifty_ATM_CE={ltp_nifty_ATM_CE}, ltp_nifty_ATM_PE={ltp_nifty_ATM_PE}"
                iLog(strMsg)





            #-- Find processing time and Log only if processing takes more than 2 seconds
            t2 = time.time() - t1
            if t2 > 2.0: 
                strMsg="Processing time(secs)= {0:.2f}".format(t2)
                iLog(strMsg,2)


 

        if cur_HHMM > 1530 and cur_HHMM < 1532 :   # Exit the program post NSE closure
            # Reset trading flag for bank if bank is enabled on the instance
            if enable_bank : 
                iLog("Enabling BankNifty trading...")
                set_config_value("realtime","trade_banknifty","1")
            
            # Reset trading flag for nifty if nifty is enabled on the instance
            if enable_NFO : 
                iLog("Enabling NFO trading...")
                set_config_value("realtime","trade_nifty","1")
        
            iLog("Closing down... Calling sys.exit() @ " + str(cur_HHMM),sendTeleMsg=True)
            sys.exit(0)
   

            
            # #-- Cancel all open Crude orders after 11:10 PM, time can be parameterised
            # if cur_HHMM > bank_sqoff_time and not processCrudeEOD:
            #     close_all_orders('CRUDE')
            #     processCrudeEOD = True

           
            #-- Check if any open order greater than pending_ord_limit_mins and cancel the same 
            close_all_orders(ord_open_time=pending_ord_limit_mins)

    time.sleep(9)   # May be reduced to accomodate the processing delay

    check_orders()  # Checks SL orders and sets target, should be called every 10 seconds. check logs
