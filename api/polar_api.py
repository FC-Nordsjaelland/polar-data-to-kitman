#%%
import requests
import webbrowser
import base64
import pandas as pd
import sys, os

from api.polar_IO import (flatten_list,
                              daterange,
                              get_key)
# POLAR API DOCUMENTATION
# https://www.polar.com/teampro-api/?python#teampro-api

# -------- AUTHORIZATION AND ACCESS TOKENS --------- #
class POLAR_API:
    def __init__(self, client_id, client_secret, team):
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.team = team
        self.authorize_url = 'https://auth.polar.com/oauth/authorize'
        self.access_token_url = 'https://auth.polar.com/oauth/token'
        self.authorize_params = {'client_id': self.client_id,
                                 'response_type': 'code',
                                 'scope': 'team_read'}
    
    def _extract_team_id(self, teams_info, team):
        teams_data = teams_info['data']
        for data in teams_data:
            if data['name'] == self.team:
                print(data['name'])
                team_id = data['id']
                
                return team_id
    
    def extract_players(self, players_and_staff):
        # extract only players
        players = players_and_staff['data']['players']
        # convert to dataframe
        df_players = pd.json_normalize(players)
        # remove staff
        df_players = df_players[df_players['player_number'] < 100]
        
        return df_players

    def retrieve_authorization_code(self):
        r = requests.get(self.authorize_url, params=self.authorize_params)

        webbrowser.open(r.history[0].url, new=2)
        authorization_code = input("Authorization Code: ")

        return authorization_code
    
    def retrieve_tokens(self):
        
        encoding = self.client_id+':'+self.client_secret
        message_bytes = encoding.encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_encoding = base64_bytes.decode('ascii')
        headers = {'Authorization': 'Basic '+base64_encoding}

        authorization_code = self.retrieve_authorization_code()

        # POST request to get access token
        access_token_data = {'grant_type': 'authorization_code',
                             'code': authorization_code}
        r_post = requests.post(self.access_token_url,
                               data=access_token_data,
                               headers=headers)
        tokens = r_post.json()
        
        return tokens
    
    def get_teams_info(self, tokens, get_team_id=False):
        access_token = tokens['access_token']
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer '+access_token
            }
        r = requests.get('https://teampro.api.polar.com/v1/teams',
                         params={},
                         headers=headers)
        teams_info = r.json()
        if get_team_id:
            return self._extract_team_id(teams_info, self.team)
        
        return teams_info
    
    def get_team_players(self, tokens, team_id):
        access_token = tokens['access_token']
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer '+access_token
            }
        r = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}',
                         params={},
                         headers = headers)
        players_and_staff = r.json()
        
        return players_and_staff

    def get_sessions(self, tokens, team_id, date):
        access_token = tokens['access_token']
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer '+access_token
            }
        day, month, year = date.split('-')
        r = requests.get(f'https://teampro.api.polar.com/v1/teams/{team_id}/training_sessions',
                        params={'since': f'{year}-{month}-{day}T00:00:00',
                                'until': f'{year}-{month}-{day}T23:59:59',
                                'per_page': '100'},
                        headers = headers)
        sessions_metadata = r.json()
        
        return sessions_metadata
        
    def get_players_session_data(self, tokens, session_id):
        access_token = tokens['access_token']
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer '+access_token
            }
        r = requests.get(f'https://teampro.api.polar.com/v1/teams/training_sessions/{session_id}',
                        params={}, headers = headers)
        session_data = r.json()

        return session_data
    
    def get_player_session_details(self, tokens, player_session_id):
        access_token = tokens['access_token']
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer '+access_token
            }
        r = requests.get(f'https://teampro.api.polar.com/v1/training_sessions/{player_session_id}',
                         params={'samples': 'all'}, headers = headers)
        player_session_details = r.json()
        
        return player_session_details

    def get_trimmed_player_session_details(self, tokens, player_session_id):
        access_token = tokens['access_token']
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer '+access_token
            }
        r = requests.get(f'https://teampro.api.polar.com/v1/training_sessions/{player_session_id}/session_summary',
                        params={}, headers = headers)
        session_details = r.json()
        
        return session_details

    def get_player_session_ids(self, tokens, session_id):
        """helper function"""
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
        
