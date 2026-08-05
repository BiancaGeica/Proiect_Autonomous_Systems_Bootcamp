FROM osrf/ros:jazzy-desktop

# joint_state_publisher_gui gives us the leg sliders; the rest (rviz2,
# robot_state_publisher, rclpy) is already in the desktop image.
# Signatures get mangled by the network proxy in this environment, so verify is
# disabled here. Fine for a local viz sandbox; do not copy this to production.
RUN apt-get -o Acquire::AllowInsecureRepositories=true \
            -o Acquire::Check-Valid-Until=false update \
    && apt-get -o APT::Get::AllowUnauthenticated=true install -y --no-install-recommends \
        ros-jazzy-joint-state-publisher-gui \
        ros-jazzy-xacro \
        ros-jazzy-controller-manager \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
        ros-jazzy-gz-ros2-control \
        ros-jazzy-slam-toolbox \
        ros-jazzy-dummy-sensors \
        ros-jazzy-tf2-ros \
        ros-jazzy-nav2-map-server \
        ros-jazzy-nav2-lifecycle-manager \
        ros-jazzy-ros-gz \
        ros-jazzy-ros-gz-sim \
        ros-jazzy-ros-gz-bridge \
        ros-jazzy-ros-gz-interfaces \
        wmctrl x11-utils \
        git \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /ws/src

WORKDIR /ws

RUN git clone https://github.com/G-Levine/pupper_v3_description /ws/src/pupper_v3_description

RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && colcon build --symlink-install"

ENV QT_X11_NO_MITSHM=1
ENTRYPOINT ["/bin/bash", "-lc", "set -e; for f in {/opt/ros/jazzy,/ws/install}/setup.bash; do [ -f \"$f\" ] && source \"$f\"; done; exec \"$@\"", "entrypoint"]
CMD ["bash"]