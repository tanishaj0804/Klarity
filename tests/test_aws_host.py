"""Tests for scripts/aws_host.py against a fake AWS (moto). No real AWS is touched."""
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import aws_host  # noqa: E402


@pytest.fixture()
def aws(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")
    with mock_aws():
        client = boto3.client("ec2", region_name="ap-south-1")
        group = client.create_security_group(GroupName="klarity-sources-sg", Description="test")["GroupId"]
        ami = client.describe_images()["Images"][0]["ImageId"]
        client.run_instances(ImageId=ami, MinCount=1, MaxCount=1, InstanceType="t3.small",
                             SecurityGroupIds=[group],
                             TagSpecifications=[{"ResourceType": "instance",
                                                 "Tags": [{"Key": "Name", "Value": "klarity-sources"}]}])
        yield client


def rules(client):
    group = aws_host.find_group(client)
    return {(p["FromPort"], r["CidrIp"], r.get("Description", ""))
            for p in group["IpPermissions"] for r in p.get("IpRanges", [])}


def test_status_runs(aws, capsys):
    assert aws_host.main(["status"], client=aws) == 0
    assert "klarity" not in capsys.readouterr().err


def test_stop_then_start_updates_env_file(aws, tmp_path):
    env = tmp_path / ".env.aws"
    env.write_text("ORACLE_HOST=localhost\nMYSQL_HOST=localhost\nPG_PASSWORD=keepme\n", encoding="utf-8")
    assert aws_host.main(["stop"], client=aws) == 0
    assert aws_host.main(["start", "--env-file", str(env)], client=aws) == 0
    text = env.read_text(encoding="utf-8")
    ip = aws_host.find_instance(aws)["PublicIpAddress"]
    assert f"ORACLE_HOST={ip}" in text and f"MYSQL_HOST={ip}" in text and f"PG_HOST={ip}" in text
    assert "PG_PASSWORD=keepme" in text  # other settings are untouched


def test_allow_my_ip_adds_all_ports_and_replaces_old_ip(aws, monkeypatch):
    monkeypatch.setattr(aws_host, "my_ip", lambda: "203.0.113.7")
    aws_host.main(["allow-my-ip", "--label", "home"], client=aws)
    assert {(p, c) for p, c, _ in rules(aws)} == {(p, "203.0.113.7/32") for p in aws_host.PORTS}
    monkeypatch.setattr(aws_host, "my_ip", lambda: "198.51.100.9")  # the laptop moved
    aws_host.main(["allow-my-ip", "--label", "home"], client=aws)
    assert {c for _, c, _ in rules(aws)} == {"198.51.100.9/32"}


def test_two_laptops_keep_separate_rules(aws, monkeypatch):
    monkeypatch.setattr(aws_host, "my_ip", lambda: "203.0.113.7")
    aws_host.main(["allow-my-ip", "--label", "home"], client=aws)
    monkeypatch.setattr(aws_host, "my_ip", lambda: "198.51.100.9")
    aws_host.main(["allow-my-ip", "--label", "office"], client=aws)
    assert {c for _, c, _ in rules(aws)} == {"203.0.113.7/32", "198.51.100.9/32"}


def test_allow_my_ip_twice_is_harmless(aws, monkeypatch):
    monkeypatch.setattr(aws_host, "my_ip", lambda: "203.0.113.7")
    for _ in range(2):
        assert aws_host.main(["allow-my-ip", "--label", "home"], client=aws) == 0


def test_set_hosts_requires_existing_file(tmp_path):
    with pytest.raises(SystemExit):
        aws_host.set_hosts(tmp_path / "missing.env", "1.2.3.4")
