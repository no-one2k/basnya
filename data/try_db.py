import pandas as pd
import sqlite3 as sq
import os
bss_id_games = os.listdir('21-22/boxscoresummaryv2')
bst_id_games = os.listdir('21-22/boxscoretraditionalv2')
players = os.listdir('20-21/players')
teams = os.listdir('20-21/team')
# df = pd.read_csv(f'20-21/boxscoresummaryv2/{bss_id_games[0]}')
# print(', '.join(df.columns.tolist()))
# df = pd.read_csv(f'20-21/boxscoresummaryv2/{bss_id_games[0]}', dtype=dtypes_bss_0)
# for i in df.iloc[0]:
#     print(i)
with sq.connect('bas.db') as con:
    for file_name in bss_id_games:
        df = pd.read_csv(f'21-22/boxscoresummaryv2/{file_name}')
        if 'GAME_ID' in df.columns:
            game_id_str = file_name[:-4].split('_')
            df['GAME_ID_STR'] = game_id_str[-1]
        df.columns = df.columns.str.strip()
        df.to_sql(file_name[:-15], con, if_exists='append')


    procces_files = len(bst_id_games)
    for file_name in bst_id_games:
        df = pd.read_csv(f'21-22/boxscoretraditionalv2/{file_name}')
        if 'GAME_ID' in df.columns:
            game_id_str = file_name[:-4].split('_')
            df['GAME_ID_STR'] = game_id_str[-1]
        df.columns = df.columns.str.strip()
        df.to_sql(file_name[:-15], con, if_exists='append')
        procces_files -= 1
        print(f'Осталось {procces_files} сделать')


    count_players = len(players)
    flag = True
    for player in players:
        try:
            df = pd.read_csv(f'20-21/players/{player}')
            df.columns = df.columns.str.strip()
            name_table = player.split('_')
            name_table = f"{name_table[0]}_{name_table[1]}"
            df.to_sql(name_table, con, if_exists='append')
            if flag and name_table[-1] == '1':
                cur = con.cursor()
                cur.execute(f"""ALTER TABLE {name_table} ADD COLUMN PIE REAL DEFAULT NULL
                """)
                flag = False
            count_players -= 1
            print('Осталось еще', count_players, 'игроков')
            non_error = player
        except Exception as e:
            print(e)
            print(f'Проблема тут брат, {non_error} и {player}')


    for team in teams:
        df = pd.read_csv(f'20-21/team/{team}')
        df.columns = df.columns.str.strip()
        df.to_sql('teams', con, if_exists='append')