#!/usr/bin/python2.7
#encoding=utf-8

import socket
from threading import Thread
import sys
import signal

SOCKTIMEOUT=5#客户端连接超时(秒)
RESENDTIMEOUT=300#转发超时(秒)

VER=chr(0x05)
METHOD=chr(0x00)

SUCCESS=chr(0x00)
SOCKFAIL=chr(0x01)
NETWORKFAIL=chr(0x02)
HOSTFAIL=chr(0x04)
REFUSED=chr(0x05)
TTLEXPIRED=chr(0x06)
UNSUPPORTCMD=chr(0x07)
ADDRTYPEUNSPPORT=chr(0x08)
UNASSIGNED=chr(0x09)

class SocketTransform(Thread):
	def __init__(self,src,dest_ip,dest_port,bind=False):
		Thread.__init__(self)
		self.dest_ip=dest_ip
		self.dest_port=dest_port
		self.src=src
		self.bind=bind
		self.setDaemon(True)

	def run(self):
		try:
			self.resend()
		except Exception,e:
			sys.stderr.write("Error on SocketTransform %s\n" %(e.message,))
			self.sock.close()
			self.dest.close()

	def resend(self):
		self.sock=self.src
		self.dest=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.dest.connect((self.dest_ip,self.dest_port))
		if self.bind:
			sys.stdout.write("waiting for the client\n")
			self.sock,info=sock.accept()
			sys.stdout.write("Client connected\n")
		sys.stdout.write("Starting Resending\n")
		self.sock.settimeout(RESENDTIMEOUT)
		self.dest.settimeout(RESENDTIMEOUT)
		Resender(self.sock,self.dest).start()
		Resender(self.dest,self.sock).start()


class Resender(Thread):
	def __init__(self,src,dest):
		Thread.__init__(self)
		self.src=src
		self.setDaemon(True)
		self.dest=dest

	def run(self):
		try:
			self.resend(self.src,self.dest)
		except Exception,e:
			sys.stderr.write("Connection lost %s\n" %(e.message,))
			self.src.close()
			self.dest.close()

	def resend(self,src,dest):
		data=src.recv(10)
		while data:
			dest.sendall(data)
			data=src.recv(10)
		src.close()
		dest.close()
		sys.stdout.write("Client quit normally\n")


def create_server(ip,port):
	transformer=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	transformer.bind((ip,port))
	signal.signal(signal.SIGTERM,OnExit(transformer).exit)
	transformer.listen(1000)
	while True:
		sock,addr_info=transformer.accept()
		sock.settimeout(SOCKTIMEOUT)
		sys.stdout.write("\nGot one client connection\n")
		try:
			ver,nmethods,methods=(sock.recv(1),sock.recv(1),sock.recv(1))
			sock.sendall(VER+METHOD)
			ver,cmd,rsv,atyp=(sock.recv(1),sock.recv(1),sock.recv(1),sock.recv(1))
			dst_addr=None
			dst_port=None
			if atyp==chr(0x01):#IPV4
				dst_addr,dst_port=sock.recv(4),sock.recv(2)
				dst_addr=".".join([str(ord(i)) for i in dst_addr])
			elif atyp==chr(0x03):#Domain
				addr_len=ord(sock.recv(4))*256+ord(sock.recv(4))
				dst_addr,dst_port=sock.recv(addr_len),sock.recv(2)
				dst_addr="".join([unichr(ord(i)) for i in dst_addr])
			elif atyp==chr(0x04):#IPV6
				dst_addr,dst_port=sock.recv(16),sock.recv(2)
				tmp_addr=[]
				for i in xrange(len(dst_addr)/2):
					tmp_addr.append(unichr(ord(dst_addr[2*i])*256+ord(dst_addr[2*i+1])))
				dst_addr=":".join(tmp_addr)
			dst_port=ord(dst_port[0])*256+ord(dst_port[1])
			sys.stdout.write("Client wants to connect to %s:%d\n" %(dst_addr,dst_port))
			server_sock=sock
			server_ip="".join([chr(int(i)) for i in ip.split(".")])

			if cmd==chr(0x02):#BIND
				#Unimplement
				sock.close()
			elif cmd==chr(0x03):#UDP
				#Unimplement
				sock.close()
			elif cmd==chr(0x001):#CONNECT
				sock.sendall(VER+SUCCESS+chr(0x00)+chr(0x01)+server_ip+chr(port/256)+chr(port%256))
				sys.stdout.write("Starting transform thread\n")
				SocketTransform(server_sock,dst_addr,dst_port).start()
			else:#Unspport Command
				sock.sendall(VER+UNSPPORTCMD+server_ip+chr(port/256)+chr(port%256))
				sock.close()
		except Exception,e:
			sys.stderr.write("Error on starting transform:"+e.message+"\n")
			sock.close()

class OnExit:
	def __init__(self,sock):
		self.sock=sock

	def exit(self):
		self.sock.close()


if __name__=='__main__':
	try:
		ip="192.168.1.14"
		port=8080
		create_server(ip,port)
	except Exception,e:
		sys.stderr.write("Error on create server:"+e.message+"\n")


