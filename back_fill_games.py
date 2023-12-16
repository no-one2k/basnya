import datetime
import sqlite3
from collections import defaultdict
import datetime as dt
from typing import List, Tuple

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, boxscoresummaryv2, boxscoretraditionalv2, commonplayerinfo
from prefect import task, flow


DEFAULT_GAMES_COLUMNS = ['unseen_game', 'game_id', 'game_date', 'teams', 'score']


# @task(log_prints=True)
def get_db_path() -> str:
    """
    Get the path to the SQLite database file.

    Returns:
    - str: The path to the SQLite database file.
    """
    result = 'basnya.db'
    print(f"DB path: '{result}'")
    return result


# @task(retries=2, log_prints=True)
def get_latest_game(db_path: str) -> pd.DataFrame:
    """
    Retrieve the row(s) for the game(s) with the latest GAME_DATE_EST from the "GAMES" table.

    Parameters:
    - db_path (str): The path to the SQLite database file.

    Returns:
    - pd.DataFrame or None: A DataFrame containing the row(s) for the game(s) with the latest GAME_DATE_EST,
      or None if an error occurs.
    """
    # SQL query to find the game with the latest GAME_DATE_EST
    sql_query = """
    SELECT *
    FROM "GAMES"
    WHERE "GAME_DATE_EST" = (SELECT MAX("GAME_DATE_EST") FROM "GAMES");
    """

    # Use 'with' statement to automatically close the connection
    with sqlite3.connect(db_path) as connection:
        # Use pandas to execute the SQL query and read the results into a DataFrame
        result_df = pd.read_sql(sql_query, connection)
    if result_df.empty:
        print("DB seems to be empty")
    else:
        print(f"Found games on latest date of '{result_df.GAME_DATE_EST.iloc[0]}': {len(result_df)}")
    return result_df


def game_id_2_season_type(game_id: str) -> int:
    if game_id[0] == '0':
        if game_id[2] == '1':
            return 1  # Pre Season
        elif game_id[2] == '2':
            return 2  # Regular Season
        elif game_id[2] == '3':
            return 3  # All Star
        elif game_id[2] in ['4', '5']:
            return 4  # Playoffs or Play-in
        else:
            return 1  # Pre Season
    else:
        return 1  # Pre Season


