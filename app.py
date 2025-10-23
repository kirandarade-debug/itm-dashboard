import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import base64
import re
import os
import pandas as pd
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # This is important for deployment


# NEW: Load short interest tickers from finviz_short.csv
def load_short_interest_tickers():
    """Load tickers from finviz_short.csv for short interest indicator"""
    try:
        short_df = pd.read_csv("finviz_short.csv")
        if 'Ticker' in short_df.columns:
            short_tickers = set(short_df['Ticker'].str.strip().str.upper())
            print(f"✓ Loaded {len(short_tickers)} tickers from finviz_short.csv")
            return short_tickers
        else:
            print("⚠️ 'Ticker' column not found in finviz_short.csv")
            return set()
    except FileNotFoundError:
        print("⚠️ finviz_short.csv not found. Short interest indicators will not be shown.")
        return set()
    except Exception as e:
        print(f"⚠️ Error loading finviz_short.csv: {str(e)}")
        return set()


# Load short interest tickers at startup
SHORT_INTEREST_TICKERS = load_short_interest_tickers()


def parse_itm_content(content_str):
    # Parse normal tickers data
    tickers_data, puts_data, calls_data = {}, {}, {}

    # Parse earnings tickers data
    earnings_tickers_data, earnings_puts_data, earnings_calls_data = {}, {}, {}

    # NORMAL TICKERS PARSING (existing logic)
    tickers_section = re.search(
        r'FINAL QUALIFYING TICKERS WITH CURRENT PRICES:\s*=+\s*(.*?)\s*CALL ACTIVITY ANALYSIS:',
        content_str, re.DOTALL
    )

    if tickers_section:
        for line in tickers_section.group(1).splitlines():
            match = re.match(
                r'([A-Z]+):\s*Current Price \$?([\d,.]+),\s*(\d+)\s*ITM puts,\s*Total Premium \$?([\d,.]+)', line)
            if match:
                ticker, price, num_puts, prem = match.groups()
                tickers_data[ticker] = {
                    'current_price': float(price.replace(',', '')),
                    'num_puts': int(num_puts),
                    'total_premium': float(prem.replace(',', ''))
                }

    puts_section = re.search(
        r'DETAILED PUT BREAKDOWN BY TICKER:\s*=+\s*(.*?)\s*ANALYSIS METADATA:',
        content_str, re.DOTALL
    )

    if puts_section:
        current_ticker = None
        for line in puts_section.group(1).splitlines():
            line = line.strip()
            ticker_match = re.match(r'([A-Z]+)\s*\(Current Price.*\):', line)
            if ticker_match:
                current_ticker = ticker_match.group(1)
                puts_data[current_ticker] = []
            elif current_ticker and line.startswith('Put #'):
                put_match = re.match(
                    r'Put #(\d+):\s*Strike \$?([\d,.]+),\s*Spot \$?([\d,.]+),\s*ITM by \$?([\d,.]+),\s*Premium \$?([\d,.]+),\s*Exp:\s*(.+)',
                    line)
                if put_match:
                    idx, strike, spot, itm_by, premium, exp = put_match.groups()
                    puts_data[current_ticker].append({
                        'put_number': int(idx),
                        'strike': float(strike.replace(',', '')),
                        'spot': float(spot.replace(',', '')),
                        'itm_by': float(itm_by.replace(',', '')),
                        'premium': float(premium.replace(',', '')),
                        'expiration': exp.strip()
                    })

    calls_section = re.search(
        r'CALL ACTIVITY ANALYSIS:\s*=+\s*(.*?)\s*DETAILED PUT BREAKDOWN',
        content_str, re.DOTALL
    )

    if calls_section:
        current_ticker = None
        for line in calls_section.group(1).splitlines():
            line = line.strip()
            ticker_match = re.match(r'([A-Z]+)\s*\(Current Price.*\):', line)
            if ticker_match:
                current_ticker = ticker_match.group(1)
                calls_data[current_ticker] = ""
            elif current_ticker and line and not re.match(r'[A-Z]+\s*\(Current Price', line):
                calls_data[current_ticker] += line + " "
        for tk in calls_data:
            calls_data[tk] = calls_data[tk].strip()

    # NEW: EARNINGS TICKERS PARSING
    earnings_tickers_section = re.search(
        r'FINAL QUALIFYING TICKERS WITH CURRENT PRICES with upcoming earnings:\s*=+\s*(.*?)\s*CALL ACTIVITY ANALYSIS with upcoming earnings:',
        content_str, re.DOTALL
    )

    if earnings_tickers_section:
        for line in earnings_tickers_section.group(1).splitlines():
            match = re.match(
                r'([A-Z]+):\s*Current Price \$?([\d,.]+),\s*(\d+)\s*ITM puts,\s*Total Premium \$?([\d,.]+)', line)
            if match:
                ticker, price, num_puts, prem = match.groups()
                earnings_tickers_data[ticker] = {
                    'current_price': float(price.replace(',', '')),
                    'num_puts': int(num_puts),
                    'total_premium': float(prem.replace(',', ''))
                }

    earnings_puts_section = re.search(
        r'DETAILED PUT BREAKDOWN BY TICKER with upcoming earnings:\s*=+\s*(.*?)\s*$',
        content_str, re.DOTALL
    )

    if earnings_puts_section:
        current_ticker = None
        for line in earnings_puts_section.group(1).splitlines():
            line = line.strip()
            ticker_match = re.match(r'([A-Z]+)\s*\(Current Price.*\):', line)
            if ticker_match:
                current_ticker = ticker_match.group(1)
                earnings_puts_data[current_ticker] = []
            elif current_ticker and line.startswith('Put #'):
                put_match = re.match(
                    r'Put #(\d+):\s*Strike \$?([\d,.]+),\s*Spot \$?([\d,.]+),\s*ITM by \$?([\d,.]+),\s*Premium \$?([\d,.]+),\s*Exp:\s*(.+)',
                    line)
                if put_match:
                    idx, strike, spot, itm_by, premium, exp = put_match.groups()
                    earnings_puts_data[current_ticker].append({
                        'put_number': int(idx),
                        'strike': float(strike.replace(',', '')),
                        'spot': float(spot.replace(',', '')),
                        'itm_by': float(itm_by.replace(',', '')),
                        'premium': float(premium.replace(',', '')),
                        'expiration': exp.strip()
                    })

    earnings_calls_section = re.search(
        r'CALL ACTIVITY ANALYSIS with upcoming earnings:\s*=+\s*(.*?)\s*DETAILED PUT BREAKDOWN BY TICKER with upcoming earnings:',
        content_str, re.DOTALL
    )

    if earnings_calls_section:
        current_ticker = None
        for line in earnings_calls_section.group(1).splitlines():
            line = line.strip()
            ticker_match = re.match(r'([A-Z]+)\s*\(Current Price.*\):', line)
            if ticker_match:
                current_ticker = ticker_match.group(1)
                earnings_calls_data[current_ticker] = ""
            elif current_ticker and line and not re.match(r'[A-Z]+\s*\(Current Price', line):
                earnings_calls_data[current_ticker] += line + " "
        for tk in earnings_calls_data:
            earnings_calls_data[tk] = earnings_calls_data[tk].strip()

    return tickers_data, puts_data, calls_data, earnings_tickers_data, earnings_puts_data, earnings_calls_data


