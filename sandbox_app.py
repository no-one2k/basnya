import os
from typing import List, Tuple
import hmac

import pandas as pd
import streamlit as st
import datetime as dt

from anomaly.resource.utils import AnomalyCalculation
from back_fill_games import fetch_games_for_date, DEFAULT_GAMES_COLUMNS

SQLITE_DB_PATH = "basnya.db"
AD_MODEL_PATH = 'isolation_forest_model_2021-10-19_2023-10-23.joblib'


def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
            for secret in ["OPENAI_API_KEY", "OPENAI_ORGANIZATION"]:
                os.environ[secret] = st.secrets[secret]
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


def on_get_games():
    _date = st.session_state['date']
    df_games_for_date = fetch_games_for_date(_date)
    st.session_state["run_for_date"] = _date
    st.session_state["df_games_for_date"] = df_games_for_date


def on_generate():
    _df = st.session_state["df_games_for_date"]
    selected_game_ids = _df.game_id[_df.unseen_game.notna()].to_list()
    if selected_game_ids:
        anomaly = AnomalyCalculation(db_path=SQLITE_DB_PATH, path_model_weights=AD_MODEL_PATH)
        tweets_anomaly = anomaly.get_tweets(selected_game_ids=selected_game_ids)
        if tweets_anomaly:
            st.session_state.txt_tweets = "\n".join([t.tweet_text for t in tweets_anomaly])
    else:
        st.info("no games to generate tweets")


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
    if "df_games_for_date" not in st.session_state:
        st.session_state.df_games_for_date = pd.DataFrame(columns=DEFAULT_GAMES_COLUMNS)

    st.button("Get games", key='btn_get_games', on_click=on_get_games)
    st.dataframe(data=st.session_state.df_games_for_date, hide_index=True, use_container_width=True)
    st.button("Generate tweets", key='btn_generate', on_click=on_generate)
    st.text_area("NBA. Where amazing tweets happen...", key="txt_tweets", label_visibility='hidden')


def main():
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.
    add_app_logic()


if __name__ == '__main__':
    main()