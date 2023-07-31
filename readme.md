<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/unilit-io/libltc20-indexer.git">
    <img src="assets/images/logo@128x.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">UniLit Indexer (ltc-20) library</h3>

  <p align="center">
    This library fully implements the specification protocol of ltc-20.
    <br />
    <br />
    <a href="https://github.com/unilit-io/libltc20-indexer/issues">Report Bug</a>
    ·
    <a href="https://github.com/unilit-io/libltc20-indexer/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

Developers can integrate this library in the code according to their needs.

When the `main/Updater.py` program is running, it will analyze and index the latest data based on the input data, and output a detailed list of all Token information and holder balances in postgreSQL database.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started
To get a local copy up and running follow these simple example steps.

### Prerequisites
1. Install PostgreSQL locally.
* postgreSQL (Linux)
  ```sh
  sudo apt-get install postgresql postgresql-client
  ```
  The Linux system can directly switch to the Postgres user to start the command line tool.
  ```
  sudo -u postgres psql
  ```
  Install python-postgresql
  ```
  pip3 install psycopg2-binary
  ```
  Modify postgreSQL password
  ```
  sudo -u postgres psql
  \\password
  ```
* postgreSQL (Mac)
  ```sh
  brew install postgresql
  ```
  Mac start the server:  
  ```
  brew services start postgresql
  ```

2. Set up your own env file in `config/.env`. 
   ```js
    DB_IDX_NAME = 'postgres' #the default db name. use to login the postgres system for the first time.
    DB_IDX_USER = 'postgres'   #the default user.
    DB_IDX_PASSWORD = 'your_password' #the default user password
    DB_IDX_APPUSER = 'unilitioapp' #the application user for pgbouncer
    DB_IDX_APPUSER_PWD = 'ULDBXQ_Auns0oP' #the application user password for pgbouncer

    DB_IDX_HOST = '127.0.0.1' #host
    DB_IDX_PORT = '5432' #port
    DB_NAME = 'unilit_idx' #name of the db

    TB_FILE = '../config/IDX_tables.yml' #table structure file.
    SP_FILE = '../config/Snapshots.yml'  #snapshot details file
   ```

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/unilit-io/libltc20-indexer.git
   ```

2. Download Litecoin core 0.21.2.2 from official website https://litecoin.org/

    ```sh
    tar -zxvf litecoin-0.21.2.2-x86_64-linux-gnu.tar.gz
    sudo install -m 0755 -o root -g root -t /usr/local/bin ~/litecoin-0.21.2.2/bin/*
    ```

3. Now start litecoin node with daemon
    ```
    litecoind
    ```

4. Edit `litecoin.conf` the full node settings to make sure ordinals sync 
    ```
    cd ~/.litecoin
    vi litecoin.conf
    ```
    fill the content and save
    ```
    txindex=1
    rpcserialversion=1
    ```

5. Run the Litecoin full node until fully sync (depend on your network, generally it takes serveral hours to a day. You need to prepare an empty space over 150GB) 

6. Set up ord-litecoin server (Optional using ordinalslite.com). Download `ord-litecoin 0.5.2` from release for your platform.

7. Sync the full ordinals with sats. 
    ```sh
    ./ord --index-sats index
    ```

8. Compile another `ord-litecoin` api branch with Cargo. After the compile, run the local server.
    ```
    ./ord server
    ```

9. run `main/Updater.py`
    ```sh
    pip install psycopg2-binary tqdm python-dotenv
    ```

    ```python
    # use which full-node and ord server. 
    # If you have your own server, change it to 
    url_base = 'https://ordinalslite.com'

    #the mode.
    # if mode==UPDATE_BLK_BY_BLK. It can be slow but it is easy for you to understand how indexer works
    # if mode==FAST_CATCHUP, then you need download all tx_pairs and all inscription history first
    mode = 'UPDATE_BLK_BY_BLK'

    # you need change the biggest height in the database in the fast catchup setting
    fast_catchup_target_height = 2467872
    ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [x] Add Changelog
- [x] Python version 1.0.0
- [x] Two running modes (Vectorized/Block-by-block)
- [ ] Shared litecoin full-node data
- [ ] Shared ord-litecoin .redb data
- [ ] Updated Golang version
- [ ] Indexer directly from Litecoin-full-node binary info in transactions

See the [open issues](https://github.com/unilit-io/libltc20-indexer/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

UniLit - [@unilit_io](https://twitter.com/unilit_io) - admin@unilit.io

Project Link: [https://github.com/unilit-io/libltc20-indexer.git](https://github.com/unilit-io/libltc20-indexer.git)

<p align="right">(<a href="#readme-top">back to top</a>)</p>