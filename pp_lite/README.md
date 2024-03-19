# 隐私求交轻客户端

## 文件结构
轻客户端的文件由以下几个部分组成，
- images/pp_lite：定义容器入口shell脚本，以及Dockerfile。
- pp_lite：定义具体业务逻辑和客户端打包方法。
- tools/tcp_grpc_proxy：提供了tcp转grpc的功能，主要用于OtPsi。
```
images
.
└── pp_lite
    ├── nginx.tmpl  # nginx模版或其他脚本
    ├── entrypoint.sh  # 入口文件  
    └── Dockerfile
```

```
pp_lite
.
├── cli.py     # 入口文件
├── requirements.txt
├── data_join  # 求交实现
│   ├── psi_rsa   # rsa求交
│   ├── psi_ot    # ot求交
│   └── utils
├── rpc     # rpc相关代码
├── test    # 集成测试
└── deploy  # 轻客户端打包脚本
```
- 其中cli.py通过click实现，封装了轻客户端提供的各种功能。images/psi/scripts/entrypoint.sh将外部参数透传给cli.py。
- test中实现了一些集成测试，一些局部的ut和被测试文件放在一起。
- proto文件不单独存放，放在具体的使用的位置。

## 镜像管理方式
整个轻客户端只打包一个镜像，其中
- Dockerfile存储在images/pp_lite/Dockerfile
- 入口脚本为images/pp_lite/entrypoint.sh

通过传递不同的参数指定容器不同的行为。

## 使用方式
- 服务端通过平台中的数据模块进行求交。
- 客户端的使用方式可参考pp_lite/deploy/README.md。

具体demo可参考test中的测试用例。