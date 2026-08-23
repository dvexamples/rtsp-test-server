import argparse
import sys
import urllib.parse
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

class DynamicMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self):
        super().__init__()
        self.set_shared(True)

    def do_create_element(self, url):
        # Extract query parameters from the URL safely
        query_string = url.query if hasattr(url, 'query') else None
        params = {}
        if query_string:
            params = dict(urllib.parse.parse_qsl(query_string))

        print(f"Incoming stream request with params: {params}")

        codec = params.get('codec', 'h264')
        res = params.get('res', '720p')
        pattern = params.get('pattern', 'smpte')

        # Validate parameters
        if codec not in ["h264", "h265", "mjpeg"]:
            codec = "h264"
        
        if res == "1024p":
            width, height = 1280, 1024
        else:
            width, height = 1280, 720

        valid_patterns = ['smpte', 'zone-plate', 'ball', 'snow', 'checkers1', 'blink']
        if pattern not in valid_patterns:
            pattern = "smpte"

        pattern_props = f"pattern={pattern}"
        if pattern == "zone-plate":
            pattern_props += " kx2=40 ky2=40 kt=2"
        elif pattern == "ball":
            pattern_props += " motion=sweep animation-mode=wall-time"

        src = f"videotestsrc {pattern_props} is-live=true ! video/x-raw,width={width},height={height},framerate=30/1"
        overlay = f"! timeoverlay valignment=bottom halignment=left text='{codec.upper()} {width}x{height} - {pattern}' font-desc='Sans, 24'"
        
        if codec == "mjpeg":
            pipeline_str = f"( {src} {overlay} ! videoconvert ! jpegenc ! rtpjpegpay name=pay0 pt=26 )"
        elif codec == "h264":
            pipeline_str = f"( {src} {overlay} ! videoconvert ! x264enc tune=zerolatency bitrate=2000 speed-preset=ultrafast ! rtph264pay name=pay0 pt=96 )"
        elif codec == "h265":
            pipeline_str = f"( {src} {overlay} ! videoconvert ! x265enc tune=zerolatency bitrate=2000 ! rtph265pay name=pay0 pt=96 )"
        else:
            raise ValueError(f"Unsupported codec: {codec}")

        print(f"Spawning pipeline -> Codec: {codec}, Resolution: {width}x{height}, Pattern: {pattern}")
        return Gst.parse_launch(pipeline_str)

class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, port):
        super().__init__()
        self.set_service(str(port))
        
        factory = DynamicMediaFactory()
        self.get_mount_points().add_factory("/live", factory)
        self.attach(None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Query-based Dynamic GStreamer RTSP Server")
    parser.add_argument('--port', type=int, default=8554, help="Network port to serve RTSP on")
    args = parser.parse_args()

    Gst.init(None)
    server = GstServer(args.port)
    
    print("==================================================")
    print(f"Dynamic RTSP Server active on port: {args.port}")
    print("Format: rtsp://<server-ip>:<port>/live?codec=<c>&res=<r>&pattern=<p>")
    print("Example: rtsp://<server-ip>:%d/live?codec=h264&res=720p&pattern=blink" % args.port)
    print("==================================================")
    
    loop = GObject.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping server...")
