import csv
import argparse
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import numpy as np
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os

def parse_csv_to_dict(file_name, skip_rows=0):
    data_dict = {}
    with open(file_name, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        headers = reader.fieldnames
        for header in headers:
            data_dict[header] = []
        
        # Skip the specified number of rows
        for _ in range(skip_rows):
            next(reader, None)

        for row in reader:
            for key, value in row.items():
                data_dict[key].append(try_convert(value))
    return data_dict

def parse_custom_format(file_name, skip_rows=0):
    data_dict = {'TIME': [], 'TEMP': [], 'CAL_72': []}
    with open(file_name, 'r') as file:
        lines = file.readlines()[skip_rows:]
        for line in lines:
            parts = line.split('|')
            for part in parts:
                if 'TEMP?' in part:
                    time_str, temp_str = part.split(';')
                    time = time_str.strip()
                    temp = float(temp_str.split('=')[1].strip())
                    data_dict['TIME'].append(time)
                    data_dict['TEMP'].append(temp)
                elif 'CAL? 72' in part:
                    cal_str = part.split('=')[1].strip()
                    cal = float(cal_str)
                    data_dict['CAL_72'].append(cal)
    return data_dict

def detect_format(file_name):
    with open(file_name, 'r') as file:
        first_line = file.readline()
        if '|' in first_line:
            return 'custom'
        else:
            return 'csv'

def try_convert(value):
    if value is None:
        return value
    try:
        return float(value)
    except ValueError:
        return value

def find_best_tempco(parsed_data):
    x_dates = [datetime.strptime(d, '%d/%m/%Y-%H:%M:%S') for d in parsed_data['TIME']]
    temp_diffs = parsed_data['TEMP'] - np.median(parsed_data['TEMP'][0:2])
    ppm_72 = (parsed_data['CAL_72'] / np.median(parsed_data['CAL_72'][0:2]) - 1) * 1e6
    best_tempco = 0
    min_variance = float('inf')

    for tempco in np.arange(-0.5, 0.5, 0.001):
        corr_72 = ppm_72 + (temp_diffs * tempco)
        trendline = np.poly1d(np.polyfit(mdates.date2num(x_dates), corr_72, 1))(mdates.date2num(x_dates))
        variance = np.var(corr_72 - trendline)
        if variance < min_variance:
            min_variance = variance
            best_tempco = tempco

    return round(best_tempco,4)

def plot_data(parsed_data, save_path, title):
    fig, ax1 = plt.subplots(figsize=(11,9))
    
    # Date formatting for the x-axis
    x_dates = [datetime.strptime(d, '%d/%m/%Y-%H:%M:%S') for d in parsed_data['TIME']]
    ax1.xaxis.set_major_locator(mdates.DayLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d-%H'))
    ax1.xaxis.set_major_locator(MaxNLocator(nbins=25))
    plt.xticks(rotation=45)
    
    # Calculating linear fit for corr_72
    coeffs = np.polyfit(mdates.date2num(x_dates), parsed_data['corr_72'], 1)
    poly = np.poly1d(coeffs)
    trendline = poly(mdates.date2num(x_dates))
    
    # Plotting the data
    ax1.plot(x_dates, parsed_data['TEMP'], marker='x', color='purple', fillstyle='none', label='Temperature')
    ax1.set_ylim(15,np.max(parsed_data['TEMP'])+2)
    ax1.set_ylabel('Temperature [°C]')
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    ax2 = ax1.twinx()
    ax2.scatter(x_dates, parsed_data['ppm_72'], marker='o', color='gray', facecolors='none', label='PPM 72')
    ax2.plot(x_dates, parsed_data['corr_72'], marker='^', color='green', label='Corrected PPM 72')
    ax2.plot(x_dates, trendline, color='orange', linestyle='--', label='Trend Line')
    ax2.set_ylim(np.min(parsed_data['ppm_72'])-0.5,np.max(parsed_data['ppm_72'])+0.5)
    ax2.set_ylabel('Deviation from first 3 ACALs [µV/V]')
    
        
    # Adding drift calculations
    one_day_drift = coeffs[0] * 1  # coeffs[0] gives us slope (change per day)
    one_year_drift = coeffs[0] * 365
    textstr = f"24 Hour Drift: {one_day_drift:.6f} ppm/day\n1 Year Drift estimate: {one_year_drift:.2f} ppm/year\n{parsed_data['tempco']} ppm/K TC Gain correction"
    ax1.text(0.05, 0.15, textstr, transform=ax1.transAxes, fontsize=9,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Styling and saving the plot
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.savefig(save_path, dpi=300)  # Save the figure
    plt.title(title)
    plt.show()
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Parse CSV file into a dictionary and generate plots')
    parser.add_argument('file_name', type=str, help='The CSV file to be parsed')
    parser.add_argument('--skip_rows', type=int, default=0, help='Number of rows to skip from the start of the CSV file')
    parser.add_argument('--tempco', type=float, default=0, help='Manual temperature coefficient')
    parser.add_argument('--auto_tempco', action='store_true', help='Automatically find the best temperature coefficient')
    parser.add_argument('--monitor', action='store_true', help='Monitor the file for changes and re-plot on changes')
    parser.add_argument('--save_path', type=str, default='sn18_plot.png', help='Path to save the plot image')
    args = parser.parse_args()
    
    file_format = detect_format(args.file_name)
    print(file_format)
    if file_format == 'csv':
        parsed_data = parse_csv_to_dict(args.file_name, skip_rows=args.skip_rows)
    else:
        parsed_data = parse_custom_format(args.file_name, skip_rows=args.skip_rows)
    
    for key in parsed_data:
        parsed_data[key] = np.array(parsed_data[key])

    tempco = args.tempco
    if args.auto_tempco:
        tempco = find_best_tempco(parsed_data)
    
    temp_diff = parsed_data['TEMP'] - parsed_data['TEMP'][0]
    temp_diff = parsed_data['TEMP'] - np.median(parsed_data['TEMP'][0:2])
    ppm_72 = (parsed_data['CAL_72'] / np.median(parsed_data['CAL_72'][0:2]) - 1) * 1e6
    corr_72 = ppm_72 + (temp_diff * tempco)
    parsed_data['ppm_72'] = ppm_72
    parsed_data['corr_72'] = corr_72
    parsed_data['tempco'] = tempco
    print(args.file_name)
    plot_data(parsed_data, args.save_path, os.path.splitext(os.path.basename(args.file_name))[0].replace('_',' '))

    if args.monitor:
        monitor_file(args.file_name)

class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".csv"):
            print(f"Detected change in file: {event.src_path}")
            main()  # Call main function to parse data and regenerate plot

def monitor_file(file_path):
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=file_path, recursive=False)
    observer.start()
    print(f"Watching for changes in {file_path}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()

