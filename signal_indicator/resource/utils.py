import logging
import re
import sqlite3
from collections import defaultdict
from copy import deepcopy
from enum import Enum
from typing import Dict, List, Union, Optional

import openai
import pandas as pd
from langchain.llms.openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from pydantic import BaseModel


DEFAULT_GPT_MODEL = 'gpt-3.5-turbo-instruct'
DEFAULT_TEMPERATURE = 0.8


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
output_handler = logging.StreamHandler()
output_handler.setLevel(logging.INFO)

logger = logging.getLogger()


def min_to_second(string: str) -> int:
    """
    Перевеод формата времени матча в секунды
    
    Аргументы:
        string: str - формат времени матча 
    Возвращает:
        время в секундах (int)
    """

    if isinstance(string, str):
        pattern = r"(\d+)\.(\d+):(\d+)"

        match = re.match(pattern, string)
        if match:
            minutes = int(match.group(1)) * 60
            seconds = int(match.group(3))
            return minutes + seconds
    elif isinstance(string, int):
        return string
    else:
        return 0


def str_min_to_float_min(string: str) -> float:
    """
    Перевеод формата времени матча в минуты

    Аргументы:
        string: str - формат времени матча
    Возвращает:
        время в минутах (float)
    """

    if isinstance(string, str):
        pattern = r"(\d+)\.(\d+):(\d+)"

        match = re.match(pattern, string)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(3)) / 60
            return minutes + seconds
    elif isinstance(string, int):
        return string
    elif isinstance(string, float):
        return string
    else:
        return 0


def get_completion(prompt, model):
    """
    Получить ответ модели Openai
    """

    messages = [{"role": "user", "content": prompt}]
    response = openai.Completion.create(
        model=model,
        prompt=prompt,
        temperature=DEFAULT_TEMPERATURE,  # this is the degree of randomness of the model's output
    )
    return response.choices[0]["text"]


class TweetType(Enum):
    RATING_CHANGE_SEASON_SUM = 'rating_change_season_sum'
    ANOMALY_UNIQUE = 'anomaly_unique'
    ANOMALY_REPEAT = 'anomaly_repeat'


class Tweet(BaseModel):
    game_ids: List[str]
    player_ids: List[int]
    tweet_text: str
    tweet_type: TweetType


def remove_records(
        player_stats: Dict[int, List[pd.Series]],
        game_ids_to_remove: Union[int, List[int]]
) -> Dict[int, List[pd.Series]]:
    """
    Удаляет информацию по матчам из указанной статистики игроков

    Аргументы:
       last_ids - Список идентификаторов игр, которые необходимо удалить из статистики
       player_stats - статистика по игрокам, из которой удаляем записи об играх
    """
    result_stats = deepcopy(player_stats)
    if isinstance(game_ids_to_remove, int):
        game_ids_to_remove = [game_ids_to_remove]

    for player_id in result_stats.keys():
        result_stats[player_id] = [game for game in result_stats[player_id]
                                   if game['GAME_ID'] not in game_ids_to_remove]
    return result_stats


