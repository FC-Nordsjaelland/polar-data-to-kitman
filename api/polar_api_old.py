#%%
import requests
import webbrowser
import base64
import json
from tqdm import tqdm
import sys, os
import isodate
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
from api.polar_api import POLAR_API

# POLAR API
# https://www.polar.com/teampro-api/?python#teampro-api

# -------- Setup variables -------- #
# -------- UTILITY FUNCTIONS -------- #
def flatten_list(l):
    return [item for sublist in l for item in sublist]

# from https://stackoverflow.com/questions/1060279/iterating-through-a-range-of-dates-in-python
def daterange(start_date, end_date):
    add_date = timedelta(days=1)
    for n in range(int(((end_date + add_date) - start_date).days)):
        yield start_date + timedelta(n)
        
def get_key(val, my_dict):
    for key, value in my_dict.items():
         if val == value:
             return key
    return "key doesn't exist"

# ---------- GET TEAM DATA ----------- #
# https://www.polar.com/teampro-api/?python#team

def get_team_ids(tokens, team):
    """Get Polar team id for a specified team

        Args:
            tokens (json object): tokens json object
            team (str): team name from Polar

        Returns:
            str: team id
    """
    # retrieve access token
    access_token = tokens['access_token']
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+access_token
        }
    # get team data
    r = requests.get('https://teampro.api.polar.com/v1/teams', params={}, headers=headers)
    team_data = r.json()
    team_data = team_data['data']
    for data in team_data:
        if data['name'] == team:
            print(data['name'])
            team_id = data['id']
            return team_id
        #else:
        #    return 'Not a valid team'

def get_players(tokens, team_id):
    """Get players and player ids from the current players

        Args:
            tokens (json objoct): tokens json object
            team_id (str): team name from Polar

        Returns:
            DataFrame: dataframe of players and players ids from current players
    """
    access_token = tokens['access_token']
    headers = {
    'Accept': 'application/json',
    'Authorization': 'Bearer '+access_token
    }
    # get team details
    r = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}', params={}, headers = headers)
    
    # extract only players
    players_staff = r.json()
    players = players_staff['data']['players']
    # convert to dataframe
    df_players = pd.json_normalize(players)
    # remove staff
    df_players = df_players[df_players['player_number'] < 100]
    
    return df_players

def get_sessions(tokens, team_id, date=None):
    """Get information from session(s). Can get sessions from a single date, daterange or all available dates

        Args:
            tokens (json object): tokens json object
            team_id (str): team name from Polar
            date (str or list, optional): date or date range to get sessions from
                                          (e.g. date -> "12-08-2021" or "["01-08-2021", "12-08-2021"]").
                                          Defaults to None.

        Returns:
            DataFrame: information from the sessions (id, team_id, created, modified etc.)
    """
    
    access_token = tokens['access_token']
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+access_token
        }
    
    # return sessions dependent on date specifics
    # Get session data within a date range
    if type(date) == list:
        day1, month1, year1 = date[0].split('-')
        day2, month2, year2 = date[1].split('-')
        r_new = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}/training_sessions',
                             params={'since': f'{year1}-{month1}-{day1}T00:00:00',
                                     'until': f'{year2}-{month2}-{day2}T23:59:59'},
                             headers = headers)
        # get total session in order to load all sessions
        session_data = r_new.json()
        total_pages = session_data['page']['total_pages']
        # if more than one page of data, then iterate through
        if total_pages > 0:
            all_sessions = []
            for i in range(total_pages):
                r_new = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}/training_sessions?page={i}',
                            params={'since': f'{year1}-{month1}-{day1}T00:00:00',
                                    'until': f'{year2}-{month2}-{day2}T23:59:59'},
                            headers = headers)

                page_data = r_new.json()
                session_data = page_data['data']
                all_sessions.append(session_data)        
            # concatenate list of sessions
            all_sessions = flatten_list(all_sessions)
            # convert to dataframe
            df_sessions = pd.json_normalize(all_sessions)

            return df_sessions
        
        page_data = r_new.json()
        session_data = page_data['data']
        df_sessions = pd.json_normalize(session_data)
        
        return df_sessions
    
    # Get session data from a single date
    if type(date) == str:
        day1, month1, year1 = date.split('-')
        r_new = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}/training_sessions',
                             params={'since': f'{year1}-{month1}-{day1}T00:00:00',
                                     'until': f'{year1}-{month1}-{day1}T23:59:59'},
                             headers = headers)
        page_data = r_new.json()
        session_data = page_data['data']
        df_sessions = pd.json_normalize(session_data)
        
        return df_sessions

    # Get session data from all sessions
    if date == None:
        r = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}/training_sessions',
                         params={}, headers = headers)
    
        # get total session in order to load all sessions
        session_data = r.json()
        total_pages = session_data['page']['total_pages']
        
        all_sessions = []
        # iterate through all pages
        for i in range(total_pages):
            r_new = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}/training_sessions?page={i}',
                                 params={}, headers = headers)
            page_data = r_new.json()
            session_data = page_data['data']
            all_sessions.append(session_data)        
        # concatenate list of sessions
        all_sessions = flatten_list(all_sessions)
        # convert to dataframe
        df_sessions = pd.json_normalize(all_sessions)
        
        return df_sessions

