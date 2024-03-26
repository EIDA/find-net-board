import requests

r = requests.get("https://www.fdsn.org/ws/networks/1/query")

for net in r.json()["networks"]:
    print(net["fdsn_code"])
