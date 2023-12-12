from typing import List, Tuple
import hmac

import pandas as pd
import streamlit as st
import sqlite3
import datetime as dt

from nba_api.stats.endpoints import leaguegamefinder
from prefect import flow

from back_fill_games import back_fill_games

SQLITE_DB_PATH = "basnya.db"
DEFAULT_GAMES_COLUMNS = tuple(['GAME_ID', 'GAME_DATE_EST', 'GAMECODE'])


@flow
def get_game_ids_for_date(date: dt.date) -> List[str]:
    """
    Finds id's of nba games that have already ended

    return:
        list
            string id
    """
    to_date_str = (date + dt.timedelta(days=1)).strftime('%m/%d/%Y')
    from_date_str = date.strftime('%m/%d/%Y')
    print(from_date_str, to_date_str)
    games = leaguegamefinder.LeagueGameFinder(
        date_from_nullable=from_date_str,
        date_to_nullable=to_date_str,
    ).get_data_frames()[0]
    games_id = list()
    for i in games['GAME_ID']:
        if i not in games_id and i[0] == '0':
            games_id.append(i)
    return games_id


def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the passward is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


def split_games_dfs(
        game_ids: List[str],
        back_filled_dfs: List[Tuple[str, pd.DataFrame]],
        db_path: str,
        columns: List[str] = DEFAULT_GAMES_COLUMNS,
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
    added_games_df = pd.DataFrame(columns=columns)
    added_game_ids = set()
    for k, _games_df in back_filled_dfs:
        if k == 'games':
            added_games_df = _games_df
            if len(added_games_df) > 0:
                added_game_ids = set(added_games_df.GAME_ID_STR)

    existed_game_ids = [g for g in game_ids if g not in added_game_ids]
    if existed_game_ids:
        with sqlite3.connect(db_path) as connection:
            select_query = f"""
            SELECT *
            FROM "GAMES"
            WHERE "GAME_ID_STR" IN ({', '.join(['?' for _ in existed_game_ids])});
            """
            existed_games_df = pd.read_sql(select_query, connection, params=existed_game_ids)
    else:
        existed_games_df = pd.DataFrame(columns=columns)

    def _select_columns(_df):
        return _df[[c for c in columns if c in _df.columns]]
    return _select_columns(existed_games_df), _select_columns(added_games_df)


def on_get_games():
    _date = st.session_state['date']
    games = get_game_ids_for_date(_date)
    st.session_state["run_for_date"] = _date
    st.session_state["game_id_options"] = games
    st.session_state["game_id_default"] = games


def on_collect():
    selected_game_ids = st.session_state["select_game_id"]
    if selected_game_ids:
        back_filled_dfs = back_fill_games(game_ids=selected_game_ids)
        existed_games_df, added_games_df = split_games_dfs(
            game_ids=selected_game_ids,
            back_filled_dfs=back_filled_dfs,
            db_path=SQLITE_DB_PATH
        )
        st.session_state.existed_games_df = existed_games_df
        if len(existed_games_df) > 0:
            st.session_state.txt_tweets_from_db = "\n".join(f"\t\ttweet based on {g}" for g in existed_games_df.GAME_ID)
        st.session_state.added_games_df = added_games_df
        if len(added_games_df) > 0:
            st.session_state.txt_new_tweets = "\n".join(f"\t\ttweet based on {g}" for g in added_games_df.GAME_ID)
    else:
        st.info("no games to collect")


def add_app_logic():
    st.title("Basnya Prototype")

    st.header("Get Latest Games")

    _date = st.date_input(
        label="enter date",
        value=dt.date.today() - dt.timedelta(days=1),
        min_value=dt.date(2020, 1, 1),
        max_value=dt.date.today(),
        format='DD.MM.YYYY',
        key="date"
    )

    st.button("Get games", key='btn_get_games', on_click=on_get_games)
    st.header("Collect data for game")
    if "game_id_options" not in st.session_state:
        st.session_state.game_id_options = []
        st.session_state.game_id_default = []
        st.session_state.existed_games_df = pd.DataFrame(columns=DEFAULT_GAMES_COLUMNS)
        st.session_state.added_games_df = pd.DataFrame(columns=DEFAULT_GAMES_COLUMNS)
    _game_id = st.multiselect(
        label="select games",
        options=st.session_state.game_id_options,
        default=st.session_state.game_id_default,
        key='select_game_id'
    )
    st.button("Collect", key='btn_collect', on_click=on_collect)
    st.subheader("Processed games:")
    st.dataframe(data=st.session_state.existed_games_df, hide_index=True)
    st.text_area("", key="txt_tweets_from_db")
    st.subheader("New games:")
    st.dataframe(data=st.session_state.added_games_df, hide_index=True)
    st.text_area("", key="txt_new_tweets")


def main():
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.
    add_app_logic()


if __name__ == '__main__':
    main()