def get_player_session_ids(tokens, session_id):
    """Get session ids from all players from a session

        Args:
            tokens (json object): tokens json object
            session_id (str): id from session

        Returns:
            dict: dictionary of mapping between player id and session id
    """
    
    access_token = tokens['access_token']
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+access_token
        }
    r = requests.get(f'https://teampro.api.polar.com/v1/teams/training_sessions/{session_id}',
                     params={}, headers = headers)
    
    # get session data
    session_data = r.json()
    # get player session id
    participants = session_data['data']['participants']
    df_participants = pd.json_normalize(participants)

    # create dictionary of session ids and player ids
    player_ids = list(df_participants['player_id'])
    player_session_ids = list(df_participants['player_session_id'])
    
    zip_iterator = zip(player_ids, player_session_ids)
    session_ids_dict = dict(zip_iterator)
    
    return session_ids_dict

def get_player_session_details(tokens, player_session_id, training_session_id):
    """Get session details for a specific player from a specific session (see below for example response)
        https://www.polar.com/teampro-api/?python#get-player-training-session-details
        Args:
            tokens ([type]): [description]
            player_session_id ([type]): [description]
            training_session_id ([type]): [description]

        Returns:
            DataFrame: DataFrame of training session details
    """
    access_token = tokens['access_token']
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+access_token
        }
    r = requests.get(f'https://teampro.api.polar.com/v1/training_sessions/{player_session_id}',
                     params={'samples': 'all'}, headers = headers)
    player_session_details = r.json()
    
    # get dataframe header
    df_header = list(player_session_details['data']['samples']['fields'])
    df = pd.DataFrame(player_session_details['data']['samples']['values'],
                      columns=df_header)
    # Clean time column
    df['time'] = df['time'].apply(lambda x: isodate.parse_duration(x))

    # Get session start time (to add "time_expanded")
    start_time = isodate.parse_datetime(player_session_details['data']['start_time'])
    df.insert(1, column='time_expanded', value=start_time)
    #df['time_expanded'] = pd.to_datetime(df['time_expanded'], format='%H:%M:%S')
    
    # Add time and time_expanded
    df['time_expanded'] = df['time_expanded'] + df['time']
    df['time_expanded'] = df['time_expanded']
    
    # Add session details (type and phases)
    df_session_details = get_session_phases(tokens, training_session_id)

    # Add row with phase type and then concat
    df_start = pd.merge(df, df_session_details,
                         left_on='time_expanded', right_on='start_time',
                         how='left')
    df_end = pd.merge(df, df_session_details,
                         left_on='time_expanded', right_on='end_time',
                         how='left')
    df_merged = pd.concat([df_start, df_end]).drop_duplicates().sort_values('time_expanded').reset_index(drop=True)
    
    # Fill values between phases https://stackoverflow.com/questions/68883770/how-to-fill-nan-values-between-two-values
    df_merged = df_merged.ffill().where(df_merged.ffill() == df_merged.bfill())
    #df_merged['name'] = df_merged['name'].fillna('break')
    
    # Forward fill values that are every 1 sec. and not every 0.1 sec.
    df_merged[['hr', 'cadence', 'lat', 'lon']] = df_merged[['hr', 'cadence', 'lat', 'lon']].ffill()
    df_merged['session_type'] = df_merged['session_type'].ffill().bfill()
    
    # Clean time columns
    df_merged[['start_time', 'end_time']] = df_merged[['start_time', 'end_time']].apply(lambda x: x.dt.time)
    df_merged['time'] = df_merged['time'].astype(str).str.split('0 days ').str[-1]
    
    # remove altitude column
    df_merged.drop(['altitude', 'marker_type', 'note', 'start_time', 'end_time'],
                   axis=1, inplace=True)
    
    # Fill NaN values
    df_merged.fillna('NaN', inplace=True)
    
    return df_merged

