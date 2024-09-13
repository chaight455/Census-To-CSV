from flask import Flask, request, render_template, Response
from pandas import DataFrame
import requests
#from geopandas import read_file
from io import BytesIO,StringIO

app = Flask(__name__)



@app.route('/')
def index():
    return render_template('index.html')

#AMERICAN COMMUNITY SURVEY PULLERS
@app.route("/data_profiles", methods=['GET', 'POST'])
def data_profiles():
    if request.method == 'POST':
        return acs_post_helper("data_profiles.html",request)
    return render_template("data_profiles.html")

@app.route("/subject_tables", methods=['GET', 'POST'])
def subject_tables():
    if request.method == 'POST':
        return acs_post_helper("subject_tables.html",request)
    return render_template("subject_tables.html", error = "")

@app.route("/detailed_tables", methods=['GET', 'POST'])
def detailed_tables():
    if request.method == 'POST':
        return acs_post_helper("detailed_tables.html",request)
    return render_template("detailed_tables.html", error = "")

"""Helper Method for ACS"""
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

def acs_post_helper(html,request):
    census_api_key = request.form['key']
    if census_api_key == "":
        return render_template(html, error = "Error: All boxes must be filled in.")
    if len(census_api_key) != 40:
        return render_template(html, error = "Error: Invalid Census API key")
    variables = request.form['variables']
    state_name = request.form['state']
    county_name = request.form['county']
    year = request.form['year']
    if (variables == "") or (state_name == "") or (county_name == "") or (year == ""):
        return render_template(html, error = "Error: All boxes must be filled in.")
    if int(year)>2022:
        return render_template(html, error = "Error: Invalid year")
    state_code = 0
    county_code = 0
    if (state_name != "*") and (county_name != "*"):
        state_code, county_code = get_state_and_county_code(state_name,county_name,census_api_key)
    elif (county_name == "*") and (state_name != "*"):
        state_code = get_state_code(state_name,census_api_key)
        county_code = "*"
    elif (state_name == "*") and (county_name == "*"):
      state_code = "*"
      county_code = "*"
    if state_code == -1:
        return render_template(html, error = f"Error: State or County is incorrect. Make sure you include \"County\" after the county name.")
    variables = variables.replace(" ", "").replace("\"","")
    # URL for ACS data
    url = ""
    if html=="detailed_tables.html":
      url = f"https://api.census.gov/data/{year}/acs/acs5?get=NAME,{variables}&for=tract:*&in=state:{state_code}&in=county:{county_code}&key={census_api_key}"
    if html=="subject_tables.html":
      url = f"https://api.census.gov/data/{year}/acs/acs5/subject?get=NAME,{variables}&for=tract:*&in=state:{state_code}&in=county:{county_code}&key={census_api_key}"
    if html=="data_profiles.html":
      url = f"https://api.census.gov/data/{year}/acs/acs5/profile?get=NAME,{variables}&for=tract:*&in=state:{state_code}&in=county:{county_code}&key={census_api_key}"
    # Request ACS data
    response = requests.request("GET", url)
    print(url)
    if response.status_code != 200:
        return render_template(html, error = f"Error: Variables entered do not exist")
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

#GEO DATA PULLER
@app.route("/geo_tract", methods=['GET', 'POST'])
def geo_tract():
    if request.method == 'POST':
        state_name = request.form['state']
        year = request.form['year']
        key = request.form['key']
        state_code = get_state_code(state_name, key)
        # Load in tract data
        tract_url = f"https://www2.census.gov/geo/tiger/TIGER{year}/TRACT/tl_{year}_{state_code}_tract.zip"
        response = requests.request("GET", tract_url)
        if response.status_code != 200:
            return render_template("geo_polygon", error = f"Error: Variables entered do not exist")
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
    return render_template("geo_tract.html", error = "")
    
if __name__ == '__main__':
    app.run()