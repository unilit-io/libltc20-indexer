import requests
from tqdm import tqdm
import re
import os
import json
import time

'''
get the current height of the blockchain
will change to api after we fix the ord-litecoin api
'''
def get_current_height(url_base):
    pattern = r'<ol start=(\d+) reversed class=blocks>'
    response = requests.get(url_base)
    data = response.text
    last_block = re.findall(pattern, data)
    return int(last_block[0])

'''
get the current ins num of the blockchain
will change to fully api after we fix the ord-litecoin api
'''
def get_current_ins_num(url_base):
    pattern = r'href=(/inscription/\S+?)>'
    response = requests.get(url_base)
    data = response.text
    last_ins = re.findall(pattern, data)
    
    url = url_base + last_ins[0]
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    data = json.loads(response.text)
    
    return data['number']

def get_content(url, api=False):
    if api:
        try:
            headers = {'Accept': 'application/json'}
            response = requests.get(url, headers=headers)
            data = json.loads(response.text)
        except:
            response = requests.get(url)
            data = response.text
            #print(data) #most of time this shows: 'Internal Server Error'
            #or maybe the endpoint is not available for some reason (most of case the address is missing)
            #such as https://ordinalslite.com/tx/3357c736600dad44851406f535f6780a35ebb0b601a56632398099a346bf1975
    else:
        response = requests.get(url)
        data = response.text
    return data

def get_all_ins_list_in_a_page(url_base, last):
    url = url_base + '/inscriptions/' + str(last)
    inscriptions = get_content(url, True)['inscriptions']
    inscriptions.reverse()
    urls = [url_base + inscription['href'] for inscription in inscriptions]

    return urls

def get_details_of_an_ins(url):
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    result = json.loads(response.content)
    
    #not matter which format of the content, we will get the ins_num any way
    #also the genesis height of the ins
    ins_num = int(result['number'])
    genesis_height = result['genesis_height']

    if "text/plain" in result['content_type'] or "application/json" in result['content_type']:
        ins_num = int(result['number'])
        #current_stamp = parser.parse(result['timestamp'])
        #current_stamp = current_stamp.timestamp()
        current_stamp = result['timestamp']
        loc = result['location'].find(':')

        url_content = {
            'inscription_number': ins_num, 
            'genesis_transaction': result['genesis_transaction'], 
            'address': result['address'], #current address
            'offset': result['offset'], #current offset BE CAREFUL
            'height': result['genesis_height'], #genesis height
            'timestamp': current_stamp, #genesis tx timestamp
            'content_href': result['_links']['content']['href'],
            'location': result['location'][:loc]
        }
    else:
        url_content = None
    
    return url_content, ins_num, genesis_height


