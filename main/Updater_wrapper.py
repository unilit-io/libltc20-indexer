import requests
import json
from tqdm import tqdm
from multiprocessing.dummy import Pool as ThreadPool
import time, os, sys
import yaml

path_cst = os.path.abspath('../base/')+'/'
sys.path.append(path_cst)

from DB_init import *
from OL_Base import *

def get_txpairs_until_target_height_seq(url_base, db_manager, last_height, 
                                                        target_height):
    for height in tqdm(range(last_height + 1, target_height + 1), desc='txpairing'):
        #get the txpairs and save them into the database
        dict_txpairs = get_txpairs_at_a_height(url_base, height)
        all_txhash = dict_txpairs['txhash']
        all_txpairs = dict_txpairs['txpairs']
        for a in all_txpairs:
            constraint_info = {'tx_id': a['tx_id'], 'input': a['input'], 'output': a['output']}
            row = db_manager.search_a_table_with_constraints(db_manager.conn, 'utxo_spent_list', constraint_info)
            if len(row)==0:
                db_manager.insert_a_row_to_a_table(db_manager.conn, 'utxo_spent_list', a)
            else:
                print('Already inserted')

def get_snapshots_data_until_target_height_seq(url_base, db_manager, snapshots_details, all_flag, height):
    snapshot_items = []
    if not all_flag:
        if height in snapshots_details['applied_height']:
            i = snapshots_details['applied_height'].index(height)
            ins_id = snapshots_details['ins_id'][i]
            ins_num = snapshots_details['ins_num'][i]
            tick = snapshots_details['ins_tick'][i]

            snapshot_items = get_snapshot(url_base, db_manager, ins_num, ins_id, h, '', tick)
        
    else:
        num_snapshot = len(snapshots_details['ins_id'])
        for i in range(num_snapshot):
            h = snapshots_details['applied_height'][i]
            ins_id = snapshots_details['ins_id'][i]
            ins_num = snapshots_details['ins_num'][i]
            tick = snapshots_details['ins_tick'][i]

            snapshot_itemp = get_snapshot(url_base, db_manager, ins_num, ins_id, h, '', tick)
            snapshot_items = snapshot_items + snapshot_itemp

    for s in snapshot_items:
        constraints = {'ins_id': s['ins_id']} 
        row = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_ins_list', constraints)
        if len(row)==0:
            db_manager.insert_a_row_to_a_table(db_manager.conn, 'ltc20_ins_list', s)
        else:
            print('Already insert the snapshot item')
    print('Total item in this snapshot: {}'.format(len(snapshot_items)))