def get_all_expiry_dates(puts_data, earnings_puts_data):
    """Extract all unique expiry dates from both normal and earnings puts data"""
    expiry_dates = set()
    for ticker_puts in puts_data.values():
        for put in ticker_puts:
            expiry_dates.add(put['expiration'])

    for ticker_puts in earnings_puts_data.values():
        for put in ticker_puts:
            expiry_dates.add(put['expiration'])

    return sorted(list(expiry_dates))


def filter_by_expiry_dates(puts_data, selected_expiry_dates):
    """Filter puts data by selected expiry dates"""
    if not selected_expiry_dates:
        return puts_data

    filtered_puts = {}
    for ticker, ticker_puts in puts_data.items():
        filtered_ticker_puts = [put for put in ticker_puts if put['expiration'] in selected_expiry_dates]
        if filtered_ticker_puts:
            filtered_puts[ticker] = filtered_ticker_puts
    return filtered_puts


def recalculate_ticker_data_for_filtered_puts(tickers_data, filtered_puts_data):
    """Recalculate ticker summaries based on filtered puts"""
    filtered_tickers_data = {}
    for ticker in filtered_puts_data.keys():
        if ticker in tickers_data:
            ticker_puts = filtered_puts_data[ticker]
            total_premium = sum(put['premium'] for put in ticker_puts)
            filtered_tickers_data[ticker] = {
                'current_price': tickers_data[ticker]['current_price'],
                'num_puts': len(ticker_puts),
                'total_premium': total_premium
            }
    return filtered_tickers_data


