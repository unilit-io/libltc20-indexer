import yaml
import psycopg2

class DB_Base():
    def __init__(self, init_setup):
        #setup the default db info.
        #before we create any new database, we need this default db to connect with postgres
        self.db_info = {'database': init_setup['DBNAME'],
                        'user': init_setup['USER'],
                        'password': init_setup['PASSWORD'],
                        'host': init_setup['HOST'],
                        'port': init_setup['PORT']}

        #conn with postgres
        self.conn = None
        self.cur = None


    '''
    connect with the postgres with postgres setup
    '''
    def connect_with_postgres(self, database_name):
        self.conn = psycopg2.connect(database = database_name.lower(), 
                                user=self.db_info['user'], 
                                password=self.db_info['password'], 
                                host=self.db_info['host'], 
                                port=self.db_info['port'])
        #autocommit on
        self.conn.autocommit = True

        #define the cursor to manipulate the database
        self.cur = self.conn.cursor()  
        print('Connect with db {} successfully.'.format(database_name)) 

    '''
    create a database
    '''
    def create_a_database(self, new_dbs_name):
        #connect postgres database using admin account
        self.connect_with_postgres(self.db_info['database'])

        sql_create_database = ''' CREATE database {} '''.format(new_dbs_name)
        try:
            self.cur.execute(sql_create_database)
            self.conn.commit()
            return True
            print("Database {} has been created successfully.".format(new_dbs_name))
        except:
            #maybe the user want to migrate the database instead of doing nothing
            #he/she can modify this section for his/her purpose
            print("Database {} exists. Please let me know what should I do.".format(new_dbs_name))
            return False
        
        #close the conn
        self.conn.close()

    '''
    create an app user. For safety issue we will use app user 
    instead of the default login user to manage the database
    '''
    def create_an_appuser(self, user_setup):
        appuser = user_setup['appuser'].lower()
        appuser_password = user_setup['password']

        #connect with postgres db using admin account
        self.connect_with_postgres(self.db_info['database'])
        
        #query whether the appuser exists
        query = 'select * from pg_authid where rolname=\'{}\';'.format(appuser)
        self.cur.execute(query)
        nuser = self.cur.fetchall()

        if len(nuser)==0:
            print('The app user does not exist. Create it')
            query = 'CREATE ROLE {} with LOGIN PASSWORD \'{}\''.format(appuser, appuser_password)
            self.cur.execute(query)
            self.conn.commit()
        else:
            print('The app user already exists.')
        
        #close the conn
        self.conn.close()

    '''
    grant the access of the database to the appuser
    '''
    def grant_access_to_appuser(self, appuser):
        query = 'GRANT ALL ON ALL TABLES IN SCHEMA \"public\" TO {};'.format(appuser)
        self.cur.execute(query)
        self.conn.commit()

    '''
    create a table
    '''
    def create_a_table(self, table_name, table_row):
        table_name = table_name.lower()

        #see whether the table exist
        sql_seq = 'select * from information_schema.tables where table_name=\'{}\';'.format(table_name)
        self.cur.execute(sql_seq)
        ntable = self.cur.fetchall()

        create_flag = False
        if len(ntable)==0:
            print('We need create table [{}]...'.format(table_name))
            create_flag = True
        else: 
            sql_seq = 'select COLUMN_NAME from information_schema.columns where table_name=\'{}\';'.format(table_name)
            self.cur.execute(sql_seq)
            info_table = self.cur.fetchall()
            
            if len(info_table)==len(table_row):
                print('The table [{}] is fine.'.format(table_name))
                create_flag = False
            else:
                print('Seems the table {} changes. Will drop it and then create'.format(table_name))
                sql_seq = 'drop table {}'.format(table_name)
                self.cur.execute(sql_seq)
                self.conn.commit()
                create_flag = True

        if create_flag:
            #the information allows to be NULL or NOT NULL is setting in db_tables.yml
            sql_p1f = 'CREATE TABLE {} '.format(table_name)

            sql_p2 = '({} {},'.format(table_row[0][0], table_row[0][1])
            for ii in range(1, len(table_row)):
                sql_p2 = sql_p2 + ' {} {},'.format(table_row[ii][0], table_row[ii][1])
            sql_p2f = sql_p2[:len(sql_p2)-1]+')'
            sql_seq = sql_p1f + sql_p2f

            #create tables
            self.cur.execute(sql_seq)
            self.conn.commit()

    '''
    load table setup file
    '''
    def load_tables_setup(self, tables_setup_file):
        with open(tables_setup_file, 'r') as file:
            yt_service = yaml.safe_load(file)
    
        tables = list(yt_service.keys())
        dict_table = {}
        for tb in tables:
            tb_item = list(yt_service[tb].keys())
            dict_table[tb] = []
            for tc in tb_item:
                tc_set = yt_service[tb][tc]
                item_c = [tc, tc_set]
                dict_table[tb].append(item_c) 
        return dict_table  

    '''
    initialize the database
    '''
    def initialize_database(self, db_name, table_filen_list, appuser):
        #used to manipulate databases.
        self.new_dbname = db_name
        self.table_filen = table_filen_list

        #create database
        flag_cd = self.create_a_database(self.new_dbname)

        #might need migrat data
        if flag_cd==False:
            #we need consider the migration of the database if anything changes.. for now we omit this.
            pass

        #connect with newly create database
        self.new_dbname = self.new_dbname.lower()
        self.connect_with_postgres(self.new_dbname)

        #load table setup
        print('The table setup file is [{}]'.format(self.table_filen))
        self.db_tables = self.load_tables_setup(self.table_filen)

        #create tables
        tables = list(self.db_tables.keys())
        for ky in range(len(tables)):
            table_name = tables[ky]
            table_info = self.db_tables[ table_name ]
            self.create_a_table(table_name, table_info)

        #after the tables are created, we need grant access to appuser
        self.grant_access_to_appuser(appuser)

        #close the connection
        self.conn.close()

    #we cannot search with constraint info containing lists.
    #if you want search that, please use elastic search instead
    @staticmethod
    def search_a_table_with_constraints(conn, table_name, constraint_info):
        table_name = table_name.lower()

        sql_p1f = 'SELECT * FROM {} '.format(table_name)

        sql_p2 = 'WHERE '
        for k in constraint_info.keys():
            sql_p2 = sql_p2 + k.lower() + '=' + '\'' + str(constraint_info[k]) + '\'' + ' and '
        sql_p2f = sql_p2[:len(sql_p2)-5]
        
        sql = sql_p1f + sql_p2f

        #get rows
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.commit()
        
        return rows

    #row_info can contain a list.
    @staticmethod
    def insert_a_row_to_a_table(conn, table_name, row_info):
        table_name = table_name.lower()

        #generate sql excute
        sql_p1f = 'INSERT INTO {} '.format(table_name)
        
        sql_p2 = '('
        sql_p3 = 'VALUES ('
        for k in row_info.keys():
            sql_p2 = sql_p2 + k + ', '
            if type(row_info[k])==list:
                valuec = '{' + ','.join(row_info[k]) + '}'
            else:
                valuec = str(row_info[k])
                valuec = valuec.replace('\'', '*')
            sql_p3 = sql_p3 + '\'' + valuec +'\', '
        sql_p2f = sql_p2[:len(sql_p2)-2] + ') '
        sql_p3f = sql_p3[:len(sql_p3)-2] + ')'

        sql = sql_p1f + sql_p2f + sql_p3f
        
        #insert the new row into the table...
        #print(sql)
        cur = conn.cursor()
        try:
            cur.execute(sql)
            conn.commit()
        except:
            #print('The item already exists')
            pass

    #row_info can contain a list.
    @staticmethod
    def update_a_row_with_constraint(conn, table_name, row_info, constraint_info):
        table_name = table_name.lower()

        sql_p1f = 'UPDATE {} '.format(table_name)

        sql_p2 = 'SET '
        for k in row_info.keys():
            if type(row_info[k])==list:
                valuec = '{' + ','.join(row_info[k]) + '}'
            else:
                valuec = str(row_info[k])
                valuec = valuec.replace('\'', '*')
            subsec = k.lower() + '=' + '\'' + valuec + '\'' + ', '
            sql_p2 = sql_p2 + subsec
        sql_p2f = sql_p2[:len(sql_p2)-2]

        sql_p3 = ' WHERE '
        for k in constraint_info.keys():
            sql_p3 = sql_p3 + k.lower() + '=' + '\'' + str(constraint_info[k]) + '\'' + ' and '
        sql_p3f = sql_p3[:len(sql_p3)-5]

        sql = sql_p1f + sql_p2f + sql_p3f

        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()

    @staticmethod
    def delete_a_row_from_a_table(conn, table_name, constraint_info):
        table_name = table_name.lower()

        sql_p1f = 'DELETE FROM {} '.format(table_name)
        sql_p2 = 'WHERE '
        for k in constraint_info.keys():
            sql_p2 = sql_p2 + k.lower() + '=' + '\'' + str(constraint_info[k]) + '\'' + ' and '
        sql_p2f = sql_p2[:len(sql_p2)-5]

        sql = sql_p1f + sql_p2f

        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()

    #copy a table.
    @staticmethod
    def copy_a_table(conn, table_name, new_table_name):
        table_name = table_name.lower()
        new_table_name = new_table_name.lower()

        #copy the old table to new table
        cur = conn.cursor()
        cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
        table_structure = cur.fetchall()
        conn.commit()

        columns = ", ".join(f"{col[0]} {col[1]}" for col in table_structure)
        cur.execute(f"CREATE TABLE {new_table_name} ({columns})")
        conn.commit()

        sql = "INSERT INTO {} SELECT * FROM {}".format(new_table_name, table_name)
        cur.execute(sql)
        conn.commit()

        print('Copy {} as {} finished.'.format(table_name, new_table_name))

    #drop a table from the database
    @staticmethod
    def drop_a_table(conn, table_name):
        table_name = table_name.lower()

        cur = conn.cursor()
        sql = "DROP TABLE IF EXISTS {}".format(table_name)
        cur.execute(sql)
        conn.commit()

        print('Drop table {} finished.'.format(table_name))

