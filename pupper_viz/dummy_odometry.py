import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


class DummyOdometry(Node):
    def __init__(self):
        super().__init__('dummy_odometry')

        # Starea robotului (x, y, yaw/theta)
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0

        # Vitezele curente primite de la /cmd_vel
        self.vx = 0.0
        self.vy = 0.0
        self.vth = 0.0

        self.last_time = self.get_clock().now()

        # Subscriber pentru viteze
        self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        # Broadcaster TF pentru odom -> base_link
        self.tf_broadcaster = TransformBroadcaster(self)

        # Publisher opțional pentru /odom
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)

        # Timer pentru actualizare la 30 Hz
        self.create_timer(1.0 / 30.0, self.update_odometry)

        self.get_logger().info("Nodul Dummy Odometry a pornit! Ascultă pe /cmd_vel...")

    def cmd_vel_callback(self, msg: Twist):
        self.vx = msg.linear.x
        self.vy = msg.linear.y
        self.vth = msg.angular.z

    def update_odometry(self):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time

        # Integrăm vitezele pentru a obține poziția nouă (Model Omnidirecțional / Holonomic)
        delta_x = (self.vx * math.cos(self.th) - self.vy * math.sin(self.th)) * dt
        delta_y = (self.vx * math.sin(self.th) + self.vy * math.cos(self.th)) * dt
        delta_th = self.vth * dt

        self.x += delta_x
        self.y += delta_y
        self.th += delta_th

        # Calculăm Cuaternionul pentru rotația 2D
        q_z = math.sin(self.th / 2.0)
        q_w = math.cos(self.th / 2.0)

        # 1. Publicăm Transformarea TF: odom -> base_link
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'

        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0

        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = q_z
        t.transform.rotation.w = q_w

        self.tf_broadcaster.sendTransform(t)

        # 2. Publicăm mesajul /odom
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_link'

        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.orientation.z = q_z
        odom_msg.pose.pose.orientation.w = q_w

        odom_msg.twist.twist.linear.x = self.vx
        odom_msg.twist.twist.linear.y = self.vy
        odom_msg.twist.twist.angular.z = self.vth

        self.odom_pub.publish(odom_msg)


def main(args=None):
    rclpy.init(args=args)
    node = DummyOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()