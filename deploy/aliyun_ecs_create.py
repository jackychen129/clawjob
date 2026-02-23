#!/usr/bin/env python3
"""
使用阿里云 API 创建一台海外 ECS（按量付费），并输出公网 IP 与登录密码。
依赖: pip install -r requirements-aliyun.txt
环境变量（必填）:
  ALIBABA_CLOUD_ACCESS_KEY_ID
  ALIBABA_CLOUD_ACCESS_KEY_SECRET
可选:
  ALIBABA_CLOUD_REGION  默认 ap-southeast-1（新加坡）
  ALIBABA_CLOUD_ECS_PASSWORD  实例 root 密码（8-30 位，含大小写数字特殊字符）；不设则自动生成
输出: 打印 InstanceId、PublicIp、Password，便于后续 SSH 部署。
"""
from __future__ import print_function
import os
import sys
import time
import random
import string

def env(key, default=""):
    return os.environ.get(key, default).strip()

def random_password(length=16):
    up = string.ascii_uppercase
    lo = string.ascii_lowercase
    dig = string.digits
    sp = "!@#$%^&*-_+=|"
    s = random.SystemRandom()
    p = [s.choice(up), s.choice(lo), s.choice(dig), s.choice(sp)]
    p += [s.choice(up + lo + dig + sp) for _ in range(length - 4)]
    random.shuffle(p)
    return "".join(p)

