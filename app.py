from flask import Flask, render_template, jsonify
import pandas as pd  # Import pandas
import seaborn as sns
import matplotlib.pyplot as plt
import time
import math

app = Flask(__name__)

@app.route('/')
def heatmap():
    # Your data loading and processing here...
    column_names = ['interval_name', 'interval_begin', 'interval_end', 'keys', 'values']

    # Read the file using read_csv with pipe '|' as the separator
    df = pd.read_csv('lanl_intervals', sep='|', header=None, names=column_names)

    # The DataFrame 'df' now contains the data from the file with the specified columns

    # Extract unique interval begin and end points and sort them
    interval_points = sorted(set(df['interval_begin'].tolist() + df['interval_end'].tolist()))

    # Initialize a dictionary to hold the mapping of interval names to segments
    names_to_segments = {name: [] for name in df['interval_name'].unique()}

    # Go through each interval and assign it to the segments it spans
    for index, row in df.iterrows():
        interval_name = row['interval_name']
        begin = row['interval_begin']
        end = row['interval_end']
        
        # Find and store the segments that the current interval spans
        for i in range(len(interval_points) - 1):
            segment_start = interval_points[i]
            segment_end = interval_points[i + 1]
            
            # Check if the interval spans this segment
            if begin <= segment_end and end >= segment_start:
                names_to_segments[interval_name].append((segment_start, segment_end))

    # Convert the segments into a string representation
    segment_tuples = sorted(set(sum(names_to_segments.values(), [])))
    segment_labels = [f"{start}-{end}" for start, end in segment_tuples]

    # Create a DataFrame with zeros where rows are intervals and columns are segments
    heatmap_df = pd.DataFrame(0, index=names_to_segments.keys(), columns=segment_labels)
    # Populate the DataFrame with counts
    for interval_name, segments_list in names_to_segments.items():
        for segment in segments_list:
            # Convert the segment tuple to its string representation
            segment_str = f"{segment[0]}-{segment[1]}"
            # Increment the count for the segment that the interval spans
            heatmap_df.at[interval_name, segment_str] += 1
    # print(heatmap_df)
    # Convert DataFrame to a JSON-like format for D3.js
    data_for_d3 = []
    for interval_name in heatmap_df.index:
        for segment, value in heatmap_df.loc[interval_name].items():
            # print(interval_name,segment)
            start, end = segment.split('-')
            keys = list(df[df['interval_name'] == interval_name]['keys'].values)
            i = 0
            while i < len(keys):
                if isinstance(keys[i], float) and math.isnan(keys[i]):
                    keys.pop(i)
                else:
                    i += 1
            
            values = list(df[df['interval_name'] == interval_name]['values'].values)
            i = 0
            while i < len(values):
                if isinstance(values[i], float) and math.isnan(values[i]):
                    values.pop(i)
                else:
                    i += 1

            keys = [0 if len(keys) ==0 else keys]
            values = [0 if len(values) ==0 else values]

            data_for_d3.append({
                "interval_name": interval_name,
                "segment_start": start,
                "segment_end": end,
                "value": value,
                "keys": keys,
                "values": values
            })
    return render_template('heatmap.html', data=data_for_d3)

if __name__ == '__main__':
    app.run(debug=True)