def get_ins_data_until_target_height_all_seq(url_base, db_manager, last_ins_num, 
                                                last_height, target_height):
    #download normal ins
    continue_flag = True
    start = last_ins_num + 1
    ss = time.time()
    while continue_flag:
        last = start + 100 - 1
        urls_content = []
        ltc20_ins_items = []
    
        urls = get_all_ins_list_in_a_page(url_base, last)
        for ii in tqdm(range(len(urls)), desc='ins'):
            url = urls[ii]
            url_content, ins_num, genesis_height = get_details_of_an_ins(url)

            if url_content != None:
                if genesis_height > last_height and genesis_height <= target_height:
                    page_item = get_ltc20_details_of_an_ins(url_base, url_content)
                    if type(page_item)== dict:
                        if type(page_item['data'])==dict:
                            urls_content.append(url_content)
                            ltc20_ins_items.append(page_item)
                            last_ins_num = ins_num
                        else:
                            print(url)
                elif genesis_height > target_height:
                    continue_flag = False
                    break
                else:
                    pass

        for ins_data in ltc20_ins_items:
            action = ins_data['action']
            data = ins_data['data']

            tick = data['tick']
            ins_num = data['ins_num']
            ins_id = data['ins_id']
            address = data['address']
            tx_id = data['tx_id']
            height = data['height']
            time_inscribed = data['time']
            offset = data['offset']
            value = data['genesis_value']

            #since we will modify ins_id for snapshot, THIS is the only unique key we will use
            constraints = {'ins_id': data['ins_id']} 
            row = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_ins_list', constraints)
            if len(row)>0:
                pass
            else:
                if action == 'deploy':
                    supply = data['supply']
                    lim = data['lim']
                    dec = data['dec']
                    minted = data['minted']
                    ele = {'genesis_tx_id': tx_id, 'sender': '', 'receiver': address, 'action': 'deploy',
                            'supply': supply, 'lim': lim, 'dec': dec, 'tick': tick, 
                            'ins_id': ins_id, 'ins_num': ins_num,
                            'height': height, 'time': time_inscribed, 'c_offset': offset,
                            'valid': True, 'spent': False, 'value': value}
                    db_manager.insert_a_row_to_a_table(db_manager.conn, 'ltc20_ins_list', ele)
                elif action == 'mint':
                    amt = data['amt']
                    ele = {'genesis_tx_id': tx_id, 'sender': '', 'receiver': address, 'action': 'mint',
                            'amt': amt, 'tick': tick, 
                            'ins_id': ins_id, 'ins_num': ins_num,
                            'height': height, 'time': time_inscribed, 'c_offset': offset,
                            'valid': True, 'spent': False, 'value': value}
                    db_manager.insert_a_row_to_a_table(db_manager.conn, 'ltc20_ins_list', ele)
                elif action ==  'transfer':
                    amt = data['amt']
                    ele = {'genesis_tx_id': tx_id, 'sender': '', 'receiver': address, 'action': 'transfer',
                                'amt': amt, 'tick': tick, 
                                'ins_id': ins_id, 'ins_num': ins_num,
                                'height': height, 'time': time_inscribed, 'c_offset': offset,
                                'valid': True, 'spent': False, 'value': value}
                    db_manager.insert_a_row_to_a_table(db_manager.conn, 'ltc20_ins_list', ele)

        ee = time.time()
        print('Finish #{} to #{} inscription (included).'.format(start, last))
        print('Current ins num #{}'.format(last_ins_num))
        print('')
        start = last + 1

def update_deploy_table(item_c, db_manager):

    ins_num = item_c['ins_num']
    ins_id = item_c['ins_id']
    tick = item_c['tick']
    supply = item_c['supply']
    lim = item_c['lim']
    dec = item_c['dec']
    minted = item_c['minted']
    tx_id = item_c['tx_id']
    height = item_c['height']

    if dec > 18:
        return False

    new_deploy = True
    constraint_info = {'tick': item_c['tick']}
    row = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_list', constraint_info)
    if len(row)==0:
        new_deploy = True
        ele = {'ins_num': ins_num, 'ins_id': ins_id,
                'tick': tick, 'supply': supply, 'lim': lim , 'dec': dec,
                'minted': minted, 'height': height}
        db_manager.insert_a_row_to_a_table(db_manager.conn, 'ltc20_list', ele)

        constraint = {'ins_id': ins_id}
        row_info = {'valid': True, 'spent': True}
        db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', row_info, constraint)

    else:
        new_deploy = False
        constraint = {'ins_id': ins_id}
        row_info = {'valid': False, 'spent': False}
        db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', row_info, constraint)

    return new_deploy


def update_mint_ins(item_c, db_manager):
    tick = item_c['tick']
    amt = item_c['amt']
    ins_id = item_c['ins_id']
    ins_num = item_c['ins_num']

    constraint_info = {'tick': tick}
    row = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_list', constraint_info)
    if len(row)==0:
        #this mint is invalid.. will discard for now
        constraint = {'ins_id': ins_id}
        row_info = {'valid': False, 'spent': False}
        db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', row_info, constraint)
        return False, 0

    tick_lim = row[0][5]
    tick_supply = row[0][4]
    tick_minted = row[0][7]
    if (tick_lim==0 or tick_lim >= amt) and (tick_supply > tick_minted):
        if tick_minted ==0:
            row_info = {'start_mint': ins_num, 'end_mint': 0}
            constraint_info = {'tick': tick}
            db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_list', row_info, constraint_info)
        if tick_minted + amt >= tick_supply:
            row_info = {'end_mint': ins_num}
            constraint_info = {'tick': tick}
            db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_list', row_info, constraint_info)

        #modify mint balance. Partial mint is valid.
        adjust_balance = amt
        if tick_minted + amt > tick_supply:
            adjust_balance = tick_supply - tick_minted

        #let's update ltc20 balance
        constraint_info = {'tick': tick}
        ele = {'minted': tick_minted + adjust_balance}
        db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_list', ele, constraint_info)

        constraint = {'ins_id': ins_id}
        row_info = {'valid': True, 'spent': True}
        db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', row_info, constraint)
        return True, adjust_balance
    else:
        constraint = {'ins_id': ins_id}
        row_info = {'valid': False, 'spent': False}
        db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', row_info, constraint)
        return False, 0

