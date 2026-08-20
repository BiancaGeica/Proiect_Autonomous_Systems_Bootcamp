#!/usr/bin/env bash
# Launch the CS123 Lab 2 RViz viz-only mock inside Docker.
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Allow the container to talk to the host X server.
xhost +local:root >/dev/null

IT=""
[ -t 0 ] && IT="-it"

# Cautare automata a repository-ului de alarma termica
# in cazul in care nu exista apare un warning si se ruleaza fara harta termica.
# Cautam inteligent sistemul de alarma oriunde in calculatorul userului
ALARM_DIR=$(find "$HOME" -type d -name "pupper-alarm-system" 2>/dev/null | head -n 1)

ALARM_MOUNT=""
if [ -n "$ALARM_DIR" ]; then
    echo -e "\e[32m[INFO] Am gasit sistemul de alarma la: $ALARM_DIR\e[0m"
    ALARM_MOUNT="-v $ALARM_DIR:/alarm"
else
    echo -e "\e[33m[WARNING] Sistemul de alarma termica nu a fost gasit!\e[0m"
    echo -e "\e[33mPentru a avea acces la harta termica, te rugam sa clonezi repo-ul:\e[0m"
    echo -e "\e[33mhttps://github.com/Horiqq7/pupper-alarm-system\e[0m"
    echo ""
fi

# --ulimit core=0: a crashing ros2_control_node otherwise leaves multi-GB
# core files in ws/ (the container inherits the host's core pattern).
if [[ $1 == "1" ]]; then
    docker run --rm $IT \
        --net=host \
        --ulimit core=0 \
        -e DISPLAY="$DISPLAY" \
        -e QT_X11_NO_MITSHM=1 \
        -e LIBGL_ALWAYS_SOFTWARE=1 \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v "$HERE":/work \
                $ALARM_MOUNT \
        pupper_viz \
            ros2 launch /work/proiect_gazebo.launch.py
else
    docker run --rm $IT \
        --net=host \
        --ulimit core=0 \
        -e DISPLAY="$DISPLAY" \
        -e QT_X11_NO_MITSHM=1 \
        -e LIBGL_ALWAYS_SOFTWARE=1 \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v "$HERE":/work \
                $ALARM_MOUNT \
        pupper_viz \
            ros2 launch /work/proiect.launch.py
fi

