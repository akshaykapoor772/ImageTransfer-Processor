import asyncio
import cv2
from aiortc import MediaStreamTrack, RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import TcpSocketSignaling
import numpy as np
import multiprocessing


class FrameProcessor(MediaStreamTrack):
    """
    Processes video frames received from a track.

    Args:
        track (MediaStreamTrack): The media stream track for video frames.
        datachannel (DataChannel): The data channel for sending coordinate information.

    Attributes:
        kind (str): Type of media stream track ("video").
        track (MediaStreamTrack): The media stream track for video frames.
        queue (multiprocessing.Queue): A multiprocessing queue for storing video frames.
        coordinates (multiprocessing.Array): Shared memory for storing the coordinates of the object in the frame.
        datachannel (DataChannel): The data channel for sending coordinate information.
    """

    kind = "video"

    def __init__(self, track, datachannel=None):
        super().__init__()
        self.track = track
        self.queue = multiprocessing.Queue()
        self.coordinates = multiprocessing.Array('d', 2)
        self.coordinates[0], self.coordinates[1] = 0.0, 0.0
        self.datachannel = datachannel

    async def recv(self):
        """
        Receives video frames from the track and processes them.

        Returns:
            VideoFrame: The received video frame.
        """
        while True:
            frame = await self.track.recv()
            if frame is not None:
                self.queue.put(frame.to_ndarray(format='rgb24'))
                with self.coordinates.get_lock():
                    x, y = self.coordinates[0], self.coordinates[1]
                    self.send_channel(self.datachannel, str((x, y)))

                img = frame.to_ndarray(format="bgr24")
                cv2.imshow('Bouncing Ball', img)
                if cv2.waitKey(1) & 0xFF == ord('q'):  # Close window when 'q' key is pressed
                    break
                await asyncio.sleep(0.5)

            else:
                self.queue.put(None)
        plt.close()

    def send_channel(self, channel, message):
        """
        Sends a message through the data channel.

        Args:
            channel (DataChannel): The data channel.
            message (str): The message to be sent.
        """
        full_message = "Coordinates (x, y): " + message
        print(full_message)
        channel.send(message)


def process_a(queue, coordinates):
    """
    Processes video frames by extracting the coordinates of the object.

    Args:
        queue (multiprocessing.Queue): The queue containing video frames.
        coordinates (multiprocessing.Array): Shared memory for storing the coordinates.
    """
    while True:
        frame = queue.get()
        if frame is None:
            break
        x, y = parse_frame(frame)
        with coordinates.get_lock():
            coordinates[0], coordinates[1] = x, y


def parse_frame(frame):
    """
    Extracts the coordinates of the object in the video frame.

    Args:
        frame (ndarray): The video frame.

    Returns:
        tuple: The x and y coordinates of the object.
    """
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])

    hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_image, lower_green, upper_green)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_contour = max(contours, key=cv2.contourArea)
    ((center_x, center_y), radius) = cv2.minEnclosingCircle(largest_contour)

    return int(center_x), int(center_y)


class MediaClient:
    """
    Represents a media client for video streaming.

    Args:
        timeout (bool): Indicates whether to include a timeout for consuming signaling messages.

    Attributes:
        pc (RTCPeerConnection): The RTCPeerConnection object for handling the peer connection.
        signaling (TcpSocketSignaling): The TcpSocketSignaling object for handling signaling.
        timeout (bool): Indicates whether to include a timeout for consuming signaling messages.

    Methods:
        consume_signaling: Consumes signaling messages.
        operate_client: Operates the media client.
        client_startup: Starts the media client.
    """

    def __init__(self, timeout=False):
        self.pc = RTCPeerConnection()
        self.signaling = TcpSocketSignaling('0.0.0.0', 1234)
        self.timeout = timeout

    async def consume_signaling(self, pc, signaling):
        """
        Consumes signaling messages.

        Args:
            pc (RTCPeerConnection): The RTCPeerConnection object.
            signaling (TcpSocketSignaling): The TcpSocketSignaling object.
        """
        while True:
            obj = await signaling.receive()

            if isinstance(obj, RTCSessionDescription):
                await pc.setRemoteDescription(obj)

                if obj.type == "offer":
                    await pc.setLocalDescription(await pc.createAnswer())
                    await signaling.send(pc.localDescription)
            elif isinstance(obj, RTCIceCandidate):
                await pc.addIceCandidate(obj)
            elif obj is None:
                break

    async def operate_client(self, pc, signaling):
        """
        Operates the media client.

        Args:
            pc (RTCPeerConnection): The RTCPeerConnection object.
            signaling (TcpSocketSignaling): The TcpSocketSignaling object.
        """
        await self.signaling.connect()

        @pc.on("track")
        async def on_track(track):
            print("Track received %s" % track.kind)

            @pc.on("datachannel")
            async def on_channel(channel):
                local_track = FrameProcessor(track, channel)
                process_a_instance = multiprocessing.Process(target=process_a, args=(local_track.queue, local_track.coordinates))
                process_a_instance.start()
                await local_track.recv()
                local_track.queue.put(None)
                process_a_instance.join()

        # Receiving server offer
        server_offer = await signaling.receive()
        await pc.setRemoteDescription(RTCSessionDescription(sdp=server_offer.sdp, type=server_offer.type))
        print('OFFER RECEIVED')

        # Sending client answer
        client_answer = await pc.createAnswer()
        await pc.setLocalDescription(client_answer)
        await signaling.send(pc.localDescription)

        if not self.timeout:
            await self.consume_signaling(pc, signaling)

    def client_startup(self):
        """
        Starts the media client.
        """
        print("Starting client")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.operate_client(self.pc, self.signaling))
        finally:
            loop.run_until_complete(self.signaling.close())
            loop.run_until_complete(self.pc.close())
            print('Exiting client')


if __name__ == "__main__":
    clientApp = MediaClient()
    clientApp.client_startup()