def get_all_player_session_details(tokens, player_session_ids, training_session_id,
                                   save_as_csv=False, path=None):
    """Get session details from multiple players for one session

        Args:
            tokens (json object): tokens json object
            player_session_ids (dict): dictionary of player ids and player session ids
            training_session_id (str): id from the session
            save_as_csv (bool, optional): True/False option to save DataFrame as csv file. Defaults to False.
            path (str, optional): If "save_as_csv" then provide path and file name to save. Defaults to None.

        Returns:
            DataFrame: DataFrame with session details from players provided in dictionary
    """
    # go through all session ids and get_player_session_details
    all_session_details = []
    for player_id, player_session_id in tqdm(player_session_ids.items(), desc='Getting player data'):
        df_session_player = get_player_session_details(tokens, player_session_id, training_session_id)
        df_session_player.insert(loc=0, column='player_id', value=player_id)
        
        all_session_details.append(df_session_player)
        # save as csv
        if save_as_csv:
            df_session_player.to_csv(f'{path}/{player_id}_raw_gps.csv', index=False)
    # If not save session details in indivdiual files, we create single dataframe and return it
    if not save_as_csv:
        df_session_details = pd.concat(all_session_details)
        return df_session_details
    else:
        return None

# ------ GET TRAINING SESSION PHASES TIMES ------ #
def get_session_phases(tokens, training_session_id):
    """ Get details of the training session and details of each phase (e.g. Warm Up, Rondos)
        https://www.polar.com/teampro-api/?python#get-team-training-session-details
        Args:
            tokens (json object): tokens json object
            training_session_id (str): id from session

        Returns:
            DataFrame: Details from the session
    """
    access_token = tokens['access_token']
    headers = {
    'Accept': 'application/json',
    'Authorization': 'Bearer '+access_token
    }
    r = requests.get(f'https://teampro.api.polar.com/v1/teams/training_sessions/{training_session_id}',
                     params={}, headers = headers)

    # Get session type (training or match)
    session_details = r.json()
    session_type = session_details['data']['type']
    session_type_list = []
    session_type_list.append(session_type)

    # Extract session markers
    session_phase_markers = session_details['data']['markers']
    df_session_phases = pd.json_normalize(session_phase_markers)
    # Insert session type
    if len(df_session_phases) > 0:
        # Add start and end time
        start_end_dict = {}
        start_end_dict['end_time'] = isodate.parse_datetime(session_details['data']['end_time'])
        start_end_dict['start_time'] = isodate.parse_datetime(session_details['data']['start_time'])
        df_session_phases = df_session_phases.append(start_end_dict, ignore_index=True)
        # Add session type
        session_type_list = session_type_list*len(df_session_phases)
        df_session_phases['session_type'] = session_type_list

    else:
        # Add start and end time
        start_end_dict = {}
        start_end_dict['end_time'] = isodate.parse_datetime(session_details['data']['end_time'])
        start_end_dict['start_time'] = isodate.parse_datetime(session_details['data']['start_time'])
        df_session_phases = df_session_phases.append(start_end_dict, ignore_index=True)
        # Add session type
        df_session_phases['session_type'] = session_type_list*len(df_session_phases)
        # Add phase name column
        df_session_phases['name'] = np.NaN
        df_session_phases['marker_type'] = np.NaN
        df_session_phases['note'] = np.NaN
    #df_final = pd.concat([df, df_session_phases], axis=1)
    # Convert start and end time to only time
    df_session_phases['start_time'] = pd.to_datetime(df_session_phases['start_time'])
    df_session_phases['end_time'] = pd.to_datetime(df_session_phases['end_time'])
    #df_session_phases['start_time'] = df_session_phases['start_time'].apply(lambda x: isodate.parse_datetime(x))
    #df_session_phases['end_time'] = df_session_phases['end_time'].apply(lambda x: isodate.parse_datetime(x))
    
    return df_session_phases

# ------ TRAINING SESSION TRIMMED ------- #

