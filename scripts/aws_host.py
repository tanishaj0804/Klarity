"""Control the Klarity EC2 server from the command line (story S1-06).

Why this exists: the server's public IP address changes every time it is stopped and
started, and your own IP changes when you move between home, office and mobile data.
This script removes the manual clicking, and makes "stop the server when idle" one command.

Commands (repo root, venv active, AWS CLI configured):
    python scripts/aws_host.py status                       # state, IP, firewall rules
    python scripts/aws_host.py start --env-file .env.aws    # start, wait, write the new IP into .env.aws
    python scripts/aws_host.py stop                         # stop (NOT terminate) to save credits
    python scripts/aws_host.py update-env .env.aws          # write the current IP into a settings file
    python scripts/aws_host.py allow-my-ip --label office   # let this laptop reach the databases

Uses your normal AWS settings (aws configure). Region defaults to ap-south-1.
"""
import argparse
import re
import socket
import sys
import urllib.request
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "ap-south-1"
NAME_TAG = "klarity-sources"
SG_NAME = "klarity-sources-sg"
PORTS = {22: "ssh", 1521: "oracle", 3306: "mysql", 5432: "postgres"}
HOST_KEYS = ("ORACLE_HOST", "MYSQL_HOST", "PG_HOST")
RULE_PREFIX = "klarity-auto:"


def find_instance(client, name=NAME_TAG):
    resp = client.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [name]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}])
    found = [i for r in resp["Reservations"] for i in r["Instances"]]
    if not found:
        raise SystemExit(f"No instance named '{name}' found in this region. Launch it first.")
    return found[0]


def find_group(client, name=SG_NAME):
    groups = client.describe_security_groups(Filters=[{"Name": "group-name", "Values": [name]}])["SecurityGroups"]
    if not groups:
        raise SystemExit(f"No security group named '{name}' found.")
    return groups[0]


def my_ip():
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=10) as r:
        return r.read().decode().strip()


def set_hosts(path, host):
    """Write the server address into the *_HOST lines of a settings file (UTF-8)."""
    file = Path(path)
    if not file.exists():
        raise SystemExit(f"{path} does not exist. Create it first: copy .env.example {path}")
    lines = file.read_text(encoding="utf-8").splitlines()
    seen = set()
    for n, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in HOST_KEYS and "=" in line:
            lines[n] = f"{key}={host}"
            seen.add(key)
    lines += [f"{k}={host}" for k in HOST_KEYS if k not in seen]
    file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def show_status(client):
    inst = find_instance(client)
    group = find_group(client)
    print(f"Instance : {inst['InstanceId']} ({inst['InstanceType']})")
    print(f"State    : {inst['State']['Name']}")
    print(f"Public IP: {inst.get('PublicIpAddress', '(none while stopped)')}")
    print("Firewall rules:")
    open_world = False
    for perm in group["IpPermissions"]:
        for rng in perm.get("IpRanges", []):
            cidr, note = rng["CidrIp"], rng.get("Description", "")
            open_world |= cidr == "0.0.0.0/0"
            print(f"  port {perm.get('FromPort')}: {cidr:<18} {note}")
        for rng in perm.get("Ipv6Ranges", []):
            open_world |= rng["CidrIpv6"] == "::/0"
            print(f"  port {perm.get('FromPort')}: {rng['CidrIpv6']}")
    if open_world:
        print("WARNING: a rule is open to the whole internet. Remove it (project security rule).")
    return inst


def allow_my_ip(client, label, ip):
    """Replace this laptop's earlier rules (same label) with rules for its current IP."""
    group = find_group(client)
    note = f"{RULE_PREFIX}{label}"
    cidr = f"{ip}/32"
    for perm in group["IpPermissions"]:
        for rng in perm.get("IpRanges", []):
            if rng.get("Description") == note and rng["CidrIp"] != cidr:
                client.revoke_security_group_ingress(GroupId=group["GroupId"], IpPermissions=[{
                    "IpProtocol": "tcp", "FromPort": perm["FromPort"], "ToPort": perm["ToPort"],
                    "IpRanges": [{"CidrIp": rng["CidrIp"]}]}])
    for port in PORTS:
        try:
            client.authorize_security_group_ingress(GroupId=group["GroupId"], IpPermissions=[{
                "IpProtocol": "tcp", "FromPort": port, "ToPort": port,
                "IpRanges": [{"CidrIp": cidr, "Description": note}]}])
        except ClientError as err:
            if err.response["Error"]["Code"] != "InvalidPermission.Duplicate":
                raise
    return cidr


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["status", "start", "stop", "update-env", "allow-my-ip"])
    ap.add_argument("file", nargs="?", help="settings file for update-env")
    ap.add_argument("--env-file", help="with start: also write the new IP into this settings file")
    ap.add_argument("--label", default=re.sub(r"[^a-z0-9-]", "", socket.gethostname().lower()) or "laptop",
                    help="name of this laptop for allow-my-ip, for example home or office")
    ap.add_argument("--region", default=REGION)
    args = ap.parse_args(argv)
    client = client or boto3.client("ec2", region_name=args.region)

    if args.command == "status":
        show_status(client)
    elif args.command == "start":
        inst = find_instance(client)
        if inst["State"]["Name"] != "running":
            client.start_instances(InstanceIds=[inst["InstanceId"]])
            client.get_waiter("instance_running").wait(InstanceIds=[inst["InstanceId"]])
        inst = find_instance(client)
        ip = inst.get("PublicIpAddress")
        print(f"Server running. Public IP: {ip}")
        if args.env_file:
            set_hosts(args.env_file, ip)
            print(f"Wrote {ip} into {args.env_file}. Update the host in DBeaver too.")
        print("Containers restart by themselves. Oracle needs about 2 minutes before it accepts logins.")
    elif args.command == "stop":
        inst = find_instance(client)
        client.stop_instances(InstanceIds=[inst["InstanceId"]])
        print("Stop requested. The server keeps its data. You are not charged for compute while it is stopped.")
    elif args.command == "update-env":
        if not args.file:
            raise SystemExit("Give the settings file, for example: update-env .env.aws")
        ip = find_instance(client).get("PublicIpAddress")
        if not ip:
            raise SystemExit("The server has no public IP. Is it running? Try: start")
        set_hosts(args.file, ip)
        print(f"Wrote {ip} into {args.file}")
    elif args.command == "allow-my-ip":
        cidr = allow_my_ip(client, args.label, my_ip())
        print(f"Allowed {cidr} (label '{args.label}') on ports {', '.join(str(p) for p in PORTS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
