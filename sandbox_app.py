import os
from typing import Optional
import hmac

import pandas as pd
import streamlit as st
import datetime as dt
import textwrap

from anomaly.resource.utils import AnomalyCalculation
from back_fill_games import fetch_games_for_date, DEFAULT_GAMES_COLUMNS
from signal_indicator.resource.prompts_template import prompt as rating_prompt
from signal_indicator.resource.strategies import StrategyRating
from signal_indicator.resource.utils import StatsHolder, Tweet, TweetType

SQLITE_DB_PATH = "basnya.db"
AD_MODEL_PATH = 'isolation_forest_model_2021-10-19_2023-10-23.joblib'
DUMMY_TWEET_GENERATION = False


def get_form_for_tweet(container: st.container) -> None:
    """
    Create a form with tweets and buttons to copy
    
    Parameters:
        - container (st.container): container where buttons and tweets will be created
    """
    
    st.session_state.generate_tweets = True
    on_generate()
    tweets = st.session_state.txt_tweets
    with container:
        for index, tweet in enumerate(tweets):
            body = "\n".join(textwrap.wrap(text=tweet, width=80))
            st.code(body=body, language=None)
            

def dataframe_with_selections(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Line selection df
    
    Parameters:
        - df (pd.DataFrame)
    Return:
        - elected_rows (pd.DataFrame) or None
    """
    
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
    )
    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop('Select', axis=1)


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
    if (_date < get_min_allowed_date()) or (_date > get_max_allowed_date()):
        st.info(f"Select date from {get_min_allowed_date()} to {get_max_allowed_date()}.")
        return
    _token_git = st.secrets['TOKEN_GIT']
    df_games_for_date = fetch_games_for_date(_date, _token_git)
    st.session_state["run_for_date"] = _date
    st.session_state["df_games_for_date"] = df_games_for_date
    if (df_games_for_date is None) or (len(df_games_for_date) == 0):
        st.info(f"No games to generate tweets for date {_date}. Please select another date.")


def on_generate():
    _df = st.session_state.data_for_tweets  # отсюда берем айдишники игр
    selected_game_ids = _df.game_id[_df.unseen_game.notna()].to_list()
    if selected_game_ids:
        if DUMMY_TWEET_GENERATION:
            tweets = [Tweet(
                player_ids=[],
                game_ids=[g],
                tweet_text=f"tweet_text for game {g} with interesting details" * 4,
                tweet_type=TweetType.ANOMALY_UNIQUE) for g in selected_game_ids]
        else:
            anomaly = AnomalyCalculation(db_path=SQLITE_DB_PATH, path_model_weights=AD_MODEL_PATH)
            tweets_anomaly = anomaly.get_tweets(selected_game_ids=selected_game_ids)

            stats = StatsHolder.from_sql(db_path=SQLITE_DB_PATH, prompt=rating_prompt)
            strategy_top_10 = StrategyRating(top=10, player_id_to_name_dict=stats.player_id_to_name_dict)
            stats.add_strategy(strategy_top_10)
            tweets_rating = stats.get_tweets(selected_game_ids=selected_game_ids)
            tweets = (tweets_anomaly or []) + (tweets_rating or [])
        if tweets:
            st.session_state.txt_tweets = [tweet.tweet_text for tweet in tweets if len(tweet.tweet_text) != 0]
    else:
        st.info("Select at least 1 game by ticking cells in 'Select' column.")


def add_app_logic():
    st.title("BASNya Demo")

    _date = st.date_input(
        label="enter date",
        value=dt.date.today() - dt.timedelta(days=1),
        min_value=get_min_allowed_date(),
        max_value=get_max_allowed_date(),
        format='DD.MM.YYYY',
        key="date"
    )
    
    if "df_games_for_date" not in st.session_state:
        st.session_state.df_games_for_date = pd.DataFrame(columns=DEFAULT_GAMES_COLUMNS)
    if "data_for_tweets" not in st.session_state:
        st.session_state.data_for_tweets = None

    if 'generate_tweets' not in st.session_state:
        st.session_state.generate_tweets = False

    st.button("Get games", key='btn_get_games', on_click=on_get_games)
    df = st.session_state.df_games_for_date
    selection = dataframe_with_selections(df)
    st.session_state.data_for_tweets = selection
    
    container_with_tweets = st.container() 
    with container_with_tweets:
        st.button("Generate tweets", key='btn_generat', on_click=get_form_for_tweet, 
                  args=(container_with_tweets,))


def get_max_allowed_date():
    return dt.date.today()


def get_min_allowed_date():
    return dt.date.today() - dt.timedelta(days=30)


def main():
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.
    add_app_logic()


if __name__ == '__main__':
    main()
