import socketio
import asyncio
import os
import re
import aiohttp
import json
from aiohttp import web
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
from collections import defaultdict
from interval_hierarchy import *

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'config.json')

with open(config_path, 'r') as config_file:
    config = json.load(config_file)

keywords = ['during', 'before']

# Load the new intervals file (space-separated or pipe-separated)
int_column_names = config["column_names"]
event_column_names = config["event_column_names"]

intervals = pd.read_csv(config["intervals_file_name"], 
                        sep='|', header=None, names=int_column_names)
unique_intervals = intervals['interval_name'].unique().tolist()

# Load the new events file
events = pd.read_csv(config["events_file_name"], sep='|', header=None, names=event_column_names)


# Create sample data
def process_kv(l):
    return l.split(',')

def parse_nfer_file(file_path):
    spec_data = defaultdict(list)
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    for line in lines:
        line = line.strip()
        if ":-" in line:
            interval_name, values = line.split(":-")
            interval_name = interval_name.strip()
            values = values.strip()
            spec_data[interval_name].append(values)
    
    return spec_data

def parse_new_data(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        new_data = []
        for line in lines:
            parts = line.strip().split('|')
            if len(parts) == 2:
                id_part, timestamp_part = parts
                timestamp = int(timestamp_part)
                id_value = id_part.strip()  # Keep the full event name
                new_data.append({
                    "id": id_value,
                    "timestamp": timestamp
                })
        return new_data
    except Exception as e:
        print(f"Error parsing new data: {e}")
        return []

def process_chunk(chunk, segments):
    chunk_names_to_segments = defaultdict(list)
    data_for_d3_chunk = []
    begin_array = chunk['interval_begin'].values
    end_array = chunk['interval_end'].values
    name_array = chunk['interval_name'].values
    keys_array = chunk['keys'].values
    values_array = chunk['values'].values

    for i in range(len(chunk)):
        begin, end, name, key, value = begin_array[i], end_array[i], name_array[i], keys_array[i], values_array[i]
        for start, finish in segments:
            if begin <= finish - 1 and end >= start:
                segment_str = f"{start}-{finish}"
                chunk_names_to_segments[name].append((segment_str, key, value))
    
    # Process segments to create data_for_d3
    for interval_name, segments_info in chunk_names_to_segments.items():
        for segment_info in segments_info:
            segment, key, value = segment_info
            start, end = segment.split('-')

            # Find all keys and values for this segment
            segment_keys = [k for (s, k, v) in segments_info if s == segment]
            segment_values = [v for (s, k, v) in segments_info if s == segment]

            # Clean up NaNs and ensure non-empty lists
            segment_keys = [k for k in segment_keys if k == k]  # NaN check shorthand
            segment_values = [v for v in segment_values if v == v]
            segment_keys = segment_keys if segment_keys else [0]
            segment_values = segment_values if segment_values else [0]

            keys_string = ','.join(str(k) for k in segment_keys) if segment_keys else '0'
            values_string = ','.join(str(v) for v in segment_values) if segment_values else '0'
            
            data_for_d3_chunk.append({
                "interval_name": interval_name,
                "segment_start": start,
                "segment_end": end,
                "value": len(segment_keys),
                "keys": keys_string,
                "values": values_string
            })

    return data_for_d3_chunk

def merge_dicts(dicts):
    return [item for sublist in dicts for item in sublist]

def get_data(request):
    column_names = config["column_names"]

    # Read the file using read_csv with pipe '|' as the separator
    df = pd.read_csv(config["intervals_file_name"], sep='|', header=None, names=column_names)
    interval_points = np.sort(np.unique(df[['interval_begin', 'interval_end']].values.ravel()))

    # Pre-create segments based on interval points (only need to do this once)
    segments = list(zip(interval_points[:-1], interval_points[1:]))

    # Split the DataFrame into chunks
    num_chunks = 10  # You can adjust this number based on your system's capabilities
    chunks = np.array_split(df, num_chunks)

    with concurrent.futures.ProcessPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(process_chunk, chunk, segments) for chunk in chunks]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    # Merge results
    data_for_d3 = merge_dicts(results)

    test = pd.DataFrame(data_for_d3)
    test = test.drop_duplicates(keep='first').reset_index(drop=True)
    test['keys'] = test['keys'].apply(process_kv)
    test['values'] = test['values'].apply(process_kv)

    # don't convert to a dict!!!
    data_for_d3 = test.to_dict(orient='records')
    new_data = parse_new_data(config["events_file_name"])
    spec_data = parse_nfer_file(config["rules_file_name"])

    response_data = {
        "heatmap_data": data_for_d3,
        "event_data": new_data,
        "specification_data": spec_data 
    }
    
    return web.Response(text=json.dumps(response_data), content_type='application/json')


# Async Socket.IO Server
sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

@sio.event
async def connect(sid, environ):
    print("Client connected:", sid)

@sio.event
async def disconnect(sid):
    print("Client disconnected:", sid)

async def index(request):
    with open(config["template_file_path"], 'r') as f:
        return web.Response(text=f.read(), content_type='text/html')

# send no cache header, serve no cache.

