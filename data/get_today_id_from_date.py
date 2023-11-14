from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd


def get_today_ids(current_date: str) -> list: # date like mm/dd/yyyy
    games = leaguegamefinder.LeagueGameFinder(date_from_nullable=current_date).get_data_frames()[0]
    games_id = list()
    for i in games['GAME_ID']:
        if i not in games_id:
            games_id.append(i)
    return games_id


print(get_today_ids('11/13/2023'))
