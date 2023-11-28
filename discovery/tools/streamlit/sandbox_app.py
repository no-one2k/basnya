from typing import List

import pandas as pd
import streamlit as st
import sqlite3
import datetime as dt

from nba_api.stats.endpoints import leaguegamefinder
from prefect import flow


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


def main():
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
                df = pd.DataFrame(index=_game_id)
                df['game_id'] = df.index.map(int)
                df['game_date'] = _date
                df['teams_slug'] = df.index
                with sqlite3.connect("test.db") as con:
                    df.to_sql(con=con, name='games', if_exists='append', index=False)
                st.dataframe(df, hide_index=True)
            else:
                st.info("no games to collect")


if __name__ == '__main__':
    main()
