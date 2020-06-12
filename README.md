# Simple-SSH-Client
Simple SSH client coded in Python

# Usage: 
## Use case 1 : programatic commands
``` python
myssh=SSH_Client(host="192.168.7.2", port="22", user="sponge_bob", password="iambob") 
connected=myssh.connect()
reply=myssh.cmd("cd /")
reply=myssh.cmd("ls -la")

for line in reply:
  print(line)
```
## Use case 2 : interactive (mainly used for debugging)
``` python
myssh=SSH_Client(host="192.168.7.2", port="22", user="sponge_bob", password="iambob") 
myssh.session()
ssh sponge_bob@192.168.7.2>>> ls -la
```