def clean_zone_df(df, zone):
    """Clean columns that are divided into zones (e.g. heart rate, acceleration, running distance)

        Args:
            df (DataFrame): DataFrame with Polar data to be cleaned
            zone (str): which zone to be cleaned, "hr", "speed" or "acceleration"

        Returns:
            DataFrame: clean dataframe
    """
    cols_to_drop = ['lower_limit_1', 'lower_limit_2', 'lower_limit_3', 'lower_limit_4', 'lower_limit_5',
                    'higher_limit_1', 'higher_limit_2', 'higher_limit_3', 'higher_limit_4', 'higher_limit_5']
    hr_cols_to_keep = ['in_zone_1', 'in_zone_2', 'in_zone_3', 'in_zone_4', 'in_zone_5']
    speed_cols_to_keep = ['in_zone_meters_1', 'in_zone_meters_2', 'in_zone_meters_3', 'in_zone_meters_4', 'in_zone_meters_5']
    if zone == 'hr':
        cols_to_keep = hr_cols_to_keep
    elif zone == 'speed':
        cols_to_keep = speed_cols_to_keep
    elif zone == 'acceleration':
        # Convert row into columns
        df = df.pivot(index='player_session_id', columns='limit').reset_index()
        # Collapse columns
        df.columns = df.columns.to_flat_index()
        df.rename(columns = lambda x: '_'.join(map(str, x)), inplace=True)
        return df
    else:
        print('Not a valid zone')
        return None
    # Convert row into columns
    df = df.pivot(index='player_session_id', columns='index').reset_index()
    # Collapse columns
    df.columns = df.columns.to_flat_index()
    df.rename(columns = lambda x: '_'.join(map(str, x)), inplace=True)
    df.drop(cols_to_drop, axis=1, inplace=True) # drop higher and lower limits
    # Parse times and rename columns
    if zone == 'hr':
        for col in cols_to_keep:
            df[col] = df[col].apply(isodate.parse_duration)
            # Remove days from time zones
            df[col] = df[col].astype(str).str.split('0 days ').str[-1]
            df[col].replace('0 days', '00:00:00', inplace=True) #entries with 0 minutes show 0 days, thus replace with 00:00:00
    return df

    
