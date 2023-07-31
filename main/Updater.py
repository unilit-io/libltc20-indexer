import requests
import json
from tqdm import tqdm
from multiprocessing.dummy import Pool as ThreadPool
import time, os, sys
import yaml

from Updater_wrapper import *

from dotenv import load_dotenv
dotenv_path = '../Config/.env'
load_dotenv(dotenv_path)


if __name__=='__main__':
    # use which full-node and ord server. 
    # If you have your own server, change it to 
    url_base = 'https://ordinalslite.com'

    #the mode.
    # if mode==UPDATE_BLK_BY_BLK. It can be slow but it is easy for you to understand how indexer works
    # if mode==FAST_CATCHUP, then you need download all tx_pairs and all inscription history first
    mode = 'UPDATE_BLK_BY_BLK'

    # you need change the biggest height in the database in the fast catchup setting
    fast_catchup_target_height = 2467872

    #backup tables parameters
    max_num_old_table = 5
    history_freq = 1000

    '''------------------------------------------------------------------
    ------------------------------------------------------------------
    in most of time, you do not need to change the following code
    ------------------------------------------------------------------
    ------------------------------------------------------------------'''
    #init the db
    # we start from the first ltc20 inscription.
    ele = {'last_ins_num': 224060, 'last_height': 2465225}
    init_idx_database(ele)

    # build a connetion with the db
    db_manager = generate_a_db_manager()
    db_name = os.getenv('DB_NAME')
    db_manager.connect_with_postgres(db_name)

    #snapshot details:
    snapshots_file = os.getenv('SP_FILE')
    with open(snapshots_file, 'r') as file:
        snapshots_details = yaml.safe_load(file)
    
    # get the last_in_num and last_height in the db
    row = db_manager.search_a_table_with_constraints(db_manager.conn, 'misc', {'id': 1})
    last_ins_num = row[0][1]
    last_height = row[0][2]
    print('The last ins num in the db (included) is {}.'.format(last_ins_num))
    print('The last height in the db (included) is {}.'.format(last_height))


    # get current height and current ins_num in the blockchain
    current_height = get_current_height(url_base)
    current_ins_num = get_current_ins_num(url_base)
    print('The current height and ins_num is {} and {}.'.format(current_height, current_ins_num))

    #for any mode, we download snapshots first 
    # so even for UPDATE_BLK_BY_BLK we do not need to download snapshots transfer anymore.
    get_snapshots_data_until_target_height_seq(url_base, db_manager, snapshots_details, True, None)

    # ok. let start to catch up with these
    if mode == 'FAST_CATCHUP':
        if fast_catchup_target_height < last_height:
            #the database is not ok. switch to UPDATE_BLK_BY_BLK mode
            print('*****BE CAREFUL**** we set the mode as UPDATE_BLK_BY_BLK')
            mode == 'UPDATE_BLK_BY_BLK'
        else:
            #download data. #we will only modify ltc20_ins_list and utxo_spent_list
            get_ins_data_until_target_height_all_seq(url_base, db_manager, last_ins_num, 
                                                        last_height, fast_catchup_target_height) 
            get_txpairs_until_target_height_seq(url_base, db_manager, last_height, 
                                                        fast_catchup_target_height)

    continue_flag = True
    s = time.time()
    blk_num = 0
    while continue_flag:
        ss = time.time()

        #if the fast catchup already exhaust all data. Then stop
        #for update you need swith from the fast catchup mode to update blk by blk mode.
        if last_height > fast_catchup_target_height and mode == 'FAST_CATCHUP':
            mode = 'UPDATE_BLK_BY_BLK'
        
        #update the current height
        #if there is no new height, wait for the new height..
        current_height = get_current_height(url_base)
        remain = current_height - last_height
        while remain == 0:
            time.sleep(30)
            current_height = get_current_height(url_base)
            remain = current_height - last_height

        print('Current height {} and we are at {}. {} blocks remain.'.format(current_height, last_height, remain))
        es = time.time()
        print('{} blocks finished. {} sec consumes in total'.format(blk_num, es-s))

        #get the data for the next block
        height = last_height + 1

        # get ranked tx in this block
        # ranked tx includes both the paired input/output spent AND the newly inscribed inscription
        all_tx_value, last_ins_num_block = get_ranked_txpair_and_ins_at_a_height(url_base, db_manager, height, snapshots_details, last_ins_num, mode)
        print(all_tx_value)
        print(last_ins_num_block)

        # modify the balance according to the ranked tx
        for a in all_tx_value:
            if a[3]['type']=='ins':
                modify_balance_by_new_inscribed_inscription(db_manager, a[3]['data'])
            if a[3]['type']=='txpair':
                valid_spent = modify_balance_according_to_a_tx_pair(db_manager, a[3]['data'], snapshots_details)

        #move to the next block
        last_height = height
        last_ins_num = last_ins_num_block
        blk_num = blk_num + 1

        # update the current position
        ele = {'last_ins_num': last_ins_num, 'last_height': last_height}
        row = db_manager.update_a_row_with_constraint(db_manager.conn, 'misc', ele, {'id': 1})

        # take a snapshot
        #take_a_history_checkpoint(db_manager, height, max_num_old_table, history_freq)

        ee = time.time()

        print('Spend: {} sec for the current block'.format(ee-ss))
        print('======================================')

        time.sleep(100)

    db_manager.conn.close()