def format_currency(value):
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    elif value >= 1e6:
        return f"${value / 1e6:.2f}M"
    elif value >= 1e3:
        return f"${value / 1e3:.2f}K"
    else:
        return f"${value:.2f}"


app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H5("📅 Filter by Put Expiry Dates"),
            dbc.ButtonGroup([
                dbc.Button("All Dates", id="select-all-expiry", color="info", size="sm"),
                dbc.Button("Clear Dates", id="clear-all-expiry", color="secondary", size="sm")
            ], style={'margin-bottom': '5px'}),
            html.Div(
                dcc.Checklist(
                    id='expiry-dates',
                    options=[],
                    value=[],
                    inputStyle={"margin-right": "5px"},
                    labelStyle={"display": "block", "margin-bottom": "4px"}
                ),
                style={
                    "height": "200px",
                    "overflowY": "auto",
                    "border": "1px solid #ddd",
                    "padding": "6px",
                    "borderRadius": "5px",
                    "background": "#f0f8ff",
                    "marginBottom": "15px"
                }
            ),

            html.H5("🎯 Select Tickers"),
            # NEW: Legend for short interest indicator
            html.Div([
                html.Small("⚠️ = High short interest", style={'color': '#ff6b6b', 'fontWeight': 'bold'})
            ], style={'marginBottom': '5px', 'fontSize': '11px'}),

            dbc.ButtonGroup([
                dbc.Button("Normal", id="select-normal", color="primary", size="sm"),
                dbc.Button("Earnings", id="select-earnings", color="success", size="sm"),
                dbc.Button("Clear", id="clear-all", color="secondary", size="sm")
            ], style={'margin-bottom': '5px'}),
            html.Div(
                dcc.Checklist(
                    id='tickers',
                    options=[],
                    value=[],
                    inputStyle={"margin-right": "5px"},
                    labelStyle={"display": "block", "margin-bottom": "4px"}
                ),
                style={
                    "height": "300px",
                    "overflowY": "auto",
                    "border": "1px solid #ddd",
                    "padding": "6px",
                    "borderRadius": "5px",
                    "background": "#fafafa",
                    "marginBottom": "15px"
                }
            ),

            html.H5("📁 Upload Data File"),
            dcc.Upload(
                id='upload-data',
                children=html.Div(
                    ['Drag and Drop or ', html.A('Select a file')],
                    style={'lineHeight': '100px', 'textAlign': 'center'}
                ),
                style={
                    'width': '100%',
                    'height': '100px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'margin-bottom': '10px'
                },
                multiple=False,
                accept=".txt"
            ),
            html.Div(id='upload-status'),

        ], width=3, style={"paddingRight": "10px"}),
        dbc.Col([
            html.H4("📉 Detailed Put Breakdown"),
            html.Div(id='put-breakdown-div', style={
                'height': '600px',
                'overflowY': 'auto',
                'border': '1px solid #ddd',
                'padding': '10px',
                'borderRadius': '5px',
                'backgroundColor': '#fff5f5'
            }),
        ], width=4),
        dbc.Col([
            html.H4("📞 Call Activity Analysis"),
            html.Div(id='call-activity-div', style={
                'height': '600px',
                'overflowY': 'auto',
                'border': '1px solid #ddd',
                'padding': '10px',
                'borderRadius': '5px',
                'backgroundColor': '#f0fff4'
            }),
        ], width=5)
    ])
], fluid=True)


