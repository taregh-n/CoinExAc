from coinex.coinex import CoinEx
import os
import sqlite3
import requests
import json
from ctypes import windll, byref
from ctypes.wintypes import SMALL_RECT
import platform
from sys import exit
import subprocess

WindowsSTDOUT = windll.kernel32.GetStdHandle(-11)
dimensions = SMALL_RECT(0, 0, 54, 33) # (left, top, right, bottom)
# Width = (Right - Left) + 1; Height = (Bottom - Top) + 1
windll.kernel32.SetConsoleWindowInfo(WindowsSTDOUT, True, byref(dimensions)) 

# Make DataBase ---------------------------------
cnx = sqlite3.connect('Data.db')
curser = cnx.cursor()
curser.execute('''CREATE TABLE IF NOT EXISTS trades 
                  (crypto text, price real, amount real)''')
cnx.commit()
cnx.close()
cnx = sqlite3.connect('Data.db')
curser = cnx.cursor()
curser.execute('''CREATE TABLE IF NOT EXISTS CoinEX_Access 
                  (user text, ACCESS_ID text, SECRET_KEY text)''')
cnx.commit()
cnx.close()

# Functions -------------------------------------
def ping(host):
    param = '-n' if platform.system().lower()=='windows' else '-c'
    command = ['ping', param, '1', host]
    return subprocess.call(command) == 0 
    
def getOnlinePortfo():
    for key in crypto_keys:
        crypto_amount = float(online_portfo[key]['available'])
        if key != 'USDT':
            crypUSDT = key + 'USDT'
            last_price = float(coinex.market_ticker(crypUSDT)['ticker']['last'])
            crypto_value = crypto_amount * last_price
            print(' %s: %f (%.2f USDT)' % (key, crypto_amount , crypto_value))
        else:
            print(' %s: %f' % (key, crypto_amount))

def update():
    cnx = sqlite3.connect('Data.db')
    curser = cnx.cursor()
    curser.execute('SELECT crypto FROM trades')
    saved_cryptos = [crypto[0] for crypto in curser]
    new_crypos = list(set(crypto_keys) - set(saved_cryptos))
    if 'USDT' in new_crypos:
        new_crypos.remove('USDT')
    if len(new_crypos) > 0:
        print('You have %i new crypto(s) in your CoinEx portfo.' % len(new_crypos))
        print('If you don\'t want to save it enter "skip".')
        for crypto in new_crypos:
            amount = float(online_portfo[crypto]['available'])
            price = input('At what price did you buy %s? ' % crypto)
            if price != 'skip':
                curser.execute('INSERT INTO trades VALUES (\'%s\' , %f , %f)' % (crypto, float(price), amount))
                cnx.commit()
    cnx.close()  
    print('\n * Informations is up to date.') 

def addPosition(crypto, price, amount):
    cnx = sqlite3.connect('Data.db')
    curser = cnx.cursor()
    curser.execute('INSERT INTO trades VALUES (\'%s\' , %f , %f)' % (crypto, price, amount))
    cnx.commit()
    cnx.close()
    print('OK')

def deletePosition(crypto):
    cnx = sqlite3.connect('Data.db')
    curser = cnx.cursor()
    curser.execute('DELETE FROM trades WHERE crypto = \'%s\'' % crypto)
    cnx.commit()
    cnx.close()
    print('OK')

def showInformations():
    print('''====================================================
                    Informations                
----------------------------------------------------''')
    cnx = sqlite3.connect('Data.db')
    curser = cnx.cursor()
    curser.execute('SELECT * FROM trades')
    if len([crypto[0] for crypto in curser]) > 0:
        print(' your profit in open trades: ')
        curser.execute('SELECT * FROM trades')   
        for crypto, price, amount in curser:
            cryptoUSDT = crypto + 'USDT'
            last = float(coinex.market_ticker(cryptoUSDT)['ticker']['last'])
            current_value = last * amount
            if price != 0:
                investment = price * amount
                profit = (current_value - investment) / investment * 100
                print (' %s: %.4f ' % (crypto, profit) + "%")
            else:
                profit = 0
                print (' %s: Unknown (You don\'t enter buy price)' % (crypto))
            print()
    print(' Your online portfolio is: ')
    getOnlinePortfo()
    print()
    crypto_list = list(crypto_keys)
    if 'USDT' in crypto_list:
        crypto_list.remove('USDT')
        USDT_value = float(online_portfo['USDT']['available'])
    else:
        USDT_value = 0
    for crypto in crypto_list:
        crypto_amount = float(online_portfo[crypto]['available'])
        cryptoUSDT = crypto + 'USDT'
        last_price = float(coinex.market_ticker(cryptoUSDT)['ticker']['last'])
        crypto_value = last_price * crypto_amount
        USDT_value += crypto_value
    print (' total current value is: %.2f USDT' % USDT_value)
    print(' Or:', int(USDT_value * getBestBuyOrder()), 'Tomans')
    print(' Best USDT buy order in Nobitex.ir is: ' , getBestBuyOrder(), 'Tomans')
    print('----------------------------------------------------')
    cnx.close()

