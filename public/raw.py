import re
import time
import os
import math
import glob
import sys

resolution_to_altitude = {'360': 1, '480': 2, '720': 3, '1080': 4, '1440': 5, '2160': 6}
outputs = []

if len(sys.argv) > 1:
    outputs = [str(sys.argv[1])]
else:
    for q in glob.glob('outputs/*.txt'):
        outputs.append(q[8:])
output_file_number = None
file = open('metrics/all_metrics.csv', 'w')
file.writelines(['Name,r1,r2,L(buffer size),#sample,MOS(resolution),Average Resolution,Sum of Switches,Average Altitude,Average Video Bitrate,'
                 'Mean Network Throughput r1,Mean Network Throughput r2,MOS(stallings),Stallings,'
                 'Total Stalling Time,Mean Stalling Time,Total Network Usage Time,Initial Playback Delay,'
                 'Number of cached bits delivered,Number of non-cached bits delivered,Cache Miss Ratio,'
                 'Cache Hit Ratio,Backhaul traffic ratio\n'])
file.close()
for output_file in outputs:
    if len(sys.argv) > 1:
        output_file_number = re.search('_.*\.txt', output_file).group()
        print(output_file_number)

    file = open('outputs/' + output_file, 'r')
    Lines = file.readlines()

    data_to_csv = []

    pattern = '%Y-%m-%d %H:%M:%S'
    resolution_before = None
    seconds_before = None
    my_lines = []

    manifest_time = 0
    td_1 = 0
    number_of_stallings = 0
    sum_mos_res = 0
    sum_stalling_duration = 0
    sum_size = 0
    sum_bitrate = 0
    sum_resolution = 0
    sum_switches = 0
    sum_cache_hit = 0
    sum_size_cache_hit = 0
    sum_altitude = 0
    time_1st = 0
    time_61st = 0

    for line in Lines:
        if line.startswith('INFO:root:[') and 'audio' not in line:
            if 'manifest.mpd' in line:
                date_time_m = re.search('\[([^.]+)', line).group()[1:]
                manifest_time = int(time.mktime(time.strptime(date_time_m, pattern)))

            if 'video_' in line:
                video_name = line.split(' ')[2]
                date_time = re.search('\[([^.]+)', line).group()[1:]
                resolution = re.search('_.*_', line).group()[1:-1]
                segment = re.search('\_[0-9]*\.', line).group()[1:-1]

                # timestamp in epoch time
                seconds = int(time.mktime(time.strptime(date_time, pattern)))

                if resolution == '360':
                    mos_res = 2.07744
                elif resolution == '480':
                    mos_res = 3.02246
                elif resolution == '720':
                    mos_res = 3.97185
                elif resolution == '1080':
                    mos_res = 4.47112
                elif resolution == '1440':
                    mos_res = 4.52586
                elif resolution == '2160':
                    mos_res = 4.58036

                sum_mos_res += mos_res

                if resolution_before is None:
                    resolution_before = resolution

                if seconds_before is None:
                    seconds_before = seconds
                seconds_diff = seconds - seconds_before
                sum_resolution += int(resolution)
                td_2 = td_1 + seconds_diff - 5

                if segment == '1':
                    time_1st = seconds
                    td_1 = 0
                    td_2 = 0
                if segment == '61':
                    time_61st = seconds

                if td_2 > 0:
                    number_of_stallings += 1
                    stalling = 1
                    stalling_duration = td_2
                    td_1 = 0
                else:
                    stalling = 0
                    stalling_duration = 0
                    td_1 = td_2

                sum_stalling_duration += stalling_duration

                # Size calculation
                size = int(os.path.getsize(video_name))
                sum_size += size

                # Bitrate calculation to bps
                bitrate = (size / 5) * 8
                # to mbps
                bitrate = bitrate / 1000000
                sum_bitrate += bitrate

                # Altitude
                altitude = abs(resolution_to_altitude.get(resolution) - resolution_to_altitude.get(resolution_before))
                sum_altitude += altitude

                switch = 0
                if resolution != resolution_before:
                    switch = 1
                    sum_switches += switch

                # ip = re.search('[0-9]*\.[0-9]*\.[0-9]*\.[0-9]', line).group()
                ip = line.split(' ')[-1].rstrip()
                cache_hit = 0
                if ip == 'HIT':
                    cache_hit = 1
                    sum_cache_hit += 1
                    sum_size_cache_hit += size

                momentary_network_usage = seconds - manifest_time
                momentary_throughput_r1 = ((sum_size * 8) / momentary_network_usage) / 1000000  # Mbps
                momentary_throughput_r2 = (((sum_size - sum_size_cache_hit) * 8) / momentary_network_usage) / 1000000  # Mbps
                if momentary_throughput_r2 == 0.0:
                    r1_divided_by_r2 = 0
                else:
                    r1_divided_by_r2 = momentary_throughput_r1 / momentary_throughput_r2

                print('----------')
                print(line)
                print('video_name', video_name)
                print('CACHE ' + str(ip))
                print('date_time', date_time)
                print('resolution_before', resolution_before)
                print('resolution', resolution)
                print('size', size)
                print('bitrate', bitrate)
                print('segment', segment)
                print('seconds', seconds)
                print('seconds_before', seconds_before)
                print('seconds_diff', seconds_diff)
                print('altitude', altitude)
                print('sum_size', sum_size)
                data_to_csv.append(
                    str(segment) + ', ' + str(resolution) + ', ' + str(switch) + ', ' + str(altitude) + ', ' + str(bitrate) + ', ' + str(cache_hit) + ', ' + str(size) + ', ' + str(stalling) + ', ' + str(mos_res) + ', ' + str(seconds_diff) + ', ' + str(stalling_duration) + ', ' + str(r1_divided_by_r2) + '\n')
                print('----------')

                resolution_before = resolution
                seconds_before = seconds

            my_lines.append(line)

    '''
        METRICS 
    '''

    if time_1st == 0 or time_61st == 0 or manifest_time == 0:
        raise Exception('cant find 1st or 61st segment or manifest.mpd')

    avg_bitrate = sum_bitrate / 61
    avg_altitude = sum_altitude / 61
    avg_resolution = sum_resolution / 61
    avg_mos_res = sum_mos_res / 61
    percentage_cache_hit = (sum_cache_hit / 61) * 100

    percentage_cache_miss = ((61 - sum_cache_hit) / 61) * 100

    sum_size_cache_miss = sum_size - sum_size_cache_hit
    traffic_ratio_percentage = (sum_size_cache_miss / sum_size) * 100
    if number_of_stallings != 0:
        mean_stalling_time = sum_stalling_duration / number_of_stallings
    else:
        mean_stalling_time = 0
    mos_stallings = (3.5 * math.exp((-(0.15 * mean_stalling_time + 0.19)) * number_of_stallings)) + 1.5
    network_usage = time_61st - manifest_time

    throughput_r1 = ((sum_size * 8) / network_usage) / 1000000  # Mbps
    throughput_r2 = ((sum_size_cache_miss * 8) / network_usage) / 1000000  # Mbps

    initial_playback_delay = time_1st - manifest_time

    '''
    write to csv
    '''

    all_metrics = [
        '=============================================================================================================' +
        '\nAverage Resolution                                                                 = ' + str(avg_resolution) +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nSum of Switches                                                                    = ' + str(sum_switches) +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nAverage Altitude                                                                   = ' + str(avg_altitude) +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nAverage Video Bitrate                                                              = ' + str(avg_bitrate) + ' Mbps' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nMean Network Throughput r1 = (non-cached +cached bits) / total network usage time  = ' + str(throughput_r1) + ' Mbps' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nMean Network Throughput r2 = non-cached / total network usage time                 = ' + str(throughput_r2) + ' Mbps' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nMOS (for stallings)                                                                = ' + str(mos_stallings) +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nMOS (for resolutions)                                                              = ' + str(avg_mos_res) +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nStallings                                                                          = ' + str(number_of_stallings) +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nTotal Stalling Time                                                                = ' + str(sum_stalling_duration) + ' seconds' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nMean Stalling Time                                                                 = ' + str(mean_stalling_time) + ' seconds' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nTotal Network Usage Time                                                           = ' + str(network_usage) + ' seconds' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nInitial Playback Delay                                                             = ' + str(initial_playback_delay) + ' seconds' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nNumber of cached bits delivered                                                    = ' + str(sum_size_cache_hit) + ' bits' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nNumber of non-cached bits delivered                                                = ' + str(sum_size_cache_miss) + ' bits' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nCache Miss Ratio                                                                   = ' + str(percentage_cache_miss) + '%' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nCache Hit Ratio                                                                    = ' + str(percentage_cache_hit) + '%' +
        '\n------------------------------------------------------------------------------------------------------------' +
        '\nBackhaul traffic ratio = non cached bits / total size                              = ' + str(traffic_ratio_percentage) + '%' +
        '\n=============================================================================================================']
    file.close()
    if len(sys.argv) > 1:
        file1 = open('metrics/metrics' + output_file_number, "w")
    else:
        file1 = open("metrics/metrics" + str(output_file[6:]), "w")

    file1.writelines(['Segment Number, Resolution, Switch, Altitude, Video Bitrate (Mbps), Cache hit ,Size (Bytes) ,'
                      'Stallings, MOS, Segment Duration, Stalling Duration, R1/R2 \n'] + data_to_csv + all_metrics)
    file1.close()
    with open('metrics/all_metrics.csv', 'a') as fd:
        parts = output_file.split('_')
        fd.write(
            str([output_file,float(parts[1]),float(parts[2]),int(parts[3]),int(parts[4][:-4]), avg_mos_res, avg_resolution,
                 sum_switches, avg_altitude,avg_bitrate, throughput_r1, throughput_r2, mos_stallings,
                 number_of_stallings, sum_stalling_duration, mean_stalling_time, network_usage, initial_playback_delay,
                 sum_size_cache_hit, sum_size_cache_miss, percentage_cache_miss, percentage_cache_hit,
                 traffic_ratio_percentage])[1:-1] + '\n')
