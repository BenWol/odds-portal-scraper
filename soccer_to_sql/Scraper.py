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
from selenium.webdriver.chrome.options import Options
from SoccerMatch import SoccerMatch
from datetime import datetime, timedelta

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
        # chrome options
        chrome_options = Options()
        # chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

        self.browser = webdriver.Chrome("/usr/local/bin/chromedriver", chrome_options=chrome_options)
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
        # add window scroll
        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        # let's go
        tournament_tbl = self.browser.find_element_by_xpath(
            "//div[@class='flex flex-col px-3 text-sm max-mm:px-0']"
        )
        tournament_tbl_html = tournament_tbl.get_attribute("innerHTML")
        tournament_tbl_soup = BeautifulSoup(tournament_tbl_html, "html.parser")

        # get season
        try:
            season = self.get_season(tournament_tbl_soup)
        except:
            # no more matches displayed per season
            return False

        # get significant rows
        significant_rows = tournament_tbl_soup.find_all(
            "div", {"class": "flex flex-col w-full text-xs eventRow"}
        )

        # start extracting information of significant match rows
        current_date_str = None
        counter = 0
        catched_rows = len(significant_rows)
        for block in significant_rows:
            game_type = 'leaque'
            sub_rows = block.find_all("div", recursive=False)
            counter_2 = 0
            for row in sub_rows:
                if self.is_date(row):
                    current_date_str = self.get_date(row)
                    if self.check_if_leaque_game(row) == False:
                        game_type = 'promotion'
                elif (
                    self.is_date_string_supported(current_date_str) == False
                ) and (counter_2 > 0):
                    # not presently supported
                    print(f"'{current_date_str}' currently not supported.")
                    continue
                elif self.is_match_and_time(row):
                    # is a soccer match w/ date
                    this_match = SoccerMatch()
                    game_datetime_str = (
                        current_date_str + " " + self.get_time(row)
                    )
                    this_match.set_start(game_datetime_str)
                    this_match.set_season(season)
                    this_match.set_game_type(game_type)
                    participants = self.get_participants(row)
                    if game_type == 'promotion':
                        print(
                            f"Match between {participants} on the "
                            f"{current_date_str} is a promotion game."
                        )
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
                    if len(odds) == 0:
                        # if no odds available, don't save the match
                        continue
                    else:
                        this_match.set_odds(odds)

                    # save match as data point
                    self.db_manager.add_soccer_match(
                        self.league, url, this_match
                    )
                    self.df_manager.add_soccer_match(
                        self.league, url, this_match
                    )
                counter_2 += 1
            counter += 1
        
        # rows successfully extracted
        print(f"{counter}/{catched_rows} matches were scraped!")

        # duplicated rows produced -> page not revewed under new page number
        duplicates = self.df_manager.df.duplicated(
            subset=[
                col for col in self.df_manager.df.columns
                if col != 'retrieved_from_url'
            ], keep = 'first'
        )
        if duplicates.any():
            # clean duplicates & keep first
            self.df_manager.df = (
                self.df_manager.df[duplicates].reset_index(drop=True)
            )
            return False

        return True

    def is_soccer_match_with_date(self, tag):
        """
        Determine whether a provided HTML tag is a row for a soccer match 
        date.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool)
        """
        if tag.name != "tr":
            return False
        if tag.has_attr("xeid"):
            # for match lines without class tag
            return True
        if "center" in tag["class"] and "nob-border" in tag["class"]:
            # for grey datelines
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
        if tag.has_attr("class"):
            return (
                "border-l" in tag["class"]
            ) and (
                "border-r" in tag["class"]
            ) and (
                "min-h-[30px]" in tag["class"]
            )
        else:
            return False

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
        elif "Relegation" in date_string:
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

        this_date = tag.find(
            class_=(
                "w-full text-xs font-normal leading-5 text-black-main "
                "font-main"
            )
        ).string.strip()
        if "Today" in this_date:
            return datetime.today().strftime("%d %b %Y")
        elif "Tomorrow" in this_date:
            return (datetime.today() + timedelta(days=1)).strftime("%d %b %Y")
        elif "Yesterday" in this_date:
            return (datetime.today() + timedelta(days=-1)).strftime("%d %b %Y")
        elif this_date.endswith(" - Play Offs"):
            return " ".join(this_date.split(" ")[:3])
        elif this_date.endswith(" - Relegation"):
            return " ".join(this_date.split(" ")[:3])
        elif this_date.endswith("Promotion"):
            return " ".join(this_date.split(" ")[:3])
        return this_date
    
    def check_if_leaque_game(self, tag):
        """
        Check if leaque or promotion game from an HTML tag for a date row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool) Extracted boolean.
        """

        this_date = tag.find(
            class_=(
                "w-full text-xs font-normal leading-5 text-black-main "
                "font-main"
            )
        ).string.strip()

        # check if date string ends with word related to promotion game
        if (
            this_date.endswith("Play Offs")
        ) or (
            this_date.endswith("Relegation")
        ) or (
            this_date.endswith("Promotion")
        ):
            return False
        return True
    
    def is_match_and_time(self, tag):
        """
        Determine whether a provided HTML tag is a row containing a match and
        its time of the day.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (bool)
        """
        if tag.has_attr("class"):
            return (
                "border-black-borders" in tag["class"]
            ) and (
                "border-l" not in tag["class"]
            ) and (
                "flex-col" in tag["class"]
            )
        else:
            return False

    def get_time(self, tag):
        """
        Extract the time from an HTML tag for a soccer match row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (str) Extracted time.
        """

        return tag.find(
            class_="flex min-w-[100%] next-m:!min-w-[30px]"
        ).text.strip()

    def get_participants(self, tag):
        """
        Extract the match's participants from an HTML tag for a soccer match
        row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of str) Extracted match participants.
        """
        participants = []
        participants.append(tag.find(
            class_=(
                "flex items-start justify-start min-w-0 gap-1 cursor-pointer "
                "justify-content next-m:!items-center next-m:!justify-center "
                "min-sm:min-w-[180px] next-m:!gap-2"
            )
        ).find('div').text.strip())
        participants.append(tag.find(
            class_=(
                "min-w-[0] gap-1 flex justify-content items-center "
                "cursor-pointer next-m:!gap-2 min-sm:min-w-[180px]"
            )
        ).find('div').text.strip())
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

        season_element = tag.find(
            class_=(
                "flex items-center justify-start min-h-[40px] "
                "bg-gray-med_light "
                "w-full gap-1 bg-gray-med_light text-black-main"
            )
        ).find(
            class_=(
                "text-xs font-normal truncate"
            )
        ).text.strip()

        if 'Bundesliga' in season_element:
            season_elements = season_element.split(' ')
            if len(season_elements) == 1:
                return "xx/xx"
            else:
                return season_elements[-1]
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
        score_block = tag.find(class_="flex gap-1 font-bold font-bold")
        if score_block is None:
            return [-1, -1]
        # score_str = tag.find(class_="table-score").string
        # if self.is_invalid_game_from_score_string(score_str):
        #     return [-1,-1]
        else:
            score_rows = score_block.find_all("div")
            score_home = score_rows[0].text.strip()
            score_away = score_rows[-1].text.strip()
        return [score_home, score_away]

    def get_odds(self, tag):
        """
        Extract the betting odds for a match from an HTML tag for a soccer
        match row.

        Args:
            tag (obj): HTML tag object from BeautifulSoup.

        Returns:
            (list of str) Extracted match odds.
        """

        odds_cells = tag.find_all(class_=(
            "cursor-pointer next-m:min-w-[80%] next-m:min-h-[26px] "
            "next-m:max-h-[26px] flex justify-center items-center "
            "font-bold hover:border hover:border-orange-main min-w-[50px] "
            "min-h-[50px]"
        ))
        odds = []
        for cell in odds_cells:
            odds.append(cell.find('p').string.strip())
        return odds

    # def is_invalid_game_from_score_string(self, score_str):
    #     """
    #     Assess, from the score string extracted from a soccer match row,
    #     whether a game actually paid out one of the bet outcomes.

    #     Args:
    #         score_str (str): Score string to assess.

    #     Returns:
    #         (bool)
    #     """

    #     if score_str == "postp.":
    #         return True
    #     elif score_str == "canc.":
    #         return True
    #     return False
