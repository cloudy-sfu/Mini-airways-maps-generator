# [Ref] https://airportsbase.org/ICAO.php
import io
import json
import re

from requests import Session
from bs4 import BeautifulSoup
import pandas as pd

session = Session()
session.trust_env = False
with open("headers/airports_base_search.json") as f:
    header_1 = json.load(f)
remove_bracket = re.compile(r"\(.*\)")


def get_airport_info(icao):
    response = session.get(
        "https://airportsbase.org/search.php",
        params={"code": icao},
        headers=header_1,
        timeout=2
    )
    page = BeautifulSoup(response.text, "html.parser")
    info_table = page.find("div", {"class": "table-wrap"}).find("table")
    info_table = pd.read_html(io.StringIO(str(info_table)))[0]
    info_dict = {
        "name": info_table.loc[info_table.iloc[:, 0] == "Name"].iloc[0, -1],
        "city": re.sub(
            remove_bracket, "",
            info_table.loc[info_table.iloc[:, 0] == "City"].iloc[0, -1]
        ).strip(),
        "country": re.sub(
            remove_bracket, "",
            info_table.loc[info_table.iloc[:, 0] == "Country"].iloc[0, -1]
        ).strip(),
        "iso_country_code":
            info_table.loc[info_table.iloc[:, 0] == "ISO country code"].iloc[0, -1],
    }
    return info_dict
