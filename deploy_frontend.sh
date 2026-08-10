#!/bin/bash
# 前端改动后手动重建部署：build → 拷贝产物到仓库根 → 推送
# 日常数据更新不需要跑这个（cron 只推 data/）
set -e
cd "$HOME/market-hotspot"
echo "① 构建 React…"
cd react && npm run build && cd ..
echo "② 部署产物到仓库根…"
cp react/dist/index.html ./index.html
rm -rf assets && cp -r react/dist/assets ./assets
echo "③ 提交推送…"
git add -A
git diff --cached --quiet || git commit -m "frontend $(date +%F_%H%M)"
git push origin main
echo "✅ https://jwz2003.github.io/market-hotspot/"
