from flask import Flask, render_template, request
import requests
import datetime
import numpy as np
import concurrent.futures
import plotly.graph_objs as go
from plotly.offline import plot

app = Flask(__name__)

def fetch_api(date_str):
    url = f"https://api.data.gov.sg/v1/environment/4-day-weather-forecast?date={date_str}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
        print(f"Fetched data for date: {date_str}")
        results = []
        # Process the JSON response as before
        for payload in json_data['items'][-1]['forecasts'][::-1]:
            temp = np.array(list(payload['temperature'].values())).mean()
            humidity = np.array(list(payload['relative_humidity'].values())).mean()
            results.append({"date": payload['date'], "temperature": temp, "humidity": humidity})
        return results
    except Exception as e:
        print(f"Error fetching data for {date_str}: {e}")
        return []

def fetch_weather_data(start_date, N=8):
    # Create a list of date strings
    date_strs = [
        (start_date + datetime.timedelta(days=(-(i+1)*4))).strftime("%Y-%m-%d")
        for i in range(N)
    ]
    data = []
    # Use ThreadPoolExecutor to run requests concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_api, date_str): date_str for date_str in date_strs}
        for future in concurrent.futures.as_completed(futures):
            data.extend(future.result())
    data.sort(key=lambda x: x['date'])
    return data[::-1]


def generate_charts(data):
    """
    Generate two interactive Plotly charts for temperature and humidity.
    Returns two HTML divs that can be embedded in the template.
    """
    # Filter out days with missing data
    filtered = [d for d in data if d["temperature"] is not None and d["humidity"] is not None]
    dates = [d["date"] for d in filtered]
    temps = [d["temperature"] for d in filtered]
    hums = [d["humidity"] for d in filtered]

    # Create Temperature Chart
    trace_temp = go.Scatter(x=dates, y=temps, mode='lines+markers', name='Temperature', 
                            line={'color':'red','shape': 'spline'}
                )
    layout_temp = go.Layout(
        title='Temperature Trend (Last 30 Days)',
        xaxis={'title': 'Date'},
        yaxis={'title': 'Temperature','rangemode': 'tozero'},
        margin=dict(l=40, r=40, t=40, b=40)
    )
    fig_temp = go.Figure(data=[trace_temp], layout=layout_temp)
    chart_div_temp = plot(fig_temp, output_type='div', include_plotlyjs=False)

    # Create Humidity Chart
    trace_hum = go.Scatter(x=dates, y=hums, mode='lines+markers', name='Humidity', 
                           line={'color':'blue','shape': 'spline'}
                )
    layout_hum = go.Layout(
        title='Humidity Trend (Last 30 Days)',
        xaxis={'title': 'Date'},
        yaxis={'title': 'Humidity','rangemode': 'tozero'},
        margin=dict(l=40, r=40, t=40, b=40)
    )
    fig_hum = go.Figure(data=[trace_hum], layout=layout_hum)
    chart_div_hum = plot(fig_hum, output_type='div', include_plotlyjs=False)

    return chart_div_temp, chart_div_hum


@app.route('/', methods=['GET', 'POST'])
def index():
    # Default start date: today
    if request.method == 'POST':
        date_str = request.form.get('start_date')
        try:
            start_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception as e:
            start_date = datetime.date.today()
    else:
        start_date = datetime.date.today()

    weather_data = fetch_weather_data(start_date)
    chart_temp, chart_hum = generate_charts(weather_data[::-1])
    return render_template('index.html', data=weather_data, chart_temp=chart_temp, chart_hum=chart_hum, start_date=start_date.strftime("%Y-%m-%d"))


if __name__ == '__main__':
    app.run(debug=True)