def insert_transfer_ins(item_c, db_manager):
    tick = item_c['tick']
    amt = item_c['amt']
    ins_num = item_c['ins_num']
    ins_id = item_c['ins_id']
    address = item_c['address']
    tx_id = item_c['tx_id']
    height = item_c['height']
    time_inscribed = item_c['time']
    offset = item_c['offset']
    value = item_c['genesis_value']

    #insert the tx history
    #for mint if it is invalid, we do not insert it in.
    ele = {'genesis_tx_id': tx_id, 'sender': '', 'receiver': address, 'action': 'transfer',
                'supply': 0, 'lim': 0, 'amt': amt, 'tick': tick, 
                'ins_id': ins_id, 'ins_num': ins_num,
                'height': height, 'time': time_inscribed, 'c_offset': offset,
                'valid': True, 'spent': False, 'value': value}
    db_manager.insert_a_row_to_a_table(db_manager.conn, 'ltc20_ins_list', ele)

def get_ins_items_wrapper(row_data):

    page_items = []
    #linek = ['ins_id':0, 'genesis_tx_id':1, 'sender':2, 'receiver':3, 'action':4,
    #            'tick':5, 'supply':6, 'lim':7, 'dec':8, 'amt':9, 'ins_num':10, 
    #            'height':11, 'time':12, 'c_offset':13, 'value':14, 'valid':15, 'spent':16]

    for d in row_data:
        action = d[4]
        if action == 'deploy':
            item_c = {'address': d[3], 'tick': d[5], 'ins_num': d[10], 'ins_id': d[0], 
                        'supply': d[6], 'lim':d[7], 'dec': d[8],
                        'minted': 0, 'tx_id': d[1],  'action': 'deploy', 'height': d[11],
                        'time': d[12], 'c_offset': d[13], 'genesis_value': d[14]}
            page_item = {'action': 'deploy', 'data': item_c}
            page_items.append(page_item)

        if action == 'mint':
            item_c = {'address': d[3], 'tick': d[5], 'amt': d[9],
                      'ins_num': d[10], 'ins_id': d[0], 
                      'tx_id': d[1], 'height': d[11], 'time': d[12],
                      'c_offset': d[13], 'genesis_value': d[14]}
            page_item = {'action': 'mint', 'data': item_c}
            page_items.append(page_item)

        if action == 'transfer':
            item_c = {'address': d[3], 'tick': d[5], 'amt': d[9],
                      'ins_num': d[10], 'ins_id': d[0], 
                      'tx_id': d[1], 'height': d[11], 'time': d[12],
                      'c_offset': d[13], 'genesis_value': d[14]}
            page_item = {'action': 'transfer', 'data': item_c}
            page_items.append(page_item)

    return page_items

