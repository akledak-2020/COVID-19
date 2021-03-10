import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import requests
from os import path
from datetime import datetime


def get_config(conf_file):
    with open(conf_file) as f_in:
        return json.load(f_in)


def get_district_info():
    Landkreis_info = pd.read_csv(config['landkreise_info_file'], sep=";")
    Landkreis_info['Fläche _in_km2'] = Landkreis_info['Fläche _in_km2'].str.replace(",", ".").astype(float)
    Landkreis_info['Bev_insgesamt'] = Landkreis_info['Bev_insgesamt'].str.replace(" ", "").astype(int)
    Landkreis_info['Bev_männlich'] = Landkreis_info['Bev_männlich'].str.replace(" ", "").astype(int)
    Landkreis_info['Bev_weiblich'] = Landkreis_info['Bev_weiblich'].str.replace(" ", "").astype(int)
    return Landkreis_info


def read_from_rki():
    r = requests.get(config['rki_file_url'], allow_redirects=True)
    f = open(config['rki_file'], 'wb')
    f.write(r.content)
    f.close()
    print("RKI data updated")


def get_reports():
    if path.exists(config['rki_file']):  # file exist
        filedate = datetime.fromtimestamp(path.getctime(config['rki_file'])).date()
        if filedate < datetime.now().date():
            read_from_rki()
    else:
        read_from_rki()
    return pd.read_csv(config['rki_file'])


def seven_days(cases):
    cumsum = cases.cumsum()
    cases_7 = pd.DataFrame(cumsum[7:].values - cumsum[:-7].values, index=cumsum[7:].index, columns=cumsum.columns)
    return cases_7


start_time = datetime.now()
# load data
config = get_config("config_covid-19.json")
Landkreis_info = get_district_info()
Reports = get_reports()

# prepare data
Reports = Reports.sort_values('Meldedatum')
Reports['Meldedatum'] = pd.to_datetime(Reports['Meldedatum'], format="%Y/%m/%d %H:%M:%S").dt.date
bundeslaender = Reports['Bundesland'].unique()
landkreise = Reports['Landkreis'].unique()
altersgruppen = Reports['Altersgruppe'].unique()

# analyze data
Selection_bundesland = Reports[Reports['Bundesland'].isin(config['Bundesland'])]
Selection_landkreis = Reports[Reports['Landkreis'].isin(config['Landkreis'])]
if config['Bundesland'] and config['Landkreis']:
    Cases_bundesland = Selection_bundesland.groupby(['Meldedatum', 'Bundesland'])[config['ArtFall']].sum().unstack()
    Cases_landkreis = Selection_landkreis.groupby(['Meldedatum', 'Landkreis'])[config['ArtFall']].sum().unstack()
    Cases = pd.merge(Cases_bundesland, Cases_landkreis, on='Meldedatum')
elif config['Bundesland']:
    Cases = Selection_bundesland.groupby(['Meldedatum', 'Bundesland'])[config['ArtFall']].sum().unstack()
elif config['Landkreis']:
    Cases = Selection_landkreis.groupby(['Meldedatum', 'Landkreis'])[config['ArtFall']].sum().unstack()
else:  # ganz Deutschland
    Selection = Reports
    Cases = Selection.groupby(['Meldedatum', 'Altersgruppe'])[config['ArtFall']].sum().unstack()
    Cases['Alle Altersgruppen'] = Selection.groupby('Meldedatum')[config['ArtFall']].sum()

if config['7Tage-je-100T']:
    Cases = seven_days(Cases)
    for area in Cases.columns:
        if area in Landkreis_info['Bundesland'].values:
            inhabitants = Landkreis_info[Landkreis_info['Bundesland'] == area]['Bev_insgesamt'].sum()
        elif area in Landkreis_info['Kreis'].values:
            inhabitants = Landkreis_info[Landkreis_info['Kreis'] == area]['Bev_insgesamt']
        else:
            inhabitants = Landkreis_info['Bev_insgesamt'].sum()
        Cases[area] = Cases[area] / np.array(inhabitants / 100000)

# show results
pd.options.display.float_format = '{:,.1f}'.format
print(Cases[-14:])  # last 14 days

plt.plot(Cases)
plt.title(config, fontsize=8)
plt.ylabel(config['ArtFall'])
plt.grid()
plt.legend(Cases.columns)
plt.show()

end_time = datetime.now()
print("Runtime for analysis:", end_time - start_time)
