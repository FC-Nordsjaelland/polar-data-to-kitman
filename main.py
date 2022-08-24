#%%
import streamlit as st
import pandas as pd
import base64
import webbrowser
import requests
import datetime
from PIL import Image
from api.polar_api_old import get_all_player_session_details_trimmed, get_player_session_ids, get_players
from api.polar_api import POLAR_API

#%%

client_id = st.secrets['client_id']
client_secret = st.secrets['client_secret']

st.set_page_config(page_title="Polar data extraction", layout ='centered')

st.title("Polar training/match data extraction")
st.text("")
st.header("**Instruction**")

authorize_url = 'https://auth.polar.com/oauth/authorize'
access_token_url = 'https://auth.polar.com/oauth/token'
authorize_params = {'client_id': client_id,
                                 'response_type': 'code',
                                 'scope': 'team_read'}

encoding = client_id+':'+ client_secret
message_bytes = encoding.encode('ascii')
base64_bytes = base64.b64encode(message_bytes)
base64_encoding = base64_bytes.decode('ascii')
headers = {'Authorization': 'Basic '+ base64_encoding}
r = requests.get(authorize_url, params=authorize_params)
# st.write(r.history[0].url)
# webbrowser.open(r.history[0].url, new=2)
link = r.history[0].url

st.markdown("1) Navigate to the [link](%s)" % link)
st.markdown("2) After a successful authentication, expand the link of the page and copy the code (fx. 'http://xyz/?code=u9xMkv')")
st.markdown("3) Paste the code into the first cell in the form below")
st.markdown("4) Choose your team, training/match date, session number (in case there's multiple sessions in a day, fx. 1 stands for the first session in a day")  
st.markdown("5) Input the session's name (fx. 'FCN U17 vs FCM U17' / default: 'Football Training')")



with st.form(key='my_form'):
    authorization_code = st.text_input('Input the Polar authentication token below')
    # account = st.selectbox("Choose Account", options=["Men's", "Women's"])
    chosen_team = st.selectbox("Choose a team", options=["Superliga", "Kvindeliga", "RTD senior", "U19", "U17", "U15","Girls U18", "U16W"])
    d = st.date_input(
        "Choose a training session's date",
        datetime.date(2022, 8, 17))
    no_of_session = st.selectbox("Session number", ['1','2','3','4'])
    session_name = st.text_input("Input session's name", "Football Training")
    st.form_submit_button()

access_token_data = {'grant_type': 'authorization_code',
                    'code': authorization_code}
r_post = requests.post(access_token_url,
data=access_token_data,
headers=headers)
tokens = r_post.json()

x = str(d).split("-")
year = x[0]
month = x[1]
day = x[2]

if chosen_team in ["Superliga", "RTD senior", "U19", "U17", 'U15']:
    account = "M"
elif chosen_team in ["Kvindeliga", 'Girls U18', "U16W"]:
    account = 'W'


set_date = day + "-" + month + "-" + year

api = POLAR_API(client_id, client_secret, team=chosen_team)

template = pd.read_excel("templates/CSV_template.xlsx", skiprows=1)
# girls_template = pd.read_excel("CSV_template.xlsx", skiprows=1)
girls_template = pd.read_csv("templates/CSV_girls_template.csv", delimiter=";")

# # tokens = api.retrieve_tokens()
team_id = api.get_teams_info(tokens, get_team_id=True)



# set_date = '08-08-2022'
sessions_meta = api.get_sessions(tokens, team_id=team_id, date=set_date)
session_id = sessions_meta['data'][-(int(no_of_session))]['id']
player_session_ids = get_player_session_ids(tokens, session_id)
# %%
def hms_to_m(s):
    t = 0
    for u in s.split(':'):
        t = 60 * t + int(float(u))
    return int(t/60)

