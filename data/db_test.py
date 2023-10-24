import sqlite3 as sq
import pandas as pd
import os


id_games = os.listdir('playbyplayv2')
while 'play' in id_games[0]:
    id = id_games[0][13:-4]
    id_games.append(id)
    id_games.pop(0)
con = sq.connect('test.db')
for id in id_games:
    df = pd.read_csv(f'playbyplayv2/playbyplayv2_{id}.csv')
    df.columns = df.columns.str.strip()
    df.to_sql(id, con, if_exists='replace')

con.close()
