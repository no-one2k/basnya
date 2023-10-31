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

from dotenv import load_dotenv
import openai
from tqdm import tqdm
import pandas as pd

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
    
    
def get_file_list(path_docs: str) -> List[str]:
    """
    Получитьл список всех файлов в папке
    
    Аргументы:
        path_docs - путь до папки с исходниками для рассчёта статистики  
    Возвращает:
        список путей исходников
    """
    
    path = Path(path_docs)
    parent =  path.parent
    name = path.name
    return [parent/name/path for path in os.listdir(path)]


class StatsHolder:
    """
    Класс для хранение и обработки сигнальных показателей
    """
    
    target_columns: list= ['MIN', 'FGM','FGA','FG3M','FTM','FTA','FT_PCT', 
                           'OREB','DREB','REB','AST','STL','BLK','TO','PF','PTS', 'PLAYER_ID', 'GAME_ID']
    calculus_columns: list = ['MIN', 'FGM','FGA','FG3M','FTM','FTA',
                              'FT_PCT','OREB','DREB','REB','AST','STL','BLK','TO','PF','PTS']
    labels_columns: list = ['PLAYER_ID', 'GAME_ID']
    
    def __init__(self, players_stats: Dict[int, List[pd.Series]]):
        """
        Аргументы:
            players_stats - статистика по игрокам. Ключи - индексы игроков, 
                            значения - сисок статистики по игроку за все указанные игры
        """
        
        self.players_stats: Dict[int, List[pd.Series]] = players_stats # статистика по игрокам
        self.strategies = {} # словарь, содержащий все стратегии для отслеживания сигнальных показателей
    
    def add_strategy(self, strategy):
        """
        Добавить стратегию для отслеживания сигнальных показателей
        """
        
        # obj_strategy = strategy(players_stats=self.players_stats, calculus_columns=self.calculus_columns)
        # self.strategies[obj_strategy.title] = obj_strategy
        # logger.info(f'Added "{obj_strategy.title}" strategy')
        self.strategies[strategy.title] = strategy
        logger.info(f'Added "{strategy.title}" strategy')
    
        
    
    def show_strategies(self):
        return [strategy  for strategy in  self.strategies]
    
    @classmethod
    def from_csv(cls, path_docs: str) -> 'StatsHolder':
        """ 
        Создание объекта StatsHolder из списка файлов со статистикой формата .csv
        """
       
        file_list = get_file_list(path_docs)[:100]
        players_stats = defaultdict(list)
        
        for path in tqdm(file_list, total=len(file_list)):
            df = pd.read_csv(path).fillna(0)
            
            if 'PLAYER_ID' not in df.columns:
                continue
            
            df['MIN'] = df['MIN'].apply(min_to_second)
            df[cls.calculus_columns] =df[cls.calculus_columns].fillna(0).astype(int)
            for index, row in df.iterrows():
                players_stats[row.PLAYER_ID].append(row[cls.target_columns])
                
        return cls(players_stats=players_stats)
        
        
    def add_record(self, record: pd.DataFrame) -> None:
        """
        Добавить запись к общецй статистике игроков
        
        Аргументы:
            record: pd.DataFrame - новая запись игры
        """
        
        record['MIN'] = record['MIN'].apply(min_to_second).fillna(0).astype(int)

        for _, row in record[self.target_columns].iterrows():
            player_id = row.PLAYER_ID
            game_id = row.GAME_ID
            id_game_list = [stat.GAME_ID for stat in  self.players_stats[player_id]]
             
            if game_id in id_game_list:
                logger.info(f'This GAME_ID:{game_id} is already in the dataset') 
                return None
            
            self.players_stats[player_id].append(row.fillna(0).astype(int)) 
            
        logger.info(f'added game_id: {game_id}') 
        
        # пройтись по всем стратегиям и пересчитать для них показатели
        for strategy in self.strategies.values():
            # Добавить в стратегию новый рейтинг игроков
            strategy.add_record_in_strategy(self.players_stats)
           # logger.info(strategy.show_data_strategy())
        