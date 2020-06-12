#!/usr/bin/python3
from subprocess import Popen, PIPE, check_output
from threading import Thread
from queue import Queue, Empty
from time import sleep

USER= 'root'
HOST='192.168.7.2'

# returns true if port 22 is open for SSH communication on target host
def is_host_up(host):
	return "22/tcp open  ssh" in \
	check_output(["nmap", host, "-PN", "-p", "ssh"]).decode('utf-8')

# used to launch a thread that puts everything printed in stdout into a queue object
def enqueue_output(out, queue):
	for line in iter(out.readline, b''):
		queue.put(line)
	out.close()

# send an encoded command to the input stream. The command "echo $?" is appended to the desired
# command to force the host to report the exit status for last command. This makes sure the responses
# are never empty and we can always expect a response.
def send(command):
	command=command+"\necho $?\n"

	# writes to and flushes the input stream (stdin)
	def in_write(in_stream, msg):
		in_stream.write(msg)
		in_stream.flush()

	in_write(p.stdin, command.encode("utf-8"))

# sr = send-receive. Sends a command, waits for response then prints the full response.
# TODO: currently, only stdout is supported, but errors go silent. Add stderr support. 
def sr(command,msg_queue,timeout):
	send(command)
	#waits for reply and empties the queue
	while True:
		try: 
			# This line blocks
			line= msg_queue.get(timeout=timeout).decode("utf-8").strip()
		except Empty:
			# Host should at least reply exit code... check host connectivity
			if is_host_up(HOST):
				raise TimeoutError("Unexpected condition: the host appears to be up but it didn't reply")
			else:
				raise TimeoutError("The host is down.")
		print(line)
		if line.isdigit():
			last_return_code=line
			break

def check_stderr(msg_queue):
	while True:
		if msg_queue.empty(): break
		try:
			print(msg_queue.get().decode('utf-8'))
		except Empty:
			break

# SSH prompt
if __name__=="__main__":

	print("SSH client demo. This does not support passwords yet.")

	# setup
	setup= input("use default settings ?\nHOST="+HOST+"\nUSER="+USER+"\nyes/no: ")
	if setup in ["no", "n"]:
		HOST=input("Enter host IP address: ")
		USER=input("Enter username: ")
	elif setup in ["yes", "y"]:
		print("using defaults...")

	# check connectivity and connect
	if not is_host_up(HOST): 
		raise ConnectionError("The host appears to be down...")
	p=Popen(['ssh','-T', USER+"@"+HOST, 'bash -l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)

	# Main loop execution
	q_stdout=Queue()
	q_stderr=Queue()
	stream_enqueue_t = Thread(target=enqueue_output, daemon=True, args=(p.stdout,q_stdout))
	stream_enqueue_t.start()
	stream_enqueue_t = Thread(target=enqueue_output, daemon=True, args=(p.stderr,q_stderr))
	stream_enqueue_t.start()
	last_return_code="0"

	# Main loop
	while True:
		command=input("ssh "+USER+"@"+HOST+">>> ")
		if command=="": break
		sr(command, q_stdout ,timeout=5)
		check_stderr(q_stderr)