def get_ranked_txpair_and_ins_at_a_height(url_base, db_manager, height, snapshots_details, last_ins_num, mode):
    '''
    if the mode is update blk by blk
    then we assume we get the block data directly from the json-rpc server.
    '''
    if mode == 'UPDATE_BLK_BY_BLK':
        get_ins_data_until_target_height_all_seq(url_base, db_manager, last_ins_num, 
                                                height - 1, height)
        get_txpairs_until_target_height_seq(url_base, db_manager, height - 1, height)

    '''
    until this point, these two modes are aligned.
    we assume we get the block data directly from the postgres database.
    '''
    constraint = {'height': height}
    row_txpairs = db_manager.search_a_table_with_constraints(db_manager.conn, 'utxo_spent_list', constraint)
    all_txpairs = []
    for i in range(len(row_txpairs)):
        item_c = {'tx_id': row_txpairs[i][1], 'input': row_txpairs[i][2], 'output': row_txpairs[i][3], 
                    'address': row_txpairs[i][4], 'value': row_txpairs[i][5], 'height': row_txpairs[i][6]}
        all_txpairs.append(item_c)

    #get the ins at this height
    row_ins = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_ins_list', constraint)
    cur_ins = [row_ins[i][10] for i in range(len(row_ins))]
    if len(cur_ins)>0:
        last_ins_num_block = max(cur_ins)
    else:
        last_ins_num_block = last_ins_num

    ltc20_ins_items = get_ins_items_wrapper(row_ins)
    all_txhash = get_all_tx_at_a_height(url_base, height)

    #ranking the txpairs, new ins snapshot using tx hash ranking
    vout_max = 1
    all_tx_data = []
    for a in all_txpairs:
        idxp = all_txhash.index(a['tx_id'])
        loc = a['output'].find(':')
        vout = int(a['output'][loc+1:])
        vout_max = max([vout, vout_max])
        tx_value = [idxp, vout, None, {'type': 'txpair', 'data': a}]
        all_tx_data.append(tx_value)
        
    for a in ltc20_ins_items:
        tx_id_a = a['data']['tx_id']
        idxp = all_txhash.index(tx_id_a)
        vout = a['data']['c_offset']
        vout_max = max([vout, vout_max])
        tx_value = [idxp, vout, None, {'type': 'ins', 'data': a}]
        all_tx_data.append(tx_value)

    for a in all_tx_data:
        total_rank = a[0] + (a[1]/(2.0*vout_max))
        a[2] = total_rank
        
    all_tx_data_ranked = sorted(all_tx_data, key=(lambda x:x[2]),reverse = False) #True: big-->small

    return all_tx_data_ranked, last_ins_num_block


