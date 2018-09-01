import sys, json, time, logging

# TODO the assetregister will be read from a JSON or even from the blockchain itself, it needs to list all available assets.
assetreg = ['assetid1', 'assetid2','assetid3','assetid4','assetid5','assetid6']


# Storing a passphrase in plain text is dangerous. Only use this on a local node, and maybe rather for
# fun not for serious amounts of Ardor/Ignis.
passPhrase = "top secret collection of words"
BaseAccount = "ARDOR-ACCOUNT-RELATED-TO-THE-PHRASE"

def sendQuery(Query):
  """function to query the Ardor API"""
  from urllib import parse, request
  params = parse.urlencode(Query)
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  # port is the testnet port, change it for mainnet use.
  req = request.Request("http://localhost:26876/nxt", params.encode('utf-8'))
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
    for e in data['transactions']:
        if e['recipientRS'] == acc:
            if 'message' in e['attachment'].keys():
                if e['amountNQT'] == price and e['attachment']['message'] == msg:
                    logger.info('buy transaction detected from account:',e['senderRS'],' with fullHash: ',e['fullHash'])
                    buys.append({'buyer':e['senderRS'],'height':e['height'],'confirmations':e['confirmations'],'message':e['attachment']['message'],'fullHash':e['fullHash']})
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



#class WheelOfFortune(objects)
def spin(array):
    """the function picking an asset from the list, can pick duplicates if ran multiple times"""
    import random
    num_choices = len(array)
    secure_random = random.SystemRandom()
    return secure_random.choice(array)


# a fixed query to ask for purchases
#TODO read out blockTimestamp and set a min timestamp to filter out old TX
QueryPayments = {'requestType': 'getBlockchainTransactions',
'account': BaseAccount, 'type': '0', 'subtype': '0', 'executedOnly': 'true','chain':'IGNIS'}


# a fixed query to ask outgoing transactions
#TODO read out blockTimestamp and set a min timestamp to filter out old TX
QueryAssetTransfers = {'requestType': 'getBlockchainTransactions',
'account': BaseAccount, 'type': '2', 'subtype': '1', 'executedOnly': 'true','chain':'IGNIS'}

# a fixed query to ask unconfirmed outgoing transactions (to prevent double spending)
QueryUnconfirmedDeliveries = {'requestType': 'getUnconfirmedTransactions',
'account': BaseAccount,'chain':'IGNIS'}



if __name__ == "__main__":
    logger = logging.getLogger('ARDR_lottery')
    logger.setLevel(logging.INFO)
    consoleHandler = logging.StreamHandler(sys.stdout)
    logger.addHandler(consoleHandler)
    while True:
        logger.info("querying the blockchain for a new purchase")
        output = sendQuery(QueryPayments)
        payments = json.loads(output.decode('utf-8'))

        buys = detectBuy(payments,"1200000000",BaseAccount,'lottery')

        output = sendQuery(QueryAssetTransfers)
        assettransfers = json.loads(output.decode('utf-8'))

        output = sendQuery(QueryUnconfirmedDeliveries)
        unconfDeliveries = json.loads(output.decode('utf-8'))

        allDeliveries = assettransfers['transactions'] + unconfDeliveries['unconfirmedTransactions']
        deliveryRequired = matchPurchases(assettransfers['transactions'],buys,BaseAccount)

        if deliveryRequired:
            for d in deliveryRequired:
                logger.info('Delivery for: ',d)
                print('Delivery for: ',d)
                assetId = [spin(assetreg), spin(assetreg), spin(assetreg)]
                #TODO add a doublespend protection -> set a flag TRUE if a delivery has been transmitted, wait for N cycles until delivery would be repeated
                for aid in assetId:
                    QueryTransferAsset = {'chain':'IGNIS','requestType': 'transferAsset', 'recipient': d['buyer'], 'asset': aid, 'secretPhrase':passPhrase, 'broadcast':'true','message':d['fullHash'],'messageIsText':'true','quantityQNT':'1','feeNQT':'101000000'}
                    resp = sendQuery(QueryTransferAsset)
                    response = json.loads(resp.decode('utf-8'))
                    if 'errorCode' in response.keys():
                        print('response: ',response)
                    else:
                        logger.info('assetTransfer success.')
        print('pausing')
        time.sleep(50)
