import pandas as pd 
from tqdm import tqdm 
from pathlib import Path
from typing import Dict, List
import re 
from collections import defaultdict
import os
import re
import logging
from abc import ABC, abstractmethod
from copy import deepcopy 
from pprint import pprint 
import json

from dotenv import load_dotenv
import openai
from tqdm import tqdm
import pandas as pd
import sqlite3

from strategies import Strategy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
output_handler = logging.StreamHandler()
output_handler.setLevel(logging.INFO)

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

load_dotenv('../openai.env')
openai.api_key  = os.getenv('API_KEY')
logger = logging.getLogger()


def min_to_second(string: str):
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
            minutes = int(match.group(1))*60
            seconds = int(match.group(3))
            return minutes+seconds
    else:
        return 0
    
    
    
def get_completion(prompt, model='gpt-3.5-turbo'):
    """
    Получить ответ модели Openai
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0.8, # this is the degree of randomness of the model's output
    )
    return response.choices[0].message["content"]


class StatsHolder:
    """
    Класс для хранение и обработки сигнальных показателей
    """
    
    target_columns: list= ['MIN', 'FGM','FGA','FG3M','FTM','FTA','FT_PCT', 
                           'OREB','DREB','REB','AST','STL','BLK','TO','PF','PTS', 'PLAYER_ID', 'GAME_ID']
    calculus_columns: list = ['MIN', 'FGM','FGA','FG3M','FTM','FTA',
                              'FT_PCT','OREB','DREB','REB','AST','STL','BLK','TO','PF','PTS']
    labels_columns: list = ['PLAYER_ID', 'GAME_ID']
    
    def __init__(self, players_stats: Dict[int, List[pd.Series]], all_data: pd.DataFrame, db_path: str):
        """
        Аргументы:
            players_stats - статистика по игрокам. Ключи - индексы игроков, 
                            значения - сисок статистики по игроку за все указанные игры
            all_data - данные обо всех матчах (в формате boxscoretraditionalv2_0)
        """
        
        self.players_stats: Dict[int, List[pd.Series]] = players_stats # статистика по игрокам
        self.all_data = all_data
        self.strategies = {} # словарь, содержащий все стратегии для отслеживания сигнальных показателей
        self.db_path = db_path
        self.get_prompt_template()
        self.get_payerID2name()
    
    
    def get_prompt_template(self, path_template:str = r'..\resource\prompt\signal_indicator\prompt_tempalte.json') -> None:
        """
        Получить шаблон для Openai
        
        Аргументы:
            path_template - путь до шаблона
        """
        
        with open(path_template,'r') as f:
            self.prompt_template  = json.load(f)['text']
    
    def get_payerID2name(self) -> Dict:
        '''
        Получить справочник. кокторый сопоставляет id игрока с именем игрока и страной
        '''

        conn = sqlite3.connect(self.db_path)
        playerId2name = (
                        pd.read_sql_query(f"SELECT PERSON_ID, DISPLAY_FIRST_LAST, COUNTRY  FROM 'player_0'", conn)
                        .set_index('PERSON_ID')
                        .rename(columns={'DISPLAY_FIRST_LAST': 'NAME'})
                        .to_dict(orient='index')
                        )
        self.playerId2name = playerId2name
    
    def add_strategy(self, strategy):
        """
        Добавить стратегию для отслеживания сигнальных показателей
        """
        
        self.strategies[strategy.title] = strategy
        
        logger.info(f'Added "{strategy.title}" strategy')
    
    def show_strategies(self):
        return [strategy  for strategy in  self.strategies]
        
    @classmethod
    def from_sql(cls, db_path: str=r'../../data/basnya.db') -> 'StatsHolder':
        """
        Создание объекта StatsHolder из бд SQlite
        
        Аргументы:
            db_path - путь до локаьной базы SQlite
        """
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM boxscoretraditionalv2_0", conn)
        conn.close()

        players_stats = defaultdict(list)
        for game_id in tqdm(df.GAME_ID.unique(), total = len(df.GAME_ID.unique())):
            game = df.query("""GAME_ID==@game_id""")
            game.loc[:, 'MIN'] = game['MIN'].apply(min_to_second)
            game.loc[:, cls.calculus_columns] = game[cls.calculus_columns].fillna(0).astype(int)
            for index, row in game.iterrows():
                players_stats[row.PLAYER_ID].append(row[cls.target_columns])
                
        return cls(players_stats=players_stats, all_data=df, db_path=db_path)
    
    def remove_records(self, player_stats: dict,  last_ids) -> None:
        """
        Удаляет информацию по матчам из указанной статистики игроков
        
        Аргументы:
           last_ids - Список идентификаторов игр, которые необходимо удалить из статистики
           player_stats - статистика по игрокам, из которой удаляем записи об играх
        """
        player_stats = deepcopy(player_stats)
        if isinstance(last_ids, int):
            last_ids = [last_ids]
            
        for game_id in last_ids:
            for player_id in player_stats.keys():
                player_stats[player_id] = [game for game in player_stats[player_id] if game['GAME_ID'] !=game_id]
   
        return player_stats
        
        
    def add_record(self, player_stats: dict, record: pd.DataFrame) -> None:
        """
        Добавить запись к указанной статистике игроков
        
        Аргументы:
            record: pd.DataFrame - новая запись игры
            player_stats - статистика по игрокам, в которую добавляем новую запись
        """
        
        player_stats = deepcopy(player_stats)
        record.loc[:,'MIN'] = record['MIN'].apply(min_to_second).fillna(0).astype(int)

        for _, row in record[self.target_columns].iterrows():
            player_id = row.PLAYER_ID
            game_id = row.GAME_ID
            id_game_list = [stat.GAME_ID for stat in  player_stats[player_id]]
             
            if game_id in id_game_list:
                logger.info(f'This GAME_ID:{int(game_id)} is already in the dataset') 
                return None
      
            else:
                player_stats[player_id].append(row.fillna(0).astype(int)) 
            
        return player_stats
    
    def get_report(self, N_last_game: int, db_path: str = r'../../data/basnya.db') -> None:
        """ 
        Получить отчёт за N последних игр
        
        Аргументы:
            db_path - путь до локаьной бд
            N_last_game - указать, сколько последних игр учитывать для создания отчёта
        """
        
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f'SELECT DISTINCT GAME_ID FROM boxscoretraditionalv2_0 ORDER BY GAME_ID DESC LIMIT {N_last_game}', conn)
        last_game_id = list(reversed(df.GAME_ID))
        old_stats = self.remove_records(self.players_stats, last_game_id)
        new_stats = old_stats
        logger.info('Start processing...')
        for game_id in tqdm(last_game_id):
            new_data =  self.all_data.query("""GAME_ID==@game_id""")
            new_stats = self.add_record(new_stats, new_data)
              
        answer = {
            'title': f'For the past {N_last_game} games',
            'result':[]
        }
        
        logger.info('calculation of strategy results ...') 
        for strategy in tqdm(self.strategies.values()):
            answer['result'].append(strategy.result(old_stats, new_stats))
            
        answer['result']  = list(filter(lambda x: x !=None, answer['result']))
        return  answer
    
    def get_twits(self,
                  N_last_game: int):
        """
        Создать твиты в зависимости от стратегии
        
        Аргументы:
            N_last_game - сколько последних игр взять для проверки рейтинга
        """
        
        result = self.get_report(N_last_game)
        
        title = result['title']
        twits = []
        logger.info('Tweeting ...')
        for data_prompt in tqdm(result['result']):
            for_prompt = {'title': title, 'data': data_prompt }
            prompt = self.prompt_template.format(stat_players=for_prompt)
            twit = get_completion(prompt, model="gpt-3.5-turbo") 
            twits.append(twit)
            
        return twits
    
            

        
    