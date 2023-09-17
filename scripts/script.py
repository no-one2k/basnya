import pandas as pd
import time
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.endpoints import boxscoresummaryv2, playbyplayv2
from nba_api.stats.endpoints import boxscoretraditionalv2
a = []
games = leaguegamefinder.LeagueGameFinder(season_nullable='2021-22').get_data_frames()[0]
for i in games['GAME_ID']:
    a.append(i)
games_id = list(set(a))
end_of_program = len(games_id)
print(end_of_program)

c = 0
while True:
    try:
        while len(games_id) > 0:
            time.sleep(0.2)
            boxscoretrad = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=games_id[0]).get_data_frames()
            for j in range(len(boxscoretrad)):
                file_download = boxscoretrad[j]
                df = pd.DataFrame(file_download)
                df.to_csv(f'boxscoretraditionalv2/boxscoretraditionalv2_{j}_{games_id[0]}.csv', index=False)
            time.sleep(0.2)
            playbyplay = playbyplayv2.PlayByPlayV2(game_id=games_id[0]).get_data_frames()[0]
            df = pd.DataFrame(playbyplay)
            df.to_csv(f'playbyplayv2/playbyplayv2_{games_id[0]}.csv', index=False)
            time.sleep(0.2)
            boxscoresumm = boxscoresummaryv2.BoxScoreSummaryV2(game_id=games_id[0]).get_data_frames()
            for j in range(len(boxscoresumm)):
                file_download = boxscoresumm[j]
                df = pd.DataFrame(file_download)
                df.to_csv(f'boxscoresummaryv2/boxscoresummaryv2_{j}_{games_id[0]}.csv', index=False)
            c += 1
            games_id.pop(0)
            print(f'Осталось {end_of_program - c}')
            if end_of_program - c == 0:
                break
    except Exception as error:
        print(error)
        continue
    if end_of_program - c == 0:
        print('Игры закончились')
        break
    
