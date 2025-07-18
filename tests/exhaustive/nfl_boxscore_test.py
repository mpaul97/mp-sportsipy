from pyquery import PyQuery as pq
from nfl_constants import (BOXSCORE_ELEMENT_INDEX,
                        BOXSCORE_ELEMENT_SUB_INDEX,
                        BOXSCORE_SCHEME,
                        BOXSCORE_URL,
                        BOXSCORES_URL)
import regex as re
import time
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.DEBUG)

WIN = 'Win'
LOSS = 'Loss'
DRAW = 'Draw'
TIE = 'Tie'
HOME = 'Home'
AWAY = 'Away'
NEUTRAL = 'Neutral'
REGULAR_SEASON = 'Reg'
POST_SEASON = 'Post'
CONFERENCE_TOURNAMENT = 'Conf-Tourney'
NON_DI = 'Non-DI School'

def get_page_source(url: str):
    with sync_playwright() as p:
        # Launch browser in headfull mode for debugging (can switch to headless later)
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
        )
        page = browser.new_page()
        try:
            # Set longer default timeout and navigate to URL
            page.set_default_timeout(60000)
            page.goto(url)
            # Wait for main content to load - adjust selector as needed
            page.wait_for_selector('.box', state='attached', timeout=45000)
            # Optional: Wait for additional time if needed
            time.sleep(2)
            # Get page content and parse with BeautifulSoup
            html = page.content()
            logging.info(f"Page content successfully retrieved! URL: {url}")
            return html
        except Exception as e:
            logging.error(f"Error occurred: {str(e)}")
            return None
        finally:
            browser.close()

def _parse_abbreviation(uri_link):
    """
    Returns a team's abbreviation.

    A school or team's abbreviation is generally embedded in a URI link which
    contains other relative link information. For example, the URI for the
    New England Patriots for the 2017 season is "/teams/nwe/2017.htm". This
    function strips all of the contents before and after "nwe" and converts it
    to uppercase and returns "NWE".

    Parameters
    ----------
    uri_link : string
        A URI link which contains a team's abbreviation within other link
        contents.

    Returns
    -------
    string
        The shortened uppercase abbreviation for a given team.
    """
    abbr = re.sub(r'/[0-9]+\..*htm.*', '', uri_link('a').attr('href'))
    abbr = re.sub(r'/.*/schools/', '', abbr)
    abbr = re.sub(r'/teams/', '', abbr)
    return abbr.upper()

def _parse_field(parsing_scheme, html_data, field, index=0, strip=False,
                 secondary_index=None):
    """
    Parse an HTML table to find the requested field's value.

    All of the values are passed in an HTML table row instead of as individual
    items. The values need to be parsed by matching the requested attribute
    with a parsing scheme that sports-reference uses to differentiate stats.
    This function returns a single value for the given attribute.

    Parameters
    ----------
    parsing_scheme : dict
        A dictionary of the parsing scheme to be used to find the desired
        field. The key corresponds to the attribute name to parse, and the
        value is a PyQuery-readable parsing scheme as a string (such as
        'td[data-stat="wins"]').
    html_data : string
        A string containing all of the rows of stats for a given team. If
        multiple tables are being referenced, this will be comprised of
        multiple rows in a single string.
    field : string
        The name of the attribute to match. Field must be a key in
        parsing_scheme.
    index : int (optional)
        An optional index if multiple fields have the same attribute name. For
        example, 'HR' may stand for the number of home runs a baseball team has
        hit, or the number of home runs a pitcher has given up. The index
        aligns with the order in which the attributes are recevied in the
        html_data parameter.
    strip : boolean (optional)
        An optional boolean value which will remove any empty or invalid
        elements which might show up during list comprehensions. Specify True
        if the invalid elements should be removed from lists, which can help
        with reverse indexing.
    secondary_index : int (optional)
        An optional index if multiple fields have the same attribute, but the
        original index specified above doesn't work. This happens if a page
        doesn't have all of the intended information, and the requested index
        isn't valid, causing the value to be None. Instead, a secondary index
        could be checked prior to returning None.

    Returns
    -------
    string
        The value at the specified index for the requested field. If no value
        could be found, returns None.
    """
    if field == 'abbreviation':
        return _parse_abbreviation(html_data)
    scheme = parsing_scheme[field]
    if strip:
        items = [i.text() for i in html_data(scheme).items() if i.text()]
    else:
        items = [i.text() for i in html_data(scheme).items()]
    # Stats can be added and removed on a yearly basis. If not stats are found,
    # return None and have the be the value.
    if len(items) == 0:
        return None
    # Default to returning the first element. Optionally return another element
    # if multiple fields have the same tag attribute.
    try:
        return items[index]
    except IndexError:
        if secondary_index:
            try:
                return items[secondary_index]
            except IndexError:
                return None
        return None