def get_player_session_details_trimmed(tokens, player_session_id):
    """Get trimmed values for a player

        Args:
            tokens (json object): tokens json object
            player_session_id (str): session id from a player

        Returns:
            DataFrame: trimmed training session values (formatted like the "Export" function in teampro.polar.com)
    """
    access_token = tokens['access_token']
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+access_token
        }
    r = requests.get(f'https://teampro.api.polar.com/v1/training_sessions/{player_session_id}/session_summary',
                     params={}, headers = headers)
    session_details = r.json()
    #time.sleep(2)
    
    # Split columns with zones into multiple dataframe and merge them in get_all function
    # ------ Heart Rate Zones ------- #
    #heart_rate_zones	speed_zones_kmh	acceleration_zones_ms2
    df_hr_zones = pd.json_normalize(session_details['data'], record_path='heart_rate_zones',
                                    meta='player_session_id')
    df_hr_zones = clean_zone_df(df_hr_zones, zone='hr')
    hr_cols = ['player_session_id', 'Time in HR zone 1 (50 - 59 %)', 'Time in HR zone 2 (60 - 69 %)',
               'Time in HR zone 3 (70 - 79 %)', 'Time in HR zone 4 (80 - 89 %)', 'Time in HR zone 5 (90 - 100 %)']
    df_hr_zones.columns = hr_cols
    # ------ Speed Zones ------- #
    df_speed_zones = pd.json_normalize(session_details['data'], record_path='speed_zones_kmh',
                                       meta='player_session_id')
    df_speed_zones = clean_zone_df(df_speed_zones, zone='speed')
    speed_cols = ['player_session_id', 'Distance in Speed zone 1 [m] (12.00 - 20.99 km/h)', 'Distance in Speed zone 2 [m] (21.00 - 23.99 km/h)',
                  'Distance in Speed zone 3 [m] (24.00 - 25.19 km/h)', 'Distance in Speed zone 4 [m] (25.20 - 29.99 km/h)', 'Distance in Speed zone 5 [m] (30.00- km/h)']
    df_speed_zones.columns = speed_cols
    # ------ Acceleration Zones ------- #
    df_acceleration_zones = pd.json_normalize(session_details['data'], record_path='acceleration_zones_ms2',
                                              meta='player_session_id')
    df_acceleration_zones = clean_zone_df(df_acceleration_zones, zone='acceleration')
    acceleration_cols = ['player_session_id', 'Number of accelerations (-50.00 - -9.00 m/s²)', 'Number of accelerations (-8.99 - -6.00 m/s²)', 'Number of accelerations (-5.99 - -3.00 m/s²)',
                         'Number of accelerations (-2.99 - -0.50 m/s²)', 'Number of accelerations (0.50 - 2.99 m/s²)', 'Number of accelerations (3.00 - 5.99 m/s²)',
                         'Number of accelerations (6.00 - 8.99 m/s²)', 'Number of accelerations (9.00 - 50.00 m/s²)']
    df_acceleration_zones.columns = acceleration_cols
    
    # ---- Merge zones dataframes with original dataframe ----- #
    df_all_details = pd.json_normalize(session_details['data'])
    
    # Modify time columns (duration, start_time, end_time)
    df_all_details['trimmed_start_time'] = isodate.parse_datetime(df_all_details['trimmed_start_time'][0])
    df_all_details['trimmed_start_time'] = df_all_details['trimmed_start_time'].dt.time
    df_all_details['duration_ms'] = pd.to_datetime(df_all_details['duration_ms'], unit='ms').dt.time
    # Calculate distance per min.
    df_all_details['distance_per_min'] = df_all_details['distance_meters'] / df_all_details['duration_ms'].astype(str).str.split(':').apply(lambda x: int(x[0]) * 60 + int(x[1]))
    # Calculate end time
    df_all_details['end_time'] = (pd.to_timedelta(df_all_details['trimmed_start_time'].astype(str))
                                  + pd.to_timedelta(df_all_details['duration_ms'].astype(str)))
    df_all_details['end_time'] = df_all_details['end_time'].astype(str).str.split('0 days ').str[-1]
    
    # Remove and rename columns
    df_all_details.drop(['heart_rate_zones', 'speed_zones_kmh', 'acceleration_zones_ms2'],
                        axis=1, inplace=True)
    df_all = [df_all_details.set_index('player_session_id'), df_hr_zones.set_index('player_session_id'),
              df_speed_zones.set_index('player_session_id'), df_acceleration_zones.set_index('player_session_id')]
    
    df_final = pd.concat(df_all, axis=1).reset_index()
    # Drop and rename columns
    cols_to_drop = ['created', 'modified', 'player_session_id', 'cadence_avg', 'cadence_max']
    cols_to_rename = {'duration_ms': 'Duration',
                    'trimmed_start_time': 'Start time',
                    'end_time': 'End time',
                    'heart_rate_min': 'HR min [bpm]',
                    'heart_rate_avg': 'HR avg [bpm]',
                    'heart_rate_max': 'HR max [bpm]',
                    'heart_rate_min_percent': 'HR min [%]',
                    'heart_rate_avg_percent': 'HR avg [%]',
                    'heart_rate_max_percent': 'HR max [%]',
                    'distance_meters': 'Total distance [m]',
                    'distance_per_min': 'Distance / min [m/min]',
                    'speed_max_kmh': 'Maximum speed [km/h]',
                    'speed_avg_kmh': 'Average speed [km/h]',
                    'sprint_counter': 'Sprints',
                    'kilo_calories': 'Calories [kcal]',
                    'training_load': 'Training load score'
                    }   
    df_final.drop(cols_to_drop, axis=1, inplace=True)
    df_final.rename(columns=cols_to_rename, inplace=True)
    
    # ------ Clean top speeds ------- #
    #df_top_speed = pd.read_csv('utils/top_speeds.csv')
    top_speed = 37
    df_final['Maximum speed [km/h]'] = df_final['Maximum speed [km/h]'].apply(lambda x: x if x <= top_speed else top_speed)
    

    # Calculate times in minutes
    #cols_to_convert = ['Duration', 'Time in HR zone 1 (50 - 59 %)', 'Time in HR zone 2 (60 - 79 %)',
    #                   'Time in HR zone 3 (80 - 84 %)', 'Time in HR zone 4 (85 - 94 %)', 'Time in HR zone 5 (95 - 100 %)']
    
    #df_final = pd.concat([df_final, df_converted])
    
    return df_final #df_final

def get_all_player_session_details_trimmed(tokens, player_session_ids, team_id,
                                           save_as_csv=False, path=None):
    """Get trimmed values from multiple players

        Args:
            tokens (json object): tokens json object
            player_session_ids (dictionary): player ids and player session ids
            team_id (str): id for a team
            save_as_csv (bool, optional): True/False option to save as csv file. Defaults to False.
            path (str, optional): If save as csv, then provide path and filename. Defaults to None.

        Returns:
            DataFrame: All trimmed values from all players for a session
    """
    # go through all session ids and get_player_session_details
    df_all = []
    for player_id, player_session_id in player_session_ids.items():
        df_session_player = get_player_session_details_trimmed(tokens, player_session_id)
        df_session_player.insert(loc=0, column='player_id', value=player_id)
        
        df_all.append(df_session_player)
    # Concatenate all players into 1 dataframe
    df_all_players = pd.concat(df_all).reset_index(drop=True)
    
    # Make heart_rate_zones, speed_zones and distance into different columns/zones
    #df_all_players = df_all_players.pivot(index='player_id', columns='index').reset_index()
    #df_all_players.columns = df_all_players.columns.to_flat_index()
    
    # save as csv
    if save_as_csv:
        df_all_players.to_csv(f'{path}/{player_id}_trimmed_data.csv', index=False)

    return df_all_players