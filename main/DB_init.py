import os, sys
from psycopg2 import sql, pool

current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)
faster_directory =  os.path.abspath(os.path.join(current_directory, ".."))
path_cst = f"{faster_directory}/base"
sys.path.append(path_cst)
from DB_Base import DB_Base

from dotenv import load_dotenv
dotenv_path = f'{faster_directory}/config/.env'
load_dotenv(dotenv_path)

def generate_a_db_manager():
    init_setup = {'DBNAME': os.getenv('DB_IDX_NAME', default=''),
                  'USER': os.getenv('DB_IDX_USER', default=''),
                  'PASSWORD': os.getenv('DB_IDX_PASSWORD', default=''),
                  'HOST': os.getenv('DB_IDX_HOST', default='127.0.0.1'),
                  'PORT': os.getenv('DB_IDX_PORT', default='5432')}
    db_manager = DB_Base(init_setup)

    return db_manager

def init_idx_database(ele):
    db_manager = generate_a_db_manager()

    #create appuser (include check the appuser exists or not)
    appuser = os.getenv('DB_IDX_APPUSER', default='')
    appuser_password = os.getenv('DB_IDX_APPUSER_PWD', default='')
    user_setup = {'appuser': appuser, 'password': appuser_password}
    db_manager.create_an_appuser(user_setup)

    #create ordinals indexer database, and also grant the access to appuser
    db_name = os.getenv('DB_NAME')
    table_filen = os.getenv('TB_FILE')
    db_manager.initialize_database(db_name, table_filen, appuser)

    #init the table misc
    db_manager = generate_a_db_manager()
    db_manager.connect_with_postgres(db_name)

    row = db_manager.search_a_table_with_constraints(db_manager.conn, 'misc', {'id': 1})
    if len(row)==0:
        db_manager.insert_a_row_to_a_table(db_manager.conn, 'misc', ele)
    db_manager.conn.close()

