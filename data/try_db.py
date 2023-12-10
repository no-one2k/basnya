import sqlite3 as sq
import pandas as pd
import os
from tqdm import tqdm


def create_table(name_db: str):
    with sq.connect(f"{name_db}.db") as con:
        cur = con.cursor()

        cur.execute("""
           CREATE TABLE "player_1" (
               "index" INTEGER NOT NULL PRIMARY KEY,
               "PLAYER_ID" INTEGER,
               "PLAYER_NAME" TEXT,
               "TimeFrame" TEXT,
               "PTS" REAL,
               "AST" REAL,
               "REB" REAL,
               "ALL_STAR_APPEARANCES" INTEGER,
               "PIE" REAL DEFAULT NULL
           )
       """)

        cur.execute("""
           CREATE TABLE "player_2" (
               "index" INTEGER NOT NULL PRIMARY KEY,
               "SEASON_ID" INTEGER
           )
       """)

        cur.execute("""
           CREATE TABLE "teams" (
               "index" INTEGER NOT NULL PRIMARY KEY,
               "id" INTEGER,
               "full_name" TEXT,
               "abbreviation" TEXT,
               "nickname" TEXT,
               "city" TEXT,
               "state" TEXT,
               "year_founded" INTEGER
           )
        """)

        cur.execute("""
           CREATE TABLE "games" (
               "index" INTEGER NOT NULL PRIMARY KEY,
               "GAME_DATE_EST" TEXT,
               "GAME_SEQUENCE" INTEGER,
               "GAME_ID" INTEGER,
               "GAME_STATUS_ID" INTEGER,
               "GAME_STATUS_TEXT" TEXT,
               "GAMECODE" TEXT,
               "HOME_TEAM_ID" INTEGER,
               "VISITOR_TEAM_ID" INTEGER,
               "SEASON" INTEGER,
               "LIVE_PERIOD" INTEGER,
               "LIVE_PC_TIME" REAL,
               "NATL_TV_BROADCASTER_ABBREVIATION" REAL,
               "LIVE_PERIOD_TIME_BCAST" TEXT,
               "WH_STATUS" INTEGER,
               "GAME_ID_STR" TEXT
           )
        """)

        cur.execute("""
            CREATE TABLE "player_0" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "PERSON_ID" INTEGER,
                "FIRST_NAME" TEXT,
                "LAST_NAME" TEXT,
                "DISPLAY_FIRST_LAST" TEXT,
                "DISPLAY_LAST_COMMA_FIRST" TEXT,
                "DISPLAY_FI_LAST" TEXT,
                "PLAYER_SLUG" TEXT,
                "BIRTHDATE" TEXT,
                "SCHOOL" TEXT,
                "COUNTRY" TEXT,
                "LAST_AFFILIATION" TEXT,
                "HEIGHT" TEXT,
                "WEIGHT" INTEGER,
                "SEASON_EXP" INTEGER,
                "JERSEY" REAL,
                "POSITION" TEXT,
                "ROSTERSTATUS" TEXT,
                "GAMES_PLAYED_CURRENT_SEASON_FLAG" TEXT,
                "TEAM_ID" INTEGER,
                "TEAM_NAME" REAL,
                "TEAM_ABBREVIATION" REAL,
                "TEAM_CODE" REAL,
                "TEAM_CITY" REAL,
                "PLAYERCODE" TEXT,
                "FROM_YEAR" INTEGER,
                "TO_YEAR" INTEGER,
                "DLEAGUE_FLAG" TEXT,
                "NBA_FLAG" TEXT,
                "GAMES_PLAYED_FLAG" TEXT,
                "DRAFT_YEAR" TEXT,
                "DRAFT_ROUND" TEXT,
                "DRAFT_NUMBER" TEXT,
                "GREATEST_75_FLAG" TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_0" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_DATE_EST" TEXT,
                "GAME_SEQUENCE" INTEGER,
                "GAME_ID" INTEGER,
                "GAME_STATUS_ID" INTEGER,
                "GAME_STATUS_TEXT" TEXT,
                "GAMECODE" TEXT,
                "HOME_TEAM_ID" INTEGER,
                "VISITOR_TEAM_ID" INTEGER,
                "SEASON" INTEGER,
                "LIVE_PERIOD" INTEGER,
                "LIVE_PC_TIME" REAL,
                "NATL_TV_BROADCASTER_ABBREVIATION" TEXT,
                "LIVE_PERIOD_TIME_BCAST" TEXT,
                "WH_STATUS" INTEGER,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT home_team_id_fk FOREIGN KEY (HOME_TEAM_ID) REFERENCES teams (id),
                CONSTRAINT visitor_team_id_fk FOREIGN KEY (VISITOR_TEAM_ID) REFERENCES teams (id),
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID)
            )
        """)

        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_1" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "LEAGUE_ID" INTEGER,
                "TEAM_ID" INTEGER,
                "TEAM_ABBREVIATION" TEXT,
                "TEAM_CITY" TEXT,
                "PTS_PAINT" INTEGER,
                "PTS_2ND_CHANCE" INTEGER,
                "PTS_FB" INTEGER,
                "LARGEST_LEAD" INTEGER,
                "LEAD_CHANGES" INTEGER,
                "TIMES_TIED" INTEGER,
                "TEAM_TURNOVERS" INTEGER,
                "TOTAL_TURNOVERS" INTEGER,
                "TEAM_REBOUNDS" INTEGER,
                "PTS_OFF_TO" INTEGER,
                
                CONSTRAINT team_id_fk FOREIGN KEY (TEAM_ID) REFERENCES teams (id)
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_2" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "OFFICIAL_ID" INTEGER,
                "FIRST_NAME" TEXT,
                "LAST_NAME" TEXT,
                "JERSEY_NUM" INTEGER
            )
        """)

        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_3" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "PLAYER_ID" TEXT,
                "FIRST_NAME" TEXT,
                "LAST_NAME" TEXT,
                "JERSEY_NUM" TEXT,
                "TEAM_ID" TEXT,
                "TEAM_CITY" TEXT,
                "TEAM_NAME" TEXT,
                "TEAM_ABBREVIATION" TEXT,
                
                CONSTRAINT plauyer_id_fk FOREIGN KEY (PLAYER_ID) REFERENCES player_0 (PERSON_ID),
                CONSTRAINT team_id_fk FOREIGN KEY (TEAM_ID) REFERENCES teams (id)
            )
        """)

        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_4" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_DATE" TEXT,
                "ATTENDANCE" INTEGER,
                "GAME_TIME" TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_5" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_DATE_EST" TEXT,
                "GAME_SEQUENCE" INTEGER,
                "GAME_ID" INTEGER,
                "TEAM_ID" INTEGER,
                "TEAM_ABBREVIATION" TEXT,
                "TEAM_CITY_NAME" TEXT,
                "TEAM_NICKNAME" TEXT,
                "TEAM_WINS_LOSSES" TEXT,
                "PTS_QTR1" INTEGER,
                "PTS_QTR2" INTEGER,
                "PTS_QTR3" INTEGER,
                "PTS_QTR4" INTEGER,
                "PTS_OT1" INTEGER,
                "PTS_OT2" INTEGER,
                "PTS_OT3" INTEGER,
                "PTS_OT4" INTEGER,
                "PTS_OT5" INTEGER,
                "PTS_OT6" INTEGER,
                "PTS_OT7" INTEGER,
                "PTS_OT8" INTEGER,
                "PTS_OT9" INTEGER,
                "PTS_OT10" INTEGER,
                "PTS" INTEGER,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID),
                CONSTRAINT team_id_fk FOREIGN KEY (TEAM_ID) REFERENCES teams (id)
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_6" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_ID" TEXT,
                "LAST_GAME_ID" TEXT,
                "LAST_GAME_DATE_EST" TEXT,
                "LAST_GAME_HOME_TEAM_ID" TEXT,
                "LAST_GAME_HOME_TEAM_CITY" TEXT,
                "LAST_GAME_HOME_TEAM_NAME" TEXT,
                "LAST_GAME_HOME_TEAM_ABBREVIATION" TEXT,
                "LAST_GAME_HOME_TEAM_POINTS" TEXT,
                "LAST_GAME_VISITOR_TEAM_ID" TEXT,
                "LAST_GAME_VISITOR_TEAM_CITY" TEXT,
                "LAST_GAME_VISITOR_TEAM_NAME" TEXT,
                "LAST_GAME_VISITOR_TEAM_CITY1" TEXT,
                "LAST_GAME_VISITOR_TEAM_POINTS" TEXT,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID)
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_7" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_ID" INTEGER,
                "HOME_TEAM_ID" INTEGER,
                "VISITOR_TEAM_ID" INTEGER,
                "GAME_DATE_EST" TEXT,
                "HOME_TEAM_WINS" INTEGER,
                "HOME_TEAM_LOSSES" INTEGER,
                "SERIES_LEADER" TEXT,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT home_team_id_fk FOREIGN KEY (HOME_TEAM_ID) REFERENCES teams (id),
                CONSTRAINT visitor_team_id_fk FOREIGN KEY (VISITOR_TEAM_ID) REFERENCES teams (id),
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID)
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoresummaryv2_8" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_ID" INTEGER,
                "VIDEO_AVAILABLE_FLAG" INTEGER,
                "PT_AVAILABLE" INTEGER,
                "PT_XYZ_AVAILABLE" INTEGER,
                "WH_STATUS" INTEGER,
                "HUSTLE_STATUS" INTEGER,
                "HISTORICAL_STATUS" INTEGER,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID)
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoretraditionalv2_0" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_ID" INTEGER,
                "TEAM_ID" INTEGER,
                "TEAM_ABBREVIATION" TEXT,
                "TEAM_CITY" TEXT,
                "PLAYER_ID" INTEGER,
                "PLAYER_NAME" TEXT,
                "NICKNAME" TEXT,
                "START_POSITION" TEXT,
                "COMMENT" TEXT,
                "MIN" TEXT,
                "FGM" REAL,
                "FGA" REAL,
                "FG_PCT" REAL,
                "FG3M" REAL,
                "FG3A" REAL,
                "FG3_PCT" REAL,
                "FTM" REAL,
                "FTA" REAL,
                "FT_PCT" REAL,
                "OREB" REAL,
                "DREB" REAL,
                "REB" REAL,
                "AST" REAL,
                "STL" REAL,
                "BLK" REAL,
                "TO" REAL,
                "PF" REAL,
                "PTS" REAL,
                "PLUS_MINUS" REAL,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID),
                CONSTRAINT team_id_fk FOREIGN KEY (TEAM_ID) REFERENCES teams (id),
                CONSTRAINT player_id FOREIGN KEY (PLAYER_ID) REFERENCES player_0 (PERSON_ID)
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoretraditionalv2_1" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_ID" INTEGER,
                "TEAM_ID" INTEGER,
                "TEAM_NAME" TEXT,
                "TEAM_ABBREVIATION" TEXT,
                "TEAM_CITY" TEXT,
                "MIN" TEXT,
                "FGM" INTEGER,
                "FGA" INTEGER,
                "FG_PCT" REAL,
                "FG3M" INTEGER,
                "FG3A" INTEGER,
                "FG3_PCT" REAL,
                "FTM" INTEGER,
                "FTA" INTEGER,
                "FT_PCT" REAL,
                "OREB" INTEGER,
                "DREB" INTEGER,
                "REB" INTEGER,
                "AST" INTEGER,
                "STL" INTEGER,
                "BLK" INTEGER,
                "TO" INTEGER,
                "PF" INTEGER,
                "PTS" INTEGER,
                "PLUS_MINUS" REAL,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID)
                CONSTRAINT team_id_fk FOREIGN KEY (TEAM_ID) REFERENCES teams (id)
            )
        """)
        cur.execute("""
            CREATE TABLE "boxscoretraditionalv2_2" (
                "index" INTEGER NOT NULL PRIMARY KEY,
                "GAME_ID" INTEGER,
                "TEAM_ID" INTEGER,
                "TEAM_NAME" TEXT,
                "TEAM_ABBREVIATION" TEXT,
                "TEAM_CITY" TEXT,
                "STARTERS_BENCH" TEXT,
                "MIN" TEXT,
                "FGM" INTEGER,
                "FGA" INTEGER,
                "FG_PCT" REAL,
                "FG3M" INTEGER,
                "FG3A" INTEGER,
                "FG3_PCT" REAL,
                "FTM" INTEGER,
                "FTA" INTEGER,
                "FT_PCT" REAL,
                "OREB" INTEGER,
                "DREB" INTEGER,
                "REB" INTEGER,
                "AST" INTEGER,
                "STL" INTEGER,
                "BLK" INTEGER,
                "TO" INTEGER,
                "PF" INTEGER,
                "PTS" INTEGER,
                "GAME_ID_STR" TEXT,
                
                CONSTRAINT game_id_fk FOREIGN KEY (GAME_ID) REFERENCES GAMES (GAME_ID)
                CONSTRAINT team_id_fk FOREIGN KEY (TEAM_ID) REFERENCES teams (id)
            )
        """)


def add_data_to_db(name_db):
    with sq.connect(f"{name_db}.db") as con:
        bss_id_games = os.listdir('21-22/boxscoresummaryv2')
        bst_id_games = os.listdir('21-22/boxscoretraditionalv2')
        bss_id_games_20_21 = os.listdir('20-21/boxscoresummaryv2')
        bst_id_games_20_21 = os.listdir('20-21/boxscoretraditionalv2')
        players = os.listdir('20-21/players')
        teams = os.listdir('20-21/team')

        print('players')
        for player in tqdm(players):
            df = pd.read_csv(f'20-21/players/{player}')
            df.columns = df.columns.str.strip()
            name_table = player.split('_')
            name_table = f"{name_table[0]}_{name_table[1]}"
            df.to_sql(name_table, con, if_exists='append', index=False)

        print('teams')
        for team in tqdm(teams):
            df = pd.read_csv(f'20-21/team/{team}')
            df.columns = df.columns.str.strip()
            df.to_sql('teams', con, if_exists='append', index=False)

        print('games')
        for file_name in tqdm(bss_id_games):
            index = file_name.split('_')
            if index[1] == '0':
                df = pd.read_csv(f'21-22/boxscoresummaryv2/{file_name}')
                if 'GAME_ID' in df.columns:
                    game_id_str = file_name[:-4].split('_')
                    df['GAME_ID_STR'] = game_id_str[-1]
                df.columns = df.columns.str.strip()
                df.to_sql("games", con, if_exists='append', index=False)
        for file_name in tqdm(bss_id_games_20_21):
            index = file_name.split('_')
            if index[1] == '0':
                df = pd.read_csv(f'20-21/boxscoresummaryv2/{file_name}')
                if 'GAME_ID' in df.columns:
                    game_id_str = file_name[:-4].split('_')
                    df['GAME_ID_STR'] = game_id_str[-1]
                df.columns = df.columns.str.strip()
                df.to_sql("games", con, if_exists='append', index=False)

        print('boxscoresummaryv2 2021 - 2022')
        for file_name in tqdm(bss_id_games):
            df = pd.read_csv(f'21-22/boxscoresummaryv2/{file_name}')
            if 'GAME_ID' in df.columns:
                game_id_str = file_name[:-4].split('_')
                df['GAME_ID_STR'] = game_id_str[-1]
            df.columns = df.columns.str.strip()
            df.to_sql(file_name[:-15], con, if_exists='append', index=False)

        print('boxscoretraditionalv2 2021 - 2022')
        for file_name in tqdm(bst_id_games):
            df = pd.read_csv(f'21-22/boxscoretraditionalv2/{file_name}')
            if 'GAME_ID' in df.columns:
                game_id_str = file_name[:-4].split('_')
                df['GAME_ID_STR'] = game_id_str[-1]
            df.columns = df.columns.str.strip()
            df.to_sql(file_name[:-15], con, if_exists='append', index=False)

        print('boxscoresummaryv2 2020 - 2021')
        for file_name in tqdm(bss_id_games_20_21):
            df = pd.read_csv(f'20-21/boxscoresummaryv2/{file_name}')
            if 'GAME_ID' in df.columns:
                game_id_str = file_name[:-4].split('_')
                df['GAME_ID_STR'] = game_id_str[-1]
            df.columns = df.columns.str.strip()
            df.to_sql(file_name[:-15], con, if_exists='append', index=False)

        print('boxscoretraditionalv2 2020 - 2021')
        for file_name in tqdm(bst_id_games_20_21):
            df = pd.read_csv(f'20-21/boxscoretraditionalv2/{file_name}')
            if 'GAME_ID' in df.columns:
                game_id_str = file_name[:-4].split('_')
                df['GAME_ID_STR'] = game_id_str[-1]
            df.columns = df.columns.str.strip()
            df.to_sql(file_name[:-15], con, if_exists='append', index=False)


def create_season_type():
    with sq.connect('test.db') as con:
        cur = con.cursor()
        cur.execute("""ALTER TABLE "games" ADD COLUMN "season_type" INTEGER REFERENCES season_types(season_type_id) """)


def add_type_season(name_db: str) -> None:
    with sq.connect(f'{name_db}.db') as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE season_types("season_type_id" INTEGER NOT NULL PRIMARY KEY, "description" TEXT)
        """)

        cur.execute("""
        INSERT INTO season_types("season_type_id", "description") VALUES (1, "Pre Season");
        """)
        cur.execute("""
        INSERT INTO season_types("season_type_id", "description") VALUES (2, "Regular Season");
        """)
        cur.execute("""
        INSERT INTO season_types("season_type_id", "description") VALUES (3, "All Star");
        """)
        cur.execute("""
        INSERT INTO season_types("season_type_id", "description") VALUES (4, "Playoffs");
        """)

        cur.execute("""
        ALTER TABLE games ADD COLUMN season_type REFERENCES season_types(season_type_id);
        """)

        game_ids_str = cur.execute('SELECT GAME_ID_STR FROM games').fetchall()
        for id in game_ids_str:
            if id[0][2] == '1':
                cur.execute(f"""
                UPDATE games SET season_type=1 WHERE GAME_ID_STR="{str(id[0])}"
                """)
            if id[0][2] == '2':
                cur.execute(f"""
                UPDATE games SET season_type=2 WHERE GAME_ID_STR="{str(id[0])}"
                """)
            if id[0][2] == '3':
                cur.execute(f"""
                UPDATE games SET season_type=3 WHERE GAME_ID_STR="{str(id[0])}"
                """)
            if id[0][2] == '4':
                cur.execute(f"""
                UPDATE games SET season_type=4 WHERE GAME_ID_STR="{str(id[0])}"
                """)
