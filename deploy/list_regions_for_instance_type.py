#!/usr/bin/env python3
"""
列出哪些海外地域有指定 ECS 实例规格（如 ecs.e-c1m2.large）。
依赖: pip install -r requirements-aliyun.txt
环境变量: ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET
用法: python3 deploy/list_regions_for_instance_type.py [InstanceType]
默认: ecs.e-c1m2.large
"""
from __future__ import print_function
import os
import sys

def env(key, default=""):
    return os.environ.get(key, default).strip()

# NOTE: translated comment in English.
OVERSEAS_REGIONS = [
    ("ap-southeast-1", "新加坡"),
    ("ap-northeast-1", "日本东京"),
    ("cn-hongkong", "中国香港"),
    ("ap-southeast-2", "澳大利亚悉尼"),
    ("ap-southeast-3", "马来西亚吉隆坡"),
    ("ap-southeast-5", "印度尼西亚雅加达"),
    ("us-west-1", "美国硅谷"),
    ("us-east-1", "美国弗吉尼亚"),
    ("eu-central-1", "德国法兰克福"),
    ("eu-west-1", "英国伦敦"),
    ("me-east-1", "阿联酋迪拜"),
    ("ap-south-1", "印度孟买"),
]

def main():
    access_key_id = env("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = env("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    instance_type = (sys.argv[1] if len(sys.argv) > 1 else "ecs.e-c1m2.large").strip()

    if not access_key_id or not access_key_secret:
        print("请设置 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET", file=sys.stderr)
        sys.exit(1)

    try:
        from alibabacloud_tea_openapi.models import Config as OpenApiConfig
        from alibabacloud_ecs20140526.client import Client as EcsClient
        from alibabacloud_ecs20140526 import models as ecs_models
    except ImportError as e:
        print("Install: pip install -r deploy/requirements-aliyun.txt", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(2)

    print("查询实例规格: %s 在海外地域的可用情况\n" % instance_type)
    print("%-20s %-12s %s" % ("地域ID", "地域名", "可用区"))
    print("-" * 60)

    available = []
    for region_id, region_name in OVERSEAS_REGIONS:
        try:
            config = OpenApiConfig(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                endpoint="ecs.%s.aliyuncs.com" % region_id,
                region_id=region_id,
            )
            client = EcsClient(config)
            # NOTE: translated comment in English.
            req = ecs_models.DescribeAvailableResourceRequest(
                region_id=region_id,
                destination_resource="Zone",
                instance_type=instance_type,
                io_optimized="optimized",
            )
            resp = client.describe_available_resource(req)
            body = resp.body
            # NOTE: translated comment in English.
            zones = getattr(body, "available_zones", None) or getattr(body, "AvailableZones", None)
            zone_list = []
            if zones is not None:
                if isinstance(zones, list):
                    zone_list = zones
                elif isinstance(zones, dict):
                    zone_list = zones.get("AvailableZone") or zones.get("available_zone") or []
                elif hasattr(zones, "available_zone"):
                    zone_list = list(zones.available_zone) if zones.available_zone else []
                elif hasattr(zones, "AvailableZone"):
                    zone_list = list(zones.AvailableZone) if zones.AvailableZone else []
            if not zone_list and hasattr(body, "to_map"):
                m = body.to_map()
                zone_list = m.get("AvailableZones", {}).get("AvailableZone") or m.get("available_zones", {}).get("AvailableZone") or []
            if not zone_list and hasattr(body, "__dict__"):
                for k, v in body.__dict__.items():
                    if "zone" in k.lower() and v is not None:
                        if isinstance(v, list):
                            zone_list = v
                            break
                        if hasattr(v, "available_zone"):
                            zone_list = list(v.available_zone) if v.available_zone else []
                            break
                        if isinstance(v, dict):
                            zone_list = v.get("AvailableZone") or v.get("available_zone") or []
                            if zone_list:
                                break
            if not isinstance(zone_list, list):
                zone_list = [zone_list] if zone_list else []
            zone_ids = []
            for z in zone_list:
                zid = None
                if isinstance(z, dict):
                    zid = z.get("ZoneId") or z.get("zone_id")
                else:
                    zid = getattr(z, "zone_id", None) or getattr(z, "ZoneId", None)
                if zid:
                    zone_ids.append(zid)
            if zone_ids:
                print("%-20s %-12s %s" % (region_id, region_name, ", ".join(zone_ids)))
                available.append((region_id, region_name, zone_ids))
            else:
                print("%-20s %-12s (无)" % (region_id, region_name))
        except Exception as e:
            err = str(e)
            if "InvalidInstanceType" in err or "NotSupported" in err:
                print("%-20s %-12s (规格不可用)" % (region_id, region_name))
            else:
                print("%-20s %-12s 查询失败: %s" % (region_id, region_name, err[:50]))

    print("-" * 60)
    if available:
        print("\n有 %s 的地域: %s" % (instance_type, ", ".join(r[0] for r in available)))
    else:
        print("\n未在所列海外地域中发现该规格，可能仅在国内地域售卖。")

if __name__ == "__main__":
    main()
