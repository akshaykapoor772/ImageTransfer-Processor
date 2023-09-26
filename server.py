from aiortc import MediaStreamTrack, RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import cv2
import asyncio
import numpy as np


class FrameGenerator(MediaStreamTrack):
    """
    Generates video frames for streaming.

    Args:
        frame_count (int): Number of frames to generate.

    Attributes:
        kind (str): Type of media stream track ("video").
        radius (int): Radius of the circle.
        screen_dim (tuple): Dimensions of the screen (width, height).
        velocity (list): Velocity of the circle in pixels per frame [x, y].
        position (list): Current position of the circle [x, y].
        color (tuple): Color of the circle (B, G, R).
        frame_array (ndarray): Array representing the current video frame.
        frame_rate (int): Frame rate of the video.
        timestamp (int): Current timestamp of the frame.
    """

    kind = "video"

    def __init__(self, frame_count):
        super().__init__()
        self.radius = 20
        self.screen_dim = (800, 600)
        self.velocity = [10, 21]
        self.position = [self.radius, self.radius]
        self.color = (0, 255, 0)
        self.frame_array = np.zeros((self.screen_dim[1], self.screen_dim[0], 3), dtype=np.uint8)
        self.frame_rate = 60
        self.timestamp = 0

    def calculate_position(self):
        """
        Calculates the position of the circle in the video frame.

        Returns:
            tuple: Tuple containing the updated video frame, and the new x and y coordinates of the circle.
        """
        self.frame_array.fill(0)
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]

        if self.position[0] <= self.radius or self.position[0] >= self.screen_dim[0] - self.radius:
            self.velocity[0] = -self.velocity[0]
            self.position[0] = max(self.radius, min(self.position[0], self.screen_dim[0] - self.radius))

        if self.position[1] <= self.radius or self.position[1] >= self.screen_dim[1] - self.radius:
            self.velocity[1] = -self.velocity[1]
            self.position[1] = max(self.radius, min(self.position[1], self.screen_dim[1] - self.radius))

        cv2.circle(self.frame_array, tuple(np.round(self.position).astype(int)), self.radius, self.color, -1)
        return self.frame_array, self.position[0], self.position[1]

    async def recv(self):
        """
        Receives the next video frame.

        Returns:
            VideoFrame: The next video frame.
        """
        image, self.position[0], self.position[1] = self.calculate_position()
        v_frame = VideoFrame.from_ndarray(image, format='bgr24')
        v_frame.pts = self.timestamp
        v_frame.time_base = f'1/{self.frame_rate}'
        self.timestamp += 1
        return v_frame


class VideoStream:
    """
    Represents a video streaming server.

    Args:
        destination (str): Optional destination for streaming.

    Attributes:
        peer_conn (RTCPeerConnection): RTCPeerConnection object for handling the peer connection.
        socket_sig (TcpSocketSignaling): TcpSocketSignaling object for handling signaling.
        destination (str):Optional destination for streaming.

    Methods:
        signal_handler: Handles signaling messages.
        run_server: Runs the video streaming server.
        initiate_server: Initiates the video streaming server.
    """

    def __init__(self, destination=None):
        self.peer_conn = RTCPeerConnection()
        self.socket_sig = TcpSocketSignaling('0.0.0.0', 1234)
        self.destination = destination

    async def signal_handler(self, connection, signal):
        """
        Handles signaling messages.

        Args:
            connection (RTCPeerConnection): The RTCPeerConnection object.
            signal (TcpSocketSignaling): The TcpSocketSignaling object.
        """
        while True:
            obj = await signal.receive()
            if isinstance(obj, RTCSessionDescription):
                await connection.setRemoteDescription(obj)
                if obj.type == "offer":
                    await connection.setLocalDescription(await connection.createAnswer())
                    await signal.send(connection.localDescription)
            elif isinstance(obj, RTCIceCandidate):
                await connection.addIceCandidate(obj)
            elif obj is None:
                break

    async def run_server(self, connection, signal):
        """
        Runs the video streaming server.

        Args:
            connection (RTCPeerConnection): The RTCPeerConnection object.
            signal (TcpSocketSignaling): The TcpSocketSignaling object.
        """
        await signal.connect()
        data_ch = connection.createDataChannel('channel')
        frame_gen = FrameGenerator(200)
        connection.addTrack(frame_gen)

        @data_ch.on("open")
        def on_open():
            pass

        @data_ch.on("message")
        def on_message(message):
            x_coor, y_coor = eval(message)
            err = np.sqrt((x_coor - frame_gen.position[0])**2 + (y_coor - frame_gen.position[1])**2)
            print(f'Client coordinates:{(x_coor,y_coor)}')
            print(f'Calculated Error:{err}')
            print()

        offer_desc = await connection.createOffer()
        await connection.setLocalDescription(offer_desc)
        await signal.send(connection.localDescription)

        response = await signal.receive()
        print("Server Received Answer")
        await connection.setRemoteDescription(RTCSessionDescription(sdp=response.sdp, type=response.type))

        if not self.destination:
            await self.signal_handler(connection, signal)

    def initiate_server(self):
        """
        Initiates the video streaming server.
        """
        print("Server starting")
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
        try:
            async_loop.run_until_complete(self.run_server(self.peer_conn, self.socket_sig))
        finally:
            async_loop.run_until_complete(self.socket_sig.close())
            async_loop.run_until_complete(self.peer_conn.close())


if __name__ == "__main__":
    video_srv = VideoStream()
    video_srv.initiate_server()
