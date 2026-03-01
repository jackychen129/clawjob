# ECS 实例规格 ecs.e-c1m2.large 地域可用性

## 官方查询方式（最准确）

在阿里云控制台按地域查看实例规格是否可售：

- **实例规格可购买地域**：https://ecs-buy.aliyun.com/instanceTypes/#/instanceTypeByRegion  
  选择地域（如「华东1」、「新加坡」等），在列表中查找 **ecs.e-c1m2.large** 是否出现及所在可用区。

## 已知说明（来自阿里云文档与社区）

- **ecs.e-c1m2.large** 属于**经济型 e 实例**（2 核 4G，高性价比）。
- 经济型 e 实例**目前主要在国内约 32 个可用区售卖**，海外地域上架情况较少且会变动。
- 海外地域（如新加坡 ap-southeast-1、香港 cn-hongkong、美国等）是否支持该规格，需以控制台或 API 实时查询为准。

## 本仓库脚本查询（需配置 AccessKey）

在项目下用 API 批量查海外地域是否有该规格：

```bash
cd /path/to/clawjob
export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=yyy
# 或从 jasonproject/aliyun/accesskey.txt 读取
python3 deploy/list_regions_for_instance_type.py ecs.e-c1m2.large
```

脚本会遍历新加坡、日本东京、中国香港、悉尼、吉隆坡、雅加达、美国硅谷/弗吉尼亚、法兰克福、伦敦、迪拜、印度孟买等海外地域，并输出有该规格的地域及可用区（若 API 返回正常）。

## 若海外无 ecs.e-c1m2.large

创建海外 ECS 时可改用当前海外常用规格，例如：

- **ecs.g6.large**（通用型）
- **ecs.c6.large**（计算型）

在 `create-ecs-singapore-cli.sh` 或 `aliyun_ecs_create.py` 中通过环境变量指定：

```bash
export ALIBABA_CLOUD_ECS_INSTANCE_TYPE=ecs.g6.large
bash deploy/create-ecs-singapore-cli.sh
```
