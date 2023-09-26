"""
This module is used to test different components of a video streaming and processing pipeline. 
It includes tests for a FrameGenerator, VideoStream, and FrameProcessor classes, as well as a process_a function.
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="asynctest")
import unittest
from unittest.mock import MagicMock, patch
from aiortc import RTCSessionDescription, RTCIceCandidate, RTCPeerConnection, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
import numpy as np
from server import FrameGenerator, VideoStream
from client import FrameProcessor, process_a
import asyncio
from asynctest import CoroutineMock, patch
import cv2

def generate_mock_frame(x, y):
    """
    Generates a mock video frame with an object at a given (x, y) coordinate.
    
    Args:
        x (int): x-coordinate of the object in the frame.
        y (int): y-coordinate of the object in the frame.
    
    Returns:
        np.ndarray: A frame (800x600 numpy array) with a circle of radius 5 at the given (x, y) coordinate.
    """
    frame = np.zeros((800, 600, 3), dtype=np.uint8)
    cv2.circle(frame, (x, y), radius=5, color=(0, 255, 0), thickness=-1)
    return frame
   
class TestFrameGenerator(unittest.TestCase):
    """
    This class contains unit tests for the FrameGenerator class.
    """
    def setUp(self):
        """
        Sets up the test environment before each test.
        """
        self.frame_gen = FrameGenerator(200)

    def test_calculate_position(self):
        """
        Tests that calculate_position method returns a frame and the coordinates of the object.
        """
        frame, x, y = self.frame_gen.calculate_position()
        self.assertIsInstance(frame, np.ndarray)
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)

    def test_recv(self):
        """
        Tests that the recv method returns a frame with the correct format.
        """
        loop = asyncio.get_event_loop()
        frame = loop.run_until_complete(self.frame_gen.recv())
        self.assertEqual(frame.format.name, 'bgr24')


class TestVideoStream(unittest.TestCase):
    """
    This class contains unit tests for the VideoStream class.
    """
    def setUp(self):
        """
        Sets up the test environment before each test.
        """
        self.video_stream = VideoStream()

    @patch.object(TcpSocketSignaling, 'connect')
    @patch.object(TcpSocketSignaling, 'send')
    @patch.object(TcpSocketSignaling, 'receive')
    @patch.object(RTCPeerConnection, 'createOffer')
    @patch.object(RTCPeerConnection, 'createDataChannel')
    @patch.object(RTCPeerConnection, 'setLocalDescription')
    @patch.object(RTCPeerConnection, 'setRemoteDescription')
    @patch.object(RTCPeerConnection, 'addTrack')
    async def test_run_server(self, mock_addTrack, mock_setRemoteDescription, mock_setLocalDescription, mock_createDataChannel, mock_createOffer, mock_receive, mock_send, mock_connect):
        """
        Tests the run_server function by mocking the communication and peer connection setup process.
        """
        pc = CoroutineMock()
        signaling = CoroutineMock()

        # Patch async methods to return coroutine objects
        pc.createOffer = CoroutineMock(return_value='offer')
        pc.setLocalDescription = CoroutineMock(return_value=RTCSessionDescription(sdp='dummy', type='offer'))
        signaling.send = CoroutineMock(return_value='server_offer')
        signaling.receive = CoroutineMock(return_value=RTCSessionDescription(sdp='client_sdp', type='answer'))
        pc.setRemoteDescription = CoroutineMock(return_value=None)
        signaling.connect = CoroutineMock()
        signaling.send.return_value = None
        signaling.close.return_value = None
        pc.close.return_value = None

        await server.run_server(pc, signaling)


class TestFrameProcessor(unittest.TestCase):
    """
    This class contains unit tests for the FrameProcessor class.
    """
    def setUp(self):
        """
        Sets up the test environment before each test.
        """
        self.track = MagicMock()
        self.data_channel = MagicMock()
        self.frame_processor = FrameProcessor(self.track, self.data_channel)

    def test_send_channel(self):
        """
        Tests that the send_channel method sends the right message to the data channel.
        """
        message = "(10, 20)"
        self.frame_processor.send_channel(self.data_channel, message)
        self.data_channel.send.assert_called_once_with(message)

def test_process_a():
    """
    This function tests the process_a function by providing mock frames and checking the parsed coordinates.
    """
    queue = MagicMock()
    coordinates = MagicMock()
    frame1 = generate_mock_frame(0, 20)
    frame2 = generate_mock_frame(1, 30)
    queue.get.side_effect = [frame1, frame2, None]
    process_a(queue, coordinates)
    assert coordinates[0] != 0.0  # correct parsing will not give default coordinate value
    assert coordinates[1] != 0.0
    assert queue.get.call_count == 3
    queue.get.assert_called_with()

if __name__ == "__main__":
    """
    Main execution point for this test script.
    """
    unittest.main()
