# 智维空间开关

智维空间暂时关闭，不对客户端开放。

## 默认

```env
SASES_ZHIWEI_ENABLED=0
```

关闭时：

```text
发现页不显示入口
 /wisdom-space/nodes 返回 404
引导第 4–7 步自动跳过
```

## 恢复

```env
SASES_ZHIWEI_ENABLED=1
```

并在宿主页面注入：

```js
window.SASES_ZHIWEI_ENABLED = true;
```

前端入口才会显示。

## 说明

这是临时开关，不是删除功能。

数据、路由、宠物/基地功能保留；只关闭入口和节点读取。
