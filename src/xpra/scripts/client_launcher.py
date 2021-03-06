# This file is part of Parti.
# Copyright (C) 2009-2012 Antoine Martin <antoine@nagafix.co.uk>
# Parti is released under the terms of the GNU GPL v2, or, at your option, any
# later version. See the file COPYING for details.

""" client_launcher.py

This is a simple GUI for starting the xpra client.

"""

import sys
import os.path
import thread
import subprocess

import pygtk
pygtk.require('2.0')
import gtk
import pango
import gobject

import socket
from xpra.client import XpraClient


""" Start of crappy platform workarounds """
SUBPROCESS_CREATION_FLAGS = 0
if sys.platform.startswith("win"):
	try:
		import win32process			#@UnresolvedImport
		SUBPROCESS_CREATION_FLAGS = win32process.CREATE_NO_WINDOW
	except:
		pass		#tried our best...

	if getattr(sys, 'frozen', ''):
		#on win32 we must send stdout to a logfile to prevent an alert box on exit shown by py2exe
		#UAC in vista onwards will not allow us to write where the software is installed, so place the log file in "~/Application Data"
		appdata = os.environ.get("APPDATA")
		if not os.path.exists(appdata):
			os.mkdir(appdata)
		log_path = os.path.join(appdata, "Xpra")
		if not os.path.exists(log_path):
			os.mkdir(log_path)
		log_file = os.path.join(log_path, "Xpra.log")
		sys.stdout = open(log_file, "a")
		sys.stderr = sys.stdout


LOSSLESS = "lossless (best)"
LOSSY_5 = "lowest quality"
LOSSY_20 = "low quality"
LOSSY_50 = "average quality"
LOSSY_90 = "best lossy quality"

XPRA_COMPRESSION_OPTIONS = [LOSSLESS, LOSSY_5, LOSSY_20, LOSSY_50, LOSSY_90]
XPRA_COMPRESSION_OPTIONS_DICT = {LOSSLESS : None,
						LOSSY_5 : 5,
						LOSSY_20 : 20,
						LOSSY_50 : 50,
						LOSSY_90 : 90
						}

