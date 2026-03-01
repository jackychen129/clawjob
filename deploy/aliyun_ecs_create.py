#!/usr/bin/env python3
"""
使用阿里云 API 创建一台海外 ECS，默认包年包月（PrePaid），使用本机密钥对，支持 SSH 登录。
依赖: pip install -r requirements-aliyun.txt
环境变量（必填）:
  ALIBABA_CLOUD_ACCESS_KEY_ID
  ALIBABA_CLOUD_ACCESS_KEY_SECRET
可选:
  ALIBABA_CLOUD_REGION  默认 ap-southeast-1（新加坡）
  ALIBABA_CLOUD_ECS_INSTANCE_TYPE  默认 ecs.g6.large（新加坡常用）；可选 ecs.c6.large / ecs.e-c1m2.large
  ALIBABA_CLOUD_ECS_CHARGE_TYPE  默认 PrePaid（包年包月）；可选 PostPaid（按量）
  ALIBABA_CLOUD_ECS_PERIOD  包年包月时长（月），默认 1；可选 1/2/3/6/12
  LOCAL_SSH_KEY_PATH  本机私钥路径，用于导入公钥并绑定实例；默认 ~/Downloads/newclawjobkey.pem
输出: 打印 INSTANCE_ID、PUBLIC_IP、REGION；使用密钥登录无密码输出。
"""
from __future__ import print_function
import os
import sys
import time
import random
import string
import subprocess

def env(key, default=""):
    return os.environ.get(key, default).strip()

