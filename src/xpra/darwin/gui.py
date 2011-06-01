# This file is part of Parti.
# Copyright (C) 2010 Nathaniel Smith <njs@pobox.com>
# Parti is released under the terms of the GNU GPL v2, or, at your option, any
# later version. See the file COPYING for details.


class ClipboardProtocolHelper(object):
    def __init__(self, send_packet_cb):
        self.send = send_packet_cb

    def send_all_tokens(self):
        pass

    def process_clipboard_packet(self, packet):
        packet_type = packet[0]
        if packet_type == "clipboard_request":
            (_, request_id, selection, target) = packet
            self.send(["clipboard-contents-none", request_id, selection])

class ClientExtras(object):
    def __init__(self, send_packet_cb):
        self.send = send_packet_cb
        self.setup_macdock()

    def setup_macdock(self):
        print "setup_macdock()"
        self.mac_dock = None
        try:
            import os.path
            import gtk.gdk
            import gtk_osxapplication		#@UnresolvedImport
            self.macapp = gtk_osxapplication.OSXApplication()
            if "XDG_DATA_DIRS" in os.environ:
                filename = os.path.join(os.environ["XDG_DATA_DIRS"], "icons", "xpra.png")
                if os.path.exists(filename):
                    print "setup_macdock() loading icon from %s" % filename
                    pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
                    self.macapp.set_dock_icon_pixbuf(pixbuf)
            self.macapp.connect("NSApplicationBlockTermination", gtk.main_quit)
            self.macapp.ready()
        except Exception, e:
            print "failed to create dock: %s" % e


    def handshake_complete(self, capabilities):
        pass