#!/usr/bin/env python3
import os
import urllib.parse
import mysql.connector

APP_TITLE = os.getenv("APP_TITLE", "Aiven DB Viewer")
DB_URL = os.getenv("DB_URL")  # Set this in your .env file: mysql://user:pass@host:port/database?ssl-mode=REQUIRED
TABLE = os.getenv("TABLE", "traders")  # Default table to view

if not DB_URL:
    raise RuntimeError("Set DB_URL env var to your Aiven MySQL URL")

u = urllib.parse.urlparse(DB_URL)

# Optional CA cert (download from Aiven if you want strict verification)
SSL_CA = os.getenv("SSL_CA")  # path to PEM file mounted in container/host

def get_conn():
    cfg = dict(
        host=u.hostname,
        port=u.port or 3306,
        user=u.username,
        password=u.password,
        database=u.path.lstrip("/"),
    )
    # Aiven requires SSL; mysql-connector-python accepts these flags
    if SSL_CA:
        cfg.update(ssl_ca=SSL_CA, ssl_verify_cert=True)
    else:
        cfg.update(ssl_disabled=False)
    return mysql.connector.connect(**cfg)

if __name__ == "__main__":
    conn = get_conn()
    # list all the tables
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    print("Tables:", tables)

    # get the row count of the 'traders' table
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM traders")
    row_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    print("Row count for 'traders':", row_count)

    # # remove all the raws from traders
    # conn = get_conn()
    # cursor = conn.cursor()
    # cursor.execute("DELETE FROM traders")
    # conn.commit()
    # cursor.close()
    # conn.close()

    # # get the row count of the 'traders' table
    # conn = get_conn()
    # cursor = conn.cursor()
    # cursor.execute("SELECT COUNT(*) FROM traders")
    # row_count = cursor.fetchone()[0]
    # cursor.close()
    # conn.close()
    # print("Row count for 'traders':", row_count)

    # get all the columns from the 'traders' table
    # conn = get_conn()
    # cursor = conn.cursor()
    # cursor.execute("SHOW COLUMNS FROM traders")
    # columns = cursor.fetchall()
    # cursor.close()
    # conn.close()
    # print("Columns in 'traders':", columns)

    # # create new table "well_performed" the traders which have avg_trade_size >=1000 , win_rate >=50 and trades > 100
    # conn = get_conn()
    # cur = conn.cursor()
    # cur.execute("CREATE TABLE IF NOT EXISTS well_performed LIKE traders")
    # cur.execute("TRUNCATE TABLE well_performed")

    # # thresholds – tweak as you like
    # thr = {
    #     "gross_profit": 500.0,
    #     "win_rate": 55.0,
    #     "trades": 20,
    #     "avg_trade_size": 50.0,
    # }

    # sql = """
    #     INSERT INTO well_performed
    #     (wallet_address, token_address, gross_profit, win_rate, wins, losses, trade_volume, trades, avg_trade_size)
    #     SELECT wallet_address, token_address, gross_profit, win_rate, wins, losses, trade_volume, trades, avg_trade_size
    #     FROM traders
    #     WHERE gross_profit >= %s
    #     AND win_rate >= %s
    #     AND trades >= %s
    #     AND avg_trade_size >= %s
    # """
    # cur.execute(sql, (thr["gross_profit"], thr["win_rate"], thr["trades"], thr["avg_trade_size"]))
    # conn.commit()
    # cur.close()
    # conn.close()

    # # get the raw count of well_performed
    # conn = get_conn()
    # cursor = conn.cursor()
    # cursor.execute("SELECT COUNT(*) FROM well_performed")
    # well_performed_count = cursor.fetchone()[0]
    # cursor.close()
    # conn.close()
    # print("Count of well_performed:", well_performed_count)

    # # get the row count of the 'traders' table
    # conn = get_conn()
    # cursor = conn.cursor()
    # cursor.execute("SELECT COUNT(*) FROM traders")
    # row_count = cursor.fetchone()[0]
    # cursor.close()
    # conn.close()
    # print("Row count for 'traders':", row_count)

