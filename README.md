#Weather & Electricity Forecasting Pipeline 🇳🇱

This project pulls together weather data (KNMI & Open-Meteo) and electricity data (ENTSO-E), stores it in a PostgreSQL database, and uses XGBoost to forecast energy demand and solar/wind generation. Everything is automated using Airflow running in Docker on my old laptop (setup as a Linux server).

Historical data is used to create forecasting models.

---

# Data sources

- **KNMI API** – historical weather (hourly/daily)
- **ENTSO-E API** – historical electricity data (load, market, generation)
- **Open-Meteo** – weather forecasts (temp, radiation, wind, etc.)

- XGBoost was used to build models for:
 - **Electricity load** prediction using time features (hour, weekday, month, etc.) and temperature
 - **Solar & wind generation** prediction using additional weather features like shortwave radiation, wind speed, and gusts
- The models essentially combine time series structure with weather-based features to improve accuracy


- Historical data is pulled daily (electricity + weather) and upserted into db
- Forecasts run hourly using Open-Meteo
- Load & solar/wind generation predictions are written to Postgres
- Everything is visualized in Power BI using the same database


                    +------------------------+         +--------------------+
                    |  KNMI & ENTSO-E APIs   |         |  Open-Meteo API    |
                    +-----------+------------+         +---------+----------+
                                |                                |
                                v                                v
               +-----------------------------+       +-----------------------------+
               | Historical ETL DAG (Airflow)|       | Forecast DAG (Airflow, 24h)|
               +-----------------------------+       +-----------------------------+
                                |                                |
                                v                                v
                     +------------------------+       +------------------------+
                     |  Cleaned + Raw Tables  |       |  Forecasted Predictions|
                     |      (PostgreSQL)      |<------+  (load / solar / wind) |
                     +-----------+------------+       +------------------------+
                                 |
                                 v
                         +------------------+
                         |  Power BI Live    |
                         |   Visualizations  |
                         +------------------+



