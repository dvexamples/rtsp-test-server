import argparse
import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

class TestMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, codec, width, height, pattern):
        super().__init__()
        self.codec = codec
        self.width = width
        self.height = height
        self.pattern = pattern

    def do_create_element(self, url):
        # Automatically set optimal properties [властивості] for specific patterns
        pattern_props = f"pattern={self.pattern}"
        if self.pattern == "zone-plate":
            pattern_props += " kx2=40 ky2=40 kt=2"
        elif self.pattern == "ball":
            pattern_props += " motion=sweep animation-mode=wall-time"

        # The base video source [відеоджерело] and text overlay [накладання тексту]
        src = f"videotestsrc {pattern_props} is-live=true ! video/x-raw,width={self.width},height={self.height},framerate=30/1"
        overlay = f"! timeoverlay valignment=bottom halignment=left text='{self.codec.upper()} {self.width}x{self.height} - {self.pattern}' font-desc='Sans, 24'"
        
        # Build the pipeline [конвеєр GStreamer] based on the selected codec [кодек]
        if self.codec == "mjpeg":
            pipeline_str = f"( {src} {overlay} ! videoconvert ! jpegenc ! rtpjpegpay name=pay0 pt=26 )"
        elif self.codec == "h264":
            pipeline_str = f"( {src} {overlay} ! videoconvert ! x264enc tune=zerolatency bitrate=2000 speed-preset=ultrafast ! rtph264pay name=pay0 pt=96 )"
        elif self.codec == "h265":
            pipeline_str = f"( {src} {overlay} ! videoconvert ! x265enc tune=zerolatency bitrate=2000 ! rtph265pay name=pay0 pt=96 )"
        else:
            raise ValueError("Unsupported codec")

        return Gst.parse_launch(pipeline_str)

class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, codec, width, height, pattern, port):
        super().__init__()
        # Set dynamic port [динамічний порт]
        self.set_service(str(port))
        factory = TestMediaFactory(codec, width, height, pattern)
        factory.set_shared(True)
        self.get_mount_points().add_factory("/live", factory)
        self.attach(None)

if __name__ == '__main__':
    # Define command-line arguments [аргументи командного рядка]
    parser = argparse.ArgumentParser(description="GStreamer RTSP Test Server for QGroundControl")
    parser.add_argument('--pattern', type=str, default='smpte', 
                        choices=['smpte', 'zone-plate', 'ball', 'snow', 'checkers1', 'blink'],
                        help="The test pattern [тестовий шаблон] to generate")
    parser.add_argument('--res', type=str, default='720p', 
                        choices=['720p', '1024p'],
                        help="Resolution [роздільна здатність] of the video stream")
    parser.add_argument('--codec', type=str, default='h264', 
                        choices=['h264', 'h265', 'mjpeg'],
                        help="Video encoding codec [кодек]")
    parser.add_argument('--port', type=int, default=8554,
                        help="Network port [мережевий порт] to serve RTSP on")

    args = parser.parse_args()

    # Map standard labels to exact width and height
    if args.res == '720p':
        width, height = 1280, 720
    elif args.res == '1024p':
        width, height = 1280, 1024  

    Gst.init(None)
    server = GstServer(args.codec, width, height, args.pattern, args.port)
    
    print("=======================================")
    print(f"RTSP Server active on port: {args.port}")
    print(f"URL: rtsp://<your-ip>:{args.port}/live")
    print(f"Settings: {args.codec.upper()} | {width}x{height} | Pattern: {args.pattern}")
    print("Press Ctrl+C to stop.")
    print("=======================================")
    
    loop = GObject.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping server...")