@app.callback(
    [Output('upload-status', 'children'),
     Output('expiry-dates', 'options'),
     Output('expiry-dates', 'value'),
     Output('tickers', 'options'),
     Output('tickers', 'value'),
     Output('put-breakdown-div', 'children'),
     Output('call-activity-div', 'children')],
    [Input('upload-data', 'contents'),
     Input('select-all-expiry', 'n_clicks'),
     Input('clear-all-expiry', 'n_clicks'),
     Input('select-normal', 'n_clicks'),
     Input('select-earnings', 'n_clicks'),
     Input('clear-all', 'n_clicks'),
     Input('expiry-dates', 'value'),
     Input('tickers', 'value')],
    [State('upload-data', 'filename'),
     State('expiry-dates', 'options'),
     State('tickers', 'options')]
)
def update_dashboard(file_contents, select_all_expiry, clear_all_expiry, select_normal, select_earnings, clear_all,
                     selected_expiry_dates, selected_tickers, filename, expiry_options, ticker_options):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    data_str = None
    if file_contents is not None:
        content_type, content_string = file_contents.split(',')
        decoded = base64.b64decode(content_string)
        data_str = decoded.decode('utf-8')
        status_msg = f"File '{filename}' uploaded successfully."
    else:
        try:
            with open("ITM_Analysis_Summary.txt", 'r', encoding='utf-8') as f:
                data_str = f.read()
            status_msg = "Using default ITM_Analysis_Summary.txt file."
        except FileNotFoundError:
            return "No file uploaded and no default file found.", [], [], [], [], "", ""

    tickers_data, puts_data, calls_data, earnings_tickers_data, earnings_puts_data, earnings_calls_data = parse_itm_content(
        data_str)

    all_expiry_dates = get_all_expiry_dates(puts_data, earnings_puts_data)
    expiry_label_options = [{'label': exp_date, 'value': exp_date} for exp_date in all_expiry_dates]

    expiry_values = selected_expiry_dates or []
    if triggered_id == "select-all-expiry":
        expiry_values = all_expiry_dates
    elif triggered_id == "clear-all-expiry":
        expiry_values = []

    if expiry_values:
        filtered_puts_data = filter_by_expiry_dates(puts_data, expiry_values)
        filtered_tickers_data = recalculate_ticker_data_for_filtered_puts(tickers_data, filtered_puts_data)

        filtered_earnings_puts_data = filter_by_expiry_dates(earnings_puts_data, expiry_values)
        filtered_earnings_tickers_data = recalculate_ticker_data_for_filtered_puts(earnings_tickers_data,
                                                                                   filtered_earnings_puts_data)
    else:
        filtered_puts_data = puts_data
        filtered_tickers_data = tickers_data
        filtered_earnings_puts_data = earnings_puts_data
        filtered_earnings_tickers_data = earnings_tickers_data

    # NEW: Create ticker options with short interest indicator
    normal_ticker_options = []
    for tk in sorted(filtered_tickers_data.keys()):
        # Add ⚠️ symbol if ticker is in short interest list
        short_indicator = "⚠️ " if tk in SHORT_INTEREST_TICKERS else ""
        label_text = f"{short_indicator}🔹 {tk} ({filtered_tickers_data[tk]['num_puts']} | {format_currency(filtered_tickers_data[tk]['total_premium'])})"
        normal_ticker_options.append({'label': label_text, 'value': tk})

    earnings_ticker_options = []
    for tk in sorted(filtered_earnings_tickers_data.keys()):
        # Add ⚠️ symbol if ticker is in short interest list
        short_indicator = "⚠️ " if tk in SHORT_INTEREST_TICKERS else ""
        label_text = f"{short_indicator}🏢 {tk} ({filtered_earnings_tickers_data[tk]['num_puts']} | {format_currency(filtered_earnings_tickers_data[tk]['total_premium'])})"
        earnings_ticker_options.append({'label': label_text, 'value': f"earnings_{tk}"})

    all_ticker_options = normal_ticker_options + earnings_ticker_options

    ticker_values = selected_tickers or []
    if triggered_id == "select-normal":
        ticker_values = [opt['value'] for opt in normal_ticker_options]
    elif triggered_id == "select-earnings":
        ticker_values = [opt['value'] for opt in earnings_ticker_options]
    elif triggered_id == "clear-all":
        ticker_values = []

    available_values = [opt['value'] for opt in all_ticker_options]
    ticker_values = [tk for tk in ticker_values if tk in available_values]

    put_children = []
    call_children = []

    for ticker_value in ticker_values:
        if ticker_value.startswith('earnings_'):
            actual_ticker = ticker_value.replace('earnings_', '')
            if actual_ticker in filtered_earnings_puts_data:
                current_price = filtered_earnings_tickers_data[actual_ticker]['current_price']
                total_prem = format_currency(filtered_earnings_tickers_data[actual_ticker]['total_premium'])

                # NEW: Add short interest indicator to header
                short_badge = html.Span(" ⚠️ HIGH SHORT", style={'color': '#ff6b6b', 'fontSize': '12px',
                                                                 'fontWeight': 'bold'}) if actual_ticker in SHORT_INTEREST_TICKERS else ""

                put_header = html.Div([
                    html.H5([f"🏢 {actual_ticker} - Put Options Breakdown (Earnings)", short_badge]),
                    html.P([
                        html.Strong("Current Price: "),
                        f"${current_price:,.2f} | ",
                        html.Strong("Total Puts: "),
                        f"{len(filtered_earnings_puts_data[actual_ticker])} | ",
                        html.Strong("Total Premium: "),
                        total_prem
                    ])
                ], style={'backgroundColor': '#e8f5e9', 'padding': '10px', 'marginBottom': '10px',
                          'border': '2px solid #4caf50'})
                put_children.append(put_header)

                for put in filtered_earnings_puts_data[actual_ticker]:
                    put_children.append(
                        html.Div([
                            html.Strong(f"Put #{put['put_number']} | "),
                            f"Strike: ${put['strike']:,.2f} | ",
                            f"ITM by: ${put['itm_by']:,.2f} | ",
                            f"Premium: {format_currency(put['premium'])} | ",
                            f"Expires: {put['expiration']}"
                        ], style={'backgroundColor': '#f1f8e9', 'padding': '8px', 'marginBottom': '6px'})
                    )

                if actual_ticker in earnings_calls_data:
                    call_text = earnings_calls_data[actual_ticker]
                    call_children.append(
                        html.Div([
                            html.H5([f"🏢 {actual_ticker} - Call Activity Analysis (Earnings)", short_badge]),
                            html.P([
                                html.Strong("Current Price: "),
                                f"${current_price:,.2f}"
                            ]),
                            html.P(call_text)
                        ], style={'backgroundColor': '#e8f5e9', 'padding': '10px', 'marginBottom': '10px',
                                  'border': '2px solid #4caf50'})
                    )
        else:
            if ticker_value in filtered_puts_data:
                current_price = filtered_tickers_data[ticker_value]['current_price']
                total_prem = format_currency(filtered_tickers_data[ticker_value]['total_premium'])

                # NEW: Add short interest indicator to header
                short_badge = html.Span(" ⚠️ HIGH SHORT", style={'color': '#ff6b6b', 'fontSize': '12px',
                                                                 'fontWeight': 'bold'}) if ticker_value in SHORT_INTEREST_TICKERS else ""

                put_header = html.Div([
                    html.H5([f"🔹 {ticker_value} - Put Options Breakdown", short_badge]),
                    html.P([
                        html.Strong("Current Price: "),
                        f"${current_price:,.2f} | ",
                        html.Strong("Total Puts: "),
                        f"{len(filtered_puts_data[ticker_value])} | ",
                        html.Strong("Total Premium: "),
                        total_prem
                    ])
                ], style={'backgroundColor': '#e3f2fd', 'padding': '10px', 'marginBottom': '10px'})
                put_children.append(put_header)

                for put in filtered_puts_data[ticker_value]:
                    put_children.append(
                        html.Div([
                            html.Strong(f"Put #{put['put_number']} | "),
                            f"Strike: ${put['strike']:,.2f} | ",
                            f"ITM by: ${put['itm_by']:,.2f} | ",
                            f"Premium: {format_currency(put['premium'])} | ",
                            f"Expires: {put['expiration']}"
                        ], style={'backgroundColor': '#ffebee', 'padding': '8px', 'marginBottom': '6px'})
                    )

                if ticker_value in calls_data:
                    call_text = calls_data[ticker_value]
                    call_children.append(
                        html.Div([
                            html.H5([f"🔹 {ticker_value} - Call Activity Analysis", short_badge]),
                            html.P([
                                html.Strong("Current Price: "),
                                f"${current_price:,.2f}"
                            ]),
                            html.P(call_text)
                        ], style={'backgroundColor': '#e8f5e9', 'padding': '10px', 'marginBottom': '10px'})
                    )

    return status_msg, expiry_label_options, expiry_values, all_ticker_options, ticker_values, put_children, call_children


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)), debug=False)
