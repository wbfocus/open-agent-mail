# 场景：信用卡账单

把招商银行、民生银行的电子账单整理成一份 HTML 看板：同一商户加总，每一笔消费都在，退款对回原消费。滴滴和高德都算「打车」。

## 怎么用

1. 先按仓库首页绑好你自己的 Agent Mail。
2. 把信用卡电子账单转发到这个邮箱。
3. 对助手说：我已经把信用卡账单转发到我的 Agent Mail，请整理成账单看板。

助手会从收件箱取出账单，生成 `docs/dashboard.html`。

也可以自己生成：把 `.eml` 放进仓库根目录的 `bills/`，然后运行：

```bash
python scenarios/credit-card/build_ledger.py --input bills --output docs/dashboard.html
```

需要 Python 3.9 及以上，只用标准库。

账单原件和生成的看板含有个人消费，不要提交到公开仓库。
