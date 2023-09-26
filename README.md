# ImageTransfer-Processor
## Overview

ImageTransfer-Processor is an application dedicated to handling image transfer and processing tasks. At its core, the system is comprised of a server that sends out a video stream and a client that processes this stream to detect objects. The server and client work hand-in-hand using WebRTC facilitated by the aiortc library. Post object detection, the client transmits the coordinates of the detected object back to the server, which then calculates the error based on these coordinates.

## Key Components
1. server.py: This script is responsible for the server-side operations of the media streaming pipeline.

* FrameGenerator class: Generates frames that simulate a moving object to imitate a live video stream.
* VideoStream class: Establishes a WebRTC connection with the client and transmits frames from the FrameGenerator through this connection. It also remains receptive to messages relayed by the client through a data channel.
* Command to run: python3 server.py
2. client.py: This script takes care of the client-side functionalities related to the video processing pipeline.

* FrameProcessor class: Retrieves frames from the server, applies image processing techniques to discern the object in the frame, and dispatches the object's coordinates back to the server via a data channel.
* process_a function: A supplementary function that aids in the extraction of object coordinates from the frame.
* Command to run: python3 client.py
3. test.py: Encompasses unit tests for both server and client aspects of the system.

* Utilizes the uniBest library to construct test cases and simulate objects.
* Enlists tests tailored for FrameGenerator, VideoStream, and FrameProcessor classes, in addition to the process_a function.
* Command to run: pytest test.py

## Dependencies
The application is structured using Python 3.8 and relies on the following libraries:

* aiortc
* numpy
* opencv-python
* asynctest

To install the dependencies, you can use:

```bash
pip install aiortc numpy opencv-python asynctest
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.
