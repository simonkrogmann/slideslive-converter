#!/usr/bin/python3
import json
import sys
import subprocess
import os

# ----------------- SETTINGS----------------------------

# coordinates of the empty spot on the slides where the speaker video should go
# measured from top left
speaker_vid_x = 1440 - 54
speaker_vid_y = 131 + 54
# height is determined automatically
speaker_vid_width = 480
output_file = 'result.mp4'

# my slides were recorded on a screen with resolution 1920 x 1200,
# so we want to remove the black bars
# set to 0 for a screen with 1920 x 1080
black_bar_on_top_height = 60

# ------------------------------------------------------


def get_input_flags(video, file_dict):
    vid_id = video['clip']['file_id']
    inpoint = video['clip']['in_cut_ms']
    duration = video['clip']['duration_ms']
    outpoint = inpoint + duration
    vid_file = file_dict[vid_id]
    return ['-ss', f'{inpoint}ms', '-to', f'{outpoint}ms', '-i', vid_file]


def main():
    if len(sys.argv) < 2:
        print("Use the folder of the extracted zip file as the first argument")
        sys.exit(1)
    folder = sys.argv[1]
    for file in os.listdir(folder):
        if file.endswith('.json'):
            json_filename = os.path.join(folder, file)
            break
    print(json_filename)
    with open(json_filename, 'r') as json_file:
        data = json.load(json_file)
    slide_vids = data['timelines']['slides']['video']
    speaker_vids = data['timelines']['speaker']['video']

    file_dict = {}
    for file in data['files']:
        file_dict[file['id']] = file['file_name']

    call = ['ffmpeg', '-y']
    for vid in speaker_vids + slide_vids:
        call += get_input_flags(vid, file_dict)

    # prepare the index string of the videos for ffmpeg
    speaker_vids_ffmpeg = ''.join(f'[{i}:v:0][{i}:a:0]' for i in range(len(speaker_vids)))
    slide_vids_ffmpeg = ''.join(f'[{i+len(speaker_vids)}:v:0]' for i in range(len(slide_vids)))

    # concat speaker videos and audios
    command = f'{speaker_vids_ffmpeg}concat=n={len(speaker_vids)}:v=1:a=1[speaker][audio];'
    # concat slides videos
    command += f'{slide_vids_ffmpeg}concat=n={len(slide_vids)}:v=1:a=0[slides];'
    # crop black bars
    command += f'[slides]crop=1920:1080:0:{black_bar_on_top_height} [crop];'
    # make speaker video smaller
    command += f'[speaker]scale={speaker_vid_width}:-1 [small];'
    # put speaker video as overlay on slides
    command += f'[crop][small]overlay={speaker_vid_x}:{speaker_vid_y}:[video]'

    call += ['-filter_complex', command, '-map', '[video]', '-map', '[audio]',
             '-c:v', 'libx264', '-avoid_negative_ts', 'make_zero',
             '-vsync', 'vfr', output_file]

    subprocess.call(call, cwd=folder)


if __name__ == '__main__':
    main()
