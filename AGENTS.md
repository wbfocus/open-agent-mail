# 给助手的要求

用户克隆本仓库后，先完成下面两步。两步都做完之前，不要开始整理账单，也不要读取任何邮箱。

## 1. 绑定用户自己的 Agent Mail

要求用户在本机执行：

```bash
npm install -g @tencent-qqmail/agently-cli
agently-cli auth login
agently-cli +me
```

`auth login` 会打开微信扫码。必须是这位用户自己的 Agent Mail，不要使用仓库作者、示例账号或上一台电脑的登录。

`+me` 成功后，把邮箱地址告诉用户，并确认已经绑好。未登录成功就停在这里。

## 2. 请用户把信用卡账单转发到他自己的 Agent Mail

明确告诉用户：

- 可以把招商银行、民生银行的信用卡电子账单，转发到刚刚绑好的那个 Agent Mail。
- 转发完成后，跟助手说一声。助手从他的收件箱取出这些账单，整理成 HTML 看板。
- 看板规则：同一商户加总；每一笔消费都列入，不因为金额小就丢掉；退款对回原来的消费，不全额退的按剩下的金额计。滴滴和高德都算「打车」。

收到用户确认已经转发之后，再做这些事：

1. 用 `agently-cli message +list` 找到账单邮件，把 `.eml` 附件下载到 `bills/`。
2. 运行 `python mail-materials/build_ledger.py --input bills --output docs/dashboard.html`。
3. 用浏览器打开生成的看板，核对笔数和金额没有漏。
4. 不要把 `bills/` 里的原件、`dashboard-data.json` 或生成的看板提交到 Git。这些是用户的私人消费。
