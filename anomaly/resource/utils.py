import sqlite3
from typing import List

import joblib
import numpy as np
import pandas as pd
import shap
from langchain.llms import OpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.pydantic_v1 import BaseModel, Field

from anomaly.resource.prompts_template import *
from signal_indicator.resource.utils import Tweet, TweetType

DEFAULT_GPT_MODEL = 'gpt-3.5-turbo-instruct'


# ============================== Lang Chain ==================================================
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


def explain_outlier(shap_value, columns, top_k=5):
    """
    Get TOP abnormal features
    """
    _vals = shap_value.values
    top_5 = np.argsort(_vals)[:top_k]
    return {columns[idx]: _vals[idx] for idx in top_5}


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


# ================= AnomalyСalculation: ===================================================
class AnomalyCalculation:
    """
    Рассчёт аномалий по прошедшим играм
    """

    def __init__(self, db_path, path_model_weights):
        # для рассчёта аномалий
        self.calculus_col = ['min_sec', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA',
                             'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS', 'PLUS_MINUS']

        # для доп контекста
        self.labels_col = ['GAME_ID', 'TEAM_ID', 'TEAM_ABBREVIATION',
                           'TEAM_CITY', 'PLAYER_ID', 'PLAYER_NAME', 'NICKNAME']
        self.db_path = db_path
        self.clf = joblib.load(path_model_weights)
        self.df = self.get_data()

    def get_data(self):
        """
        Получить данные из локаьной SQLite
        
        Аргументы:
            db_path - путь до локальной БД
            limit - указывает, солько последних записей взять
        Возвращает:
            df - данные из бд в формате DataFrame
        """

        with sqlite3.connect(self.db_path) as conn:
            game2date = (
                pd.read_sql_query("SELECT * FROM GAMES", conn)
                .set_index('GAME_ID')['GAME_DATE_EST']
            ).to_dict()

            df = (
                pd.read_sql_query(f"SELECT * FROM boxscoretraditionalv2_0", conn)
                .drop('index', axis=1)
            )
        df[['_min', '_sec']] = df['MIN'].str.split(':', expand=True).fillna(0)
        df['min_sec'] = df['_min'].astype(float) + df['_sec'].astype(int) / 60
        df['GAME_DATE'] = pd.to_datetime(df['GAME_ID'].map(game2date)).fillna(pd.to_datetime('1900-01-01'))
        return df.fillna(0)

    def get_anomalous_records(self, df_test: pd.DataFrame):
        """
        Получить аномальные значения
        
        Аргументы:
            game_id - идентификатор игры,ПОСЛЕ которого игры проверяются на аномальность
        Возвращает: DataFrame с аномальными значениями
        """
        x_test = df_test[self.calculus_col].values
        predictions = cast_to_0_1(self.clf.predict(x_test))  # if anomaly:1 else:0
        _scaler, _iso_forest = [st[1] for st in self.clf.steps]
        explainer = shap.TreeExplainer(_iso_forest, feature_names=self.calculus_col)
        shap_values = explainer(_scaler.transform(x_test))
        return predictions, shap_values

    def _get_train_test_df(self, game_ids: List[int]) -> (pd.DataFrame, pd.DataFrame):
        df_test = self.df[self.df.GAME_ID.isin(game_ids)].drop_duplicates()
        min_date = df_test.GAME_DATE.min()
        df_train = self.df[self.df.GAME_DATE < min_date].drop_duplicates()
        return df_train, df_test

    def get_anomaly_stats_with_context(self, df_test: pd.DataFrame) -> pd.DataFrame:
        """
        Получить аномальную статистику по игрокам с контекстом (для подачи в GPT)
        """

        predictions, shap_values = self.get_anomalous_records(df_test=df_test)

        anomaly_stats = []
        for index, row in df_test[predictions == 1].reset_index(drop=True).iterrows():
            _importance = explain_outlier(shap_value=shap_values[predictions == 1][index], columns=self.calculus_col)
            _stat_line = ", ".join(
                [f"{col} = {row[col]}" for col, _ in sorted(_importance.items(), key=lambda p: p[1])])
            anomaly_stats.append((row.GAME_ID_STR, row.PLAYER_ID, row.PLAYER_NAME, row.TEAM_ABBREVIATION, _stat_line))

        return pd.DataFrame(anomaly_stats, columns=['GAME_ID_STR', 'PLAYER_ID', 'PLAYER_NAME',
                                                    'TEAM_ABBREVIATION', '_stat_line'])

    def get_tweets(self, selected_game_ids: List[str]) -> List[Tweet]:
        """
        Обработка аномальной статистики с помощью LangChain и создание твитов
        """

        int_selected_game_ids = [int(_g) for _g in selected_game_ids]
        df_train, df_test = self._get_train_test_df(game_ids=int_selected_game_ids)
        anomaly_stats = self.get_anomaly_stats_with_context(df_test=df_test)

        model_strict = OpenAI(temperature=0, model=DEFAULT_GPT_MODEL)
        model_creative = OpenAI(temperature=0.2, model=DEFAULT_GPT_MODEL)

        parser_sel_items = PydanticOutputParser(pydantic_object=SelectedItems)
        prompt_sel_items = PromptTemplate.from_template(
            template=prompt_template_sel_items,
            partial_variables={
                "format_instructions": parser_sel_items.get_format_instructions(),
                "indicators": ", ".join(self.calculus_col),
            }
        )

        prompt_tweet_only_stats = PromptTemplate.from_template(prompt_template_tweet_only_stats)
        prompt_tweet_with_analog = PromptTemplate.from_template(prompt_template_tweet_with_analog)

        chain_sel_items = (
            prompt_sel_items
            | model_strict
            | parser_sel_items
        )

        chain_with_analog = (
            prompt_tweet_with_analog
            | model_creative
        )

        chain_stats_only = (
            prompt_tweet_only_stats
            | model_creative
        )

        def _get_similar_dict(inputs):
            sel_items = inputs['sel_items']
            df_analog = get_history_analog(selected_items=sel_items, df_history=df_train)
            inputs['sim_dict'] = get_stat_line_from_analog(df_analog, sel_items=sel_items)
            return inputs

        def _use_tweet_with_analog(inputs):
            result = (inputs is not None) and (inputs.get("sim_dict", {}).get('similar_sel_items') is not None)
            print(f'use analog: {result}')
            return result

        def _run_chains(inputs):
            sel_items_from_llm = chain_sel_items.invoke(inputs)
            sel_items = []
            for si in sel_items_from_llm.selected_items:
                if si.item_name in self.calculus_col:
                    sel_items.append(si)
                else:
                    print(f"Erroneous selected item: {si}")
            sel_items = SelectedItems(selected_items=sel_items)
            args = {
                "sel_items": sel_items,  # список статов, которые выбрала модель
                "player_name": inputs["player_name"],
                "team_name": inputs["team_name"],
            }
            args = _get_similar_dict(args)
            use_analog = _use_tweet_with_analog(args)
            if use_analog:
                return chain_with_analog.invoke(args), TweetType.ANOMALY_REPEAT
            else:
                return chain_stats_only.invoke(args), TweetType.ANOMALY_UNIQUE

        tweets = []
        for _, row in anomaly_stats.iterrows():
            tweet_text, tweet_type = _run_chains(
                inputs={
                    "stat_line": row['_stat_line'],
                    "player_name": row['PLAYER_NAME'],
                    "team_name": row['TEAM_ABBREVIATION']
                }
            )
            tweets.append(Tweet(
                player_ids=[row['PLAYER_ID']],
                game_ids=[row['GAME_ID_STR']],
                tweet_text=tweet_text,
                tweet_type=tweet_type
            ))

        return tweets