def enrich_game_finder_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Modifies dataframe by adding columns 'GAME_ID_STR' and 'season_type'

    Parameters:
    - df: result of `LeagueGameFinder(...).get_data_frames()[0]`
    Returns:
    - pd.DataFrame: input dataframe with 2 new columns
    """
    df['GAME_ID_STR'] = df.GAME_ID
    df.GAME_ID = df.GAME_ID.astype(int)
    df['season_type'] = df.GAME_ID_STR.map(game_id_2_season_type)
    return df


def add_game_id_str(df: pd.DataFrame) -> pd.DataFrame:
    """
    Modifies dataframe by adding column 'GAME_ID_STR'

    Parameters:
    - df: result of nba_api.SomeEndpoint().get_data_frames()[i]`
    Returns:
    - pd.DataFrame: input dataframe with 1 new column
    """
    if 'GAME_ID' in df.columns:
        df['GAME_ID_STR'] = df.GAME_ID
        df.GAME_ID = df.GAME_ID.astype(int)
    return df


# @task(retries=2, log_prints=True)
def get_games_from_to(date_from, date_to):
    """
    Get NBA games DataFrame within a specified date range.

    Parameters:
    - date_from: Start date for the search range.
    - date_to: End date for the search range.

    Returns:
    - pd.DataFrame: Concatenated DataFrame of NBA games within the specified date range.
    """
    _dfs = []
    for s_t in [leaguegamefinder.SeasonTypeNullable.regular, leaguegamefinder.SeasonTypeNullable.playoffs]:
        _df = leaguegamefinder.LeagueGameFinder(
            date_from_nullable=(pd.to_datetime(date_from) + pd.Timedelta(days=1)).strftime('%m/%d/%Y'),
            date_to_nullable=pd.to_datetime(date_to).strftime('%m/%d/%Y'),
            season_type_nullable=s_t,
            league_id_nullable=leaguegamefinder.LeagueIDNullable.nba
        ).get_data_frames()[0]
        _dfs.append(_df)
    return pd.concat(_dfs, axis=0)


# @task(retries=2, log_prints=True)
def get_games_by_ids(game_ids: List[str]) -> pd.DataFrame:
    """
    Get NBA games DataFrame by a list of game IDs.

    Parameters:
    - game_ids (List[str]): List of NBA game IDs.

    Returns:
    - pd.DataFrame: Concatenated DataFrame of NBA games corresponding to the given game IDs.
    """
    _dfs = []
    for g_i in game_ids:
        _game_df = boxscoresummaryv2.BoxScoreSummaryV2(game_id=g_i).get_data_frames()[0]
        if _game_df.empty:
            print(f'not found game for id: {g_i}')
        _dfs.append(_game_df)
    return pd.concat(_dfs, axis=0)


def get_games_minimal_date(games_by_ids_df: pd.DataFrame) -> str:
    """
    Get the minimal date from a DataFrame of NBA games.

    Parameters:
    - games_by_ids_df (pd.DataFrame): DataFrame of NBA games.

    Returns:
    - str: Minimal date in the format '%m/%d/%Y'.
    """
    min_dt = pd.to_datetime(games_by_ids_df.GAME_DATE_EST.min())
    return min_dt.date().strftime('%m/%d/%Y')


# @flow(retries=1, log_prints=True)
def get_games_ids_to_append(latest_games: pd.DataFrame, game_ids: List[str]) -> Tuple[List[str], pd.DataFrame]:
    """
    Get a list of NBA game IDs to append to the database.

    Parameters:
    - latest_games (pd.DataFrame): DataFrame of the latest NBA games in the database.
    - game_ids (List[str]): List of NBA game IDs.

    Returns:
    - List[str]: List of NBA game IDs to append to the database.
    """
    games_by_ids_df = get_games_by_ids(game_ids=game_ids)
    latest_game_date_from_db = pd.to_datetime(latest_games.GAME_DATE_EST.max()).date().strftime('%m/%d/%Y')
    earliest_game_date_from_game_ids = get_games_minimal_date(games_by_ids_df)
    print(f"Searching for games from {latest_game_date_from_db} to {earliest_game_date_from_game_ids}")
    missing_games = get_games_from_to(
        date_from=latest_game_date_from_db,
        date_to=earliest_game_date_from_game_ids)
    missing_games = missing_games[~missing_games.GAME_ID.isin(latest_games.GAME_ID_STR)].copy()
    result = [g for g in set(missing_games.GAME_ID.to_list() + game_ids) if g not in set(latest_games.GAME_ID_STR)]
    print(f"need to append games: {len(result)}")
    return result, missing_games


# @task(retries=2, log_prints=True)
def get_current_players(db_path: str) -> pd.DataFrame:
    """
    Retrieves players from "player_0" table.

    Parameters:
    - db_path (str): The path to the SQLite database file.

    Returns:
    - pd.DataFrame or None: A DataFrame containing all players in DB,
      or None if an error occurs.
    """
    # SQL query to find the game with the latest GAME_DATE_EST
    sql_query = """
    SELECT *
    FROM "player_0";
    """
    with sqlite3.connect(db_path) as connection:
        result_df = pd.read_sql(sql_query, connection)
    if result_df.empty:
        print("DB seems to be empty")
    else:
        print(f"Found players: {len(result_df)}")
    return result_df


# @task(retries=2, log_prints=True)
def prepare_games_to_append(game_ids_to_append) -> List[Tuple[str, pd.DataFrame]]:
    """
    Get a list of NBA game IDs to append to the database.

    Parameters:
    - latest_games (pd.DataFrame): DataFrame of the latest NBA games in the database.
    - game_ids (List[str]): List of NBA game IDs.

    Returns:
    - List[str]: List of NBA game IDs to append to the database.
    """
    result = defaultdict(list)
    games_dfs = []
    for g_i in game_ids_to_append:
        for endpoint, table_prefix in zip(
                [boxscoresummaryv2.BoxScoreSummaryV2, boxscoretraditionalv2.BoxScoreTraditionalV2],
                ['boxscoresummaryv2', 'boxscoretraditionalv2']):
            _frames = endpoint(game_id=g_i).get_data_frames()
            for i, _df in enumerate(_frames):
                _df = add_game_id_str(_df)
                result[f"{table_prefix}_{i}"].append(_df)
                if (table_prefix == 'boxscoresummaryv2') and (i == 0):
                    games_dfs.append(_df)
    if games_dfs:
        games_df = pd.concat(games_dfs, axis=0)
        games_df['season_type'] = games_df.GAME_ID_STR.map(game_id_2_season_type)
    else:
        games_df = pd.DataFrame()
    return [('games', games_df)] + [(k, pd.concat(v, axis=0)) for k, v in result.items()]


# @task(retries=2, log_prints=True)
def prepare_players_to_append(
        current_players: pd.DataFrame,
        games_dataframe_list: List[Tuple[str, pd.DataFrame]]) -> List[Tuple[str, pd.DataFrame]]:
    """
    Prepare player DataFrames to append to the database.

    Parameters:
    - current_players (pd.DataFrame): DataFrame of current players in the database.
    - games_dataframe_dict (Dict[str, pd.DataFrame]): Dictionary of NBA games DataFrames.

    Returns:
    - Dict[str, pd.DataFrame]: Dictionary of player DataFrames prepared for appending to the database.
    """

    def _get_games_df():
        for k, _games_df in games_dataframe_list:
            if k == 'boxscoretraditionalv2_0':
                return _games_df
        return pd.DataFrame({'PLAYER_ID': []})

    players_from_games = _get_games_df()
    players_to_append = set(players_from_games.PLAYER_ID) - set(current_players.PERSON_ID)
    if players_to_append:
        print(f"need to append players: {len(players_to_append)}")
        result = defaultdict(list)
        for pl_i in players_to_append:
            _frames = commonplayerinfo.CommonPlayerInfo(player_id=pl_i).get_data_frames()
            for i, _df in enumerate(_frames):
                result[f"player_{i}"].append(_df)
        return [(k, pd.concat(v, axis=0)) for k, v in result.items()]
    else:
        print("no need to append players")
        return []


# @task(retries=2, log_prints=True)
def append_tables(db_path: str, dataframe_list: List[Tuple[str, pd.DataFrame]]):
    """
   Append DataFrames to SQLite database tables.

   Parameters:
   - db_path (str): The path to the SQLite database file.
   - dataframe_dict (Dict[str, pd.DataFrame]): Dictionary of DataFrames to append to the database.

   Returns:
   - None
   """
    with sqlite3.connect(db_path) as connection:
        # cursor = connection.cursor()
        # cursor.execute('begin;')
        for table_name, _df in dataframe_list:
            print(f"writing {len(_df)} records to {table_name}")
            if len(_df) > 0:
                _df.to_sql(table_name, con=connection, if_exists='append', index=False)
        # cursor.execute('commit;')
    return


# @flow(log_prints=True)
def back_fill_games(game_ids: List[str], db_path: str) -> List[Tuple[str, pd.DataFrame]]:
    """
    Back-fill NBA game and player information into the database.

    Parameters:
    - game_ids (List[str]): List of NBA game IDs to back-fill.

    Returns:
    - Dict[str, pd.DataFrame]: Dictionary of DataFrames containing back-filled game and player information.
    """
    if len(game_ids) == 0:
        return {}
    latest_game_df = get_latest_game(db_path=db_path)
    current_players = get_current_players(db_path=db_path)
    game_ids_to_append, missing_games_df = get_games_ids_to_append(
        latest_games=latest_game_df,
        game_ids=game_ids
    )
    games_to_append_list = prepare_games_to_append(game_ids_to_append)
    players_to_append_list = prepare_players_to_append(
        current_players=current_players,
        games_dataframe_list=games_to_append_list
    )

    tables_to_append = players_to_append_list + games_to_append_list  # insert players first
    append_tables(
        db_path=db_path,
        dataframe_list=tables_to_append
    )

    return tables_to_append


# @task(retries=2, log_prints=True)
def get_game_ids_for_date(date: dt.date) -> List[str]:
    """
    Finds id's of nba games that have already ended

    return:
        list
            string id
    """
    print(f"calling GameFinder for {date}")
    to_date_str = date.strftime('%m/%d/%Y')
    from_date_str = date.strftime('%m/%d/%Y')
    games = leaguegamefinder.LeagueGameFinder(
        date_from_nullable=from_date_str,
        date_to_nullable=to_date_str,
    ).get_data_frames()[0]
    game_ids = list()
    for i in games['GAME_ID']:
        if i not in game_ids and i[0] == '0':
            game_ids.append(i)
    print(f"found games for this date: {len(game_ids)}")
    return game_ids


def split_games_dfs(
        game_ids: List[str],
        back_filled_dfs: List[Tuple[str, pd.DataFrame]],
        db_path: str,
) -> (pd.DataFrame, pd.DataFrame):
    """
    splits game_ids into ones that were in DB before and new added ones
    and turns both groups into dataframes with `columns` columns

    Parameters:
    - game_ids (List[str]): List of NBA game IDs.
    - db_path (str): The path to the SQLite database file.

    Returns:
    - pd.DataFrame: DataFrame containing rows from the 'GAMES' table for the given game IDs.
    """
    added_games_df = pd.DataFrame()
    added_game_ids = set()
    for k, _games_df in back_filled_dfs:
        if k == 'boxscoresummaryv2_5':
            added_games_df = _games_df
            if len(added_games_df) > 0:
                added_game_ids = set(added_games_df.GAME_ID_STR)

    existed_game_ids = [g for g in game_ids if g not in added_game_ids]
    if existed_game_ids:
        with sqlite3.connect(db_path) as connection:
            select_query = f"""
            SELECT *
            FROM "boxscoresummaryv2_5"
            WHERE "GAME_ID_STR" IN ({', '.join(['?' for _ in existed_game_ids])});
            """
            existed_games_df = pd.read_sql(select_query, connection, params=existed_game_ids)
    else:
        existed_games_df = pd.DataFrame()

    existed_games_df['unseen_game'] = False
    added_games_df['unseen_game'] = True
    return pd.concat([existed_games_df, added_games_df], axis=0)


def prepare_game_df(on_date_game_df: pd.DataFrame) -> pd.DataFrame:
    if (on_date_game_df is None) or (len(on_date_game_df) == 0):
        return pd.DataFrame(columns=DEFAULT_GAMES_COLUMNS)
    return (
        on_date_game_df
        .assign(
            _TEAM=lambda r: r.TEAM_CITY_NAME + " " + r.TEAM_NICKNAME,
            _GAME_DATE=lambda r: pd.to_datetime(r.GAME_DATE_EST).dt.strftime('%m/%d/%Y'),
        )
        .groupby('GAME_ID_STR')
        .agg({
            'unseen_game': [('unseen_game', 'first')],
            '_GAME_DATE': [('game_date', 'first')],
            '_TEAM': [('team_1', 'first'), ('team_2', 'last')],
            'PTS': [('score_1', 'first'), ('score_2', 'last')],
        })
        .droplevel(0, axis=1)
        .assign(
            teams=lambda r: r.team_1 + ' - ' + r.team_2,
            score=lambda r: r.score_1.astype(int).astype(str) + ' - ' + r.score_2.astype(int).astype(str),
        )
        .reset_index()
        .rename(columns={'GAME_ID_STR': 'game_id'})
        [DEFAULT_GAMES_COLUMNS]
    )


# @flow(log_prints=True)
def fetch_games_for_date(date: dt.date) -> pd.DataFrame:
    """
    1) finds games on 'date' date
    2) finds what games and players need to be added to DB
    3) uploads it to DB
    return: pd.Dataframe with 'date' games and additional column 'unseen_game'
    """
    db_path = get_db_path()
    game_ids = get_game_ids_for_date(date=date)
    back_filled_dfs = back_fill_games(game_ids=game_ids, db_path=db_path)
    on_date_games_df = (
        split_games_dfs(
            game_ids=game_ids,
            back_filled_dfs=back_filled_dfs,
            db_path=db_path
        )
    )
    return prepare_game_df(on_date_games_df)


if __name__ == "__main__":
    fetch_games_for_date.serve(name="back-fill-games-deployment")
