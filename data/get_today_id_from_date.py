from nba_api.stats.endpoints import leaguegamefinder
from datetime import datetime, timedelta
from typing import List


def get_today_ids() -> List[str]:
    """
    Finds id's of nba games that have already ended

    return:
        list
            string id
    """

    current_date = datetime.today() - timedelta(days=1)
    current_date = current_date.strftime('%m/%d/%Y')
    games = leaguegamefinder.LeagueGameFinder(date_from_nullable=current_date).get_data_frames()[0]
    games_id = list()
    for i in games['GAME_ID']:
        if i not in games_id and i[0] == '0':
            games_id.append(i)
    return games_id


def main():
    get_today_ids()


if __name__ == '__main__':
    main()