def editBuyPrice(crypto, price):
    cnx = sqlite3.connect('Data.db')
    curser = cnx.cursor()
    curser.execute('UPDATE trades SET price = %f WHERE crypto = \'%s\'' % (price, crypto))
    cnx.commit()
    cnx.close()
    print('OK')

def getBestBuyOrder():
    rec = requests.post('https://api.nobitex.ir/v2/orderbook', data = {'symbol' : 'USDTIRT'})
    orders = json.loads(rec.content)
    bestBuyOrder = int(orders['asks'][1][0])
    return int(bestBuyOrder / 10)

def helpMe():
    print('''====================================================
                        Help
----------------------------------------------------
   - show      Show Informations.
   - update    Update data from your CoinEx account.
   - add       Add new trade details.
   - del       Delete a trade that closed.
   - edit      Edit buy price of a crypto.
   - exit      Close the program.
   - help      Show help.
----------------------------------------------------''')

# Program -------------------------------------
while True:
    if ping('8.8.8.8'):
        print('\n * Internet connection is ok.')
        print('----------------------------------------------------')
        break
    else:
        print('Network Error. Check your internet connection.')
        answer = input('Try again? (yes/no) ').lower()
        if answer == 'yes':
            continue
        else:
            exit()

cnx = sqlite3.connect('Data.db')
curser = cnx.cursor()
curser.execute('SELECT user FROM CoinEX_Access')
if len([user for user in curser]) == 0:
    print('''====================================================
              Create your user account
----------------------------------------------------''')
    while len([user for user in curser]) == 0:
        user = input('Enter your user name: ')
        access_id = input('Enter your CoinEx API access id: ')
        secret = input('Enter your CoinEx API secret: ')
        try:
            coinex = CoinEx(access_id, secret)
            online_portfo = coinex.balance_info()
            crypto_keys = online_portfo.keys()
            curser.execute('INSERT INTO CoinEX_Access VALUES (\'%s\', \'%s\', \'%s\')' % (user, access_id, secret))
            cnx.commit()
            print('\n * Now you can enter your user name to use the app. \n----------------------------------------------------\n')
            break
        except:
            print(access_id, secret)
            print('* Invalid Access ID or Secret Key.')
cnx.close()

cnx = sqlite3.connect('Data.db')
curser = cnx.cursor()
while True:
    user = input('Enter your user name: ')
    curser.execute('SELECT user FROM CoinEX_Access WHERE user LIKE \'%s\'' % user)
    if len([user for user in curser]) > 0:
        curser.execute('SELECT ACCESS_ID FROM CoinEX_Access WHERE user = \'%s\'' % user)
        access_id = [x for x in curser][0][0]
        cnx.commit()
        curser.execute('SELECT SECRET_KEY FROM CoinEX_Access WHERE user = \'%s\'' % user)
        secret = [x for x in curser][0][0]
        cnx.commit()
        break
    else:
        print('\n* Invalid User Name. Try again.\n')
cnx.close()

coinex = CoinEx(access_id, secret)
online_portfo = coinex.balance_info()
crypto_keys = online_portfo.keys()

helpMe()
showInformations()
update()
while True: 
    print()
    while True:
        act = input('CoinEx-> ')
        if act in ('show', 'update', 'add', 'del', 'edit', 'exit', 'help'):
            break
        print("invalid input.")
    if act == 'add':
        while True:
            crypto = input('Crypto Symbol (for example BNB not BNBUSDT): ').upper()
            cryptoUSDT = crypto + 'USDT'
            if cryptoUSDT in coinex.market_list():
                break
            else:
                print("invalid input. Maybe %s not exist in CoinEx or You entered wrong crypto symbol." % crypto)
        price = float(input('Buy price (USDT): '))
        amount = float(input('Amount: '))
        addPosition(crypto, price, amount)
    elif act == 'del':
        while True:
            crypto = input('Crypto Symbol (for example BNB not BNBUSDT): ').upper()
            cryptoUSDT = crypto + 'USDT'
            if cryptoUSDT in coinex.market_list():
                break
            else:
                print("invalid input. Maybe %s not exist in CoinEx or you entered wrong crypto symbol." % crypto)
        deletePosition(crypto)
    elif act == 'show':
        showInformations()
    elif act == 'update':
        update()
    elif act == 'edit':
        crypto = input('Crypto Symbol (for example BNB not BNBUSDT): ').upper()
        price = float(input('Enter new buy price: '))
        editBuyPrice(crypto, price)
    elif act == 'help':
        helpMe()
    elif act == 'exit':
        exit()