def preprocess():


    data = get_all_player_session_details_trimmed(tokens, player_session_ids, session_id,
                                    save_as_csv=False, path=None)
    data['Start time'] = data['Start time'].astype(str)
    data['Start time'] = set_date + " " + data['Start time']
    data['End time'] = set_date + " " + data['End time']

    id_df = get_players(tokens, team_id)
    id_df['full_name'] = id_df['first_name'] + " " + id_df['last_name']
    id_name = dict(zip(list(id_df['player_id']), list(id_df['full_name'])))

    data['Player name'] = data['player_id']
    data.replace({"Player name": id_name}, inplace=True)
    id_df = id_df[['player_id', "player_number"]]

    data = pd.merge(data, id_df, how='inner', on='player_id')
    data.rename(columns={"player_number":"Player number", "cardio_load": "Cardio load"}, inplace=True)
    data['Recovery time [h]'] = 0

    data['Session name'] = session_name
    data['Type'] = "Training"
    data['Phase name'] = "Whole session"

    if account == "M":
        data.rename(columns={"Time in HR zone 1 (50 - 69 %)":"Time in HR zone 1 (50 - 59 %)", 
                            "Time in HR zone 2 (60 - 69 %)":"Time in HR zone 2 (60 - 79 %)", 
                            "Time in HR zone 3 (70 - 79 %)":"Time in HR zone 3 (80 - 84 %)",
                            "Time in HR zone 4 (80 - 89 %)":"Time in HR zone 4 (85 - 94 %)", 
                            "Time in HR zone 5 (90 - 100 %)":"Time in HR zone 5 (95 - 100 %)"}, inplace=True)

        
        final_columns = list(template.columns.values)
        columns_before_calc = final_columns[:-6]
        data = data[columns_before_calc]

        # additional_columns = ['Duration',
        # 'Time in HR zone 1 (50 - 59 %)',
        # 'Time in HR zone 2 (60 - 69 %)',
        # 'Time in HR zone 3 (70 - 79 %)',
        # 'Time in HR zone 4 (80 - 89 %)',
        # 'Time in HR zone 5 (90 - 100 %)']

        data = pd.concat([data, pd.Series(data['Duration'].astype(str).apply(hms_to_m), name='Duration')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 1 (50 - 59 %)'].apply(hms_to_m), name='Time in HR zone 1 (50 - 59 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 2 (60 - 79 %)'].apply(hms_to_m), name='Time in HR zone 2 (60 - 69 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 3 (80 - 84 %)'].apply(hms_to_m), name='Time in HR zone 3 (70 - 79 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 4 (85 - 94 %)'].apply(hms_to_m), name='Time in HR zone 4 (80 - 89 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 5 (95 - 100 %)'].apply(hms_to_m), name='Time in HR zone 5 (90 - 100 %)')], axis=1)
        data['Maximum speed [km/h]'] = data["Maximum speed [km/h]"].round(decimals = 1)
        data['Average speed [km/h]'] = data["Average speed [km/h]"].round(decimals = 1)

        columns_dec_0 = ['Total distance [m]', 'Distance / min [m/min]', 'Distance in Speed zone 1 [m] (12.00 - 20.99 km/h)', 'Distance in Speed zone 2 [m] (21.00 - 23.99 km/h)', 'Distance in Speed zone 3 [m] (24.00 - 25.19 km/h)', 'Distance in Speed zone 4 [m] (25.20 - 29.99 km/h)', 'Distance in Speed zone 5 [m] (30.00- km/h)']
        data[columns_dec_0] = data[columns_dec_0].round(decimals=0)
        data[columns_dec_0] = data[columns_dec_0].astype(int)
    
    elif account == "W":
        # data.rename(columns={"Time in HR zone 2 (60 - 69 %)":"Time in HR zone 2 (60 - 69 %)",
        #                     "Time in HR zone 3 (70 - 79 %)":"Time in HR zone 3 (70 - 79 %)",
        #                     "Time in HR zone 4 (80 - 89 %)":"Time in HR zone 4 (80 - 89 %)", 
        #                     "Time in HR zone 5 (90 - 100 %)":"Time in HR zone 5 (90 - 100 %)"}, inplace=True)

        data.rename(columns={"Distance in Speed zone 1 [m] (12.00 - 20.99 km/h)":"Distance in Speed zone 1 [m] (10.00 - 17.99 km/h)",
                            "Distance in Speed zone 2 [m] (21.00 - 23.99 km/h)":"Distance in Speed zone 2 [m] (18.00 - 20.99 km/h)",
                            "Distance in Speed zone 3 [m] (24.00 - 25.19 km/h)":"Distance in Speed zone 3 [m] (21.00 - 23.99 km/h)",
                            "Distance in Speed zone 4 [m] (25.20 - 29.99 km/h)":"Distance in Speed zone 4 [m] (24.00 - 26.99 km/h)", 
                            "Distance in Speed zone 5 [m] (30.00- km/h)":"Distance in Speed zone 5 [m] (27.00- km/h)"}, inplace=True)
        
        data.rename(columns={"Number of accelerations (-50.00 - -9.00 m/s²)":"Number of accelerations (-50.00 - -2.70 m/s²)",
                            "Number of accelerations (-8.99 - -6.00 m/s²)":"Number of accelerations (-2.69 - -2.00 m/s²)", 
                            "Number of accelerations (-5.99 - -3.00 m/s²)":"Number of accelerations (-1.99 - -1.00 m/s²)",
                            "Number of accelerations (-2.99 - -0.50 m/s²)":"Number of accelerations (-0.99 - -0.50 m/s²)", 
                            "Number of accelerations (0.50 - 2.99 m/s²)":"Number of accelerations (0.50 - 0.99 m/s²)",
                            "Number of accelerations (3.00 - 5.99 m/s²)":"Number of accelerations (1.00 - 1.99 m/s²)",
                            "Number of accelerations (6.00 - 8.99 m/s²)":"Number of accelerations (2.00 - 2.69 m/s²)",
                            "Number of accelerations (9.00 - 50.00 m/s²)":"Number of accelerations (2.70 - 50.00 m/s²)"}, inplace=True)

        final_columns = list(girls_template.columns.values)
        columns_before_calc = final_columns[:-6]
        data = data[columns_before_calc]
        
        data = pd.concat([data, pd.Series(data['Duration'].astype(str).apply(hms_to_m), name='Duration')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 1 (50 - 59 %)'].apply(hms_to_m), name='Time in HR zone 1 (50 - 59 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 2 (60 - 69 %)'].apply(hms_to_m), name='Time in HR zone 2 (60 - 69 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 3 (70 - 79 %)'].apply(hms_to_m), name='Time in HR zone 3 (70 - 79 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 4 (80 - 89 %)'].apply(hms_to_m), name='Time in HR zone 4 (80 - 89 %)')], axis=1)
        data = pd.concat([data, pd.Series(data['Time in HR zone 5 (90 - 100 %)'].apply(hms_to_m), name='Time in HR zone 5 (90 - 100 %)')], axis=1)
        data['Maximum speed [km/h]'] = data["Maximum speed [km/h]"].round(decimals = 1)
        data['Average speed [km/h]'] = data["Average speed [km/h]"].round(decimals = 1)

        

        columns_dec_0 = ['Total distance [m]', 'Distance / min [m/min]', "Distance in Speed zone 1 [m] (10.00 - 17.99 km/h)", "Distance in Speed zone 2 [m] (18.00 - 20.99 km/h)", "Distance in Speed zone 3 [m] (21.00 - 23.99 km/h)", "Distance in Speed zone 4 [m] (24.00 - 26.99 km/h)", "Distance in Speed zone 5 [m] (27.00- km/h)"]
        data[columns_dec_0] = data[columns_dec_0].round(decimals=0)
        data[columns_dec_0] = data[columns_dec_0].astype(int)

    return data

# %%
data = preprocess()

def convert_df(df):
   return df.to_csv(index=False).encode('utf-8')


csv = convert_df(data)

date_f = day + month + year[2:]
csv_name = chosen_team + "_" + date_f + ".csv"

st.download_button(
   "Download the training session's data for " + set_date,
   csv,
   csv_name,
   "text/csv",
   key='download-csv'
)