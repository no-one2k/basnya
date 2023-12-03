from typing import List
import hmac

import pandas as pd
import streamlit as st
import sqlite3
import datetime as dt

from nba_api.stats.endpoints import leaguegamefinder
from prefect import flow

SQLITE_DB_PATH = "test.db"


@flow
def get_today_ids() -> List[str]:
    """
    Finds id's of nba games that have already ended

    return:
        list
            string id
    """
    current_date = dt.datetime.today() - dt.timedelta(days=1)
    current_date = current_date.strftime('%m/%d/%Y')
    games = leaguegamefinder.LeagueGameFinder(date_from_nullable=current_date).get_data_frames()[0]
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


def add_app_logic():
    st.title("Basnya Prototype")

    st.header("Get Latest Games")

    _date = st.date_input(
        label="enter date",
        value=dt.date.today(),
        min_value=dt.date(2020, 1, 1),
        max_value=dt.date.today(),
        format='DD.MM.YYYY'
    )

    button1 = st.button("Get games")
    if st.session_state.get('button') != True:
        st.session_state['button'] = button1
    if st.session_state['button'] == True:
        games = get_today_ids()
        st.write(f"Games for {_date}: {','.join(games)}")

        st.header("Collect data for game")

        _game_id = st.multiselect(
            label="select games",
            options=games,
            default=games,
        )
        if st.button("Collect"):
            if _game_id:
                selected_games_df, missing_games_df = select_missing_game_ids(_game_id, SQLITE_DB_PATH)
                st.subheader("Processed games:")
                st.dataframe(selected_games_df, hide_index=True)
                for g in selected_games_df.game_id:
                    st.write(f"\t\ttweet based on {g}")
                missing_games_df['game_id'] = missing_games_df.index.map(int)
                missing_games_df['game_date'] = _date
                missing_games_df['teams_slug'] = missing_games_df.index
                with sqlite3.connect(SQLITE_DB_PATH) as con:
                    missing_games_df.to_sql(con=con, name='games', if_exists='append', index=False)
                st.subheader("New games:")
                st.dataframe(missing_games_df, hide_index=True)
                for g in missing_games_df.game_id:
                    st.write(f"\t\ttweet based on {g}")
            else:
                st.info("no games to collect")


def main():
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.
    add_app_logic()


if __name__ == '__main__':
    main()