def get_public_key_from_pem(pem_path):
    """从 PEM 私钥导出公钥（OpenSSH 格式）。"""
    pem_path = os.path.expanduser(pem_path)
    if not os.path.isfile(pem_path):
        raise FileNotFoundError("Key file not found: %s" % pem_path)
    try:
        out = subprocess.check_output(
            ["ssh-keygen", "-y", "-f", pem_path],
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return out.decode().strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("ssh-keygen -y failed: %s" % (e.stderr and e.stderr.decode()))
    except FileNotFoundError:
        raise RuntimeError("ssh-keygen not found, cannot derive public key")

def main():
    access_key_id = env("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = env("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    region_id = env("ALIBABA_CLOUD_REGION") or "ap-southeast-1"
    # 新加坡 ap-southeast-1d 常用规格：g6/c6 部分可用，g7 等可作备选
    instance_type = env("ALIBABA_CLOUD_ECS_INSTANCE_TYPE") or "ecs.g6.large"
    key_path = env("LOCAL_SSH_KEY_PATH") or os.path.expanduser("~/Downloads/newclawjobkey.pem")

    if not access_key_id or not access_key_secret:
        print("Set ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET", file=sys.stderr)
        sys.exit(1)

    charge_type = env("ALIBABA_CLOUD_ECS_CHARGE_TYPE") or "PrePaid"
    period_months = int(env("ALIBABA_CLOUD_ECS_PERIOD") or "1")  # 包年包月时长（月），1/2/3/6/12
    print("计费方式：%s，地域：%s" % (charge_type, region_id), file=sys.stderr)

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

    # 2) 获取或创建 vSwitch：支持环境变量指定已有交换机，否则先查当前 VPC 再查全地域
    vswitch_id = zone_id = None
    existing_vsw = env("ALIBABA_CLOUD_VSWITCH_ID")
    if existing_vsw:
        try:
            req = vpc_models.DescribeVSwitchAttributesRequest(region_id=region_id, v_switch_id=existing_vsw)
            resp = vpc_client.describe_vswitch_attributes(req)
            vswitch_id = existing_vsw
            vpc_id = getattr(resp.body, "vpc_id", None) or getattr(resp.body, "VpcId", None)
            zone_id = getattr(resp.body, "zone_id", None) or getattr(resp.body, "ZoneId", None)
            print("Using existing VSwitch:", vswitch_id, "VpcId:", vpc_id, "ZoneId:", zone_id, file=sys.stderr)
        except Exception as e:
            print("DescribeVSwitchAttributes error:", e, file=sys.stderr)
            existing_vsw = None
    if not vswitch_id:
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
        # 获取可用区列表，逐个可用区、多个 CIDR 尝试创建 VSwitch
        zone_ids = [f"{region_id}-a", f"{region_id}-b", f"{region_id}-c"]
        try:
            zreq = ecs_models.DescribeZonesRequest(region_id=region_id)
            zresp = ecs.describe_zones(zreq)
            zraw = getattr(zresp.body, "zones", None)
            zones = (zraw or {}).get("Zone") if isinstance(zraw, dict) else getattr(zraw, "zone", None) or []
            if not isinstance(zones, list):
                zones = [zones] if zones else []
            zone_ids = []
            for z in zones:
                zid = z.get("ZoneId") if isinstance(z, dict) else getattr(z, "zone_id", None) or getattr(z, "ZoneId", None)
                if zid:
                    zone_ids.append(zid)
            if not zone_ids:
                zone_ids = [f"{region_id}-a"]
        except Exception:
            pass
        # VPC 为 10.0.0.0/8，交换机 CIDR 须在其内；10.0.1～10.0.8 常已被占用，优先试更大网段
        cidrs = ["10.0.9.0/24", "10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24", "10.1.0.0/24", "10.2.0.0/24", "10.3.0.0/24",
                 "10.0.7.0/24", "10.0.8.0/24", "10.0.5.0/24", "10.0.6.0/24", "10.0.2.0/24", "10.0.3.0/24", "10.0.4.0/24", "10.0.1.0/24"]
        for zid in zone_ids:
            for cidr in cidrs:
                try:
                    req = vpc_models.CreateVSwitchRequest(
                        region_id=region_id,
                        vpc_id=vpc_id,
                        zone_id=zid,
                        cidr_block=cidr,
                    )
                    resp = vpc_client.create_vswitch(req)
                    vswitch_id = getattr(resp.body, "v_switch_id", None) or getattr(resp.body, "VSwitchId", None)
                    zone_id = zid
                    print("Created VSwitch:", vswitch_id, "zone", zid, "cidr", cidr, file=sys.stderr)
                    time.sleep(5)
                    break
                except Exception as ex:
                    print("CreateVSwitch", zid, cidr, str(ex)[:80], file=sys.stderr)
            if vswitch_id:
                break
        if not vswitch_id:
            print("CreateVSwitch error: CreateVSwitch failed for all zones/CIDRs. 请在控制台为该地域创建 VPC 与交换机后重试。", file=sys.stderr)
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
            for port, desc in [(22, "SSH"), (80, "HTTP"), (443, "HTTPS"), (3000, "ClawJob-Frontend"), (8000, "ClawJob-API")]:
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

    # 4) 镜像：Ubuntu 22.04（instance_type 用于兼容性筛选）
    try:
        req = ecs_models.DescribeImagesRequest(
            region_id=region_id,
            image_owner_alias="system",
            ostype="linux",
            architecture="x86_64",
            instance_type=instance_type,
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

    # 4b) 导入本机公钥为密钥对，创建实例时绑定以便用私钥 SSH
    key_pair_name = "clawjob-ecs-key-%s" % int(time.time())
    try:
        public_key_body = get_public_key_from_pem(key_path)
        imp_req = ecs_models.ImportKeyPairRequest(
            region_id=region_id,
            key_pair_name=key_pair_name,
            public_key_body=public_key_body,
        )
        ecs.import_key_pair(imp_req)
        print("Imported key pair:", key_pair_name, file=sys.stderr)
    except Exception as e:
        print("ImportKeyPair error (use password fallback or fix key path):", e, file=sys.stderr)
        key_pair_name = None

    # 5) RunInstances：包年包月（PrePaid）或按量（PostPaid），使用密钥对（无密码）或密码
    run_kw = dict(
        region_id=region_id,
        image_id=image_id,
        instance_type=instance_type,
        security_group_id=sg_id,
        v_switch_id=vswitch_id,
        instance_name="clawjob-ecs",
        host_name="clawjob",
        amount=1,
        instance_charge_type=charge_type,
        spot_strategy="NoSpot",
        internet_charge_type="PayByTraffic",
        internet_max_bandwidth_out=5,
        system_disk=ecs_models.RunInstancesRequestSystemDisk(
            category="cloud_essd",
            size=100,
        ),
    )
    if charge_type == "PrePaid":
        run_kw["period"] = period_months
        run_kw["period_unit"] = "Month"
    if key_pair_name:
        run_kw["key_pair_name"] = key_pair_name
        password = None
    else:
        password = env("ALIBABA_CLOUD_ECS_PASSWORD") or random_password(16)
        run_kw["password"] = password
    try:
        req = ecs_models.RunInstancesRequest(**run_kw)
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

    def _get(obj, *keys):
        """从 dict 或 Tea 模型对象取值，兼容 .get(key) 与 getattr(obj, key)."""
        for k in keys:
            if obj is None:
                return None
            if isinstance(obj, dict):
                obj = obj.get(k) or obj.get(k.replace("_", "") if "_" in k else k)
            else:
                obj = getattr(obj, k, None) or getattr(obj, k.replace("_", "") if "_" in k else k, None)
        return obj

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
            if not isinstance(inst_list, list):
                inst_list = [inst_list] if inst_list else []
            if not inst_list:
                continue
            inst = inst_list[0]
            status = _get(inst, "Status") or _get(inst, "status")
            if status == "Running":
                pip = _get(inst, "PublicIpAddress") or _get(inst, "public_ip_address")
                if isinstance(pip, dict):
                    public_ip = pip.get("IpAddress") or pip.get("ip_address") or ((pip.get("IpAddress") or [None])[0] if isinstance(pip.get("IpAddress"), list) else None)
                elif isinstance(pip, list):
                    public_ip = pip[0] if pip else None
                else:
                    public_ip = pip
                if not public_ip:
                    eip = _get(inst, "EipAddress")
                    if isinstance(eip, dict):
                        public_ip = eip.get("IpAddress") or eip.get("ip_address")
                    else:
                        public_ip = eip
                if public_ip:
                    print("INSTANCE_ID=" + instance_id)
                    print("PUBLIC_IP=" + public_ip)
                    if password:
                        print("PASSWORD=" + password)
                    print("REGION=" + region_id)
                    return
        except Exception as e:
            print("DescribeInstances:", e, file=sys.stderr)
    print("Timeout waiting for instance or public IP", file=sys.stderr)
    print("INSTANCE_ID=" + instance_id)
    if password:
        print("PASSWORD=" + password)
    sys.exit(8)

if __name__ == "__main__":
    main()
