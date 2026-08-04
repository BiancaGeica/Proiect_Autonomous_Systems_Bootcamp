#!/usr/bin/env bash
# Launch the CS123 Lab 2 RViz viz-only mock inside Docker.
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Allow the container to talk to the host X server.
xhost +local:root >/dev/null

IT=""
[ -t 0 ] && IT="-it"


# --ulimit core=0: a crashing ros2_control_node otherwise leaves multi-GB
# core files in ws/ (the container inherits the host's core pattern).
if [[ $1 == "1" ]]; then
    docker run --rm $IT \
        --net=host \
        --ulimit core=0 \
        -e DISPLAY="$DISPLAY" \
        -e QT_X11_NO_MITSHM=1 \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v "$HERE":/work \
        pupper_viz \
            ros2 launch /work/proiect_gazebo.launch.py
else
    docker run --rm $IT \
        --net=host \
        --ulimit core=0 \
        -e DISPLAY="$DISPLAY" \
        -e QT_X11_NO_MITSHM=1 \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v "$HERE":/work \
        pupper_viz \
            ros2 launch /work/proiect.launch.py
fi

