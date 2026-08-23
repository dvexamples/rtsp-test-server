import argparse
import sys
import re
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

class DynamicMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self):
        super().__init__()
        # Ensure the pipeline is shared if multiple clients connect to the exact same URL,
        # and crucially, ensures resources are released when the last client disconnects.
        self.set_shared(True)

    def do_create_element(self, url):
        # Extract the URI path (e.g., /h264/720p/ball)
        path = url.get_abspath()
        print(f"Incoming stream request for path: {path}")

        # Default fallback parameters
        codec = "h264"
        width, height = 1280, 720
        pattern = "smpte"

        # Parse path using regex: /<codec>/<resolution>/<pattern>
        # Example match: /h264/1024p/zone-plate
        match = re.match(r"^/([a-zA-Z0-9]+)/([a-zA-Z0-9]+)/([a-zA-Z0-9\-_]+)$", path)
        if match:
            c_arg, r_arg, p_arg = match.groups()
            
            if c_arg in ["h264", "h265", "mjpeg"]:
                codec = c_arg
            
            if r_arg == "720p":
                width, height = 1280, 720
            elif r_arg == "1024p":
                width, height = 1280, 1024
            
            valid_patterns = ['smpte', 'zone-plate', 'ball', 'snow', 'checkers1', 'blink']
            if p_arg in valid_patterns:
                pattern = p_arg

        # Configure pattern-specific properties
        pattern_props = f"pattern={pattern}"
        if pattern == "zone-plate":
            pattern_props += " kx2=40 ky2=40 kt=2"
        elif pattern == "ball":
            pattern_props += " motion=sweep animation-mode=wall-time"

        # Build video source and overlay
        src = f"videotestsrc {pattern_props} is-live=true ! video/x-raw,width={width},height={height},framerate=30/1"
        overlay = f"! timeoverlay valignment=bottom halignment=left text='{codec.upper()} {width}x{height} - {pattern}' font-desc='Sans, 24'"
        
        # Build encoding pipeline based on parsed codec
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
        
        # Use a wildcard mount point so ANY subpath (e.g. /h264/720p/ball) hits our dynamic factory
        factory = DynamicMediaFactory()
        self.get_mount_points().add_factory("/*", factory)
        self.attach(None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Dynamic Multi-Stream GStreamer RTSP Server")
    parser.add_argument('--port', type=int, default=8554, help="Network port to serve RTSP on")
    args = parser.parse_args()

    Gst.init(None)
    server = GstServer(args.port)
    
    print("==================================================")
    print(f"Dynamic RTSP Server active on port: {args.port}")
    print("Clients can define streams via URL path structure:")
    print("Format: rtsp://<server-ip>:<port>/<codec>/<resolution>/<pattern>")
    print("Example: rtsp://<server-ip>:%d/h264/720p/ball" % args.port)
    print("Example: rtsp://<server-ip>:%d/mjpeg/1024p/zone-plate" % args.port)
    print("==================================================")
    
    loop = GObject.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping server...")