def modify_balance_by_new_inscribed_inscription(db_manager, ins_data):
    snapshot_valid = True

    action = ins_data['action']
    data = ins_data['data']

    constraints = {'ins_num': data['ins_num']}
    row = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_ins_list', constraints)

    if action=='deploy':
        new_deploy = update_deploy_table(data, db_manager)
    elif action=='mint':
        new_tx, mint_balance = update_mint_ins(data, db_manager)

        if new_tx:
            ele = {'address': data['address'], 'tick': data['tick'], 'transferable_delta': 0, 'available_delta': mint_balance, 
                    'total_delta': mint_balance, 'due_to_tx': data['tx_id'], 'due_to_ins': data['ins_id'], 'height': data['height'],
                    'action': 'mint'}
            db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_tx_history', ele)

            constraint = {'address': data['address'], 'tick': data['tick']}
            row_balance = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
            if len(row_balance)==0:
                ele = {'address': data['address'], 'tick': data['tick'], 'transferable': 0, 'available': mint_balance, 'total': mint_balance}
                db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_balance', ele)
            else:
                ele = {'transferable': row_balance[0][3], 
                        'available': row_balance[0][4] + mint_balance, 
                        'total': row_balance[0][5] + mint_balance}
                db_manager.update_a_row_with_constraint(db_manager.conn, 'address_balance', ele, constraint)

    elif action=='transfer':
        constraint = {'address': data['address'], 'tick': data['tick']}
        row_balance = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
        constraint = {'ins_id': data['ins_id']}
        if len(row_balance)==0:
            #this transfer is not valid
            ele = {'valid': False, 'spent': False}
            db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)
        else:
            available = row_balance[0][4]
            if available < data['amt']:
                ele = {'valid': False, 'spent': False}
                db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)
            else:
                ele = {'valid': True, 'spent': False}
                db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)

                ele = {'address': data['address'], 'tick': data['tick'], 'transferable_delta': data['amt'], 
                        'available_delta': -data['amt'], 
                        'total_delta': 0, 'due_to_tx': data['tx_id'], 'due_to_ins': data['ins_id'], 'height': data['height'],
                        'action': 'inscribe-tsf'}
                db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_tx_history', ele)

                constraint = {'address': data['address'], 'tick': data['tick']}
                row = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
                ele = {'transferable': row[0][3] + data['amt'], 'available': row[0][4] - data['amt'], 'total': row[0][5]}
                db_manager.update_a_row_with_constraint(db_manager.conn, 'address_balance', ele, constraint)

    elif action=='snapshot':
        constraint = {'address': data['sender'], 'tick': data['tick']}
        row_balance = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
        if len(row_balance)==0:
            #this snapshot transfer is not valid
            constraint = {'ins_id': data['ins_id']}
            ele = {'valid': False, 'spent': False}
            db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)
        else:
            total = row_balance[0][5] #be careful here we use total in order to deal with more complex case 
            if total < data['amt']:
                #this transfer is not valid
                constraint = {'ins_id': data['ins_id']}
                ele = {'valid': False, 'spent': False}
                db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)
            else:
                #first collect all possible unspent inscriptions
                constraint = {'receiver': data['sender'], 'valid': True, 'spent': False}
                row_balance = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_ins_list', constraint)
                
                #set all transfer inscription under the given height as invalid in order to avoid conflict.
                available_plus = 0
                for r in row_balance:
                    if r[11] <= data['height']:
                        constraint = {'ins_id': r['ins_id']}
                        ele = {'valid': False, 'spent': False}
                        db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)
                        available_plus += r[9]
                adjust_available = row_balance[0][5] - data['amt']

                constraint = {'address': data['sender'], 'tick': data['tick']}
                row_sender = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
                if len(row_sender)==0:
                    constraint = {'ins_id': data['ins_id']}
                    ele = {'valid': False, 'spent': False}
                    db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)
                else:
                    ele = {'address': data['sender'], 'tick': data['tick'], 'transferable_delta': -available_plus, 
                            'available_delta': available_plus - data['amt'], 
                            'total_delta': -data['amt'], 'due_to_tx': data['genesis_tx_id'], 'due_to_ins': data['ins_id'], 'height': data['height'],
                            'action': 'snapshot-send'}
                    db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_tx_history', ele)

                    ele = {'transferable': 0, 'available': row_sender[0][4] + available_plus - data['amt'], 'total': row_sender[0][5] - data['amt']}
                    db_manager.update_a_row_with_constraint(db_manager.conn, 'address_balance', ele, constraint)

                constraint = {'address': data['receiver'], 'tick': data['tick']}
                row = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
                if len(row_sender)==0:
                    pass
                else:
                    ele = {'address': data['receiver'], 'tick': data['tick'], 'transferable_delta': 0, 
                            'available_delta': data['amt'], 
                            'total_delta': data['amt'], 'due_to_tx': data['genesis_tx_id'], 'due_to_ins': data['ins_id'], 'height': data['height'],
                            'action': 'snapshot-receive'}
                    db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_tx_history', ele)
                   
                    ele = {'transferable': row[0][3], 'available': row[0][4] + data['amt'], 'total': row[0][5] + data['amt']}
                    db_manager.update_a_row_with_constraint(db_manager.conn, 'address_balance', ele, constraint)

                if len(row_sender) > 0:
                    constraint = {'ins_id': data['ins_id']}
                    ele = {'valid': True, 'spent': True}
                    db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', ele, constraint)