def main():
    access_key_id = env("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = env("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    region_id = env("ALIBABA_CLOUD_REGION") or "cn-hongkong"
    password = env("ALIBABA_CLOUD_ECS_PASSWORD") or random_password(16)

    if not access_key_id or not access_key_secret:
        print("Set ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET", file=sys.stderr)
        sys.exit(1)

    try:
        from alibabacloud_tea_openapi.models import Config as OpenApiConfig
        from alibabacloud_ecs20140526.client import Client as EcsClient
        from alibabacloud_ecs20140526 import models as ecs_models
        from alibabacloud_vpc20160428.client import Client as VpcClient
        from alibabacloud_vpc20160428 import models as vpc_models
    except ImportError as e:
        print("Install: pip install -r deploy/requirements-aliyun.txt", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(2)

    # ECS endpoint: 海外 region 使用 ecs.{region}.aliyuncs.com
    ecs_config = OpenApiConfig(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint=f"ecs.{region_id}.aliyuncs.com",
        region_id=region_id,
    )
    vpc_config = OpenApiConfig(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint=f"vpc.{region_id}.aliyuncs.com",
        region_id=region_id,
    )
    ecs = EcsClient(ecs_config)
    vpc_client = VpcClient(vpc_config)

    # 1) 获取或创建 VPC
    try:
        req = vpc_models.DescribeVpcsRequest(region_id=region_id)
        resp = vpc_client.describe_vpcs(req)
        raw = getattr(resp.body, "vpcs", None)
        vpcs = (raw or {}).get("Vpc") if isinstance(raw, dict) else getattr(raw, "vpc", None) or []
        if not isinstance(vpcs, list):
            vpcs = [vpcs] if vpcs else []
        if isinstance(vpcs and vpcs[0], dict):
            vpc_id = vpcs[0].get("VpcId")
        elif vpcs:
            vpc_id = getattr(vpcs[0], "vpc_id", None) or getattr(vpcs[0], "VpcId", None)
        else:
            vpc_id = None
    except Exception as e:
        print("DescribeVpcs error:", e, file=sys.stderr)
        vpc_id = None

    if not vpc_id:
        try:
            req = vpc_models.CreateVpcRequest(
                region_id=region_id,
                cidr_block="10.0.0.0/8",
                vpc_name="clawjob-vpc",
            )
            resp = vpc_client.create_vpc(req)
            vpc_id = getattr(resp.body, "vpc_id", None) or getattr(resp.body, "VpcId", None)
            print("Created VPC:", vpc_id, file=sys.stderr)
            time.sleep(3)
        except Exception as e:
            print("CreateVpc error:", e, file=sys.stderr)
            sys.exit(3)

    # 2) 获取或创建 vSwitch：先查当前 VPC，若无则遍历所有 VPC 找有 vSwitch 的
    vswitch_id = zone_id = None
    try:
        req = vpc_models.DescribeVSwitchesRequest(region_id=region_id, vpc_id=vpc_id)
        resp = vpc_client.describe_vswitches(req)
        raw = getattr(resp.body, "vswitches", None)
        if isinstance(raw, dict):
            vsws = raw.get("VSwitch") or raw.get("v_switch") or []
        elif hasattr(raw, "__iter__") and not isinstance(raw, (str, dict)):
            vsws = list(raw)
        else:
            vsws = getattr(raw, "v_switch", None) or getattr(raw, "VSwitch", None) or []
        if not isinstance(vsws, list):
            vsws = [vsws] if vsws else []
        vsw0 = vsws[0] if vsws else None
        if isinstance(vsw0, dict):
            vswitch_id = vsw0.get("VSwitchId")
            zone_id = vsw0.get("ZoneId")
        elif vsw0:
            vswitch_id = getattr(vsw0, "v_switch_id", None) or getattr(vsw0, "VSwitchId", None)
            zone_id = getattr(vsw0, "zone_id", None) or getattr(vsw0, "ZoneId", None)
    except Exception as e:
        print("DescribeVSwitches error:", e, file=sys.stderr)

    if not vswitch_id:
        # 列出区域内所有 vSwitch（不按 VPC 过滤），取第一个
        try:
            req_all = vpc_models.DescribeVSwitchesRequest(region_id=region_id)
            resp_all = vpc_client.describe_vswitches(req_all)
            raw_all = getattr(resp_all.body, "vswitches", None)
            if hasattr(raw_all, "__iter__") and not isinstance(raw_all, (str, dict)):
                all_vsws = list(raw_all)
            else:
                all_vsws = getattr(raw_all, "v_switch", None) or getattr(raw_all, "VSwitch", None) or []
            if not isinstance(all_vsws, list):
                all_vsws = [all_vsws] if all_vsws else []
            if all_vsws:
                s0 = all_vsws[0]
                vswitch_id = s0.get("VSwitchId") if isinstance(s0, dict) else getattr(s0, "v_switch_id", None) or getattr(s0, "VSwitchId", None)
                zone_id = s0.get("ZoneId") if isinstance(s0, dict) else getattr(s0, "zone_id", None) or getattr(s0, "ZoneId", None)
                vpc_id = s0.get("VpcId") if isinstance(s0, dict) else getattr(s0, "vpc_id", None) or getattr(s0, "VpcId", None)
                if vpc_id:
                    print("Using existing vSwitch:", vswitch_id, "VPC:", vpc_id, file=sys.stderr)
        except Exception as e:
            print("DescribeVSwitches(region) error:", e, file=sys.stderr)

    if not vswitch_id:
        # 获取可用区（使用该地域支持的第一个可用区）
        try:
            zreq = ecs_models.DescribeZonesRequest(region_id=region_id)
            zresp = ecs.describe_zones(zreq)
            zraw = getattr(zresp.body, "zones", None)
            zones = (zraw or {}).get("Zone") if isinstance(zraw, dict) else getattr(zraw, "zone", None) or []
            if not isinstance(zones, list):
                zones = [zones] if zones else []
            zone_id = None
            for z in zones:
                zid = z.get("ZoneId") if isinstance(z, dict) else getattr(z, "zone_id", None) or getattr(z, "ZoneId", None)
                if zid:
                    zone_id = zid
                    break
            if not zone_id:
                zone_id = f"{region_id}-a"
        except Exception:
            zone_id = f"{region_id}-a"
        try:
            for cidr in ["10.0.7.0/24", "10.0.8.0/24", "10.0.5.0/24", "10.0.6.0/24", "10.0.2.0/24", "10.0.3.0/24", "10.0.4.0/24", "10.0.1.0/24"]:
                try:
                    req = vpc_models.CreateVSwitchRequest(
                        region_id=region_id,
                        vpc_id=vpc_id,
                        zone_id=zone_id,
                        cidr_block=cidr,
                    )
                    resp = vpc_client.create_vswitch(req)
                    vswitch_id = getattr(resp.body, "v_switch_id", None) or getattr(resp.body, "VSwitchId", None)
                    print("Created VSwitch:", vswitch_id, "cidr", cidr, file=sys.stderr)
                    time.sleep(5)
                    break
                except Exception as ex:
                    if "Overlapped" not in str(ex):
                        raise
            if not vswitch_id:
                raise RuntimeError("CreateVSwitch failed for all CIDRs")
        except Exception as e:
            print("CreateVSwitch error:", e, file=sys.stderr)
            sys.exit(4)

    # 3) 安全组
    try:
        req = ecs_models.DescribeSecurityGroupsRequest(
            region_id=region_id,
            vpc_id=vpc_id,
        )
        resp = ecs.describe_security_groups(req)
        raw = getattr(resp.body, "security_groups", None)
        sgs = (raw or {}).get("SecurityGroup") if isinstance(raw, dict) else getattr(raw, "security_group", None) or []
        if hasattr(sgs, "__iter__") and not isinstance(sgs, (str, dict)):
            sgs = list(sgs)
        if not isinstance(sgs, list):
            sgs = [sgs] if sgs else []
        s0 = sgs[0] if sgs else None
        sg_id = s0.get("SecurityGroupId") if isinstance(s0, dict) else (getattr(s0, "security_group_id", None) or getattr(s0, "SecurityGroupId", None)) if s0 else None
    except Exception as e:
        print("DescribeSecurityGroups error:", e, file=sys.stderr)
        sg_id = None

    if not sg_id:
        try:
            req = ecs_models.CreateSecurityGroupRequest(
                region_id=region_id,
                vpc_id=vpc_id,
                security_group_name="clawjob-sg",
            )
            resp = ecs.create_security_group(req)
            sg_id = resp.body.security_group_id
            print("Created SecurityGroup:", sg_id, file=sys.stderr)
            time.sleep(2)
            for port, desc in [(22, "SSH"), (80, "HTTP"), (443, "HTTPS")]:
                try:
                    ecs.authorize_security_group(ecs_models.AuthorizeSecurityGroupRequest(
                        region_id=region_id,
                        security_group_id=sg_id,
                        ip_protocol="tcp",
                        port_range=f"{port}/{port}",
                        source_cidr_ip="0.0.0.0/0",
                        description=desc,
                    ))
                except Exception as ex:
                    print("AuthorizeSecurityGroup", port, ex, file=sys.stderr)
        except Exception as e:
            print("CreateSecurityGroup error:", e, file=sys.stderr)
            sys.exit(5)

    # 4) 镜像：Ubuntu 22.04
    try:
        req = ecs_models.DescribeImagesRequest(
            region_id=region_id,
            image_owner_alias="system",
            ostype="linux",
            architecture="x86_64",
            instance_type="ecs.c6.large",
            page_size=50,
        )
        resp = ecs.describe_images(req)
        raw = getattr(resp.body, "images", None)
        images = (raw or {}).get("Image") if isinstance(raw, dict) else getattr(raw, "image", None) or []
        if isinstance(images, dict):
            images = [images] if images.get("ImageId") else []
        image_id = None
        for im in images:
            name = (getattr(im, "image_name", None) or getattr(im, "ImageName", None) or getattr(im, "os_name_en", None) or getattr(im, "OSNameEn", None) or "").lower()
            if "ubuntu" in name and "22" in name:
                image_id = getattr(im, "image_id", None) or getattr(im, "ImageId", None)
                break
        if not image_id and images:
            image_id = getattr(images[0], "image_id", None) or getattr(images[0], "ImageId", None)
        if not image_id:
            print("No Ubuntu 22 image found, using first available", file=sys.stderr)
    except Exception as e:
        print("DescribeImages error:", e, file=sys.stderr)
        image_id = None

    if not image_id:
        print("Could not get ImageId", file=sys.stderr)
        sys.exit(6)

    # 5) RunInstances：按量 PostPaid
    instance_type = "ecs.c6.large"
    try:
        req = ecs_models.RunInstancesRequest(
            region_id=region_id,
            image_id=image_id,
            instance_type=instance_type,
            security_group_id=sg_id,
            v_switch_id=vswitch_id,
            instance_name="clawjob-ecs",
            host_name="clawjob",
            amount=1,
            instance_charge_type="PostPaid",
            spot_strategy="NoSpot",
            internet_charge_type="PayByTraffic",
            internet_max_bandwidth_out=5,
            system_disk=ecs_models.RunInstancesRequestSystemDisk(
                category="cloud_essd",
                size=100,
            ),
            password=password,
        )
        resp = ecs.run_instances(req)
        raw = getattr(resp.body, "instance_id_sets", None)
        if hasattr(raw, "instance_id_set"):
            instance_ids = raw.instance_id_set or []
        elif isinstance(raw, list):
            instance_ids = raw
        elif isinstance(raw, dict):
            instance_ids = raw.get("InstanceIdSet") or raw.get("instance_id_set") or []
        else:
            instance_ids = []
        if not instance_ids:
            instance_ids = [getattr(resp.body, "instance_id_sets", None)]
        id0 = instance_ids[0]
        instance_id = id0.get("InstanceId", id0) if isinstance(id0, dict) else id0
        print("Created instance:", instance_id, file=sys.stderr)
    except Exception as e:
        print("RunInstances error:", e, file=sys.stderr)
        sys.exit(7)

    # 6) 等待 Running 并取公网 IP
    for _ in range(60):
        time.sleep(10)
        try:
            req = ecs_models.DescribeInstancesRequest(
                region_id=region_id,
                instance_ids=[instance_id],
            )
            resp = ecs.describe_instances(req)
            raw = getattr(resp.body, "instances", None)
            inst_list = (raw or {}).get("Instance") if isinstance(raw, dict) else getattr(raw, "instance", None) or []
            if isinstance(inst_list, dict):
                inst_list = [inst_list] if inst_list.get("InstanceId") else []
            if not inst_list:
                continue
            inst = inst_list[0]
            status = inst.get("Status") or inst.get("status")
            if status == "Running":
                pip = inst.get("PublicIpAddress") or inst.get("public_ip_address")
                if isinstance(pip, dict):
                    public_ip = pip.get("IpAddress") or pip.get("ip_address") or (pip.get("IpAddress", []) or [None])[0]
                elif isinstance(pip, list):
                    public_ip = pip[0] if pip else None
                else:
                    public_ip = pip
                if not public_ip and inst.get("EipAddress"):
                    public_ip = inst.get("EipAddress", {}).get("IpAddress") if isinstance(inst.get("EipAddress"), dict) else inst.get("EipAddress")
                if public_ip:
                    print("INSTANCE_ID=" + instance_id)
                    print("PUBLIC_IP=" + public_ip)
                    print("PASSWORD=" + password)
                    print("REGION=" + region_id)
                    return
        except Exception as e:
            print("DescribeInstances:", e, file=sys.stderr)
    print("Timeout waiting for instance or public IP", file=sys.stderr)
    print("INSTANCE_ID=" + instance_id)
    print("PASSWORD=" + password)
    sys.exit(8)

if __name__ == "__main__":
    main()