def get_ltc20_details_of_an_ins(url_base, url_content):
    json_content = get_content_of_an_ins(url_base, url_content)

    page_item  = None

    if json_content['p']=='ltc-20':    
        ins_num = url_content['inscription_number']
        tx_id = url_content['genesis_transaction']
        vout = 0 #url_content['offset']
        ins_id = tx_id + 'i' + str(vout)
        time_inscribed = url_content['timestamp']
        address = url_content['address']

        res = get_details_of_an_ouput(url_base, tx_id, vout, True)
        if type(res)==dict:
            genesis_address = res['address']
            genesis_value = res['value']
        else:
            print('The api does not response correctly')
            print(res)
            return page_item

        if 'tick' in json_content.keys():
            tick = json_content['tick'].upper()
        else:
            print('No tick in the json')
            return page_item
            
        if 'op' not in json_content.keys():
            json_content['op'] = 'unknown'

        if json_content['op']=='deploy':
            if ('max' in json_content.keys()) and ('lim' in json_content.keys()):
                type_x, num_max = type_deciper(json_content['max'])
                type_y, num_lim = type_deciper(json_content['lim'])
                if type_x and type_y:
                    amt = [num_max, num_lim]
                else:
                    return page_item
            else:
                return page_item
                
        elif json_content['op']=='mint':
            if 'amt' in json_content.keys():
                type_x, num_amt = type_deciper(json_content['amt'])
                if type_x:
                    amt = num_amt
                else:
                    return page_item
            else:
                return page_item
        elif json_content['op']=='transfer':
            if 'amt' in json_content.keys():
                type_x, num_amt = type_deciper(json_content['amt'])
                if type_x:
                    amt = num_amt
                else:
                    return page_item
            else:
                return page_item

        #for deploy
        if json_content['op']=='deploy':
            decimals = 18
            if 'dec' in json_content.keys():
                decimals = json_content['dec']

            item_c = {'address': genesis_address, 'tick': tick, 'ins_num': ins_num, 'ins_id': ins_id, 
                        'supply': json_content['max'], 'lim': json_content['lim'] , 'dec': decimals,
                        'minted': 0, 'tx_id': tx_id,  'action': 'deploy', 'height': url_content['height'],
                        'time': url_content['timestamp'], 'offset': url_content['offset'], 'genesis_value': genesis_value}
            page_item = {'action': 'deploy', 'data': item_c}

        #for mint
        if json_content['op']=='mint':
            item_c = {'address': genesis_address, 'tick': tick, 'amt': amt,
                      'ins_num': ins_num, 'ins_id': ins_id, 
                      'tx_id': tx_id, 'height': url_content['height'], 'time': url_content['timestamp'],
                      'offset': url_content['offset'], 'genesis_value': genesis_value}
            page_item = {'action': 'mint', 'data': item_c}


        #for transfer
        if json_content['op']=='transfer':
            #the address here is the final address (final location).
            # we need to get the genesis address
            item_c = {'address': genesis_address, 'tick': tick, 'amt': amt,
                      'ins_num': ins_num, 'ins_id': ins_id, 
                      'tx_id': tx_id, 'height': url_content['height'], 'time': url_content['timestamp'],
                      'offset': url_content['offset'], 'genesis_value': genesis_value}
            page_item = {'action': 'transfer', 'data': item_c}
    
    return page_item

def type_deciper(inp):
    type_x = True
    num = None

    if type(inp)==str:
        if inp.isnumeric():
            type_x = True
            num = int(inp)
        else:
            type_x = False
    elif type(inp)==int or type(inp)==float:
        type_x = True
        num = int(inp)
    else:
        type_x = False
    
    return type_x, num
    


def get_content_of_an_ins(url_base, url_content):
    headers = {'Accept': 'application/json'}
    response = requests.get(url_base + url_content['content_href'], headers=headers)
    content = response.content
    try:
        json_content = json.loads(content)
    except:
        json_content = {'p': 'unknown'}
    
    if type(json_content) != dict:
        json_content = {'p': 'unknown'}

    if 'p' in json_content.keys():
        pass
    else:
        json_content['p'] = 'unknown'
    
    return json_content

def get_details_of_an_ouput(url_base, tx_id, vout, api=True):
    url = url_base + '/output/' + tx_id + ':' + str(vout)
    data = get_content(url, api=api)
    
    return data

def get_snapshot(url_base, db_manager, snapshot_num, snapshot_id, height, time_inscribed, tick):
    headers = {'Accept': 'application/json'}
    response = requests.get(url_base + '/content/' + snapshot_id, headers = headers)
    content = response.text.replace('\n','')
    li = list(content.split("\r"))
    snapshot_tx = [list(l.split(',')) for l in li]
    tx_id = snapshot_id[:-2]

    snapshot_items = []
    for i in range(len(snapshot_tx)):
        st = snapshot_tx[i]
        ins_id = snapshot_id + '-SNP-' + str(i)
        ele = {'genesis_tx_id': tx_id, 'sender': st[0], 'receiver': st[1], 'action': 'snapshot',
                    'supply': 0, 'lim': 0, 'amt': int(st[2]), 'tick': tick, 
                    'ins_id': ins_id, 'ins_num': int(snapshot_num),
                    'height': int(height), 'time': time_inscribed, 'c_offset': 0,
                    'valid': True, 'spent': False, 'value': 0}
        snapshot_items.append(ele)
    return snapshot_items

def get_txpairs_at_a_height(url_base, height):
    item = []
    all_tx_hash = get_all_tx_at_a_height(url_base, height)

    all_txpairs = []
    for i in tqdm(range(len(all_tx_hash)), desc='pairing'):
        a = all_tx_hash[i]
        tsf_pairs = get_sat_alignment_of_a_tx(url_base, a, height)
        all_txpairs += tsf_pairs
    
    return {'height': height, 'txpairs': all_txpairs, 'txhash': all_tx_hash}

