# Reconstruct the complete fixed_intervalHierarchy.py with all pieces in place

import pandas as pd
from collections import defaultdict
import re

keywords = ['during', 'before']

def load_data(interval_path, event_path, rule_path):
    int_column_names = ['interval_name', 'interval_begin', 'interval_end', 'keys', 'values']
    event_column_names = ['event_id', 'timestamp', 'keys', 'values']
    intervals = pd.read_csv(interval_path, sep='|', header=None, names=int_column_names)
    events = pd.read_csv(event_path, sep='|', header=None, names=event_column_names)

    spec_data = defaultdict(list)
    with open(rule_path, 'r') as file:
        for line in file:
            if ":-" in line:
                interval_name, values = line.split(':-')
                spec_data[interval_name.strip()].append(values.strip())

    events['timestamp'] = events['timestamp'].astype('int64')
    intervals['interval_begin'] = intervals['interval_begin'].astype('int64')
    intervals['interval_end'] = intervals['interval_end'].astype('int64')
    return intervals, events, spec_data


def tokenize_rule(rule, keywords):
    tokens = []
    buffer = ''
    stack = 0
    i = 0
    while i < len(rule):
        c = rule[i]
        if c == '(':
            if stack == 0 and buffer.strip():
                tokens.append(buffer.strip())
                buffer = ''
            stack += 1
            buffer += c
        elif c == ')':
            buffer += c
            stack -= 1
            if stack == 0:
                tokens.append(buffer.strip())
                buffer = ''
        elif stack == 0 and any(rule[i:].startswith(k) for k in keywords):
            if buffer.strip():
                tokens.append(buffer.strip())
                buffer = ''
            for k in keywords:
                if rule[i:].startswith(k):
                    tokens.append(k)
                    i += len(k) - 1
                    break
        else:
            buffer += c
        i += 1
    if buffer.strip():
        tokens.append(buffer.strip())
    return tokens


def check_split_rule_for_subrule(rule, keywords):
    pattern = '|'.join(re.escape(keyword) for keyword in keywords)
    parts = re.split(f'\\s*({pattern})\\s*', rule)
    parts = [part for part in parts if part]
    return parts, 1 if len(parts) > 1 else None


def is_event(element):
    match = re.search(r'event_[\w#]+', element)
    return bool(match), match.group(0) if match else None


def is_interval(element, known_intervals):
    pattern = r'\\b(' + '|'.join(re.escape(interval) for interval in known_intervals) + r')\\b'
    match = re.search(pattern, element)
    return (True, match.group(1)) if match else (False, None)


def get_event_timestamps(events, event_id):
    rows = events[events['event_id'] == event_id]
    return rows['timestamp'].tolist()


def get_interval_instances(intervals, interval_name):
    return intervals[intervals['interval_name'] == interval_name]

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


def validate_syntax(spec_data,i1_id, i1_data, i2_data, i2_id, i_start, i_end, syntax,subruleFlag):
    """
    Validate the relationship between i1 and i2 based on the syntax.
    i1_data and i2_data can be either lists of event timestamps or intervals (DataFrames).
    i_start and i_end represent the main interval's start and end, ensuring that the validation respects those bounds.
    """

    valid_instances = []
    # Case 1: Both i1_data and i2_data are lists of event timestamps
    if isinstance(i1_data, list) and isinstance(i2_data, list):  # Both are events
        
        for i1_time in i1_data:
        
            for i2_time in i2_data:
                if syntax == 'before':
                    # Event 1 must occur before Event 2, and respect the interval bounds
                    if subruleFlag ==True:
                    
                        if i1_time < i2_time and i1_time>=i_start and i2_time<=i_end:
                            valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_time,
                                        'end': i1_time,
                                        'children': None,
                                        'relationship': 'before'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_time,
                                        'end': i2_time,
                                        'children': None
                                    }
                                ]})
                    else:
                        
                        if i1_time < i2_time and i_start == i1_time and i_end == i2_time:
                            valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_time,
                                        'end': i1_time,
                                        'children': None,
                                        'relationship':'before'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_time,
                                        'end': i2_time,
                                        'children': None
                                    }
                                ]})
                # 'during' does not apply to events
                # Add more syntaxes as needed

    # Case 2: i1_data is a list of event timestamps (events), i2_data is an interval (DataFrame)
    elif isinstance(i1_data, list) and isinstance(i2_data, pd.DataFrame):  # i1 is event, i2 is interval
        new_rule = spec_data[i2_id][0]
        for i1_time in i1_data:
            for _, i2_row in i2_data.iterrows():
                i2_start = i2_row['interval_begin']
                i2_end = i2_row['interval_end']

                if syntax == 'before':
                    # Event must occur before the interval starts and respect interval bounds
                    if i1_time < i2_start and i_start == i1_time and i_end == i2_end:
                        valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_time,
                                        'end': i1_time,
                                        'children': None,
                                        'relationship':'before'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_start,
                                        'end': i2_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule, keywords), i2_start, i2_end,subruleFlag=False)
                                    }
                                ]})
                elif syntax == 'during':
                    # Event occurs during the interval, and respect interval bounds
                    if i1_time >= i2_start and i1_time <= i2_end and i_start == i2_start and i_end == i2_end:
                        valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_time,
                                        'end': i1_time,
                                        'children': None,
                                        'relationship':'during'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_start,
                                        'end': i2_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule, keywords), i2_start, i2_end,subruleFlag=False)
                                    }
                                ]})

    # Case 3: i1_data is an interval (DataFrame), i2_data is a list of event timestamps (events)
    elif isinstance(i1_data, pd.DataFrame) and isinstance(i2_data, list):  # i1 is interval, i2 is event
        new_rule = spec_data[i1_id][0]
        for _, i1_row in i1_data.iterrows():
            i1_start = i1_row['interval_begin']
            i1_end = i1_row['interval_end']

            for i2_time in i2_data:
                if syntax == 'before':
                    # Interval must end before the event and respect interval bounds
                    if i1_end < i2_time and i_start == i1_start and i_end == i2_time:
                        valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_start,
                                        'end': i1_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule, keywords), i1_start, i1_end,subruleFlag=False),
                                        'relationship':'before'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_time,
                                        'end': i2_time,
                                        'children': None
                                    }
                                ]})
                elif syntax == 'during':
                    # Event occurs during the interval and respect interval bounds
                    if i2_time >= i1_start and i2_time <= i1_end and i_start == i1_start and i_end == i1_end:
                        valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_start,
                                        'end': i1_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule, keywords), i1_start, i1_end,subruleFlag=False),
                                        'relationship':'during'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_time,
                                        'end': i2_time,
                                        'children': None
                                    }
                                ]})

    # Case 4: Both i1_data and i2_data are intervals (DataFrames)
    elif isinstance(i1_data, pd.DataFrame) and isinstance(i2_data, pd.DataFrame):  # Both are intervals
        new_rule_1 = spec_data[i1_id][0]
        new_rule_2 = spec_data[i2_id][0]
        for _, i1_row in i1_data.iterrows():
            i1_start = i1_row['interval_begin']
            i1_end = i1_row['interval_end']

            for _, i2_row in i2_data.iterrows():
                i2_start = i2_row['interval_begin']
                i2_end = i2_row['interval_end']

                if syntax == 'before':
                    # Interval 1 ends before Interval 2 starts, and respect the interval bounds
                    if i1_end < i2_start and i_start == i1_start and i_end == i2_end:
                        valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_start,
                                        'end': i1_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule_1, keywords), i1_start, i1_end,subruleFlag=False),
                                        'relationship':'before'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_start,
                                        'end': i2_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule_2, keywords), i2_start, i2_end,subruleFlag=False)
                                    }
                                ]})
                elif syntax == 'during':
                    # Interval 1 occurs during Interval 2, and respect the interval bounds
                    if i1_start >= i2_start and i1_end <= i2_end and i_start == i2_start and i_end == i2_end:
                        valid_instances.append({
                                'data': [
                                    {
                                        'id': i1_id,
                                        'start': i1_start,
                                        'end': i1_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule_1, keywords), i1_start, i1_end,subruleFlag=False),
                                        'relationship':'during'
                                    },
                                    {
                                        'id': i2_id,
                                        'start': i2_start,
                                        'end': i2_end,
                                        'children': process_general_rule(split_rule_by_keywords(new_rule_2, keywords), i2_start, i2_end,subruleFlag=False)
                                    }
                                ]})

    return valid_instances if valid_instances else None  # Return valid instances or None



