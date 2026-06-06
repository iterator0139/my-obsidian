#!/opt/homebrew/bin/bash
#
# 欠款标签翻转 - 命令生成器
# 生成一段可靠的 heredoc 命令，粘贴到 pod 终端自动执行
#
# 用法:
#   ./gen_reset_commands.sh <store_id1> [store_id2] ...
#   ./gen_reset_commands.sh store_ids.txt
#   ./gen_reset_commands.sh 1261156 1211344 1209927 > cmd.sh  （输出到文件备用）
#
# 工作流:
#   1. 本地执行此脚本
#   2. 终端 smcsh 登录 pod
#   3. 复制输出的全部内容，粘贴到 pod 终端
#   4. 自动创建脚本并执行，全程无需干预
# =============================================================================

BILLING_HOST="codis.shopeefood-ads-adsbillingsvr-vn-vn-live.ap-vn-2-general-a.vtbd.live.cache.shopee.io"
BILLING_PORT="8388"
BILLING_AUTH="kRCN1MU0VdTw"

ZHENGPAI_HOST="codis.shopeefood-ads-adsdataserver-vn.ap-vn-2-private-a.vtbd.live.cache.shopee.io"
ZHENGPAI_PORT="8156"
ZHENGPAI_AUTH="MnspRajDAeIO"

KEY_PREFIX="food_ads_update_ads_store_status"
KEY_SUFFIX="live_vn"

# --- 解析参数 ------------------------------------------------
STORE_IDS=()

for arg in "$@"; do
    case "$arg" in
        --help|-h)
            sed -n '4,20p' "$0" | sed 's/^#//'
            exit 0
            ;;
        *.txt)
            if [ -f "$arg" ]; then
                while IFS= read -r line; do
                    line="$(echo "$line" | xargs)"
                    [ -n "$line" ] && STORE_IDS+=("$line")
                done < "$arg"
            else
                echo "File not found: $arg" >&2
                exit 1
            fi
            ;;
        *)
            STORE_IDS+=("$arg")
            ;;
    esac
done

if [ ${#STORE_IDS[@]} -eq 0 ]; then
    echo "Usage: $0 <store_id1> [store_id2] ..."
    echo "       $0 store_ids.txt"
    exit 1
fi

# --- 生成 key 列表 -------------------------------------------
KEYS=()
for id in "${STORE_IDS[@]}"; do
    KEYS+=("${KEY_PREFIX}_${id}_${KEY_SUFFIX}")
done

# ─── 输出：一条 heredoc 命令，粘贴到 pod 终端即可 ──────────
echo ""
echo "# ============================================================"
echo "#  欠款标签翻转 - 粘贴后自动执行"
echo "#  生成时间: $(date '+%Y-%m-%d %H:%M')"
echo "#  操作 store 数: ${#STORE_IDS[@]}"
echo "# ============================================================"
echo ""

# 生成的脚本内容（通过 cat heredoc 写入临时文件再执行）
echo "cat > /tmp/reset_debt.sh << 'PASTEHERE'"
echo "#!/bin/bash"
echo ""

# ---- billing Redis ----
echo "echo \"===== Billing Redis =====\""
echo "BH=$BILLING_HOST"
echo "BP=$BILLING_PORT"
echo "BA='$BILLING_AUTH'"
echo "billing_redis() { redis-cli -h \"\$BH\" -p \$BP -a \"\$BA\" \"\$@\"; }"
echo ""
for key in "${KEYS[@]}"; do
    echo "val=\$(billing_redis GET \"$key\" 2>/dev/null)"
    echo "echo \"  [$key] current=\${val:-(nil)}\""
    echo "if [ -z \"\$val\" ] || [ \"\$val\" = \"true\" ]; then"
    echo "  billing_redis SET \"$key\" \"false\" >/dev/null && echo \"  => set false ✓\""
    echo "else"
    echo "  echo \"  => skip (already false)\""
    echo "fi"
done
echo ""

# ---- zhengpai Codis ----
echo "echo \"===== Zhengpai Codis =====\""
echo "ZH=$ZHENGPAI_HOST"
echo "ZP=$ZHENGPAI_PORT"
echo "ZA='$ZHENGPAI_AUTH'"
echo "zhengpai_redis() { redis-cli -h \"\$ZH\" -p \$ZP -a \"\$ZA\" \"\$@\"; }"
echo ""
for key in "${KEYS[@]}"; do
    echo "val=\$(zhengpai_redis GET \"$key\" 2>/dev/null)"
    echo "echo \"  [$key] current=\${val:-(nil)}\""
    echo "if [ -z \"\$val\" ] || [ \"\$val\" = \"true\" ]; then"
    echo "  zhengpai_redis SET \"$key\" \"false\" >/dev/null && echo \"  => set false ✓\""
    echo "else"
    echo "  echo \"  => skip (already false)\""
    echo "fi"
done
echo ""
echo "echo \"===== Done =====\""

# 结束 heredoc 并执行
echo "PASTEHERE"
echo "chmod +x /tmp/reset_debt.sh"
echo "bash /tmp/reset_debt.sh"

echo ""
echo "# 复制上面全部内容（从 cat > 到 bash 那行），粘贴到 pod 终端即可"
echo ""