def modify_balance_according_to_a_tx_pair(db_manager, tx_pair, snapshots_details):
    valid_spent = False

    ins_id = tx_pair['input'].replace(':', 'i')
    output = tx_pair['output']
    loc = output.find(':')
    spent_tx = output[:loc]
    vout = output[loc+1:]

    # see whether this spent is due to snapshots.
    for k in range(len(snapshots_details['ins_id'])):
        pt = snapshots_details['ins_id'][0]
        if ins_id.find(pt)>=0:
            constraint = {'input': tx_pair['input'], 'output': tx_pair['output']}
            ele = {'valid': False, 'spent': False}
            db_manager.update_a_row_with_constraint(db_manager.conn, 'utxo_spent_list', ele, constraint)
            return valid_spent
    
    constraint_info = {'ins_id': ins_id}
    row = db_manager.search_a_table_with_constraints(db_manager.conn, 'ltc20_ins_list', constraint_info)
    if len(row)>0:
        action = row[0][4]
        if action == 'transfer':
            valid = row[0][15]
            spent = row[0][16]
            if valid  and not spent:
                #we need set the utxo as spent
                row_info = {'spent': True, 'spent_tx': spent_tx, 'spent_offset': int(vout), 
                            'spent_to': tx_pair['address'], 'spent_height': tx_pair['height']}
                db_manager.update_a_row_with_constraint(db_manager.conn, 'ltc20_ins_list', row_info, constraint_info)

                #change the balance for who spending this transfer
                address_from = row[0][3] #be careful we set receiver as the who receive the transfer.
                address_to = tx_pair['address']
                tick = row[0][5]
                amt = row[0][9]
                ins_id = row[0][0]
                ele = {'address': address_from, 'tick': tick, 'transferable_delta': 0, 'available_delta': -amt, 
                        'total_delta': -amt, 'due_to_tx': spent_tx, 'due_to_ins': ins_id, 'height': tx_pair['height'],
                        'action': 'send'}
                db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_tx_history', ele)
                ele = {'address': address_to, 'tick': tick, 'transferable_delta': 0, 'available_delta': amt, 
                        'total_delta': amt, 'due_to_tx': spent_tx, 'due_to_ins': ins_id, 'height': tx_pair['height'],
                        'action': 'receive'}
                db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_tx_history', ele)

                constraint = {'address': address_to, 'tick': tick}
                row = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
                if len(row)==0:
                    ele = {'address': address_to, 'tick': tick, 'transferable': 0, 'available': amt, 'total': amt}
                    db_manager.insert_a_row_to_a_table(db_manager.conn, 'address_balance', ele)
                else:
                    ele = {'transferable': row[0][3], 'available': row[0][4] + amt, 'total': row[0][5] + amt}
                    db_manager.update_a_row_with_constraint(db_manager.conn, 'address_balance', ele, constraint)

                constraint = {'address': address_from, 'tick': tick}
                row = db_manager.search_a_table_with_constraints(db_manager.conn, 'address_balance', constraint)
                if len(row)==0:
                    print('Something is not right for the database in Updater!!!')
                else:
                    ele = {'transferable': row[0][3] - amt, 'available': row[0][4], 'total': row[0][5] - amt}
                    db_manager.update_a_row_with_constraint(db_manager.conn, 'address_balance', ele, constraint)

                valid_spent = True
            else:
                valid_spent = False
        else:
            valid_spent = False
    else:
        valid_spent = False

    if not valid_spent:
        constraint = {'input': tx_pair['input'], 'output': tx_pair['output']}
        ele = {'valid': False, 'spent': False}
        db_manager.update_a_row_with_constraint(db_manager.conn, 'utxo_spent_list', ele, constraint)

    return valid_spent

def take_a_history_checkpoint(db_manager, height, max_num_old_table, history_freq):
    num = max_num_old_table
    blk_num = history_freq
    if height%blk_num == 0:
        #add new tables
        table_balance = 'address_balance_{}'.format(height)
        table_tx = 'address_tx_history_{}'.format(height)
        constraint = {'height': height}
        row = db_manager.search_a_table_with_constraints(db_manager.conn, 'balance_history', constraint)
        if len(row)==0:
            db_manager.copy_a_table(db_manager.conn, 'address_balance', table_balance)
            db_manager.copy_a_table(db_manager.conn, 'address_tx_history', table_tx)
            ele = {'height': height, 
                    'address_balance': table_balance, 
                    'address_tx': table_tx}
            db_manager.insert_a_row_to_a_table(db_manager.conn, 'balance_history', ele)
            print('Save the snapshot for height: {}'.format(height))
        
        #drop old tables
        height_drop = height - num * blk_num
        constraint = {'height': height_drop}
        row = db_manager.search_a_table_with_constraints(db_manager.conn, 'balance_history', constraint)
        if len(row)>0:
            table_balance = row[0][1]
            table_tx = row[0][2]
            db_manager.drop_a_table(db_manager.conn, table_balance)
            db_manager.drop_a_table(db_manager.conn, table_tx)
            db_manager.delete_a_row_from_a_table(db_manager.conn, 'balance_history', constraint)
            print('Drop the snapshot for height: {}'.format(height_drop))