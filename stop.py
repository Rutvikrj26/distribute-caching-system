import paramiko

# list of instances' public IPs
instance_ips = [
    "3.139.103.194", "3.145.153.213", "3.145.7.90",
    "3.142.135.104", "3.12.107.84", "18.118.207.236",
    "3.15.223.27", "18.188.246.106", "18.224.69.57"
]

# list of processes to stop
processes = [
    "run_frontend.py", "run_manager.py", "run_autoscaler.py",
    "run_S3.py", "run_memapp.py"
]

# create SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
private_key = paramiko.RSAKey.from_private_key_file('ece-a1.pem')

# stop processes on each instance
for ip in instance_ips:
    print(f"Stopping processes on instance {ip}...")
    # connect to instance
    ssh.connect(hostname=ip, username='ubuntu', pkey=private_key)
    # stop processes
    command = f"sudo pkill -f 'python'"
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode())
    # close connection
    ssh.close()
