#!/usr/bin/env python
import os
import random
import re
import shutil
import subprocess
import time


def clear_folder(path):
    directory = path
    files_in_directory = os.listdir(directory)
    mpd_files = [file for file in files_in_directory if file.endswith(".mpd")]
    mp4_files = [file for file in files_in_directory if file.endswith(".mp4")]
    m4s_files = [file for file in files_in_directory if file.endswith(".m4s")]

    for file in mpd_files:
        path_to_file = os.path.join(directory, file)
        os.remove(path_to_file)
    for file in mp4_files:
        path_to_file = os.path.join(directory, file)
        os.remove(path_to_file)
    for file in m4s_files:
        path_to_file = os.path.join(directory, file)
        os.remove(path_to_file)


def fill_cache(buffers_size):
    files_in_directory = os.listdir('./public')
    segments_size = {}
    sum_size = 0.0
    attempts = 0
    transfer_segments = []
    for segment in files_in_directory:
        if segment.endswith('.m4s') and 'audio' not in segment:
            segments_size[segment] = int(os.path.getsize('./public/' + segment)) / 1000000
    segments = list(segments_size.keys())
    while True:
        print('--------------------------------------------')
        rd = random.randint(0, len(segments_size.keys()) - 1)
        current_segment = segments[rd]
        sum_size = sum_size + segments_size[current_segment]
        print('Choose segment --> ' + current_segment + ' with size ' + str(segments_size[current_segment]))
        if sum_size <= buffers_size:
            if current_segment not in transfer_segments:
                print("copy to cache --> " + current_segment + " with total size " + str(sum_size))
                shutil.copy('./public/' + current_segment, './cache')
                transfer_segments.append(current_segment)
            else:
                print('I have already copy file ' + current_segment + ', so I will remove the size')
                sum_size = sum_size - segments_size[current_segment]
        else:
            if attempts == 20:
                print("reached maximum capacity")
                break
            else:
                print('Trying one more time...')
                print()
                sum_size = sum_size - segments_size[current_segment]
                attempts += 1


def copy_all_to_public():
    files_in_directory = os.listdir('./public')
    for file in files_in_directory:
        if file.endswith('.m4s') or file.endswith('.mpd') or file.endswith('mp4'):
            shutil.copy('./public/' + file, './cache')


def kill_all(name, vlc=False):
    if vlc:
        child = subprocess.Popen(["ps aux | grep -i 'vlc'"], stdout=subprocess.PIPE, shell=True)
    else:
        child = subprocess.Popen(["ps aux | grep -i '" + name + "'"], stdout=subprocess.PIPE, shell=True)
    result = child.communicate()[0].decode('utf-8').split('\n')
    for i in result:
        i = re.sub(' +', ' ', i)
        parts = i.split(' ')
        this_name = ''
        if len(parts) < 1:
            continue
        if vlc:
            if len(parts) > 10:
                if 'vlc' in parts[10]:
                    os.system('kill ' + parts[1])
        else:
            for j in parts[10:]:
                this_name = this_name + j + ' '
            if this_name == name + ' ':
                os.system('kill ' + parts[1])


# -------------------------Open terminals and start running experiments-----------------------------
r1_values = [1, 3, 5, 10, 14, 20, 40, 60]
r2_values = [1, 5, 10, 20, 60]
buffer_size = [0, 100, 1000, 3000]
samples = [1, 2, 3]

breaking_point = 3

print('        (r1, r2, L, sample)')
for r1 in r1_values:
    for r2 in r2_values:
        # if r2 <= (r1 / breaking_point) or r2 > (breaking_point * r1):
        #     pass
        # else:
        #     continue
        for L in buffer_size:
            for sample in samples:
                # ----------Clear Local Folder-----------------
                clear_folder("./local")
                # ---------------Clear Cache Folder------------
                clear_folder("./cache")
                # ---------------------------------------------
                if L == 0:
                    pass
                elif L == 3000:
                    copy_all_to_public()
                else:
                    fill_cache(L)
                time.sleep(5)
                print('Running (' + str(r1) + ',' + str(r2) + ', ' + str(L) + ', ' + str(sample) + ')')
                main_command = "python3 main.py -a 127.0.0.4 -p 8004 -s1 127.0.0.4 -p1 8004 -s2 127.0.0.4 -p2 8004 -r " + str(
                    r2)
                proxy_command = "python3 proxy.py -a 127.0.0.3 -p 8003 -s1 127.0.0.4 -p1 8004 -s2 127.0.0.4 -p2 8004 -r1 " + str(
                    r1) + " -r2 " + str(r2) + " -l " + str(L) + " -sample " + str(sample)
                local_command = "python3 local.py -a 127.0.0.2 -p 8002 -s1 127.0.0.3 -p1 8003 -s2 127.0.0.3 -p2 8003"
                client_command = "vlc-wrapper http://127.0.0.2:8002/manifest.mpd"

                main = subprocess.Popen(["gnome-terminal -- " + main_command], cwd='public/', shell=True)
                time.sleep(1)
                proxy = subprocess.Popen(["gnome-terminal -- " + proxy_command], cwd='cache/', shell=True)
                time.sleep(1)
                local = subprocess.Popen(["gnome-terminal -- " + local_command], cwd='local/', shell=True)
                time.sleep(1)
                client = subprocess.Popen(["gnome-terminal -- " + client_command], shell=True)

                counter = 0
                while True:
                    time.sleep(2)
                    file_path = 'cache/output_' + str(float(r1)) + '_' + str(float(r2)) + '_' + str(L) + '_' + str(
                        sample) + '.txt'
                    if os.path.exists(
                            file_path) or counter == 2400:  # if counter reach 1800 it means that 1800*2=3600 seconds passed or 3600 / 60 = 1 hour passed
                        if counter == 2400:
                            print(
                                'Tuple (r1,r2) has errors --> (' + str(r1) + ', ' + str(r2) + ',' + str(L) + ', ' + str(
                                    sample) + ')')
                        elif counter == 0:
                            print('Experiment (' + str(r1) + ', ' + str(r2) + ') already exists in cache')
                            # Proxy output has been completed
                        else:
                            print('Experiment completed')
                        print()
                        time.sleep(1)
                        kill_all(main_command)
                        if counter == 0:
                            kill_all(proxy_command)
                        kill_all(local_command)
                        # kill_all(client_name)
                        kill_all(client_command, vlc=True)
                        time.sleep(2)
                        break
                    counter += 1
