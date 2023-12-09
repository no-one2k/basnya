from abc import ABC, abstractmethod
from typing import Dict, List
import logging

import pandas as pd 


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
output_handler = logging.StreamHandler()
output_handler.setLevel(logging.INFO)
logger = logging.getLogger()

class Strategy(ABC):
    '''
    Интерфейс для стратегии рассчёта сигнальных показателей
    '''

    @abstractmethod
    def result():
        """
        Показать данные после рассчета по стратегии 
        """
        pass
    

class StrategyRating(Strategy):
    """
    Расчёт сигнальных показателейна основе ТОПов
    """
    
    def __init__(self, top: int, playerID2name: dict = None):
        """ 
        Аргументы:
            top - количество лучших игроков, которых учитывает рейтинг        
            playerId2name - справочник для перевода id игрока в более подробную информацию  
        """


        self.top=top
        self.title = f'Top-{self.top}'
        self.calculus_columns = ['MIN', 'FGM','FGA','FG3M','FTM','FTA',
                              'FT_PCT','OREB','DREB','REB','AST','STL','BLK','TO','PF','PTS']
        self.playerID2name= playerID2name
   

    def __repr__(self) -> str:
         return self.title
     
    def _calculate_rating(self, players_stats: dict) -> Dict[str, pd.DataFrame]:
        """
        Рассчёт рейтинга для всех игроков по данным players_stats
        
        Аргументы:
            players_stats - статистика по игрокам. Ключи - индексы игроков, 
                            значения - сисок статистики по игроку за все указанные игры
        Возвращает:
            словарь, где:
                ключь - это наименование сигнального показателя (MIN, PTS и т.п.)
                значение - это DataFrame со следующими колонками:
                    PLAYER_ID - идентификатор игрока
                    VALUE - суммарное значение показателя игрока за весь период рассчёта
                    RATING - какое место занимает игрок в рейтинге по этому показателю \
                        относительно других игроков (0 - самое высокое место)            
        """
        
        # агрегация (суммирование) по игрокам 
        df_all = pd.concat([pd.DataFrame(records) for _, records in players_stats.items()], axis=0)
        df_all = df_all.groupby('PLAYER_ID').sum()
        #  получение словаря с рейтингами игроков для каждого сигнального показателя
        ratings = {col: df_all[col].sort_values(ascending=False).to_frame().reset_index()\
                    .rename(columns={col:'VALUE'}).assign(RATING=range(len(df_all[col]))) for col in df_all.columns} 
                                                            
        return ratings
        
    def result(self,
               old_stats: dict, 
               new_stats: dict,
               top=None):
        """
        Показать изменения рейтинга (показать N лучших игроков)
        
        Аргументы:
            top - N лучших игроков рейтинга 
            old_stats - изначальная статистика по игрокам
            new_stats - новая статистика по игрокам
        """

        if top == None:
            top = self.top
        
        result ={'in_top':{}, 
                'out_top':{}}
        
        old_rating = self._calculate_rating(old_stats)
        new_rating = self._calculate_rating(new_stats)    
        
        # получим N лучших игроков
        old_rating_N = {indicator: value.iloc[:top] for indicator, value in old_rating.items()}
        new_rating_N = {indicator: value.iloc[:top] for indicator, value in new_rating.items()}
        
        old_top = {col: set(old_rating_N[col]['PLAYER_ID'].to_list()) for col in old_rating_N.keys()}
        new_top = {col: set(new_rating_N [col]['PLAYER_ID'].to_list()) for col in new_rating_N.keys()}
     
        for col in self.calculus_columns:
                if self.playerID2name: # если передали словарь
                    in_top =  [self.playerID2name.get(player_id, '<UNKNOW>') 
                               for player_id in list(new_top[col] - old_top[col])]
                    out_top = [self.playerID2name.get(player_id, '<UNKNOW>') 
                               for player_id in list(old_top[col] -  new_top[col])]
                else:
                    in_top =  list(new_top[col] - old_top[col])
                    out_top = list(old_top[col] -  new_top[col])
                    
                
                if in_top:
                        result['in_top'][col] = in_top
                if out_top:
                        result['out_top'][col] = out_top
                        
        if  (not result['in_top'] ) & (not result['out_top']):
            return None    
            
        answer = {'description': f'Top {top} players',
                  'values': result}   
        return  answer  
           
 
        

    