'''
get all tx at a height
'''
def get_all_tx_at_a_height(url_base, height):

    url_c = url_base + '/block/' + str(height)
    resp = requests.get(url_c)
    resp_text = resp.text

    pattern = r"<h2>(\d+) Transactions</h2>"
    match = re.search(pattern, resp_text)
    if match:
        num_of_tx = int(match.group(1))
    else:
        print('something is not right... in block {}'.format(height))

    locp = resp_text.find('<ul class=monospace>')
    if locp>=0:
        strp = resp_text[locp:]
        #print(strp)
        pattern = r'href=(/tx/[^>]+)'
        match = re.findall(pattern, strp)
        all_tx_hash = []
        for i in match:
            all_tx_hash.append(i.replace('/tx/', ''))
        return all_tx_hash

    else:
        print('something is not right... in block {} for getting tx'.format(height))
        return []

def get_sat_alignment_of_a_tx(url_base, tx_id, height):
    data = get_details_of_a_tx(url_base, tx_id)
        
    if type(data)==dict:
        _input_ = [data['_links']['inputs'][i]['href'].replace('/output/','') for i in range(len(data['_links']['inputs']))]
        _output_ = [data['_links']['outputs'][i]['href'].replace('/output/','') for i in range(len(data['_links']['outputs']))]
    else:
        #print(url_base, a)
        _input_ = []
        _output_ = []

    #align the sat
    inp_details = []
    inp_sat = []
    for inp in _input_:
        loc = inp.find(':')
        result = get_ins_details(url_base, inp[:loc], inp[loc+1:])
        if type(result)==dict:
            sat = result['sat']
            item_c = [inp, sat, result]
            inp_details.append(item_c)
            inp_sat.append(sat)

    oup_details = []
    oup_sat_start = []
    for oup in _output_:
        loc = oup.find(':')
        oup_ss = get_the_sat_range_of_an_output(url_base, oup[:loc], oup[loc+1:], False)
        if len(oup_ss)>0:
            res = get_details_of_an_ouput(url_base, oup[:loc], oup[loc+1:], True)
            if type(res)==dict:
                oup_details.append([oup, oup_ss, res['address'], res['value']])
                oup_sat_start.append(oup_ss)
            else:
                #TODO: most cases it is a tx without address. We need decipher the pubkey hash using Base58Check
                pass

    #start to align
    tsf_pairs = []
    for i in range(len(inp_sat)):
        ii = inp_sat[i]
        for j in range(len(oup_sat_start)):
            if ii in oup_sat_start[j]:
                #find an alignment
                inp = inp_details[i][0]
                oup = oup_details[j][0]
                address = oup_details[j][2]
                value = oup_details[j][3]
                #inp and oup already include vin and vout
                item_c = {'tx_id': tx_id, 'input': inp, 'output': oup, 'address': address, 'value': value, 'height': height}
                tsf_pairs.append(item_c)
    return tsf_pairs

def get_ins_details(url_base, tx_id, vout):
    url = url_base + '/inscription/' + tx_id + 'i' + str(vout)

    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    str_valid = 'inscription ' +  tx_id + 'i' + str(vout) + ' not found'
    if response.text.find(str_valid)>=0:
        return None
    else:
        result = json.loads(response.content)
        return result

def get_the_sat_range_of_an_output(url_base, tx_id, vout, api):
    pattern = r'<li><a href=/range/(\d+)/(\d+) class=common>(\d+–\d+)</a></li>'

    url = url_base + '/output/' + tx_id + ':' + str(vout)
    data = get_content(url, api=api)

    loc1 = data.find('Sat Range')
    loc2 = data.find('Sat Ranges')
    loc = max([loc1, loc2])
    
    if loc >= 0:
        matches = re.findall(pattern, data[loc:])
        sat_start = [int(m[0]) for m in matches]
    else:
        sat_start = []
    
    return sat_start

def get_details_of_an_ouput(url_base, tx_id, vout, api=True):
    url = url_base + '/output/' + tx_id + ':' + str(vout)
    data = get_content(url, api=api)
    
    return data

def get_details_of_a_tx(url_base, tx_id, api=True):
    url = url_base + '/tx/' + tx_id
    data = get_content(url, api=True)

    return data
