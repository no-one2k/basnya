import pickle
import os

import shap
import pandas as pd
import numpy as np
import sqlite3
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from typing import List
from langchain.pydantic_v1 import BaseModel, Field
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import openai
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda, RunnableBranch
from operator import itemgetter

from anomaly.resource.prompts_template import *


load_dotenv('openai.env')
openai.api_key  = os.getenv('OPENAI_API_KEY')
os.getenv('OPENAI_API_KEY')


COLS = ['min_sec', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA',
        'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS', 'PLUS_MINUS']
SEED = 42


#============================== Lang Chain ==================================================
class SelectedItem(BaseModel):
    item_name: str = Field(description="name of selected item from Player's stats line")
    item_value: float = Field(description="value of selected item from Player's stats line")
class SelectedItems(BaseModel):
    selected_items: List[SelectedItem]

# ================================= Utils ==================================================
def cast_to_0_1(preds):
    """
    from  -1 for outlies and 1 for inliers
    to 0 for inliers and 1 for outliers)
    """
    return (preds == -1).astype(int)


def explain_outlier(shap_value, columns=COLS, top_k=5):
    """
    Get TOP abnormal features
    """
    _vals = shap_value.values
    top_5 = np.argsort(_vals)[:top_k]
    return ({columns[idx]: _vals[idx] for idx in top_5})


def get_history_analog(selected_items, df_history):
    query = []
    for _item in selected_items.selected_items:
        _name = _item.item_name
        _val = _item.item_value
        mean_val = df_history[_name].mean()
        _sign = ">=" if _val > mean_val else "<="
        query.append(f"({_name} {_sign} {_val})")
    query = " and ".join(query)
    return df_history.query(query).sort_values('GAME_DATE', ascending=False)

def get_stat_line_from_analog(df_analog, sel_items: SelectedItems):
    if df_analog.empty:
        return {}

    similar_sel_items = {_item.get("item_name"): df_analog[_item.get("item_name")].iloc[0] 
                         for _item in sel_items.dict().get("selected_items", [])} 
    result = {
        "similar_player_name": df_analog.PLAYER_NAME.iloc[0],
        "similar_team_name": df_analog.TEAM_CITY.iloc[0],
        "similar_date": df_analog.GAME_DATE.iloc[0], 
        "similar_sel_items": similar_sel_items,
    }
    return result

def _get_similar_dict(inputs):
    sel_items = inputs['sel_items']
    df_analog = get_history_analog(selected_items=sel_items, df_history=self.df_train)
    inputs['sim_dict'] = get_stat_line_from_analog(df_analog, sel_items=sel_items)
    return inputs

def use_tweet_with_analog(inputs):
    result = (inputs is not None) and (inputs.get("sim_dict", {}).get('similar_sel_items') is not None)
    print(f'use analog: {result}')
    return result

