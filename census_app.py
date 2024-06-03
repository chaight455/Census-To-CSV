from flask import Flask, request, render_template, Response
from pandas import DataFrame
import requests
from geopandas import read_file
from io import BytesIO,StringIO

app = Flask(__name__)

"""
Get Geographical data for given state.

Arguments:
state_name     #State name eg. "Wisconsin"
year           #Year of data

Returns Geopandas DataFrame.
"""
def get_geo_data(state_name, year):
    state_code = get_state_code(state_name)
    # Load in tract data
    tract_url = f"https://www2.census.gov/geo/tiger/TIGER{year}/TRACT/tl_{year}_{state_code}_tract.zip"
    response = requests.request("GET", tract_url)
    data = response.content
    # Convert data to GeoDataFrame
    geo_tract_data = read_file(BytesIO(data))
    return geo_tract_data


"""Helper Method for class"""
def get_state_and_county_code(state_name,county_name, census_api_key):
    # URL for getting county and state codes
    states_url = f"https://api.census.gov/data/2022/acs/acs5?get=NAME,B01001_001E&for=county:*&in=state:*&key={census_api_key}"
    
    # Request States data
    response = requests.request("GET", states_url)
    if response.status_code != 200:
        return -1,-1
    states_data = DataFrame(response.json()[1:], columns=["County, State", "Zipcode", "State Code", "County Code"])
    
    #Get state code and county code
    county_code = 0
    state_code = 0
    for index,row in states_data.iterrows():
        if (row["County, State"] == f"{county_name}, {state_name}"):
            state_code = row["State Code"]
            county_code = row["County Code"]
            break
    if (state_code == 0) or (county_code == 0):
        return -1,-1
    return state_code, county_code

"""Helper Method for class"""
def get_state_code(state_name, census_api_key):
    # URL for getting county and state codes
    states_url = f"https://api.census.gov/data/2022/acs/acs5?get=NAME,B01001_001E&for=county:*&in=state:*&key={census_api_key}"
    
    # Request States data
    response = requests.request("GET", states_url)
    if response.status_code != 200:
        return -1
    states_data = DataFrame(response.json()[1:], columns=["County, State", "Zipcode", "State Code", "County Code"])
    
    #Get state code and county code
    state_code = 0
    for index,row in states_data.iterrows():
        if (row["County, State"].endswith(state_name)):
            state_code = row["State Code"]
            break
    if (state_code == 0):
        return -1
    return state_code

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/detailed_tables.html", methods=['GET', 'POST'])
def detailed_tables():
    if request.method == 'POST':
        census_api_key = request.form['key']
        if census_api_key == "":
            return render_template("detailed_tables.html", error = "Error: All boxes must be filled in.")
        if len(census_api_key) != 40:
            return render_template("detailed_tables.html", error = "Error: Invalid Census API key")
        variables = request.form['variables']
        state_name = request.form['state']
        county_name = request.form['county']
        year = request.form['year']
        if (variables == "") or (state_name == "") or (county_name == "") or (year == ""):
            return render_template("detailed_tables.html", error = "Error: All boxes must be filled in.")
        if int(year)>2022:
            return render_template("detailed_tables.html", error = "Error: Invalid year")
        state_code = 0
        county_code = 0
        #if (type(variables) != list):
            #return render_template("detailed_tables.html", error = "Error: Variables must be in a comma-seperated list. e.g B01001_001E or B01001_001E,B01001_001C")
        if (state_name != "*") and (county_name != "*"):
            state_code, county_code = get_state_and_county_code(state_name,county_name,census_api_key)
        elif (county_name == "*") and (state_name != "*"):
            state_code = get_state_code(state_name,census_api_key)
            county_code = "*"
        elif (state_name == "*") and (county_name == "*"):
          state_code = "*"
          county_code = "*"
        if state_code == -1:
            return render_template("detailed_tables.html", error = f"Error: State or County is incorrect. Make sure you include \"County\" after the county name.")
        variables = variables.replace(" ", "")
        # URL for ACS data
        survey_url = f"https://api.census.gov/data/{year}/acs/acs5?get=NAME,{variables}&for=tract:*&in=state:{state_code}&in=county:{county_code}&key={census_api_key}"
        print(survey_url)
        # Request ACS data
        response = requests.request("GET", survey_url)
        if response.status_code != 200:
            return render_template("detailed_tables.html", error = f"Error: To see your error visit {survey_url}")
        csv_data = DataFrame(response.json()[1:], columns=response.json()[0]).to_csv()
        # Create StringIO object to hold CSV data in memory
        csv_stream = StringIO()
        csv_stream.write(csv_data)
        csv_stream.seek(0)

        # Return CSV file as a response
        return Response(
            csv_stream,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=data.csv"}
        )
    return render_template("detailed_tables.html")

if __name__ == '__main__':
    app.run()