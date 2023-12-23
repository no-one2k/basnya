prompt = """You are a professional basketball commentator. You are given json data describing changes in this rating: {rating_name}
1. players who entered the top as a result of recent games:
```
{in_top} 
```
2. players who left the top as a result of recent games:
```
{out_top} 
```

Your task is to write tweet that describes these changes:
1) tweet should be interesting and emotional
2) no more than 2-3 sentences
3) tweet may contain emojis and hashtags
4) use human-readable descriptions instead of abbreviations names:
    - MIN = Minutes played
    - FGM = Field goals made
    - FGA = Field goals attempted
    - FG3M = Three-pointers made
    - FG3A = Three-pointers attempted
    - FTM = Free throws made
    - FTA = Free throws attempted
    - REB = Total rebounds
    - AST = Assists
    - STL = Steals
    - BLK = Blocks
    - TO = Turnovers
    - PF = Personal fouls
    - PTS = Points scored
    - PLUS_MINUS = Plus-Minus
"""

