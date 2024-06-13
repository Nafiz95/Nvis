import socketio
import aiohttp
import json
from aiohttp import web
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Create sample data
def process_kv(l):
    return l.split(',')

def get_data(request):
    column_names = ['interval_name', 'interval_begin', 'interval_end', 'keys', 'values']

    # Read the file using read_csv with pipe '|' as the separator
    df = pd.read_csv('lanl_intervals', sep='|', header=None, names=column_names)
    interval_points = np.sort(np.unique(df[['interval_begin', 'interval_end']].values.ravel()))

    # Create an efficient mapping from interval points to index to speed up searches
    point_to_index = {point: index for index, point in enumerate(interval_points)}

    # Initialize an empty list to store data for each interval_name efficiently
    from collections import defaultdict
    names_to_segments = defaultdict(list)

    # Use numpy arrays for efficient computation
    begin_array = df['interval_begin'].values
    end_array = df['interval_end'].values
    name_array = df['interval_name'].values
    keys_array = df['keys'].values
    values_array = df['values'].values

    # Pre-create segments based on interval points (only need to do this once)
    segments = list(zip(interval_points[:-1], interval_points[1:]))

                
    for i in range(len(df)):
        begin, end, name, key, value = begin_array[i], end_array[i], name_array[i], keys_array[i], values_array[i]
        for start, finish in segments:
            if begin <= finish - 1 and end >= start:
                segment_str = f"{start}-{finish}"
                # Append a tuple with the segment, keys, and value
                names_to_segments[name].append((segment_str, key, value))

    data_for_d3 = []
    for interval_name, segments_info in names_to_segments.items():
        for segment_info in segments_info:
            segment, key, value = segment_info
            start, end = segment.split('-')

            # Find all keys and values for this segment
            segment_keys = [k for (s, k, v) in segments_info if s == segment]
            segment_values = [v for (s, k, v) in segments_info if s == segment]

            # Clean up NaNs and ensure non-empty lists
            segment_keys = [k for k in segment_keys if not (isinstance(k, float) and np.isnan(k))]
            segment_values = [v for v in segment_values if not (isinstance(v, float) and np.isnan(v))]
            segment_keys = segment_keys if segment_keys else [0]
            segment_values = segment_values if segment_values else [0]
            
            keys_string = ','.join(str(k) for k in segment_keys) if segment_keys else '0'
            values_string = ','.join(str(v) for v in segment_values) if segment_values else '0'
            # Append to data_for_d3
            data_for_d3.append({
                "interval_name": interval_name,
                "segment_start": start,
                "segment_end": end,
                "value": len(segment_keys),  # Summing values if multiple overlap, adjust as needed
                "keys": keys_string,
                "values": values_string
            })
    test = pd.DataFrame(data_for_d3)
    test = test.drop_duplicates(keep='first').reset_index(drop=True)
    test['keys']=test['keys'].apply(process_kv)
    test['values']=test['values'].apply(process_kv)
    data_for_d3 = test.to_dict(orient='records')

    return web.Response(text=json.dumps(data_for_d3), content_type='application/json')


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
    with open('templates/heatmap.html', 'r') as f:
        return web.Response(text=f.read(), content_type='text/html')

app.router.add_get('/', index)
app.router.add_get('/data', get_data)

if __name__ == '__main__':
    web.run_app(app, port=5000)
