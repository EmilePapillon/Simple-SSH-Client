#!/usr/bin/python3
import subprocess
from threading import Thread
from queue import Queue, Empty
from time import sleep,time

## SSHClient implements an ssh client. 
# Usage: 
# client = SSHClient() 
# client.connect()
# (output, errors) = client.cmd(command)
# where output : stdout and errors : stderr
# the last return code can be found with client.get_return_code() 
class SSHClient():

	def __init__(self, host="192.168.7.2", port="22", username="root", password=None):
		if password is not None: raise NotImplemented("Error: this doesnt support password log-in yet.")
		self.host=host
		self.port=port
		self.username=username
		self.password=password
		self.p = None
		self.q_stdout=Queue()
		self.q_stderr=Queue()
		self.stream_enqueue_t = None
		self.last_return_code = None

	# returns true if port 22 is open for SSH communication on target host
	def is_host_up(self):
		try:
			return "22/tcp open  ssh" in \
			subprocess.check_output(["nmap", self.host, "-PN", "-p", "ssh"]).decode('utf-8')
		except subprocess.CalledProcessError:
			raise subprocess.CalledProcessError("This program requires nmap utility. Is it installed?")
	
	# used to launch a thread that puts everything printed in stdout into a queue object
	@staticmethod
	def enqueue_output(out, queue):
		for line in iter(out.readline, b''):
			queue.put(line)
		out.close()

	#establish connection and starts threads that enqueue the stdout and stderr buffers
	def connect(self):
		if not self.is_host_up(): 
			raise ConnectionError("The host appears to be down...")
		self.p=subprocess.Popen(\
			['ssh','-T', self.username+"@"+self.host, 'bash -l'], \
			stdin=subprocess.PIPE, \
			stdout=subprocess.PIPE,\
			stderr=subprocess.PIPE \
			)
		#note: these threads don't need handles since they modify the queue object and they die with the program (daemons)
		Thread(target=self.enqueue_output, daemon=True, args=(self.p.stdout,self.q_stdout))\
		.start()
		Thread(target=self.enqueue_output, daemon=True, args=(self.p.stderr,self.q_stderr))\
		.start()

	# send an encoded command to the input stream. The command "echo $?" is appended to the desired
	# command to force the host to report the exit status for last command. This makes sure the responses
	# are never empty and we can always expect a response.
	def send(self, command):
		command=command+"\necho $?\n"

		# writes to and flushes the input stream (stdin)
		def in_write(in_stream, msg):
			in_stream.write(msg)
			in_stream.flush()

		in_write(self.p.stdin, command.encode("utf-8"))

	# sr = send-receive. Sends a command, waits for response then prints the full response.
	def sr(self, command,msg_queue,timeout):
		tmt=time()+timeout
		reply=[]
		self.send(command)
		#waits for reply and empties the queue
		while True:
			try: 
				# This line blocks
				line= msg_queue.get(timeout=timeout).decode("utf-8").strip()
			except Empty:
				# Host should at least reply exit code... check host connectivity
				if self.is_host_up():
					if time() < tmt:
						continue
					raise TimeoutError("Unexpected condition: the host appears to be up but it didn't reply")
				else:
					raise TimeoutError("The host is down.")
			reply.append(line)
			if line.isdigit() and msg_queue.empty():
				self.last_return_code=line
				break

		return reply

	@staticmethod
	def check_stderr(msg_queue):
		error=[]
		while True:
			if msg_queue.empty(): break
			try:
				error.append(msg_queue.get().decode('utf-8'))
			except Empty:
				break
		return error

	def cmd(self, command, timeout=5):
		reply=self.sr(command, self.q_stdout, timeout)
		error=self.check_stderr(self.q_stderr)
		return reply,error

	def get_return_code(self):
		return self.last_return_code

if __name__=="__main__":

	print("Running SSH client in interactive mode. This does not support passwords yet.\nEither use SSH key authentication or remove password from host")
	HOST = "192.168.7.2"
	USER = "root"
	# setup
	setup= input("use default settings ?\nHOST="+HOST+"\nUSER="+USER+"\nyes/no: ")
	if setup in ["no", "n"]:
		HOST=input("Enter host IP address: ")
		USER=input("Enter username: ")
	elif setup in ["yes", "y"]:
		print("using defaults...")

	client= SSHClient()
	client.connect()

	# Main loop
	while True:
		command=input("ssh "+USER+"@"+HOST+">>> ")
		if command=="": break
		reply,error=client.cmd(command ,timeout=5)
		for r in reply:
			print(r)

		for e in error:
			print(e)
