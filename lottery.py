#!/usr/bin/env python3

# A simple Python script to run a lottery on Ardor. Using Ignis assets.
# Author: malnemark (https://github.com/malnemark)

import sys, json, time, logging, argparse


def sendQuery(nodeurl,Query):
  """function to query the Ardor API"""
  from urllib import parse, request
  params = parse.urlencode(Query)
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  req = request.Request(nodeurl, params.encode('utf-8'))
  response = request.urlopen(req)
  return response.read()

def detectBuy(data, price, acc, msg):
    """
    evaluates the main account's ledger for change.
    in: data from API call getBlockchainTransactions to detect purchases
        price in ignis + 8 zeros
        acc is the account address that runs the lottery (BaseAccount)
        msg the message that the incoming transaction needs to transmit to be considered a purchase
    """
    logger = logging.getLogger('ARDR_lottery')
    buys = []
    try:
        for e in data['transactions']:
            if e['recipientRS'] == acc:
                if 'message' in e['attachment'].keys():
                    if e['amountNQT'] == price and e['attachment']['message'] == msg:
                        logger.info('buy transaction detected from account:',e['senderRS'],' with fullHash: ',e['fullHash'])
                        buys.append({'buyer':e['senderRS'],'height':e['height'],'confirmations':e['confirmations'],'message':e['attachment']['message'],'fullHash':e['fullHash']})
    except:
        return buys
    return buys


def matchPurchases(data,buys,acc):
    """
    matches any detected purchases with an outgoing transaction, to see if a purchase wasn't serviced yet.
    in: data is the json holding outgoing transactions (msg fullHash of the respective purchase transaction)
        buys are the incoming purchases
        acc the account that runs the lottery
    """
    logger = logging.getLogger('ARDR_lottery')
    deliveryRequired = []
    for b in buys:
        buy_matched = False
        for d in data:
            if 'message' in d['attachment'].keys():
                if b['fullHash'] in d['attachment']['message']: # hash of buy transation found in asset transfers
                    buy_matched = True
                    logger.info('delivery detected for purchase: ',b['buyer'],' with hash: ',b['fullHash'])
                    break
                #else:
                #    deliveryRequired.append(b)
        if not buy_matched:
            logger.info('no delivery detected for purchanse: ',b['buyer'],' with hash: ',b['fullHash'])
            deliveryRequired.append(b)
    return deliveryRequired




def spin(array):
    """Spin the wheel of fortune - the function picking an asset from the list, note: it can pick duplicates"""
    import random
    num_choices = len(array)
    secure_random = random.SystemRandom()
    return secure_random.choice(array)


# a fixed query to ask for purchases
def QueryPayments(account):
    return {'requestType': 'getBlockchainTransactions', 'account': account, 'type': '0', 'subtype': '0', 'executedOnly': 'true','chain':'IGNIS'}


# a fixed query to ask outgoing transactions
def QueryAssetTransfers(account):
    return {'requestType': 'getBlockchainTransactions', 'account': account, 'type': '2', 'subtype': '1', 'executedOnly': 'true','chain':'IGNIS'}

# a fixed query to ask unconfirmed outgoing transactions (to prevent double spending)
def QueryUnconfirmedDeliveries(account):
    return {'requestType': 'getUnconfirmedTransactions', 'account': account,'chain':'IGNIS'}

if __name__ == "__main__":

    #set up a simple logger
    logger = logging.getLogger('ardor-lottery')
    logger.setLevel(logging.INFO)
    consoleHandler = logging.StreamHandler(sys.stdout)
    logger.addHandler(consoleHandler)

    # get arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('conf', help='configuration file')
    #parser.add_argument('--account', help='lottery account')
    #parser.add_argument('--passphrase', help='passphrase of lottery account')
    #parser.add_argument('--nodeurl', help='nodeurl, default is http://localhost:26876/nxt', default="http://localhost:26876/nxt")
    #parser.add_argument('--assets', help='list of assetids')

    args = parser.parse_args()

    with open(args.conf) as json_file:
        config = json.load(json_file)

    print("Starting up the lottery on account ",config['account'], "with assets:")
    print(config['assets'])

    nodeurl = config['nodeurl']
    account = config['account']
    assetreg = config['assets']

    while True:
        status = sendQuery(nodeurl,{'requestType':'getBlockchainStatus'});

        logger.info("querying the blockchain for a new purchase")
        output = sendQuery(nodeurl,QueryPayments(account))
        payments = json.loads(output.decode('utf-8'))

        buys = detectBuy(payments,"1200000000",account,'lottery')

        output = sendQuery(nodeurl,QueryAssetTransfers(account))
        assettransfers = json.loads(output.decode('utf-8'))

        output = sendQuery(nodeurl,QueryUnconfirmedDeliveries(account))
        unconfDeliveries = json.loads(output.decode('utf-8'))

        try:
            allDeliveries = assettransfers['transactions'] + unconfDeliveries['unconfirmedTransactions']
            deliveryRequired = matchPurchases(assettransfers['transactions'],buys,account)
        except KeyError:
            deliveryRequired = None # instead of False..

        if deliveryRequired:
            for d in deliveryRequired:
                logger.info('Delivery for: ',d)
                print('Delivery for: ',d)
                assetId = [spin(assetreg), spin(assetreg), spin(assetreg)]
                for aid in assetId:
                    QueryTransferAsset = {'chain':'IGNIS','requestType': 'transferAsset', 'recipient': d['buyer'], 'asset': aid, 'secretPhrase':passPhrase, 'broadcast':'true','message':d['fullHash'],'messageIsText':'true','quantityQNT':'1','feeNQT':'101000000'}
                    resp = sendQuery(args.nodeurl,QueryTransferAsset)
                    response = json.loads(resp.decode('utf-8'))
                    if 'errorCode' in response.keys():
                        print('response: ',response)
                    else:
                        logger.info('assetTransfer success.')
        logger.info('pausing')
        time.sleep(50)
