import pandas as pd
import numpy as np
import requests
from requests import RequestException
import datetime as dt
from sqlalchemy import create_engine, text

def read_json(url):
    """
    Description: This function fetches data from the API endpoint and reads it into a pandas DataFrame object.
    Args: url
    Returns: pandas DataFrame
    """
    #Mapping the url to in function variable src_url
    src_url = url
    try:
        #Fetching the data
        response = requests.get(src_url)
        data = response.json()

        #Unpacking the json file and conversion to pandas dataframe
        from_=[]
        to_ = []
        forecast_ = []
        actual_ = []
        index_ = []
        for key, value in data.items():
            for val in value:
                from_.append("".join(val['from']))
                to_.append(val['to'])
                forecast_.append(val['intensity']['forecast'])
                actual_.append(val['intensity']['actual'])
                index_.append(val['intensity']['index'])
        df = pd.DataFrame({'from':from_, 'to': to_, 'forecast': forecast_, 'actual': actual_, 'index': index_})
        print("Data download successful!!!")
        return df
    except RequestException as re_:
        print("There was a problem reading the {}. Error: {}".format(src_url, re_))
        return pd.DataFrame()

def transform_data(df):
    new_df = df.copy()

    #Type conversion to the specific dtypes of each columns
    new_df['start_timestamp']  = pd.to_datetime(new_df['from'], utc=True)
    new_df['end_timestamp']  = pd.to_datetime(new_df['to'], utc=True)
    new_df['forecast'] = new_df['forecast'].astype('float32')
    new_df['actual'] = new_df['actual'].astype('float32')
    new_df['index_data'] = new_df['index'].astype('category')

    #Dropping renamed columns
    new_df = new_df.drop(['from', 'to', 'index'], axis=1)

    #Extracting the day, month, day and time columns from the from and to columns
    new_df['start_date'] = pd.to_datetime(new_df['start_timestamp'].dt.date)
    new_df['start_time'] = new_df['start_timestamp'].dt.time
    new_df['end_date'] = pd.to_datetime(new_df['end_timestamp'].dt.date)
    new_df['end_time'] = new_df['end_timestamp'].dt.time

    #Creating the column for the prediction error, e = (actual - forecast) and percentage_prediction_error to monitor model drift
    new_df['prediction_error'] = new_df.actual - new_df.forecast
    new_df['percentage_prediction_error'] = 100 * (new_df.actual - new_df.forecast)/new_df.actual

    #Fixing the missing values on the actual columns with the median values of the rest of the data
    new_df['actual'] = new_df['actual'].fillna(new_df['actual'].median())
    #print(new_df.info())
    return new_df

#Creating the database to load the data
def create_db():
    """
    Description: This function creates the destination database called carbon_db and table called carbon_intensity'
    Args: None
    Returns: None
    """

    #Creating the database credential variable
    db_cred_1 = {'host':'localhost', 'port':3306, 'user':'root', 'password':'tosin'}

    #Opening the database connection and creating the database
    try:
        engine_url_1 = f"mysql+mysqlconnector://{db_cred_1['user']}:{db_cred_1['password']}@{db_cred_1['host']}:{db_cred_1['port']}"
        engine_1 = create_engine(engine_url_1)
        with engine_1.connect() as conn:

            #Creating the database carbon_db
            db_text = """CREATE DATABASE IF NOT EXISTS carbon_db;"""
            conn.execute(text(db_text))
            print("Database created successfully!")
    except Exception as e:
        print("An error was encountered while connecting to the database with description {}".format(e))
        return e

    #Creating the table carbon_intensity
    try:
        engine_url_2 = f"mysql+mysqlconnector://{db_cred_1['user']}:{db_cred_1['password']}@{db_cred_1['host']}:{db_cred_1['port']}"
        engine_2 = create_engine(engine_url_2)
        with engine_2.connect() as conn_2:

            #Creating the database table carbon_db.carbon_intensity
            tbl_text = """CREATE TABLE IF NOT EXISTS carbon_db.carbon_intensity(
                            start_timestamp DATETIME,
                            start_date DATE,
                            start_time TIME,
                            end_timestamp DATETIME,
                            end_date DATE,
                            end_time TIME,
                            forecast FLOAT,
                            actual FLOAT,
                            prediction_error FLOAT,
                            prediction_error_percent FLOAT,
                            index_data VARCHAR(20));"""
            conn_2.execute(text(tbl_text))
            print("Table created successfully!")
    except Exception as e:
        print("An error was encountered while connecting to the database with description {}".format(e))
        return e

#Loading the data to the database table
def load_to_database(df):
    """
    Description: This function writes data to database table 'carbon_intensity'
    Args: df
    Returns: None
    """

    #Creating the database credential
    db_cred_2 = {'host':'localhost', 'port':3306, 'user':'root', 'password':'tosin', 'database':'carbon_db'}
    

    #Opening the database connection and writing the dataframe to database table
    try:
        engine_url_3 = f"mysql+mysqlconnector://{db_cred_2['user']}:{db_cred_2['password']}@{db_cred_2['host']}:{db_cred_2['port']}/{db_cred_2['database']}"
            
        #Writing the dataframe to the table carbon _intensity
        df.to_sql('carbon_intensity', con=engine_url_3, if_exists='replace', index=False)
        print('Data has been successfully written to the database table carbon_intensity!')
    except Exception as e:
        print("An error {} was encountered while connecting to or writing to the database table.".format(e))


def main():
    url = 'https://api.carbonintensity.org.uk/intensity/date'
    df = read_json(url)
    new_data = transform_data(df)
    create_db()
    load_to_database(new_data)

main()