import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import requests
import pytz
from datetime import datetime

DASH_HOST = "localhost"
DASH_PORT = 5000

IP_ADDRESS = "20.46.254.134"
PORT_STH = 8666
PORT_IOT_AGENT = 1026

DEVICE = "Hosp"
DEVICE_ID = "001"

triggerMinLuminosity = 30
triggerMaxLuminosity = 50

triggerMintemperature = 10
triggerMaxtemperature = 20

triggerMinHumidity = 40
triggerMaxHumidity = 60

luminosidadeAlerta = "on_alert_luminosity"
luminosidadeNormal = "on_normal_luminosity"

temperaturaAlerta = "on_alert_temperature"
temperaturaNormal = "on_normal_temperature"

umidadeAlerta = "on_alert_humidity"
umidadeNormal = "on_normal_humidity"

urlBase = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/{DEVICE}/id/urn:ngsi-ld:{DEVICE}:{DEVICE_ID}/attributes"
urlComandos = f"http://{IP_ADDRESS}:{PORT_IOT_AGENT}/v2/entities/urn:ngsi-ld:{DEVICE}:{DEVICE_ID}/attrs"
urlLuminosidade = f"{urlBase}/luminosity"
urlTemperatura = f"{urlBase}/temperature"
urlUmidade = f"{urlBase}/humidity"

headers = {
    "fiware-service": "smart",
    "fiware-servicepath": "/"
}

def pegarDados (url, lastN = 1):
    response = requests.get(f"{url}?lastN={lastN}", headers=headers)
    if response.status_code == 200:
        data = response.json()
        try:
            values = data['contextResponses'][0]['contextElement']['attributes'][0]['values']
            return values
        except KeyError as error:
            print(f"KeyError: {error}")
            return []
    else:
        print(f"Erro ao acessar {url}: {response.status_code}")
        return []
    
def enviarComando (url, comando):
    dados = {
        f"{comando}": {
            "type": "command",
            "value": ""
        } 
    }

    try:
        requests.patch(url, json=dados, headers=headers)
    except:
        print("Erro ao enviar comando")

def verificarTriggers (store_data):
    if store_data["luminosity_values"]:
        if store_data["luminosity_values"][-1] < triggerMinLuminosity or store_data["luminosity_values"][-1] > triggerMaxLuminosity:
            # Fora dos triggers
            enviarComando(urlComandos, luminosidadeAlerta)
        else:
            # Dentro dos triggers
            enviarComando(urlComandos, luminosidadeNormal)
    if store_data["temperature_values"]:
        if store_data["temperature_values"][-1] < triggerMintemperature or store_data["temperature_values"][-1] > triggerMaxtemperature:
            # Fora dos triggers
            enviarComando(urlComandos, temperaturaAlerta)
        else:
            # Dentro dos triggers
            enviarComando(urlComandos, temperaturaNormal)
    if store_data["humidity_values"]:
        if store_data["humidity_values"][-1] < triggerMinHumidity or store_data["humidity_values"][-1] > triggerMaxHumidity:
            # Fora dos triggers
            enviarComando(urlComandos, umidadeAlerta)
        else:
            # Dentro dos triggers
            enviarComando(urlComandos, umidadeNormal)

def convert_to_lisbon_time(timestamps):
    utc = pytz.utc
    lisbon = pytz.timezone('Europe/Lisbon')
    converted_timestamps = []
    for timestamp in timestamps:
        try:
            timestamp = timestamp.replace('T', ' ').replace('Z', '')
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')).astimezone(lisbon)
        except ValueError:
            # Handle case where milliseconds are not present
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')).astimezone(lisbon)
        converted_timestamps.append(converted_time)
    return converted_timestamps
 
