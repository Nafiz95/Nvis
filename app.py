from flask import Flask, render_template, jsonify, Response
import pandas as pd  # Import pandas
import seaborn as sns
import matplotlib.pyplot as plt
import time
import math

app = Flask(__name__)

@app.route('/')
# @app.route('/heatmap')
def heatmap():
    column_names = ['interval_name', 'interval_begin', 'interval_end', 'keys', 'values']

    # Read the file using read_csv with pipe '|' as the separator
    df = pd.read_csv('lanl_intervals', sep='|', header=None, names=column_names)
    interval_points = sorted(set(df['interval_begin'].tolist() + df['interval_end'].tolist()))

    # Initialize a dictionary to map each interval name to a list, for storing segments it spans
    names_to_segments = {name: [] for name in df['interval_name'].unique()}
    for index, row in df.iterrows():
        interval_name = row['interval_name']
        begin = row['interval_begin']
        end = row['interval_end']
        value = row['values']
        
    #     print(interval_name,begin,end,value)

        for i in range(len(interval_points) - 1):
            segment_start = interval_points[i]
            segment_end = interval_points[i + 1]
            if begin <= segment_end-1 and end >= segment_start:
                # Append the segment tuple to the corresponding list in 'names_to_segments' dictionary
                names_to_segments[interval_name].append((segment_start, segment_end,value))
        
    segment_tuples = sorted(set(sum(names_to_segments.values(), [])), key=lambda x: (x[0], x[1]))
    segment_labels = [f"{start}-{end}" for start, end, val in segment_tuples]
    heatmap_df = pd.DataFrame(0, index=names_to_segments.keys(), columns=segment_labels)

    for interval_name, segments_list in names_to_segments.items():
        for segment in segments_list:
            segment_str = f"{segment[0]}-{segment[1]}"
            heatmap_df.at[interval_name, segment_str] += 1
            
    import numpy as np
    interval_data = {
        name: (list(df.loc[df['interval_name'] == name, 'keys']), list(df.loc[df['interval_name'] == name, 'values']))
        for name in df['interval_name'].unique()
    }



    interval_data = {
    name: (list(df.loc[df['interval_name'] == name, 'keys']), list(df.loc[df['interval_name'] == name, 'values']))
    for name in df['interval_name'].unique()
    }



    data_for_d3 = []
    for interval_name in heatmap_df.index:
        # print(interval_name)  # Optional, for debugging purposes
        keys, values = interval_data[interval_name]  # Fetch pre-filtered keys and values
        
        # Clean up NaNs using list comprehensions
        keys = [k for k in keys if not (isinstance(k, float) and np.isnan(k))]
        values = [v for v in values if not (isinstance(v, float) and np.isnan(v))]

        # Ensure non-empty lists are not replaced with [0]
        keys = keys if keys else [0]
        values = values if values else [0]
        for segment, value in heatmap_df.loc[interval_name].items():
            start, end = segment.split('-')
            # Use pre-cleaned and pre-filtered data
            data_for_d3.append({
                "interval_name": interval_name,
                "segment_start": start,
                "segment_end": end,
                "value": value,
                "keys": keys,
                "values": values
            })
    return render_template('heatmap.html', data=data_for_d3)

# if __name__ == '__main__':
#     app.run(debug=True)

# def display_csv():
#     # Read the CSV file directly into a DataFrame
#     df = pd.read_csv('nfer_log_wCnt.csv')
#     df_viz = df.copy()
#     df_viz.drop(['interval_begin','interval_end','interval_data'], axis=1,inplace=True)

#     grouped_df = df_viz.groupby('interval_name').sum()

#     plt.figure(figsize=(10, 6))
#     sns.heatmap(grouped_df, annot=True, cmap="YlGnBu", linewidths=.5)
#     plt.title('Heatmap of Interval Name by Segments')
#     plt.xlabel('Segments')
#     plt.ylabel('Interval Name')

#     # Save the heatmap to a file
#     plt.savefig('static/heatmap.png')

#     # Optional: Close the plot to free up memory
#     plt.close()
#     time.sleep(5)
#     print('Heatmap Saved')
#     # Pass the DataFrame to the template (ensure to convert DataFrame to HTML if using directly in HTML)
#     # For Jinja template iteration, passing the DataFrame directly
#     return render_template('index.html', data=df)
@app.route('/favicon.ico')
def favicon():
    return Response(status=200)
if __name__ == '__main__':
    app.run(debug=True)