# ================= AnomalyСalculation: ===================================================
class  AnomalyСalculation:
    '''
    Рассчёт аномалий по прошедшим играм
    '''
    
    def __init__(self, db_path):
        # для рассчёта аномалий
        self.calculus_col = ['min_sec', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 
                             'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS', 'PLUS_MINUS']
        
        # для доп контекста
        self.labels_col =  ['GAME_ID', 'TEAM_ID',	'TEAM_ABBREVIATION',	
                            'TEAM_CITY',	'PLAYER_ID',	'PLAYER_NAME',	'NICKNAME']
        self.db_path = db_path
    
    
    def get_data(self):
        """
        Получить данные из локаьной SQLite
        
        Аргументы:
            db_path - путь до локальной БД
            limit - указывает, солько последних записей взять
        Возвращает:
            df - данные из бд в формате DataFrame
        """

        conn = sqlite3.connect(self.db_path)
        
        game2date = (
            pd.read_sql_query("SELECT * FROM GAMES", conn)
            .set_index('GAME_ID')['GAME_DATE_EST']
            ).to_dict()
        
        df = (
            pd.read_sql_query(f"SELECT * FROM boxscoretraditionalv2_0", conn)
            .drop('index', axis=1)
        )
        df[['_min', '_sec']] = df['MIN'].str.split(':', expand=True).fillna(0)
        df['min_sec'] = df._min.astype(float) + df._sec.astype(int) / 60 
        df['GAME_DATE'] = pd.to_datetime(df['GAME_ID'].map(game2date)).fillna(pd.to_datetime('1900-01-01'))
        return df.fillna(0)
    
    def get_anomalous_records(self, 
                              game_id: int, 
                              path_model_weights=None) -> pd.DataFrame:
        """
        Получить аномальные значения
        
        Аргументы:
            game_id - идентификатор игры,ПОСЛЕ которого игры проверяются на аномальность
        Возвращает: DataFrame с аномальными значениями
        """
        
        df = self.get_data()
        date = df.query(f'GAME_ID=={game_id}')['GAME_DATE'].unique()[0]
        
        df_train = df.loc[df['GAME_DATE'] <= pd.to_datetime(date)]
        df_test = df.loc[df['GAME_DATE'] > pd.to_datetime(date)]
        
        self.df_train = df_train
        self.df_test = df_test
        
        scaler = StandardScaler()
        
        X_train = scaler.fit_transform(df_train[self.calculus_col])
        X_test = scaler.transform(df_test[self.calculus_col])
        
        # create and fit IsolationForest model
        CONTAMINATION = 0.01
        clf =  IsolationForest(contamination=CONTAMINATION, random_state=SEED)

                 
        if path_model_weights==None:
            clf.fit(X_train)
            with open(r'isolation_forest_model.pkl', 'wb') as file:
                 pickle.dump(clf, file)
            
        else:
            with open(path_model_weights, 'rb') as file:
                clf = pickle.load(file)
            
        _preds = cast_to_0_1(clf.predict(X_test)) # if anomaly:1 else:0
        self._preds = _preds # get anomaly indices
        
        # explanation of anomalies for isolation forest
        explainer = shap.TreeExplainer(clf, feature_names=self.calculus_col)
        # get shape_values for each example X_test 
        shap_values = explainer(X_test) 
        self.shap_values = shap_values 
           
    def get_anomaly_stats_with_context(self, game_id: int):
        """
        Получить аномальную статистику по игрокам с контекстом (для подачи в GPT)
        """
        
        self.get_anomalous_records(game_id)
        df_test = self.df_test
        _preds = self._preds
        shap_values = self.shap_values
        
        
        
        anomaly_stats = []
        for index, row in df_test[_preds == 1].reset_index(drop=True).iterrows():
            _player_name = row.PLAYER_NAME
            _team_name = row.TEAM_CITY
            _importance = explain_outlier(shap_values[_preds == 1][index])
            _stat_line = ", ".join([f"{col} = {row[col]}" for col, _ in sorted(_importance.items(), key=lambda p: p[1])])
            anomaly_stats.append((_player_name, _team_name,_stat_line))
            
        return anomaly_stats
    
    def _get_similar_dict(self, inputs):
        sel_items = inputs['sel_items']
        df_analog = get_history_analog(selected_items=sel_items, df_history= self.df_train)
        inputs['sim_dict'] = get_stat_line_from_analog(df_analog, sel_items=sel_items)
        return inputs
    
    def create_twits(self, game_id):
        """
        Обработка аномальной статистики с помощью LangChain и создание твитов
        """
        
         # for _get_history_analogy
        
        model_strict = OpenAI(temperature=0)
        model_creative = OpenAI(temperature=0.2)
        
        anomaly_stats = self.get_anomaly_stats_with_context(game_id=game_id)
     
        
        prompt_tweet_only_stats = PromptTemplate.from_template(prompt_template_tweet_only_stats)
        parser_sel_items = PydanticOutputParser(pydantic_object=SelectedItems)
        prompt_sel_items = PromptTemplate(
                        template=prompt_template_sel_items,
                        input_variables=["stat_line"],
                        partial_variables={"format_instructions": parser_sel_items.get_format_instructions()})
        
        prompt_tweet_only_stats = PromptTemplate.from_template(prompt_template_tweet_only_stats)
        prompt_tweet_with_analog = PromptTemplate.from_template(prompt_template_tweet_with_analog)
        
        chain_sel_items = (
            prompt_sel_items 
            | model_strict 
            | parser_sel_items
        )
        
        chain_final = (
                {'sel_items': chain_sel_items, # список статов, которые выбрала модель
                "player_name": itemgetter("player_name"),
                "team_name": itemgetter("team_name"),
          
                }
                | RunnableLambda(self._get_similar_dict)
                | RunnableBranch(
                    (use_tweet_with_analog, prompt_tweet_with_analog),
                    prompt_tweet_only_stats
                )
                | model_creative
                
            )
        
        tweets = []
        for _player_name, _team_name, _stat_line in anomaly_stats:
            tweet = chain_final.invoke({"stat_line": _stat_line, "player_name": _player_name, "team_name": _team_name})
            tweets.append(tweet)
            
        return tweets
        
        