app = dash.Dash(__name__)
app.layout = html.Div(children=[
        html.H1("Sensor de luminosidade", style={"text-align": "center", "font-size": "90px", "font-family": "arial"}),
        dcc.Graph(id='graph-luminosity'),
        html.H1("Sensor de temperatura", style={"text-align": "center", "font-size": "90px", "font-family": "arial"}),
        dcc.Graph(id='graph-temperature'),
        html.H1("Sensor de umidade", style={"text-align": "center", "font-size": "90px", "font-family": "arial"}),
        dcc.Graph(id='graph-humidity'),
        dcc.Store(id="store-data", data={"timestamps": [], "luminosity_values": [], "temperature_values": [], "humidity_values": []}),
        dcc.Interval(
            id ='interval-component',
            interval = 5 * 1000,  # in milliseconds (5 seconds)
            n_intervals = 0
        )
    ])

@app.callback(
    Output("store-data", "data"),
    Input("interval-component", "n_intervals"),
    State("store-data", "data")
)
def update_data_store(n, store_data):
    try:
        if not store_data["timestamps"]:
            data_luminosity = pegarDados(urlLuminosidade, lastN=10)
            data_temperature = pegarDados(urlTemperatura, lastN=10)
            data_humidity = pegarDados(urlUmidade, lastN=10)

            if data_luminosity or data_temperature or data_humidity:

                # Luminosidade
                if data_luminosity:
                    timestamps = [entry.get('recvTime') for entry in data_luminosity]
                    timestamps = convert_to_lisbon_time(timestamps)
                    luminosity_values = [float(entry.get('attrValue', 0)) for entry in data_luminosity]
                
                    store_data['timestamps'] = timestamps
                    store_data['luminosity_values'] = luminosity_values

                # Temperatura
                if data_temperature:
                    temperature_values = [float(entry.get('attrValue', 0)) for entry in data_temperature]
                    store_data['temperature_values'] = temperature_values

                # Umidade
                if data_humidity:
                    humidity_values = [float(entry.get('attrValue', 0)) for entry in data_humidity]
                    store_data['humidity_values'] = humidity_values
                verificarTriggers(store_data)
            return store_data
        else:
            data_luminosity = pegarDados(urlLuminosidade, lastN=5)
            data_temperature = pegarDados(urlTemperatura, lastN=5)
            data_humidity = pegarDados(urlUmidade, lastN=5)

            if data_luminosity or data_temperature or data_humidity:
    
                # Luminosidade
                if data_luminosity:
                    timestamps = [entry.get('recvTime') for entry in data_luminosity]
                    timestamps = convert_to_lisbon_time(timestamps)
                    luminosity_values = [float(entry.get('attrValue', 0)) for entry in data_luminosity]
                
                    store_data['timestamps'].extend(timestamps)
                    store_data['luminosity_values'].extend(luminosity_values)

                # Temperatura
                if data_temperature:
                    temperature_values = [float(entry.get('attrValue', 0)) for entry in data_temperature]
                    store_data['temperature_values'].extend(temperature_values)

                # Umidade
                if data_humidity:
                    humidity_values = [float(entry.get('attrValue', 0)) for entry in data_humidity]
                    store_data['humidity_values'].extend(humidity_values)
                verificarTriggers(store_data)
            return store_data

    except Exception as e:
        print("Erro no callback update_data_store:", e)
        return store_data

@app.callback(
    Output("graph-luminosity", "figure"),
    Input("store-data", "data")
)
def updateLuminosityGraph(store_data):
    
    if store_data["timestamps"] and store_data["luminosity_values"]:
        valid_luminosity = [t for t in store_data["luminosity_values"] if isinstance(t, (int, float))]

        if not valid_luminosity:  # Se não tiver nenhum válido
            return {}

        mean_luminosity = sum(valid_luminosity) / len(valid_luminosity)

        trace_luminosity = go.Scatter(
            x=store_data['timestamps'],
            y=store_data['luminosity_values'],
            mode='lines+markers',
            name='LUMINOSIDADE',
            line=dict(color='blue')
        )
        trace_mean = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[mean_luminosity, mean_luminosity],
            mode='lines',
            name='LUMINOSIDADE MÉDIA',
            line=dict(color='orange', dash='dash')
        )

        trace_minTrigger = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[triggerMinLuminosity, triggerMinLuminosity],
            mode="lines",
            name="TRIGGER MINIMO",
            line=dict(color='red')
        )

        trace_maxTrigger = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[triggerMaxLuminosity, triggerMaxLuminosity],
            mode="lines",
            name="TRIGGER MÁXIMO",
            line=dict(color='red')
        )
 
        # Create figure
        fig_luminosity = go.Figure(data=[trace_luminosity, trace_mean, trace_minTrigger, trace_maxTrigger])
 
        # Update layout
        fig_luminosity.update_layout(
            title='LUMINOSIDADE AO LONGO DO TEMPO',
            xaxis_title='TEMPO',
            yaxis_title='LUMINOSIDADE (%)',
            hovermode='closest'
        )
 
        return fig_luminosity
 
    return {}
    
