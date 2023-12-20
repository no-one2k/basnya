import os
from typing import List, Tuple, Optional
import hmac
from functools import partial

import pandas as pd
import streamlit as st
import datetime as dt
import pyperclip 

from anomaly.resource.utils import AnomalyCalculation
from back_fill_games import fetch_games_for_date, DEFAULT_GAMES_COLUMNS
from signal_indicator.resource.prompts_template import prompt as rating_prompt
from signal_indicator.resource.strategies import StrategyRating
from signal_indicator.resource.utils import StatsHolder

SQLITE_DB_PATH = "basnya.db"
AD_MODEL_PATH = 'isolation_forest_model_2021-10-19_2023-10-23.joblib'


def get_form_for_tweet(container: st.container, data_wor_tweets: pd.DataFrame) -> None:
    """
    Create a form with tweets and buttons to copy
    
    Parameters:
        - container (st.container): container where buttons and tweets will be created
    """
    
    st.session_state.generate_tweets = True
    st.session_state.buttons = []
    
    on_generate()
    tweets = st.session_state.txt_tweets
    with container:
        for index, tweet in enumerate(tweets):
            col_button, col_text = st.columns([3,9]) 
            with col_button:
                button = st.button('Copy', key=f'button_{index}')
                st.session_state.buttons.append(index)
     
            with col_text:
                text_input = st.text_area("", value=tweet, key=f'text_{index}', height=30)
                # text_input = st.text_input(" ", value=tweet, key=f'text_{index}')
            

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
    _token_git = st.secrets['TOKEN_GIT']
    df_games_for_date = fetch_games_for_date(_date, _token_git)
    st.session_state["run_for_date"] = _date
    st.session_state["df_games_for_date"] = df_games_for_date


def on_generate():
    _df = st.session_state.data_for_tweets # отсюда берем айдишники игр
    selected_game_ids = _df.game_id[_df.unseen_game.notna()].to_list()
    if selected_game_ids:
        anomaly = AnomalyCalculation(db_path=SQLITE_DB_PATH, path_model_weights=AD_MODEL_PATH)
        tweets_anomaly = anomaly.get_tweets(selected_game_ids=selected_game_ids)

        stats = StatsHolder.from_sql(db_path=SQLITE_DB_PATH, prompt=rating_prompt)
        strategy_top_10 = StrategyRating(top=10, player_id_to_name_dict=stats.player_id_to_name_dict)
        stats.add_strategy(strategy_top_10)
        tweets_rating = stats.get_tweets(selected_game_ids=selected_game_ids)
        tweets = (tweets_anomaly or []) + (tweets_rating or [])
        if tweets:
            st.session_state.txt_tweets = [tweet for tweet in "\n".join([t.tweet_text for t in tweets]).split('\n') if len(tweet)!=0]
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
    if "data_for_tweets" not in st.session_state:
        st.session_state.data_for_tweets = None
        
    # if "buttons" not in st.session_state:
    #     st.session_state.buttons = []
    # if "text_input" not in st.session_state:
    #     st.session_state.text_input = []
        
    if 'generate_tweets' not in st.session_state:
        st.session_state.generate_tweets = False
    
    
    st.button("Get games", key='btn_get_games', on_click=on_get_games)
    df = st.session_state.df_games_for_date
    selection = dataframe_with_selections(df)
    st.session_state.data_for_tweets =  selection
    
    container_with_tweets = st.container() 
    with container_with_tweets:
        st.button("Generate tweets", key='btn_generat', on_click=get_form_for_tweet, 
                  args=(container_with_tweets, st.session_state.data_for_tweets, ))
    
    if 'buttons' in st.session_state:
        for index in st.session_state.buttons:
            if st.session_state.get(f'button_{index}', False):
                text = st.session_state[f'text_{index}']
                pyperclip.copy(text)
                st.success('Tweet copied successfully!')
                
    # st.write(st.session_state)       

    # ---------------------------------------- GENERATE TWEETS --------------------------------------
    # st.dataframe(data=st.session_state.df_games_for_date, hide_index=True, use_container_width=True)
    # st.button("Generate tweets", key='btn_generate', on_click=on_generate)
    # st.text_area("NBA. Where amazing tweets happen...", key="txt_tweets", label_visibility='hidden')
    
        
def main():
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.
    add_app_logic()

if __name__ == '__main__':
    main()



# def generate_buttons():
#     if 'buttons' not in st.session_state:
#         st.session_state.buttons = []
#     st.session_state.buttons.append(st.button(f'Button {len(st.session_state.buttons)+1}'))

# st.button('Generate buttons', on_click=generate_buttons)

# # if 'buttons' in st.session_state:
# #     for button in st.session_state.buttons:
# #         button
#st.write(st.session_state)