def process_general_rule(rule_tokens, intervals, events, spec_data, interval_begin, interval_end, keywords, subruleFlag=False):
    i1, i2, syntax = None, None, None
    sub_result = None

    for element in rule_tokens:
        sub_tokens, is_sub = check_split_rule_for_subrule(element, keywords)

        if is_sub:
            subruleFlag = True
            sub_result = process_general_rule(
                sub_tokens, intervals, events, spec_data,
                interval_begin, interval_end, keywords, subruleFlag=True
            )
            subruleFlag = False
            continue

        is_evt, evt_id = is_event(element)
        if is_evt:
            evt_timestamps = get_event_timestamps(events, evt_id)
            
            if not evt_timestamps:
                continue
            if len(rule_tokens) == 1:
                return [{'data': {
                    'id': evt_id, 'start': ts, 'end': ts,
                    'children': None
                }} for ts in evt_timestamps if interval_begin <= ts <= interval_end]
            if i1 is None:
                i1 = (evt_id, evt_timestamps)
               
            
            else:
                i2 = (evt_id, evt_timestamps)
               
            # continue

        is_int, int_name = is_interval(element, intervals['interval_name'].unique())

        if is_int:
            int_instances = get_interval_instances(intervals, int_name)
            if int_instances.empty:
                continue
            sub_rule = spec_data.get(int_name, [None])[0]
            if sub_result is not None:
                sub_result.append({
                    'data': [{
                        'id': int_name,
                        'start': interval_begin,
                        'end': interval_end,
                        'children': process_general_rule(
                            tokenize_rule(sub_rule, keywords), intervals, events,
                            spec_data, interval_begin, interval_end, keywords
                        ) if sub_rule else None
                    }]
                })
                return sub_result
            if i1 is None:
                i1 = (int_name, int_instances)
            else:
                i2 = (int_name, int_instances)
            
        if element in ['during','before']:
            syntax = element
        
        if i1 and i2 and syntax:
            i1_id, i1_data = i1
            i2_id, i2_data = i2

            
            return validate_syntax(spec_data,i1_id, i1_data, i2_data, i2_id,
                                   interval_begin, interval_end, syntax, subruleFlag)
    return None


# from anytree import Node, RenderTree

# def build_tree(data, parent=None):
#     if isinstance(data, list):
#         nodes = []
#         for entry in data:
#             nodes.extend(build_tree(entry, parent))
#         return nodes

#     if "data" in data:
#         node_list = []
#         for entry in data["data"]:
#             label = f"{entry['id']} [{entry['start']} - {entry['end']}]"
#             if "relationship" in entry:
#                 label += f" ({entry['relationship']})"
#             node = Node(label, parent=parent)
#             if entry.get("children"):
#                 build_tree(entry["children"], node)
#             node_list.append(node)
#         return node_list