@app.callback(
    Output("graph-temperature", "figure"),
    Input("store-data", "data")
)
def updateTemperatureGraph(store_data):
    
    if store_data["timestamps"] and store_data["temperature_values"]:
        valid_temperatures = [t for t in store_data["temperature_values"] if isinstance(t, (int, float))]

        if not valid_temperatures:  # Se não tiver nenhum válido
            return {}

        mean_temperature = sum(valid_temperatures) / len(valid_temperatures)

        trace_temperature = go.Scatter(
            x=store_data['timestamps'],
            y=store_data['temperature_values'],
            mode='lines+markers',
            name='TEMPERATURA',
            line=dict(color='blue')
        )
        trace_mean = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[mean_temperature, mean_temperature],
            mode='lines',
            name='TEMPERATURA MÉDIA',
            line=dict(color='orange', dash='dash')
        )

        trace_minTrigger = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[triggerMintemperature, triggerMintemperature],
            mode="lines",
            name="TRIGGER MINIMO",
            line=dict(color='red')
        )

        trace_maxTrigger = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[triggerMaxtemperature, triggerMaxtemperature],
            mode="lines",
            name="TRIGGER MÁXIMO",
            line=dict(color='red')
        )
 
        # Create figure
        fig_temperature = go.Figure(data=[trace_temperature, trace_mean, trace_minTrigger, trace_maxTrigger])
 
        # Update layout
        fig_temperature.update_layout(
            title='TEMPERATURA AO LONGO DO TEMPO',
            xaxis_title='TEMPO',
            yaxis_title='TEMPERATURA (°C)',
            hovermode='closest'
        )
 
        return fig_temperature
 
    return {}
    
@app.callback(
    Output("graph-humidity", "figure"),
    Input("store-data", "data")
)
def updateHumidityGraph(store_data):
    
    if store_data["timestamps"] and store_data["humidity_values"]:
        valid_humidity = [t for t in store_data["humidity_values"] if isinstance(t, (int, float))]

        if not valid_humidity:  # Se não tiver nenhum válido
            return {}

        mean_humidity = sum(valid_humidity) / len(valid_humidity)

        trace_humidity = go.Scatter(
            x=store_data['timestamps'],
            y=store_data['humidity_values'],
            mode='lines+markers',
            name='UMIDADE',
            line=dict(color='blue')
        )
        trace_mean = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[mean_humidity, mean_humidity],
            mode='lines',
            name='UMIDADE MÉDIA',
            line=dict(color='orange', dash='dash')
        )

        trace_minTrigger = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[triggerMinHumidity, triggerMinHumidity],
            mode="lines",
            name="TRIGGER MINIMO",
            line=dict(color='red')
        )

        trace_maxTrigger = go.Scatter(
            x=[store_data['timestamps'][0], store_data['timestamps'][-1]],
            y=[triggerMaxHumidity, triggerMaxHumidity],
            mode="lines",
            name="TRIGGER MÁXIMO",
            line=dict(color='red')
        )
 
        # Create figure
        fig_humidity = go.Figure(data=[trace_humidity, trace_mean, trace_minTrigger, trace_maxTrigger])
 
        # Update layout
        fig_humidity.update_layout(
            title='TEMPERATURA AO LONGO DO TEMPO',
            xaxis_title='TEMPO',
            yaxis_title='UMIDADE (%)',
            hovermode='closest'
        )
 
        return fig_humidity
 
    return {}
    
app.run(debug=True, host=DASH_HOST, port=DASH_PORT)