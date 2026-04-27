import os
import requests
import time
import pandas as pd

api_key = os.environ["WEATHERAPI_KEY"]

api_url = "https://api.weatherapi.com/v1/forecast.json"

zip_codes = [
    "90045",  # Los Angeles, CA
    "10001",  # New York, NY
    "60601",  # Chicago, IL
    "98101",  # Seattle, WA
    "33101",  # Miami, FL
    "77001",  # Houston, TX
    "85001",  # Phoenix, AZ
    "19101",  # Philadelphia, PA
    "78201",  # San Antonio, TX
    "92101",  # San Diego, CA
    "75201",  # Dallas, TX
    "95101",  # San Jose, CA
    "78701",  # Austin, TX
    "32099",  # Jacksonville, FL
    "43215",  # Columbus, OH
    "46201",  # Indianapolis, IN
    "94102",  # San Francisco, CA
    "28201",  # Charlotte, NC
    "80201",  # Denver, CO
    "20001",  # Washington, DC
]

weather_results = []

for zip_code in zip_codes:
    params = {
        "key": api_key,
        "q": zip_code,
        "days": 7
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    city = data["location"]["name"]
    region = data["location"]["region"]

    print(f"\n{city}, {region} — 7-Day Forecast:")

    for day in data["forecast"]["forecastday"]:
        result = {
            "zip_code": zip_code,
            "city": city,
            "region": region,
            "date": day["date"],
            "max_temp_f": day["day"]["maxtemp_f"],
            "min_temp_f": day["day"]["mintemp_f"],
            "condition": day["day"]["condition"]["text"],
        }
        weather_results.append(result)

        print(f"  {result['date']}: {result['min_temp_f']}°F - {result['max_temp_f']}°F, {result['condition']}")

    time.sleep(1)

df = pd.DataFrame(weather_results)
df.to_csv("weather_data.csv", index=False)

print(f"\nSaved weather_data.csv: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"\nFirst 10 rows:")
print(df.head(10).to_string(index=False))