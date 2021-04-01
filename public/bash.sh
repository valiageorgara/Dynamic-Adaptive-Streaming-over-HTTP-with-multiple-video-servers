#!/bin/bash

# THIS SCRIPT CONVERTS EVERY MP4 (IN THE CURRENT FOLDER AND SUBFOLDER) TO A MULTI-BITRATE VIDEO IN MP4-DASH
# For each file "videoname.mp4" it creates a folder "dash_videoname" containing a dash manifest file "stream.mpd" and subfolders containing video segments.


MYDIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
SAVEDIR=$(pwd)

# Check programs
if [ -z "$(which ffmpeg)" ]; then
    echo "Error: ffmpeg is not installed"
    exit 1
fi

if [ -z "$(which MP4Box)" ]; then
    echo "Error: MP4Box is not installed"
    exit 1
fi

cd "$MYDIR"

TARGET_FILES=$(find ./ -maxdepth 1 -type f \( -name "*.mov" -or -name "*.mp4" \))
for f in $TARGET_FILES
do
  fe=$(basename "$f") # fullname of the file
  f="${fe%.*}" # name without extension

  if [ ! -d "${f}" ]; then #if directory does not exist, convert
    echo "Converting \"$f\" to multi-bitrate video in MPEG-DASH"

    ffmpeg -i "${fe}" -c:a copy -vn "${f}_audio.mp4"
    ffmpeg -i "${fe}" -an -c:v libx264 -x264opts 'keyint=30:min-keyint=30:no-scenecut' -b:v 45000k -maxrate 45000k -bufsize 90000k -vf 'scale=-1:2160' "${f}_2160.mp4" -async 1 -vsync 1    
    ffmpeg -i "${fe}" -an -c:v libx264 -x264opts 'keyint=30:min-keyint=30:no-scenecut' -b:v 16000k -maxrate 16000k -bufsize 32000k -vf 'scale=-1:1440' "${f}_1440.mp4" -async 1 -vsync 1
    ffmpeg -i "${fe}" -an -c:v libx264 -x264opts 'keyint=30:min-keyint=30:no-scenecut' -b:v 8000k -maxrate 8000k -bufsize 16000k -vf 'scale=-1:1080' "${f}_1080.mp4" -async 1 -vsync 1
    ffmpeg -i "${fe}" -an -c:v libx264 -x264opts 'keyint=30:min-keyint=30:no-scenecut' -b:v 5000k -maxrate 5000k -bufsize 10000k -vf 'scale=-1:720' "${f}_720.mp4" -async 1 -vsync 1 
    ffmpeg -i "${fe}" -an -c:v libx264 -x264opts 'keyint=30:min-keyint=30:no-scenecut' -b:v 2500k -maxrate 2500k -bufsize 5000k -vf 'scale=-1:478' "${f}_480.mp4" -async 1 -vsync 1
    ffmpeg -i "${fe}" -an -c:v libx264 -x264opts 'keyint=30:min-keyint=30:no-scenecut' -b:v 1000k -maxrate 1000k -bufsize 2000k -vf 'scale=-1:360' "${f}_360.mp4" -async 1 -vsync 1

    rm -f ffmpeg*log*
    # if audio stream does not exist, ignore it
    if [ -e "${f}_audio.mp4" ]; then

       #MP4Box -dash 1000 -rap -frag-rap -bs-switching no -profile "dashavc264:live" "${f}_1080.mp4" "${f}_720.mp4" "${f}_480.mp4" "${f}_360.mp4" "${f}_242.mp4" "${f}_audio.mp4" -out "manifest.mpd"
       MP4Box -dash 5000 -rap -frag-rap -segment-name %s_ "video_2160.mp4" "video_1440.mp4" "video_1080.mp4" "video_720.mp4" "video_480.mp4" "video_360.mp4" "video_audio.mp4" -out "manifest.mpd"
       
    fi
    # create a jpg for poster. Use imagemagick or just save the frame directly from ffmpeg is you don't have cjpeg installed.
    ffmpeg -i "${fe}" -ss 00:00:00 -vframes 1  -qscale:v 10 -n -f image2 - | cjpeg -progressive -quality 75 -outfile "${f}"/"${f}".jpg

    fi

done

cd "$SAVEDIR"
