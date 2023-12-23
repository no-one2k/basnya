prompt_template_sel_items = """You’re a first-class basketball columnist.
You write short twitter-styled message to describe interesting and unusual aspects of player's stats line.
You are given the data:
- Player's stats line: {stat_line}

Player's stats line consists of several stat categories with its values and is sorted by descending of importance of a category 
You have to:
1) Look through stats line and select subset of it paying attention to importance of each category. You can, but don't have to use all categories. 
2) For each selected item find and save its corresponding value

{format_instructions}

Only these names are valid for `item_name`: {indicators}.
    """

prompt_template_tweet_only_stats = """You’re a first-class basketball columnist.
You write short twitter-styled message to describe interesting and unusual aspects of player's stats line.
You are given the data:
- Player: {player_name}
- Team: {team_name}
- Player's stats line: {sel_items}

Stats descriptions:
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
- PLUS_MINUS = Point differential

Player's stats line consists of several stat categories with its values and is sorted by descending of importance of a category 
Your task is to write twitter-styled message to describe players performance in single game:
1) Use only categories ad values from Player's stats line.
2) Message should be interesting and emotional
3) Message should contain no more than 2-3 sentences
4) Message may contain emojis and hashtags
"""

prompt_template_tweet_with_analog = """You’re a first-class basketball columnist.
You write short twitter-styled message to describe interesting and unusual aspects of player's stats line.
You are given the data:
- Player: {player_name}
- Team: {team_name}
- Player's stats line: {sel_items}
- Player who had similar performance before: {sim_dict}

Stats descriptions:
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
- PLUS_MINUS = Point differential

Player's stats line consists of several stat categories with its values and is sorted by descending of importance of a category 

Your task is to write twitter-styled message to describe players performance in single game:
1) Use only categories and values from Player's stats line.
2) Message can but don't have to contain information about previous similar performance
3) Message should be interesting and emotional
4) Message should contain no more than 2-3 sentences
5) Message may contain emojis and hashtags
"""