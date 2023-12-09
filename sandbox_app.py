from typing import List
import hmac

import pandas as pd
import streamlit as st
import sqlite3
import datetime as dt

from nba_api.stats.endpoints import leaguegamefinder
from prefect import flow

from back_fill_games import back_fill_games

SQLITE_DB_PATH = "test.db"


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


def select_missing_game_ids(game_ids: List[str], db_path: str) -> (pd.DataFrame, pd.DataFrame):
    """
    Select rows from the 'GAMES' table for given list of game IDs and collect missing game IDs.

    Parameters:
    - game_ids (List[str]): List of NBA game IDs.
    - db_path (str): The path to the SQLite database file.

    Returns:
    - pd.DataFrame: DataFrame containing rows from the 'GAMES' table for the given game IDs.
    """
    # Create a connection to the SQLite database
    with sqlite3.connect(db_path) as connection:
        # Query to select rows from 'GAMES' table for the given game IDs
        select_query = f"""
        SELECT *
        FROM "GAMES"
        WHERE "GAME_ID" IN ({', '.join(['?' for _ in game_ids])});
        """
        # Execute the query and fetch the results into a DataFrame
        selected_games_df = pd.read_sql(select_query, connection, params=game_ids)

    existing_game_ids = set(selected_games_df["game_id"].astype(int))
    missing_game_ids = [g for g in game_ids if int(g) not in existing_game_ids]

    missing_games_df = pd.DataFrame(index=missing_game_ids)

    return selected_games_df, missing_games_df


def on_get_games():
    _date = st.session_state['date']
    games = get_game_ids_for_date(_date)
    st.session_state["run_for_date"] = _date
    st.session_state["game_id_options"] = games
    st.session_state["game_id_default"] = games


def on_collect():
    selected_game_ids = st.session_state["select_game_id"]
    if selected_game_ids:
        back_fill_games(game_ids=selected_game_ids)
        selected_games_df, missing_games_df = select_missing_game_ids(selected_game_ids, SQLITE_DB_PATH)
        st.session_state.selected_games_df = selected_games_df
        st.session_state.txt_tweets_from_db = "\n".join(f"\t\ttweet based on {g}" for g in selected_games_df.game_id)
        missing_games_df['game_id'] = missing_games_df.index.map(int)
        missing_games_df['game_date'] = st.session_state["run_for_date"]
        missing_games_df['teams_slug'] = missing_games_df.index
        with sqlite3.connect(SQLITE_DB_PATH) as con:
            missing_games_df.to_sql(con=con, name='games', if_exists='append', index=False)
        st.session_state.missing_games_df = missing_games_df
        st.session_state.txt_new_tweets = "\n".join(f"\t\ttweet based on {g}" for g in missing_games_df.game_id)
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
        st.session_state.selected_games_df = pd.DataFrame()
        st.session_state.missing_games_df = pd.DataFrame()
    _game_id = st.multiselect(
        label="select games",
        options=st.session_state.game_id_options,
        default=st.session_state.game_id_default,
        key='select_game_id'
    )
    st.button("Collect", key='btn_collect', on_click=on_collect)
    st.subheader("Processed games:")
    st.dataframe(data=st.session_state.selected_games_df, hide_index=True)
    st.text_area("", key="txt_tweets_from_db")
    st.subheader("New games:")
    st.dataframe(data=st.session_state.missing_games_df, hide_index=True)
    st.text_area("", key="txt_new_tweets")


def main():
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.
    add_app_logic()


if __name__ == '__main__':
    main()