class StatsHolder:
    """
    Класс для хранение и обработки сигнальных показателей
    """

    target_columns: list = ['MIN', 'FGM', 'FGA', 'FG3M', 'FTM', 'FTA', 'FT_PCT',
                            'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS', 'PLAYER_ID', 'GAME_ID']
    calculus_columns: list = ['MIN', 'FGM', 'FGA', 'FG3M', 'FTM', 'FTA',
                              'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS']
    labels_columns: list = ['PLAYER_ID', 'GAME_ID']

    def __init__(self, players_stats: Dict[int, List[pd.Series]], all_data: pd.DataFrame, db_path: str, prompt: str):
        """
        Аргументы:
            players_stats - статистика по игрокам. Ключи - индексы игроков, 
                            значения - сисок статистики по игроку за все указанные игры
            all_data - данные обо всех матчах (в формате boxscoretraditionalv2_0)
        """

        self.players_stats: Dict[int, List[pd.Series]] = players_stats  # статистика по игрокам
        self.all_data = all_data
        self.strategies = {}  # словарь, содержащий все стратегии для отслеживания сигнальных показателей
        self.db_path = db_path
        self.player_id_to_name_dict = self.get_player_id_to_name_dict()

        # ----------------------------- вынести в Strategy
        self.prompt_template = prompt

    def get_player_id_to_name_dict(self) -> Dict[int, str]:
        """
        Получить справочник. кокторый сопоставляет id игрока с именем игрока и страной
        """
        with sqlite3.connect(self.db_path) as conn:
            return (
                pd.read_sql_query("""
                SELECT PERSON_ID, PERSON_ID as PLAYER_ID, DISPLAY_FIRST_LAST as NAME, COUNTRY  
                FROM 'player_0'""",
                                  conn)
                .set_index('PERSON_ID')
                .to_dict(orient='index')
            )

    def add_strategy(self, strategy):
        """
        Добавить стратегию для отслеживания сигнальных показателей
        """

        self.strategies[strategy.title] = strategy

        logger.info(f'Added "{strategy.title}" strategy')

    def show_strategies(self):
        return [strategy for strategy in self.strategies]

    @classmethod
    def from_sql(cls, prompt, db_path) -> 'StatsHolder':
        """
        Создание объекта StatsHolder из бд SQlite
        
        Аргументы:
            db_path - путь до локаьной базы SQlite
        """
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(
                sql="""SELECT bs.* 
                FROM boxscoretraditionalv2_0 as bs
                LEFT JOIN games as g on bs.GAME_ID = g.GAME_ID
                WHERE g.SEASON = (SELECT max(t.SEASON) FROM games as t)
                AND g.season_type > 1""",
                con=conn
            )
        df.drop_duplicates(subset=['PLAYER_ID', 'GAME_ID'], inplace=True)
        df.dropna(subset='MIN', inplace=True)
        df['MIN'] = df['MIN'].apply(str_min_to_float_min)

        if len(df) == 0:
            players_stats = defaultdict(list)
        else:
            players_stats = (
                df
                .groupby('PLAYER_ID', group_keys=True)
                .apply(lambda _df: [r[cls.target_columns] for i, r in _df.iterrows()])
                .to_dict()
            )
        return cls(players_stats=players_stats, all_data=df, db_path=db_path, prompt=prompt)

    def add_record(
            self,
            player_stats: Dict[int, List[pd.Series]],
            record: pd.DataFrame
    ) -> Dict[int, List[pd.Series]]:
        """
        Добавить запись к указанной статистике игроков
        
        Аргументы:
            record: pd.DataFrame - новая запись игры
            player_stats - статистика по игрокам, в которую добавляем новую запись
        """

        player_stats = deepcopy(player_stats)
        record.loc[:, 'MIN'] = record['MIN'].apply(str_min_to_float_min).fillna(0).astype(float)

        for _, row in record[self.target_columns].iterrows():
            player_id = row.PLAYER_ID
            game_id = row.GAME_ID
            id_game_list = [stat.GAME_ID for stat in player_stats[player_id]]

            if game_id in id_game_list:
                logger.info(f'This GAME_ID:{int(game_id)} is already in the dataset')
            else:
                player_stats[player_id].append(row.fillna(0).astype(int))

        return player_stats

    def run_strategies(self, selected_game_ids: List[str]) -> Dict[str, list]:
        """
        Получить отчёт за N последних игр

        Аргументы:
            db_path - путь до локаьной бд
            N_last_game - указать, сколько последних игр учитывать для создания отчёта
        """

        old_stats = remove_records(self.players_stats, [int(_g) for _g in selected_game_ids])
        new_stats = self.players_stats

        answer = {
            'title': f'For {selected_game_ids} games',
            'result': []
        }

        logger.info('calculation of strategy results ...')
        for strategy in self.strategies.values():
            answer['result'].append(strategy.result(old_stats, new_stats))

        answer['result'] = list(filter(lambda x: x is not None, answer['result']))
        return answer

    def get_tweets(self, selected_game_ids: List[str]) -> List[Tweet]:
        def split_rating_change(rating_change):
            split = []
            for _result in rating_change['result']:
                top_n = _result['description']
                in_top = _result['values']['in_top']
                out_top = _result['values']['out_top']
                for indicator, in_players in in_top.items():
                    rating_name = f"Season {top_n} by {indicator}"
                    out_players = out_top.get(indicator, [])
                    split.append({
                        'rating_name': rating_name,
                        'in_top': in_players,
                        'out_top': out_players,
                    })
            return split

        def make_rating_chain():
            model_creative = OpenAI(temperature=0.2, model=DEFAULT_GPT_MODEL)
            prompt_in_out_rating = PromptTemplate.from_template(self.prompt_template)
            chain_in_out_rating = (
                    {
                        'rating_name': RunnablePassthrough(),
                        'in_top': RunnablePassthrough(),
                        'out_top': RunnablePassthrough(),
                    }
                    | prompt_in_out_rating
                    | model_creative
            )

            def _invoke(rating_name, in_top, out_top):
                return chain_in_out_rating.invoke({'rating_name': rating_name, 'in_top': in_top, 'out_top': out_top})

            return _invoke
        strategies_result = self.run_strategies(selected_game_ids)
        split_rating = split_rating_change(strategies_result)

        logger.info('Tweeting ...')
        _gen_tweet = make_rating_chain()
        tweets = []
        for rating_change in split_rating:
            tweet_text = _gen_tweet(**rating_change)
            involved_players = [d['PLAYER_ID'] for d in rating_change['in_top'] + rating_change['out_top']]
            tweets.append(Tweet(
                player_ids=involved_players,
                game_ids=selected_game_ids[:],
                tweet_text=tweet_text,
                tweet_type=TweetType.RATING_CHANGE_SEASON_SUM
            ))

        return tweets