def split_rule_by_keywords(rule, keywords):
    # Escape the keywords for use in regex and create a pattern that matches any of the keywords
    pattern = '|'.join(re.escape(keyword) for keyword in keywords)
    
    
    # Use regex to find all parts of the rule based on the keywords
    parts = re.split(f'\\s*({pattern})\\s*', rule)
    
    
    # Filter out empty strings and keep the relevant parts
    parts = [part for part in parts if part]
    # To correctly handle nested parts within parentheses, we will keep track of them
    result = []
    current_part = []

    for part in parts:
        if '(' in part:
            current_part.append(part)
        elif ')' in part:
            current_part.append(part)
            # Join all parts within parentheses and add to result
            result.append(' '.join(current_part))
            current_part = []
        elif current_part:
            current_part.append(part)
        else:
            result.append(part)

    return result


def get_interval_instance_within_segment(intervals_df, interval_name, segment_start, segment_end):
    matching = intervals_df[
        (intervals_df['interval_name'] == interval_name) &
        (intervals_df['interval_begin'] <= segment_end) &
        (intervals_df['interval_end'] >= segment_start)
    ]
    
    if not matching.empty:
        return matching  # or return all if multiple
    else:
        return None


# @sio.event
# async def interval_click(sid, data):
#     # You can process the received data as needed.
#     # For example:
#     # interval_name = data.get("interval_name")
#     # segment_start = data.get("segment_start")
#     # segment_end = data.get("segment_end")
#     # # (Further processing can be done here.)
#     # Select an instance (Adjust index based on dataset)

    

#     # Define rule keywords
    
#     # Retrieve the rule associated with the selected interval
#     # Load the new rule definitions
#     spec_data = defaultdict(list)
#     with open(config["rules_file_name"], 'r') as file:
#         lines = file.readlines()

#     for line in lines:
#         line = line.strip()
#         if ":-" in line:
#             interval_name, values = line.split(":-")
#             interval_name = interval_name.strip()
#             values = values.strip()
#             spec_data[interval_name].append(values)

#     interval_name = data.get("interval_name")
#     segment_start = int(data.get("segment_start"))
#     segment_end = int(data.get("segment_end"))

#     # print(interval_name, interval_begin, interval_end)


#     rule = spec_data.get(interval_name, [""])[0]

    
#     # Process rule
#     split_rules = split_rule_by_keywords(rule, keywords)
#     # print('MAIN RULE:', split_rules)
#     print(f"INTERVAL NAME: {interval_name}, SEGMENT BEGIN: {segment_start}, SEGMENT END: {segment_end}")
#     print("RULE:", split_rules)

#     matching = get_interval_instance_within_segment(intervals, interval_name, segment_start, segment_end)


#     loaded_intervals, loaded_events, loaded_spec_data = load_data(
#     config["intervals_file_name"],
#     config["events_file_name"],
#     config["rules_file_name"]
# )  
#     selected_row = matching.iloc[0]
#     interval_name = selected_row['interval_name']
#     interval_begin = selected_row['interval_begin']
#     interval_end = selected_row['interval_end']

#     rule = spec_data.get(interval_name, [None])[0]

#     if rule:
#         print(f"Rule for interval {interval_name}: {rule}")
#         tokens = tokenize_rule(rule, keywords)
        
#         results = process_general_rule(tokens, loaded_intervals, loaded_events, loaded_spec_data, interval_begin, interval_end, keywords)
#         print(results)

#         # if results:
#         #     for idx, r in enumerate(results):
#         #         print(f"\nTree {idx + 1}:")
#         #         root_nodes = build_tree(r)
#         #         for root in root_nodes:
#         #             for pre, fill, node in RenderTree(root):
#         #                 print(f"{pre}{node.name}")
#         # else:
#         #     print("No valid rule matches found.")
#     else:
#         print(f"No rule found for interval {interval_name}")

#     await sio.emit('rule_result', {
#     'interval': interval_name,
#     'results': results
# })
def get_interval_hierarchy(request):
    interval_name = request.query.get('interval_name')
    segment_start = int(request.query.get('segment_start'))
    segment_end = int(request.query.get('segment_end'))

    matching = get_interval_instance_within_segment(intervals, interval_name, segment_start, segment_end)
    if matching is None:
        return web.Response(text=json.dumps({'error': 'No matching interval found'}), content_type='application/json')

    selected_row = matching.iloc[0]
    interval_begin = selected_row['interval_begin']
    interval_end = selected_row['interval_end']

    spec_data = parse_nfer_file(config["rules_file_name"])
    rule = spec_data.get(interval_name, [None])[0]

    if rule:
        tokens = tokenize_rule(rule, keywords)
        loaded_intervals, loaded_events, loaded_spec_data = load_data(
            config["intervals_file_name"],
            config["events_file_name"],
            config["rules_file_name"]
        )
        results = process_general_rule(tokens, loaded_intervals, loaded_events, loaded_spec_data, interval_begin, interval_end, keywords)
        return web.Response(text=json.dumps({
            'interval': interval_name,
            'results': results
        }, default=str), content_type='application/json')
    else:
        return web.Response(text=json.dumps({'error': 'No rule found for interval'}), content_type='application/json')









    
app.router.add_get('/', index)
app.router.add_get('/data', get_data)
app.router.add_get('/interval_hierarchy', get_interval_hierarchy)


current_directory = os.path.dirname(os.path.abspath(__file__))
static_directory = os.path.join(current_directory, 'static')
app.add_routes([web.static('/static', static_directory)])

if __name__ == '__main__':
    web.run_app(app, port=config["port"])
