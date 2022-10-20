"""
Soccer match results scraping object.
"""

from bs4 import BeautifulSoup
from DbManager import DatabaseManager
from DfManager import DataframeManager
import json
import re
import time
from selenium import webdriver
from SoccerMatch import SoccerMatch

class Scraper():

    def __init__(self, league_json, initialize_db):
        """
        Constructor. Launch the web driver browser, initialize the league
        field by parsing the representative JSON file, and connect to the
        database manager.

        Args:
            league_json (str): JSON string of the league to associate with the
                Scraper.
            initialize_db (bool): Should the database be initialized?
        """

        self.browser = webdriver.Chrome("/usr/local/bin/chromedriver")
        self.league = self.parse_json(league_json)
        self.db_manager = DatabaseManager(initialize_db)
        self.df_manager = DataframeManager(initialize_db)

    def parse_json(self, json_str):
        """
        Parse a JSON string into a dict.

        Args:
            json_str (str): JSON string to parse.

        Returns:
            (dict)
        """

        return json.loads(json_str)

    def scrape_all_urls(self, do_verbose_output=False):
        """
        Call the scrape method on every URL in this Scraper's league field, in
        order, then close the browser.

        Args:
            do_verbose_output (bool): True/false do verbose output.
        """

        if do_verbose_output is True:
            output_str = "Start scraping " + self.league["league"] + " of "
            output_str += self.league["area"] + "..."
            print(output_str)

        for url in self.league["urls"]:
            if do_verbose_output:
                list_season_str = [
                    ele for ele in url.split("/")
                    if ele.startswith('bundesliga')
                ]
                if len(list_season_str) == 0:
                    season_str = "Bundesliga this year"
                else:
                    season_str = list_season_str[0]
                print(f"Starting season {season_str} ...")

            # loop through all pages in that season
            page = 1
            while self.scrape_url("#/page/".join((url, "{}/".format(page)))):
                if do_verbose_output:
                    print("Scraped page", page)
                page += 1

            if do_verbose_output:
                print(f"Finished season {season_str}!")
                print("\n")

        self.browser.quit()

        # keep dataframe in cache of class
        self.df_manager.keep_dataset()

        if do_verbose_output is True:
            print("Done scraping this league.")

    def scrape_url(self, url):
        """
        Scrape the data for every match on a given URL and insert each into the
        database.

        Args:
            url (str): URL to scrape data from.

        Returns:
            Whether data existed for that season.
        """

        self.browser.get(url)

        # waiting for table to load
        # needed or else the data won't be complete
        delay = 5 # seconds
        time.sleep(delay)

        tournament_tbl = self.browser.find_element_by_id("tournamentTable")
        tournament_tbl_html = tournament_tbl.get_attribute("innerHTML")
        tournament_tbl_soup = BeautifulSoup(tournament_tbl_html, "html.parser")
        try:
            significant_rows = tournament_tbl_soup(self.is_soccer_match_or_date)
        except:
            return False

        current_date_str = None
        for row in significant_rows:
            if self.is_date(row) is True:
                current_date_str = self.get_date(row)
            elif self.is_date_string_supported(current_date_str) == False:
                # not presently supported
                continue
            else:  # is a soccer match
                this_match = SoccerMatch()
                game_datetime_str = current_date_str + " " + self.get_time(row)
                this_match.set_start(game_datetime_str)
                season = self.get_season(row)
                this_match.set_season(season)
                participants = self.get_participants(row)
                this_match.set_teams(participants)
                try:
                    scores = self.get_scores(row)
                except:
                    if (
                        participants == ['Bayern Munich', 'Freiburg']
                    ) and (
                        game_datetime_str == '13 Mar 2010 16:30'
                    ):
                        scores = [2, 1]
                    elif (
                        participants == [
                            'Hertha Berlin', 'B. Monchengladbach'
                        ]
                    ) and (
                        game_datetime_str == '23 Jan 2010 13:30'
                    ):
                        scores = [0, 0]
                    elif (
                        participants == [
                            'Bayern Munich', 'Hoffenheim'
                        ]
                    ) and (
                        game_datetime_str == '15 Jan 2010 18:30'
                    ):
                        scores = [2, 0]
                    else:
                        import pdb; pdb.set_trace()
                this_match.set_scores(scores)
                this_match.set_outcome_from_scores(scores)
                odds = self.get_odds(row)
                this_match.set_odds(odds)
                # extra_info = self.get_extra_info(row)
                # this_match.set_extra_info(extra_info)
                self.db_manager.add_soccer_match(self.league, url, this_match)
                self.df_manager.add_soccer_match(self.league, url, this_match)

        return True

    def is_soccer_match_or_date(self, tag):
        """
        Determine whether a provided HTML tag is a row for a soccer match or
        date.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool)
        """

        if tag.name != "tr":
            return False
        if "center" in tag["class"] and "nob-border" in tag["class"]:
            return True
        if "deactivate" in tag["class"] and tag.has_attr("xeid"):
            return True
        return False

    def is_date(self, tag):
        """
        Determine whether a provided HTML tag is a row for a date.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool)
        """

        return "center" in tag["class"] and "nob-border" in tag["class"]

    def is_date_string_supported(self, date_string):
        """
        Determine whether a given date string is currently supported by this
        software's parsing capabilities.

        Args:
            date_string (str): Date string to assess.

        Returns:
            (bool)
        """

        if date_string is None:
            return False
        elif "Today" in date_string:
            return False
        elif "Yesterday" in date_string:
            return False
        elif "Qualification" in date_string:
            return False
        elif "Promotion" in date_string:
            return False
        return True

    def get_date(self, tag):
        """
        Extract the date from an HTML tag for a date row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (str) Extracted date string.
        """

        this_date = tag.find(class_="datet").string
        if "Today" in this_date:
            return "Today"
        elif this_date.endswith(" - Play Offs"):
            this_date = this_date[:-12]
        elif this_date.endswith(" - Relegation"):
            this_date = this_date[:-12]
        return this_date

    def get_time(self, tag):
        """
        Extract the time from an HTML tag for a soccer match row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (str) Extracted time.
        """

        return tag.find(class_="datet").string

    def get_participants(self, tag):
        """
        Extract the match's participants from an HTML tag for a soccer match
        row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of str) Extracted match participants.
        """

        parsed_strings = tag.find(class_="table-participant").text.split(" - ")
        participants = []
        participants.append(parsed_strings[0].replace('\xa0', ''))
        participants.append(parsed_strings[-1].replace('\xa0', ''))
        return participants

    def get_season(self, tag):
        """
        Extract the season the match is played in from an HTML tag for a
        soccer match row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (str) season.
        """

        parsed_href_elements = tag.find(
            class_="table-participant"
        ).contents[0].attrs['href'].split('/')

        for ele in parsed_href_elements:
            if ele.startswith('bundesliga'):
                return "-".join(ele.split('-')[1:])

        return ""
        

    def get_scores(self, tag):
        """
        Extract the scores for each team from an HTML tag for a soccer match
        row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of int) Extracted match scores.
        """

        score_str = tag.find(class_="table-score").string
        if self.is_invalid_game_from_score_string(score_str):
            return [-1,-1]
        non_decimal = re.compile(r"[^\d]+")
        score_str = non_decimal.sub(" ", score_str)
        scores = [int(s) for s in score_str.split()]
        return scores

    def get_odds(self, tag):
        """
        Extract the betting odds for a match from an HTML tag for a soccer
        match row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of str) Extracted match odds.
        """

        odds_cells = tag.find_all(class_="odds-nowrp")
        odds = []
        for cell in odds_cells:
            odds.append(cell.text)
        return odds

    def is_invalid_game_from_score_string(self, score_str):
        """
        Assess, from the score string extracted from a soccer match row,
        whether a game actually paid out one of the bet outcomes.

        Args:
            score_str (str): Score string to assess.

        Returns:
            (bool)
        """

        if score_str == "postp.":
            return True
        elif score_str == "canc.":
            return True
        return False
