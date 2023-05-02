"""
Manager class to handle pandas dataframe.
"""
import pandas as pd
from typing import Optional

DF_FILENAME = "df_oddsportal_next.parquet"

class DataframeManager():

    # create cache
    _df_store: Optional[pd.DataFrame] = None
    # create method to delete cache

    def __init__(self, is_first_run):
        """
        Constructor.

        Args:
            is_first_run (bool): Is this the first DataframeManager
                created in this run?
        """

        if is_first_run:
            self.clear_kept_datasets()
            self.df = pd.DataFrame(columns=[
                'league',
                'area',
                'retrieved_from_url',
                'season',
                'game_type',
                'start_time',
                'end_time',
                'team1',
                'team2',
                'team1_score',
                'team2_score',
                'outcome',
                'team1_odds',
                'team2_odds',
                'draw_odds'
            ])
        else:
            self.recover_kept_datasets()

    def add_soccer_match(self, league, retrieved_from_url, match):
        """
        Insert a soccer match entry into the dataframe.

        Args:
            league (dict): The dict result from parsing a league.json file.

            retrieved_from_url (str): URL this match was retrieved from.

            match (object): The SoccerMatch to insert into the Dataframe.
        """

        self.df = self.df.append(
            {
                'league': league["league"],
                'area': league["area"],
                'retrieved_from_url': retrieved_from_url,
                'season': match.get_season(),
                'game_type': match.get_game_type_string(),
                'start_time': match.get_start_time_unix_int(),
                'end_time': match.get_end_time_unix_int(),
                'team1': match.get_team1_string(),
                'team2': match.get_team2_string(),
                'team1_score': match.get_team1_score(),
                'team2_score': match.get_team2_score(),
                'outcome': match.get_outcome_string(),
                'team1_odds': match.get_team1_odds(),
                'team2_odds': match.get_team2_odds(),
                'draw_odds': match.get_draw_odds(),
            },
            ignore_index=True
        )

    def save_current_df_as_parquet(self):
        """
        Save current dataframe locally as parquet file.
        """

        self.df.to_parquet(DF_FILENAME)

    def save_cached_df_as_parquet(self):
        """Save cached dataframe locally as parquet file."""
        print("Storing cached dataset for further use")
        if not isinstance(DataframeManager._df_store, pd.DataFrame):
            print(
                "Cannot store cached dataset because it is empty or was never"
                " kept"
            )
            self.df = None
            raise Exception(
                "Cannot store cached dataset because it is empty or was never"
                " kept"
            )
        DataframeManager._df_store.to_parquet(DF_FILENAME)

    def keep_dataset(self):
        """Concat current df to the df in DataframeManager's cache."""

        if DataframeManager._df_store is None:
            DataframeManager._df_store = self.df.copy()
        else:
            DataframeManager._df_store = pd.concat(
                [DataframeManager._df_store, self.df], ignore_index=True
            )

    def recover_kept_datasets(self):
        """Overwrite df in DataframeManager class with the df in cache."""
        print("Storing current dataset for further use")
        if not isinstance(DataframeManager._df_store, pd.DataFrame):
            print(
                "Cannot recover dataset because it is empty or was never kept"
            )
            self.df = None
            raise Exception(
                "Cannot recover dataset because it is empty or was never kept"
            )
        print(
            "Overwriting dataset with kept datasets. "
            f"Now dataset has {len(DataframeManager._df_store)} rows"
        )
        self.df = DataframeManager._df_store.copy()

    def clear_kept_datasets(self):
        """Clear datasets kept in the object's memory."""
        print("Clear kept dataset")
        if isinstance(DataframeManager._df_store, pd.DataFrame):
            DataframeManager._df_store.drop(
                DataframeManager._df_store.index, inplace=True
            )
        DataframeManager._df_store = None