class Boxscore:
    """
    Detailed information about the final statistics for a game.

    Stores all relevant information for a game such as the date, time,
    location, result, and more advanced metrics such as the number of yards
    from sacks, a team's passing completion, rushing touchdowns and much more.

    Parameters
    ----------
    uri : string
        The relative link to the boxscore HTML page, such as
        '201802040nwe'.
    """
    def __init__(self, uri):
        self._uri = uri
        self._date = None
        self._time = None
        self._stadium = None
        self._attendance = None
        self._duration = None
        self._away_name = None
        self._home_name = None
        self._winner = None
        self._winning_name = None
        self._winning_abbr = None
        self._losing_name = None
        self._losing_abbr = None
        self._summary = None
        self._won_toss = None
        self._roof = None
        self._surface = None
        self._weather = None
        self._vegas_line = None
        self._over_under = None
        self._away_points = None
        self._away_first_downs = None
        self._away_rush_attempts = None
        self._away_rush_yards = None
        self._away_rush_touchdowns = None
        self._away_pass_completions = None
        self._away_pass_attempts = None
        self._away_pass_yards = None
        self._away_pass_touchdowns = None
        self._away_interceptions = None
        self._away_times_sacked = None
        self._away_yards_lost_from_sacks = None
        self._away_net_pass_yards = None
        self._away_total_yards = None
        self._away_fumbles = None
        self._away_fumbles_lost = None
        self._away_turnovers = None
        self._away_penalties = None
        self._away_yards_from_penalties = None
        self._away_third_down_conversions = None
        self._away_third_down_attempts = None
        self._away_fourth_down_conversions = None
        self._away_fourth_down_attempts = None
        self._away_time_of_possession = None
        self._home_points = None
        self._home_first_downs = None
        self._home_rush_attempts = None
        self._home_rush_yards = None
        self._home_rush_touchdowns = None
        self._home_pass_completions = None
        self._home_pass_attempts = None
        self._home_pass_yards = None
        self._home_pass_touchdowns = None
        self._home_interceptions = None
        self._home_times_sacked = None
        self._home_yards_lost_from_sacks = None
        self._home_net_pass_yards = None
        self._home_total_yards = None
        self._home_fumbles = None
        self._home_fumbles_lost = None
        self._home_turnovers = None
        self._home_penalties = None
        self._home_yards_from_penalties = None
        self._home_third_down_conversions = None
        self._home_third_down_attempts = None
        self._home_fourth_down_conversions = None
        self._home_fourth_down_attempts = None
        self._home_time_of_possession = None

        self._parse_game_data(uri)

    def __str__(self):
        """
        Return the string representation of the class.
        """
        return (f'Boxscore for {self._away_name.text()} at '
                f'{self._home_name.text()} ({self._date})')

    def __repr__(self):
        """
        Return the string representation of the class.
        """
        return self.__str__()

    def _parse_game_details(self, boxscore):
        """
        Retrieve the game's extra information from kickoff.

        The games' extra information, such as weather, vegas lines, coin toss,
        and roof, follow a complex parsing scheme that changes based on the
        layout of the page. The information should be able to be parsed and set
        regardless of the order and how much information is included. To do
        this, the meta information should be iterated through line-by-line and
        fields should be determined by the values that are found in each line.

        Parameters
        ----------
        boxscore : PyQuery object
            A PyQuery object containing all of the HTML data from the boxscore.
        """
        scheme = BOXSCORE_SCHEME["game_details"]
        won_toss = None
        roof = None
        surface = None
        weather = None
        vegas_line = None
        over_under = None

        for line in boxscore(scheme).items():
            if 'won toss' in str(line).lower():
                won_toss = line('td').text()
            elif 'roof' in str(line).lower():
                roof = line('td').text().title()
            elif 'surface' in str(line).lower():
                surface = line('td').text().title()
            elif 'weather' in str(line).lower():
                weather = line('td').text()
            elif 'vegas line' in str(line).lower():
                vegas_line = line('td').text()
            elif 'over/under' in str(line).lower():
                over_under = line('td').text()
        setattr(self, '_won_toss', won_toss)
        setattr(self, '_roof', roof)
        setattr(self, '_surface', surface)
        setattr(self, '_weather', weather)
        setattr(self, '_vegas_line', vegas_line)
        setattr(self, '_over_under', over_under)

    def _parse_game_date_and_location(self, boxscore):
        """
        Retrieve the game's date and location.

        The games' meta information, such as date, location, attendance, and
        duration, follow a complex parsing scheme that changes based on the
        layout of the page. The information should be able to be parsed and set
        regardless of the order and how much information is included. To do
        this, the meta information should be iterated through line-by-line and
        fields should be determined by the values that are found in each line.

        Parameters
        ----------
        boxscore : PyQuery object
            A PyQuery object containing all of the HTML data from the boxscore.
        """
        scheme = BOXSCORE_SCHEME["game_info"]
        items = [i.text() for i in boxscore(scheme).items()]
        game_info = items[0].split('\n')
        attendance = None
        date = None
        duration = None
        stadium = None
        time = None
        date = game_info[0]
        for line in game_info:
            if 'Attendance' in line:
                attendance = line.replace('Attendance: ', '').replace(',', '')
            if 'Time of Game' in line:
                duration = line.replace('Time of Game: ', '')
            if 'Stadium' in line:
                stadium = line.replace('Stadium: ', '')
            if 'Start Time' in line:
                time = line.replace('Start Time: ', '')
        setattr(self, '_attendance', attendance)
        setattr(self, '_date', date)
        setattr(self, '_duration', duration)
        setattr(self, '_stadium', stadium)
        setattr(self, '_time', time)

    def _parse_name(self, field, boxscore):
        """
        Retrieve the team's complete name tag.

        Both the team's full name (embedded in the tag's text) and the team's
        abbreviation are stored in the name tag which can be used to parse
        the winning and losing team's information.

        Parameters
        ----------
        field : string
            The name of the attribute to parse
        boxscore : PyQuery object
            A PyQuery object containing all of the HTML data from the boxscore.

        Returns
        -------
        PyQuery object
            The complete text for the requested tag.
        """
        scheme = BOXSCORE_SCHEME[field]
        return pq(str(boxscore(scheme)).strip())

    def _parse_summary(self, boxscore):
        """
        Find the game summary including score in each quarter.

        The game summary provides further information on the points scored
        during each quarter, including the final score and any overtimes if
        applicable. The final output will be in a dictionary with two keys,
        'away' and 'home'. The value of each key will be a list for each
        respective team's score by order of the quarter, with the first element
        belonging to the first quarter, similar to the following:

        {
            'away': [0, 7, 3, 14],
            'home': [7, 7, 3, 0]
        }

        Parameters
        ----------
        boxscore : PyQuery object
            A PyQuery object containing all of the HTML from the boxscore.

        Returns
        -------
        dict
            Returns a ``dictionary`` representing the score for each team in
            each quarter of the game.
        """
        team = ['away', 'home']
        summary = {'away': [], 'home': []}
        game_summary = boxscore(BOXSCORE_SCHEME['summary'])
        for ind, team_info in enumerate(game_summary('tbody tr').items()):
            # Only pull the first N-1 items as the last element is the final
            # score for each team which is already stored in an attribute, and
            # shouldn't be duplicated.
            for quarter in list(team_info('td[class="center"]').items())[:-1]:
                # The first element contains the logo and name of the teams,
                # but not any score information, and should be skipped.
                if quarter('div'):
                    continue
                try:
                    summary[team[ind]].append(int(quarter.text()))
                except ValueError:
                    summary[team[ind]].append(None)
        return summary

    def _find_boxscore_tables(self, boxscore):
        """
        Find all tables with boxscore information on the page.

        Iterate through all tables on the page and see if any of them are
        boxscore pages by checking if the ID matches the expected list. If so,
        add it to a list and return the final list at the end.

        Parameters
        ----------
        boxscore : PyQuery object
            A PyQuery object containing all of the HTML data from the boxscore.

        Returns
        -------
        list
            Returns a ``list`` of the PyQuery objects where each object
            represents a boxscore table.
        """
        tables = []
        valid_tables = ['player_offense', 'player_defense', 'returns',
                        'kicking']

        for table in boxscore('table').items():
            if table.attr['id'] in valid_tables:
                tables.append(table)
        return tables

    def _find_player_id(self, row):
        """
        Find the player's ID.

        Find the player's ID as embedded in the 'data-append-csv' attribute,
        such as 'BreeDr01' for Drew Brees.

        Parameters
        ----------
        row : PyQuery object
            A PyQuery object representing a single row in a boxscore table for
            a single player.

        Returns
        -------
        str
            Returns a ``string`` of the player's ID, such as 'BreeDr01'
            for Drew Brees.
        """
        return row('th').attr('data-append-csv')

    def _find_player_name(self, row):
        """
        Find the player's full name.

        Find the player's full name, such as 'Drew Brees'. The name is the
        text displayed for a link to the player's individual stats.

        Parameters
        ----------
        row : PyQuery object
            A PyQuery object representing a single row in a boxscore table for
            a single player.

        Returns
        -------
        str
            Returns a ``string`` of the player's full name, such as 'Drew
            Brees'.
        """
        return row('a:first').text()

    def _find_home_or_away(self, row):
        """
        Determine whether the player is on the home or away team.

        Next to every player is their school's name. This name can be matched
        with the previously parsed home team's name to determine if the player
        is a member of the home or away team.

        Parameters
        ----------
        row : PyQuery object
            A PyQuery object representing a single row in a boxscore table for
            a single player.

        Returns
        -------
        str
            Returns a ``string`` constant denoting whether the team plays for
            the home or away team.
        """
        name = row('td[data-stat="team"]').text().upper()
        if self._home_abbr and name == self._home_abbr.upper():
            return HOME
        if self._away_abbr and name == self._away_abbr.upper():
            return AWAY
        if name == self.home_abbreviation.upper():
            return HOME
        else:
            return AWAY

    def _extract_player_stats(self, table, player_dict):
        """
        Combine all player stats into a single object.

        Since each player generally has a couple of rows worth of stats
        (rushing, passing, defense, and more) on the boxscore page, both rows
        should be combined into a single string object to easily query all
        fields from a single object instead of determining which row to pull
        metrics from.

        Parameters
        ----------
        table : PyQuery object
            A PyQuery object of a single boxscore table, such as the home
            team's advanced stats or the away team's basic stats.
        player_dict : dictionary
            A dictionary where each key is a string of the player's ID and each
            value is a dictionary where the values contain the player's name,
            HTML data, and a string constant indicating which team the player
            is a member of.

        Returns
        -------
        dictionary
            Returns a ``dictionary`` where each key is a string of the player's
            ID and each value is a dictionary where the values contain the
            player's name, HTML data, and a string constant indicating which
            team the player is a member of.
        """
        for row in table('tbody tr').items():
            player_id = self._find_player_id(row)
            # Occurs when a header row is identified instead of a player.
            if not player_id:
                continue
            name = self._find_player_name(row)
            home_or_away = self._find_home_or_away(row)
            try:
                player_dict[player_id]['data'] += str(row).strip()
            except KeyError:
                player_dict[player_id] = {
                    'name': name,
                    'data': str(row).strip(),
                    'team': home_or_away
                }
        return player_dict

    def _instantiate_players(self, player_dict):
        """
        Create a list of player instances for both the home and away teams.

        For every player listed on the boxscores page, create an instance of
        the BoxscorePlayer class for that player and add them to a list of
        players for their respective team.

        Parameters
        ----------
        player_dict : dictionary
            A dictionary containing information for every player on the
            boxscores page. Each key is a string containing the player's ID
            and each value is a dictionary with the player's full name, a
            string representation of their HTML stats, and a string constant
            denoting which team they play for as the values.

        Returns
        -------
        tuple
            Returns a ``tuple`` in the format (away_players, home_players)
            where each element is a list of player instances for the away and
            home teams, respectively.
        """
        home_players = []
        away_players = []
        # for player_id, details in player_dict.items():
        #     player = BoxscorePlayer(player_id,
        #                             details['name'],
        #                             details['data'])
        #     if details['team'] == HOME:
        #         home_players.append(player)
        #     else:
        #         away_players.append(player)
        return away_players, home_players

    def _find_players(self, boxscore):
        """
        Find all players for each team.

        Iterate through every player for both teams as found in the boxscore
        tables and create a list of instances of the BoxscorePlayer class for
        each player. Return lists of player instances comprising the away and
        home team players, respectively.

        Parameters
        ----------
        boxscore : PyQuery object
            A PyQuery object containing all of the HTML data from the boxscore.

        Returns
        -------
        tuple
            Returns a ``tuple`` in the format (away_players, home_players)
            where each element is a list of player instances for the away and
            home teams, respectively.
        """
        player_dict = {}

        tables = self._find_boxscore_tables(boxscore)
        for table in tables:
            player_dict = self._extract_player_stats(table, player_dict)
        away_players, home_players = self._instantiate_players(player_dict)
        return away_players, home_players

    def _alt_abbreviations(self, boxscore):
        """
        Find the alternative abbreviations for both teams.

        The listed team abbreviations are occasionally different from the
        abbreviations used on sports-reference.com to identify a team. In order
        properly match a player to a specific team, the abbreviations must be
        parsed directly from the page instead of the URI links.

        Parameters
        ----------
        boxscore : PyQuery object
            A PyQuery object containing all of the HTML data from the boxscore.

        Returns
        -------
        tuple
            Returns a ``tuple`` in the format (away_abbr, home_abbr)
            where each element is a string of the away and home team's
            abbreviations, respectively.
        """
        abbreviations = []
        game_info = boxscore(BOXSCORE_SCHEME['team_stats'])

        for column in game_info('th').items():
            if column.text():
                abbreviations.append(column.text())
        print(abbreviations)
        if not abbreviations:
            return None, None
        return abbreviations

    def _parse_game_data(self, uri):
        """
        Parses a value for every attribute.

        This function looks through every attribute and retrieves the value
        according to the parsing scheme and index of the attribute from the
        passed HTML data. Once the value is retrieved, the attribute's value is
        updated with the returned result.

        Note that this method is called directly once Boxscore is invoked and
        does not need to be called manually.

        Parameters
        ----------
        uri : string
            The relative link to the boxscore HTML page, such as
            '201802040nwe'.
        """
        url = BOXSCORE_URL % uri
        # boxscore = pq(open("nfl_boxscore_template.html", "r", encoding="utf-8").read())
        boxscore = pq(get_page_source(url))
        # If the boxscore is None, the game likely hasn't been played yet and
        # no information can be gathered. As there is nothing to grab, the
        # class instance should just be empty.
        if not boxscore:
            return

        for field in self.__dict__:
            # Remove the '_' from the name
            short_field = str(field)[1:]
            if short_field == 'winner' or \
               short_field == 'winning_name' or \
               short_field == 'winning_abbr' or \
               short_field == 'losing_name' or \
               short_field == 'losing_abbr' or \
               short_field == 'uri' or \
               short_field == 'date' or \
               short_field == 'time' or \
               short_field == 'stadium' or \
               short_field == 'attendance' or \
               short_field == 'duration' or \
               short_field == 'won_toss' or \
               short_field == 'roof' or \
               short_field == 'surface' or \
               short_field == 'weather' or \
               short_field == 'vegas_line' or \
               short_field == 'over_under':
                continue
            if short_field == 'away_name' or \
               short_field == 'home_name':
                value = self._parse_name(short_field, boxscore)
                setattr(self, field, value)
                continue
            if short_field == 'summary':
                value = self._parse_summary(boxscore)
                setattr(self, field, value)
                continue
            index = 0
            if short_field in BOXSCORE_ELEMENT_INDEX.keys():
                index = BOXSCORE_ELEMENT_INDEX[short_field]
            value = _parse_field(BOXSCORE_SCHEME,
                                       boxscore,
                                       short_field,
                                       index)
            setattr(self, field, value)
        self._parse_game_date_and_location(boxscore)
        self._parse_game_details(boxscore)
        self._away_abbr, self._home_abbr = self._alt_abbreviations(boxscore)
        self._away_players, self._home_players = self._find_players(boxscore)
        print(self.__str__())

if __name__ == "__main__":
    Boxscore("202502090phi")