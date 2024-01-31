# 谁的部下-服务端

**api文档：**

[文档](https://console-docs.apipost.cn/preview/1018646bc0731d14/568487a7e7010728)

**关联项目：**

[谁的部下-Android](https://github.com/KT-network/subordinate)

[部下-设备](https://github.com/KT-network/subordinate-esp32)

**需要的第三方服务：**

- MySql
- EMQX
- Rabbitmq

**介绍**

- 使用flask做为框架
- 为esp32/esp8266等物联网设备开发的服务端
- 所有的上位机控制必经此服务端的转发到设备

**功能**

- [x] 用户登录
- [x] 设备绑定
- [x] 开关的控制
- [x] 定时任务
- [ ] 像素屏的显示
- [ ] 像素屏的应用商店