class ApplicationWindow:

	def	__init__(self):
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("destroy", self.destroy)
		self.window.set_default_size(400, 300)
		self.window.set_border_width(20)

		# Title
		vbox = gtk.VBox(False, 0)
		vbox.set_spacing(15)
		label = gtk.Label("Connect to xpra server")
		label.modify_font(pango.FontDescription("sans 13"))
		vbox.pack_start(label)
		
		# Mode:
		hbox = gtk.HBox(False, 20)
		hbox.set_spacing(20)
		hbox.pack_start(gtk.Label("Mode: "))
		self.mode_combo = gtk.combo_box_new_text()
		self.mode_combo.get_model().clear()
		for option in ["tcp", "ssh"]:
			self.mode_combo.append_text(option)
		self.mode_combo.set_active(0)
		hbox.pack_start(self.mode_combo)
		vbox.pack_start(hbox)
		
		# JPEG:
		hbox = gtk.HBox(False, 20)
		hbox.set_spacing(20)
		hbox.pack_start(gtk.Label("JPEG Compression: "))
		self.jpeg_combo = gtk.combo_box_new_text()
		self.jpeg_combo.get_model().clear()
		for option in XPRA_COMPRESSION_OPTIONS:
			self.jpeg_combo.append_text(option)
		self.jpeg_combo.set_active(0)
		hbox.pack_start(self.jpeg_combo)
		vbox.pack_start(hbox)

		# Host:Port		
		hbox = gtk.HBox(False, 0)
		hbox.set_spacing(5)
		self.host_entry = gtk.Entry(max=128)
		self.host_entry.set_width_chars(40)
		if len(sys.argv)>1:
			self.host_entry.set_text(sys.argv[1])
		else:
			self.host_entry.set_text("127.0.0.1")
		self.port_entry = gtk.Entry(max=5)
		self.port_entry.set_width_chars(5)
		if len(sys.argv)>2:
			self.port_entry.set_text(sys.argv[2])
		else:
			self.port_entry.set_text("16010")
		hbox.pack_start(self.host_entry)
		hbox.pack_start(gtk.Label(":"))
		hbox.pack_start(self.port_entry)
		vbox.pack_start(hbox)
		
		# Info Label
		self.info = gtk.Label()
		self.info.set_line_wrap(True)
		self.info.set_size_request(360, -1)
		vbox.pack_start(self.info)
		
		# Connect button:
		self.button = gtk.Button("Connect")
		self.button.connect("clicked", self.connect_clicked, None)
		vbox.pack_start(self.button)

		self.window.add(vbox)
		self.window.show_all()
	
	def connect_tcp(self):
		self.info.set_text("Connecting.")
		host = self.host_entry.get_text()
		port = self.port_entry.get_text()
		self.info.set_text("Connecting..")
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.info.set_text("Connecting...")
			sock.connect((host, int(port)))
		except Exception, e:
			self.info.set_text("Socket error: %s" % e)
			return
		self.info.set_text("Connection established")
		try:
			from xpra.protocol import SocketConnection
			global socket_wrapper
			socket_wrapper = SocketConnection(sock)
		except Exception, e:
			self.info.set_text("Xpra Client error: %s" % e)
			return
		self.window.hide()
		# launch Xpra client in the same gtk.main():
		from wimpiggy.util import gtk_main_quit_on_fatal_exceptions_enable, AdHocStruct
		gtk_main_quit_on_fatal_exceptions_enable()
		opts = AdHocStruct()
		opts.clipboard = True
		opts.pulseaudio = True
		opts.password_file = None
		opts.title_suffix = None
		opts.title = "@title@ on @client-machine@"
		opts.encoding = "rgb24"
		opts.jpegquality = 80
		opts.max_bandwidth = 0.0
		opts.auto_refresh_delay = 0.0
		opts.key_shortcuts = []
		opts.compression_level = 3
		from xpra.platform import DEFAULT_SSH_CMD
		opts.ssh = DEFAULT_SSH_CMD
		opts.remote_xpra = ".xpra/run-xpra"
		opts.debug = None
		opts.dock_icon = None
		
		import logging
		logging.root.setLevel(logging.INFO)
		logging.root.addHandler(logging.StreamHandler(sys.stderr))

		app = XpraClient(socket_wrapper, opts)
		app.run()

	def launch_xpra(self):
		""" Launches Xpra in a new process """
		cmd = "xpra"
		if sys.platform.startswith("win"):
			if hasattr(sys, "frozen"):
				exedir = os.path.dirname(sys.executable)
			else:
				exedir = os.path.dirname(sys.argv[0])
			cmd = os.path.join(exedir, "xpra.exe")
			if not os.path.exists(cmd):
				self.info.set_text("Xpra command not found!")
				return
		self.info.set_text("Launching: %s" % cmd)
		self.window.hide()
		thread.start_new_thread(self.start_xpra_process, (cmd,))
		
	def start_xpra_process(self, cmd):
		try:
			self.do_start_xpra_process(cmd)
		except Exception, e:
			print("error: %s" % e)
			self.info.set_text("Error launching %s: %s" % (cmd, e))

	def do_start_xpra_process(self, cmd):
		#ret = os.system(" ".join(args))
		mode = self.mode_combo.get_active_text()
		host = self.host_entry.get_text()
		port = self.port_entry.get_text()
		jpeg = self.jpeg_combo.get_active_text()
		uri = "%s:%s:%s" % (mode, host, port)
		args = [cmd, "attach", uri]
		print("jpeg=%s" % jpeg)
		if jpeg:
			jpeg_v = XPRA_COMPRESSION_OPTIONS_DICT.get(jpeg)
			if jpeg_v:
				args.append("--jpeg-quality=%s" % jpeg_v)
		process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, creationflags=SUBPROCESS_CREATION_FLAGS)
		(out,err) = process.communicate()
		print("do_start_xpra_process(%s) command terminated" % str(cmd))
		print("stdout=%s" % out)
		print("stderr=%s" % err)
		ret = process.wait()
		def show_result(out, err):
			if len(out)>255:
				out = "..."+out[len(out)-255:]
			if len(err)>255:
				err = "..."+err[len(err)-255:]
			self.info.set_text("command:\n%s\nterminated with status %s,\noutput:\n%s\nerror:\n%s" % (args, ret, out, err))
			self.window.show_all()
		gobject.idle_add(show_result, out, err)

	def connect_clicked(self, *args):
		mode = self.mode_combo.get_active_text()
		if mode=="tcp" and not sys.platform.startswith("win"):
			""" Use built-in connector (faster and gives feedback) - does not work on win32... (dunno why) """
			self.connect_tcp()
		else:
			self.launch_xpra()

	def destroy(self, *args):
		gtk.main_quit()

def main():
	ApplicationWindow()
	gtk.main()

if __name__ == "__main__":
	main()
	sys.exit(0)
