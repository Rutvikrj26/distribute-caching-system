import paramiko

# Define the IP addresses and run files for each instance
instances = {
    "frontend": ("3.139.103.194", "run_frontend.py"),
    "manager": ("3.139.103.194", "run_manager.py"),
    "autoscaler": ("3.139.103.194", "run_autoscaler.py"),
    "s3": ("3.139.103.194", "run_S3.py"),
    "memapp_0": ("3.145.153.213", "run_memapp.py"),
    "memapp_1": ("3.145.7.90", "run_memapp.py"),
    "memapp_2": ("3.142.135.104", "run_memapp.py"),
    "memapp_3": ("3.12.107.84", "run_memapp.py"),
    "memapp_4": ("18.118.207.236", "run_memapp.py"),
    "memapp_5": ("3.15.223.27", "run_memapp.py"),
    "memapp_6": ("18.188.246.106", "run_memapp.py"),
    "memapp_7": ("18.224.69.57", "run_memapp.py")
}

# Define the SSH username and private key path
ssh_username = "ubuntu"
private_key_path = "./ece-a1.pem"

# Define a function to run a command on an instance using SSH
def run_command_on_instance(instance_ip, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(instance_ip, username=ssh_username, key_filename=private_key_path)
    stdin, stdout, stderr = ssh.exec_command(command)
    ssh.close()
    return

# Loop through the instances and run the respective run files
for instance_name, instance_info in instances.items():
    instance_ip, run_file = instance_info
    command = f"cd app && nohup python {run_file} &>/dev/null &"
    run_command_on_instance(instance_ip, command)
    print(f"Started {run_file} on {instance_ip}")
