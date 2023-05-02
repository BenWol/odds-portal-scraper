"""
Soccer match object.
"""

from datetime import datetime
import time

MINUTES_TO_SECONDS = 60

class SoccerMatch():

    def __init__(self):
        """
        Constructor.
        """

        self.start = None
        self.season = ""
        self.team1 = ""
        self.team2 = ""
        self.team1_score = ""
        self.team2_score = ""
        self.team1_odds = ""
        self.team2_odds = ""
        self.draw_odds = ""
        self.outcome = ""
        self.game_type = ""

    def set_start(self, start_time_str):
        """
        Set the match's start time from a formatted string.

        Args:
            start_time_str (str): String representing the match start time,
                expected in the format of "%d %b %Y %H:%M".
        """
        self.start = datetime.strptime(start_time_str, "%d %b %Y %H:%M")

    def set_season(self, season):
        """
        Set the match's season.

        Args:
            season (str): String representing season.
        """

        # check if season is given
        if season == "xx/xx":
            if self.start.month in range(0,7):
                self.season = f"{self.start.year-1}/{self.start.year}"
            else:
                self.season = f"{self.start.year}/{self.start.year+1}"
        else:
            self.season = season

    def set_teams(self, participants):
        """
        Set the match's participating teams.

        Args:
            participants (list of str): The names of team 1 and team 2, in
                that order.
        """

        self.team1 = participants[0]
        self.team2 = participants[1]

    def set_scores(self, scores):
        """
        Set the match's team 1 and team 2 scores.

        Args:
            scores (list of int): Team 1 and team 2 scores, in that order.
        """

        self.team1_score = scores[0]
        self.team2_score = scores[1]

    def set_outcome_from_scores(self, scores):
        """
        Set the match's outcome string, based on team 1 and team 2 scores.

        Args:
            scores (list of int): Team 1 and team 2 scores, in that order.
        """

        if scores == None or len(scores) == 0:
            self.outcome = "NONE"
        elif scores[0] == -1 and scores[1] == -1:
            self.outcome = "NONE"
        elif scores[0] > scores[1]:
            self.outcome = "TEAM1"
        elif scores[0] < scores[1]:
            self.outcome = "TEAM2"
        else:
            self.outcome = "DRAW"

    def set_odds(self, odds):
        """
        Set the odds-related fields.

        Args:
            odds (list of float): The odds od a team 1 win, a draw, and a team
                2 win, in that order.
        """

        self.team1_odds = odds[0]
        self.draw_odds = odds[1]
        self.team2_odds = odds[2]

    def set_game_type(self, game_type):
        """
        Set the game type field.

        Args:
            game_type (string): Game type, , i.e. 'leaque' or 'promotion'.
        """

        self.game_type = game_type

    def get_start_time_unix_int(self):
        """
        Get the start time of a match, as a Unix format timestamp (GMT+5).

        Returns:
            (int) Start time as a Unix timestamp.
        """

        if self.start is None:
            return 0
        return int(time.mktime(self.start.timetuple()))

    def get_end_time_unix_int(self):
        """
        Get the estimated end time of a game, where the estimate is the start
        time plus 90 minutes and 15 minutes break, as a Unix format timestamp
        (GMT+5).

        Returns:
            (int) Estimated end time as a Unix timestamp.
        """

        if self.start is None:
            return 0
        return ((90 + 15) * MINUTES_TO_SECONDS) + int(
            time.mktime(self.start.timetuple())
        )

    def get_season(self):
        """
        Get the match's season.

        Args:
            season (str): String representing season.
        """

        return self.season

    def get_team1_score(self):
        """
        Get the score of team1.

        Returns:
            (str) score of team 1.
        """

        return self.team1_score

    def get_team2_score(self):
        """
        Get the score of team2.

        Returns:
            (str) score of team 2.
        """

        return self.team2_score

    def get_team1_string(self):
        """
        Get the name of participating team 1.

        Returns:
            (str) Name of participating team 1.
        """

        return self.team1

    def get_team2_string(self):
        """
        Get the name of participating team 2.

        Returns:
            (str) Name of participating team 2.
        """

        return self.team2

    def get_team1_odds(self):
        """
        Get the odds of a team 1 win.

        Return:
            (str) Team 1 win odds.
        """

        return self.team1_odds

    def get_team2_odds(self):
        """
        Get the odds of a team 2 win.

        Return:
            (str) Team 2 win odds.
        """

        return self.team2_odds

    def get_draw_odds(self):
        """
        Get the odds of a match draw.

        Return:
            (str) Draw odds.
        """

        return self.draw_odds

    def get_outcome_string(self):
        """
        Get the outcome as a string - TEAM1 (team 1 win), TEAM2 (team 2 win),
        DRAW (draw), and NONE (no outcome, i.e. postponement or cancellation).

        Return:
            (str) Outcome string.
        """

        return self.outcome
    
    def get_game_type_string(self):
        """
        Get the game type as a string.

        Return:
            (str) Game type string, i.e. 'leaque' or 'promotion'.
        """

        return self.game_type
