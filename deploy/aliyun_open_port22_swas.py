#!/usr/bin/env python3
"""
轻量应用服务器（Simple Application Server）放行 22 端口。
需配置阿里云 AccessKey 与实例信息。

依赖: pip install aliyun-python-sdk-swas-open aliyun-python-sdk-core
用法:
  # 方式一：已知实例 ID 和地域（控制台实例详情页可见）
  ALIBABA_CLOUD_ACCESS_KEY_ID=xxx ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx \\
    python3 deploy/aliyun_open_port22_swas.py --instance-id i-xxx --region-id cn-hangzhou

  # 方式二：只填 IP，脚本会尝试根据公网 IP 查找实例（需该账号下仅有该实例或第一个匹配）
  ALIBABA_CLOUD_ACCESS_KEY_ID=xxx ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx \\
    python3 deploy/aliyun_open_port22_swas.py --public-ip 43.99.97.240
"""
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="轻量应用服务器放行 TCP 22 端口")
    parser.add_argument("--instance-id", help="实例 ID（控制台实例详情可查）")
    parser.add_argument("--region-id", default="cn-hangzhou", help="地域 ID，如 cn-hangzhou、ap-southeast-1")
    parser.add_argument("--public-ip", help="公网 IP，用于自动查找实例（若未指定 instance-id）")
    args = parser.parse_args()

    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID") or os.environ.get("ALIYUN_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or os.environ.get("ALIYUN_ACCESS_KEY_SECRET")
    if not access_key_id or not access_key_secret:
        print("请设置环境变量: ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET", file=sys.stderr)
        sys.exit(1)

    try:
        from aliyun_python_sdk_core.client import AcsClient
        from aliyun_python_sdk_swas_open.request.v20200601 import CreateFirewallRuleRequest, ListInstancesRequest
    except ImportError:
        print("请先安装: pip install aliyun-python-sdk-swas-open aliyun-python-sdk-core", file=sys.stderr)
        sys.exit(1)

    region_id = args.region_id
    client = AcsClient(access_key_id, access_key_secret, region_id)

    instance_id = args.instance_id
    if not instance_id and args.public_ip:
        # 尝试根据公网 IP 查找实例
        req = ListInstancesRequest.ListInstancesRequest()
        req.set_accept_format("json")
        try:
            resp = client.do_action_with_exception(req)
            import json
            data = json.loads(resp)
            instances = data.get("Instances") or []
            for inst in instances:
                if inst.get("PublicIpAddress") == args.public_ip or args.public_ip in (inst.get("PublicIpAddress") or ""):
                    instance_id = inst.get("InstanceId")
                    region_id = inst.get("RegionId") or region_id
                    print(f"根据 IP {args.public_ip} 找到实例: {instance_id}, 地域: {region_id}")
                    break
            if not instance_id and instances:
                print("未找到匹配 IP 的实例，将使用第一个实例。", file=sys.stderr)
                instance_id = instances[0].get("InstanceId")
                region_id = instances[0].get("RegionId") or region_id
        except Exception as e:
            print(f"ListInstances 失败: {e}", file=sys.stderr)
            print("请改用 --instance-id 和 --region-id 参数。", file=sys.stderr)
            sys.exit(1)

    if not instance_id:
        print("请提供 --instance-id 或 --public-ip。实例 ID 可在控制台 轻量应用服务器 → 实例详情 中查看。", file=sys.stderr)
        sys.exit(1)

    create_req = CreateFirewallRuleRequest.CreateFirewallRuleRequest()
    create_req.set_accept_format("json")
    if hasattr(create_req, "add_query_param"):
        create_req.add_query_param("InstanceId", instance_id)
        create_req.add_query_param("RegionId", region_id)
        create_req.add_query_param("RuleProtocol", "TCP")
        create_req.add_query_param("Port", "22/22")
        create_req.add_query_param("Remark", "SSH-22-deploy")
    else:
        create_req.set_InstanceId(instance_id)
        create_req.set_RegionId(region_id)
        create_req.set_RuleProtocol("TCP")
        create_req.set_Port("22/22")
        create_req.set_Remark("SSH-22-deploy")

    try:
        client.do_action_with_exception(create_req)
        print("已放行 TCP 22 端口。请稍等几秒后重试: ./deploy/check-ssh.sh")
    except Exception as e:
        err_msg = str(e)
        if "Duplicate" in err_msg or "already" in err_msg.lower() or "已存在" in err_msg:
            print("22 端口规则已存在，无需重复添加。若仍无法 SSH，请检查实例是否运行、本机网络是否可达。")
        else:
            print(f"添加规则失败: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
