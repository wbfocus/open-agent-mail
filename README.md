# Agent Mail 运用

这是一个 [Agent Mail](https://agent.qq.com) 的运用项目。每个场景都是：先绑上你自己的邮箱，再把相关邮件转进去，由助手帮你整理。

信用卡账单只是其中一个场景。

## 开始之前

克隆之后，先绑定你自己的 Agent Mail：

```bash
npm install -g @tencent-qqmail/agently-cli
agently-cli auth login
agently-cli +me
```

`auth login` 用微信扫码。每台电脑单独授权，登录的是你自己的邮箱。

## 场景

| 场景 | 说明 |
| --- | --- |
| [信用卡账单](scenarios/credit-card/README.md) | 把招商银行、民生银行的电子账单转发到你的 Agent Mail，整理成 HTML 看板 |

在 Cursor 里对助手说你要做哪个场景。助手会先确认邮箱已经绑好，再告诉你把什么邮件转发过去。
