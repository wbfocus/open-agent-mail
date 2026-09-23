# 信用卡账单看板

把招商银行、民生银行的电子账单整理成一份 HTML 看板：同一商户加总，每一笔消费都在，退款对回原消费。

克隆之后先做两件事。

## 1. 绑定你自己的 Agent Mail

```bash
npm install -g @tencent-qqmail/agently-cli
agently-cli auth login
agently-cli +me
```

`auth login` 用微信扫码。每台电脑单独授权，登录的是你自己的邮箱。

## 2. 把信用卡账单转发到这个邮箱

把招商银行或民生银行的信用卡电子账单，转发到第 1 步绑好的 Agent Mail。

然后在 Cursor 里对助手说：

> 我已经把信用卡账单转发到我的 Agent Mail，请整理成账单看板。

助手会从你的收件箱取出账单，生成 `docs/dashboard.html`。用浏览器打开即可。

也可以自己生成：把 `.eml` 放进 `bills/`，然后运行：

```bash
python mail-materials/build_ledger.py --input bills --output docs/dashboard.html
```

需要 Python 3.9 及以上，只用标准库。

## 看板里有什么

- 各月应还、真实消费、还款是否盖住上期
- 支付排序：去掉「支付宝-」「财付通-」之后，同名商户加在一起
- 点开商户可以看到每一笔。金额再小也会留下
- 退款按金额和商户对回原来的消费

目前能解析招商银行信用卡电子账单，以及民生银行电子对账单。

## 隐私

`bills/` 里的邮件和生成的看板含有你的消费明细，已写在 `.gitignore` 里，不要提交到公开仓库。

## 许可

[MIT](LICENSE)
