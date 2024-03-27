import requests

r = requests.get("https://www.fdsn.org/ws/networks/1/query")

for net in r.json()["networks"]:
    # doi test
    if net["doi"]:
        # success in database
        # store doi
    else:
        # fail in database
        # clear comment
        continue
    # datacite tests
    dataciteapi = "https://api.datacite.org/application/vnd.datacite.datacite+json/"
    r = requests.get(dataciteapi+net["doi"])
    datacite = r.json()
    # page test
    r.request.get(datacite["url"])
    if r.status_code == 200:
        # success in database
    else:
        # fail in database
    # open test UNSURE ABOUT THAT
    # license test
    if datacite['rightsList']:
        # success in database
        # store license
    else:
        # fail in database
        # clear comment
    # store publisher in database
    # StationXML test UNSURE HOW TO
