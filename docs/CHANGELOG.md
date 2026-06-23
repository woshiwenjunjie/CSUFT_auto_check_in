# 更新日志

## [0.15.0] — 2026-06-23

### 文档与根目录整理
- 完全重写 `README.md`，按当前实际功能描述 CLI、SCF、GitHub Actions、通知、测试和阶段三状态。
- 更新 `docs/README.md` 文档总入口，移除旧版乱码和过期版本描述。
- 版本号更新为 `v0.15.0`，测试数更新为 114。
- 清理根目录临时测试目录 `.pytest-tmp/` 和临时残片 `tmp_old.txt`。
- `.gitignore` 增加 `.pytest-tmp/`、`.claude/`，避免本地工具和测试临时文件污染根目录。

### 验证
- `python -m pytest tests/ -q --basetemp .pytest-tmp`：114 passed。
- `python scripts/tools/cross_validate.py`：5 组 JS/Python 签名交叉验证通过。

## [0.14.0] — 2026-06-23

### 🔧 CI/CD 重构：SCF 优先，GitHub Actions 单用户备选
- **`auto-checkin.yml` 重写**：拆分为 `multi-user` + `single-user` 双 Job，通过 `vars.CHECKIN_PROFILES` 自动选择
- **多用户凭据动态注入**：从 `${{ vars.CHECKIN_PROFILES }}` 自动循环读取对应 `${{ secrets.CHECKIN_OPENID_USER_X }}`，无需手动编辑 workflow
- **`auto_checkin.sh` 精简**：从 349 行降至 ~70 行，纯编排脚本，打卡+通知全交 Python 模块
- **`src/utils/notification.py` 新增 `send_telegram()`**：统一 Telegram 通知通道，与 Server酱 平级
- **`src/utils/notification.py` 新增 `send_notifications()`**：一键发送所有配置通道（Server酱 + Telegram）
- **keepalive 独立 Job**：避免因打卡 Job 失败而跳过保活提交

### 🗑️ 移除
- `auto_checkin.sh` 中的 bash 版 `send_serverchan` / `send_telegram` / 多用户通知拼接逻辑（全部迁移至 Python）

### 📦 文档同步
- AGENTS.md 更新测试计数：102 → 106；新增 CI/CD 结构说明
- README 更新 GitHub Actions 章节：SCF 优先 + 多用户动态凭据说明

# 鏇存柊鏃ュ織

## [0.13.0] 鈥?2026-06-15

### 馃彈锔?鍏变韩妯″潡閲嶆瀯锛圕LI + SCF 缁熶竴锛?
- **鏂板缓 3 涓叡浜ā鍧?*锛歚src/core/sign_builder.py`锛堟墦鍗¤姹備綋鏋勫缓锛夈€乣src/utils/notification.py`锛圫erver閰?鎺ㄩ€?绐楀彛妫€娴?閫氱煡鏋勫缓锛夈€乣src/core/token_client.py`锛圫CF 鐜鍙橀噺鈫扐piClient 閫傞厤鍣級
- **绐楀彛妫€娴嬬Щ鍏ュ叡浜?*锛歚is_window_open()` / `window_hint()` 浠?SCF 涓撶敤绉昏嚦 `notification.py`锛孋LI + SCF 鍏辩敤
- **`deploy/tencent-scf/notify.py` 鍒犻櫎**锛屽悎骞惰嚦 `src/utils/notification.py`
- **`ApiTokenClient`** 浠?SCF `checkin.py` 鎻愬彇鍒?`src/core/token_client.py`
- **SCF `checkin.py` 绮剧畝**锛氫粠 ~250 琛岄檷鑷?~80 琛岋紙绾紪鎺掑眰锛屼娇鐢ㄥ叡浜ā鍧楋級
- **CLI `checkin.py`**銆丼CF `checkin.py` 缁熶竴璋冪敤 `build_notification() + send_serverchan()`

### 馃敡 CLI 绮剧畝
- **鍛戒护 11鈫?**锛氬垹闄?`login` 姝讳唬鐮佸懡浠わ紱`record`/`month` 鍚堝苟鍒?`checkin --record`/`--month`
- **`auth.py`** 鍒犻櫎鏈娇鐢ㄧ殑 `login()` 鍑芥暟

### 馃 capture 涓€姝ュ埌浣?
- `capture_addon.py`锛氭崟鑾?OpenID 鍚庤嚜鍔ㄨ皟鐢?`sign_in_openid` 鐧诲綍锛岀渷鍘?`login-openid` 绗簩姝?
- 娣诲姞鏂拌处鍙锋祦绋嬶細3 姝?鈫?2 姝?

### 馃摤 Server閰?閫氱煡澧炲己
- **绐楀彛鐘舵€佽**锛氶€氱煡姝ｆ枃鑷姩鏄剧ず `馃獰 璺濈寮€绐楄繕鏈?X 灏忔椂 X 鍒嗛挓` / `馃獰 绐楀彛杩樺墿 X 鍒嗛挓` / `馃獰 绐楀彛宸插叧闂璥
- **鎴愬姛/澶辫触鍒嗙粍**锛氣渽 鎴愬姛鍦ㄥ墠锛屸潓 澶辫触鍦ㄥ悗锛屼竴鐩簡鐒?
- **鑻辨枃鐮佽浆涓枃**锛歚ok: 0.12` 鈫?`姝ｅ父 (0.12km)`锛宍error: 鐧诲綍澶辫触` 鈫?`澶辫触: 鐧诲綍澶辫触`
- **鏍囬甯︽棩鏈?*锛歚鎵撳崱姹囨€?06-15 | 2/3`
- **SCF 閿欒淇℃伅绮剧‘鍖?*锛歚error` 鏀逛负 `澶辫触: 鍏蜂綋鍘熷洜`锛屼笉鍐嶅彧鏈夎８ `error`

### 馃悰 Bug 淇
- **SCF `sign_date` 鏍煎紡淇**锛歚token_client.py:96` 璇敤 `%H:%M:%S` 甯︽椂鍒嗙锛屽鑷?`compute_stu_task_id` 绛惧悕涓庢湇鍔″櫒涓嶄竴鑷达紝鍏ㄨ处鍙疯繑鍥?绛惧埌澶辫触锛岃閲嶈瘯锛?

### 馃帹 浣撻獙浼樺寲
- GPS 鍋忕Щ缁熶竴涓?0.002锛圕LI 鍘?0.0003 涓嶄竴鑷村凡淇锛?
- CLI 鎶ラ敊淇℃伅鍙嬪ソ鍖栵紙绾㈣壊閿欒 + 鐏拌壊淇鎻愮ず锛?
- 閫氱煡鏃堕棿鏍囨敞 `(鍖椾含鏃堕棿)` 閬垮厤鏃跺尯娣锋穯

### 馃И 娴嬭瘯
- test_checkin_core.py锛?4 鈫?29锛堟柊澧?`_map_display` 7 涓?+ `BuildNotificationDetail` 4 涓?+ 绐楀彛閫氱煡琛?4 涓級
- 鎬昏 106 娴嬭瘯鍏ㄩ儴閫氳繃
- SCF 鎵撳寘 1.3 MB锛実en-env 姝ｅ父

## [0.10.0] 鈥?2026-06-14

### 馃摎 鏂囨。浣撶郴閲嶆瀯
- **鏂板缓 `docs/README.md`** 鈥?鏂囨。鎬荤储寮曪紝缁熶竴瀵艰埅鍏ュ彛
- **鏂板缓 `getting-started/`** 鈥?蹇€熷紑濮嬨€侀厤缃悜瀵笺€佸父瑙侀棶棰?3 绡囨柊鎵嬫寚鍗?
- **鏂板缓 `reference/`** 鈥?4 绡囨繁搴︽妧鏈暀绋嬮噸鏋勶紙绛惧悕绠楁硶銆佸皬绋嬪簭閫嗗悜銆佽璇佹姄鍖呫€亀xapkg鎻愬彇锛?
- **鏂板缓 `development/`** 鈥?闃舵涓夎矾绾垮浘銆佹暟鎹簱璁捐璇勫銆佸悗绔?API 璁捐瑙勮寖
- **鏂板 `reference/API绔偣鍙傝€?md`** 鈥?8 涓鏍?API 鎺ュ彛鏂囨。
- **鏂板 `reference/CLI鍛戒护閫熸煡琛?md`** 鈥?13 涓瓙鍛戒护涓€椤甸€熸煡
- **杩佺Щ**锛氬叧閿瘝涓庢蹇甸€熸煡浠?guides/user 杩佸叆 reference/

### 馃洜锔?浠ｇ爜鍋ュ悍妫€鏌?
- **鍏ㄦā鍧楃被鍨嬫敞瑙?* 鈥?瑕嗙洊 `src/`銆乣scripts/`銆乣deploy/tencent-scf/` 鍏?18 涓枃浠?
- **淇 5 涓仐鐣欓棶棰?*锛?
  - `sign.py` 娑堥櫎鍏ㄥ眬鐘舵€佺獊鍙橈紙`generate_sign` 鍙傛暟鍖栵級
  - `auth.py` 澧炲姞 token 绌哄€兼樉寮忔娴?
  - `checkin.py` GPS 闃堝€奸厤缃寲锛坄_DEFAULT_GPS_OFFSET` 绛夋ā鍧楀父閲忥級
  - `_common.py` / `cli_config.py` 澧炲姞 `client_mode` 鍚堟硶鎬ф牎楠?
- **娴嬭瘯澧炲己**锛氭柊澧?`tests/test_client_integration.py`锛? 涓?mock 闆嗘垚娴嬭瘯锛?
- **杈圭晫娴嬭瘯琛ュ厖**锛歚test_geo.py` +7 娴嬭瘯锛堢┖鍧愭爣銆佹瀬绔粡绾害銆侀浂鍋忕Щ锛?
- **杈圭晫娴嬭瘯琛ュ厖**锛歚test_sign.py` +3 娴嬭瘯锛堢┖璺緞銆佷腑鏂囪矾寰勩€佸惈绌烘牸璺緞锛?
- **鎬绘祴璇曟暟**锛?7 鈫?**85**

### 馃敡 宸ュ叿鑴氭湰
- **鏂板缓 `scripts/tools/verify_sign.py`** 鈥?浜や簰寮忕鍚嶉獙璇侊紝鏀寔 `--js` 瀵规瘮 Node.js
- **鏂板缓 `scripts/tools/cross_validate.py`** 鈥?5 缁勯殢鏈哄弬鏁拌嚜鍔ㄤ氦鍙夐獙璇?
- **鏂板缓 `scripts/tools/decompile_wxapkg.py`** 鈥?wxapkg 瑙ｅ寘杈呭姪锛堟鏌ヤ緷璧?+ 瑙ｅ寘 + 鍒楁枃浠讹級

### 馃摉 鏂囨。
- `AGENTS.md` 鈥?鏂囨。鐩綍/tools 璺緞/宸ュ叿鑴氭湰/85 娴嬭瘯鍚屾
- `README.md` 鈥?寰界珷 67鈫?5锛岀洰褰曠粨鏋勫悓姝?
- `docs/superpowers/plans/` 鈥?瀹屾暣瀹炴柦璁″垝鏂囨。

## [0.9.1] 鈥?2026-06-12

### 馃幆 SCF 閮ㄧ讲浼樺寲

**Cron 鏃跺尯淇**锛堢涓夋鏃跺尯鍧戯級锛?
- SCF 鎺у埗鍙?Cron 榛樿鍖椾含鏃堕棿锛圲TC+8锛夛紝闈?UTC
- 琛ㄨ揪寮忎粠 `5 13 * * *` 鈫?`0 5 21 * * ? *`锛? 瀛楁鏍煎紡锛屽惈绉?骞达級
- 鍏ㄩ噺鏂囨。銆佷唬鐮佹敞閲娿€乨ry-run 杈撳嚭鍚屾淇

**閫氱煡浼樺寲**锛?
- `_build_notification` 涓?GitHub Actions 椋庢牸瀵归綈
- 鎵撳崱鎴愬姛鏃舵樉绀?GPS 璺濈锛歚**2026-06-12** | 鐘舵€侊細姝ｅ父 | 璺濆鑸?15.3m`
- 閲嶅鎵撳崱鎻愮ず娆℃棩绐楀彛锛歚> 娆℃棩 **21:00鈥?2:30** 鑷姩鎵ц涓嬫鎵撳崱`
- Token 杩囨湡澧炲姞鎿嶄綔鎸囧紩锛歚> CLI: \`capture-openid\` / Fiddler / Reqable`
- `do_checkin` 杩斿洖 3 鍏冪粍 `(bool, str, str)` 浼犻€掕窛绂?

**绐楀彛妫€娴?*锛?
- 鏂板 `_is_window_open()` / `_nearest_window_hint()` 妫€娴嬪綋鍓嶆椂闂?
- 绐楀彛澶栬嚜鍔ㄨ繑鍥?`nowindow` 鐘舵€佽€岄潪 `error`
- 鎻愮ず淇℃伅鏄剧ず灏忔椂+鍒嗛挓锛歚"杩樻湁 8 灏忔椂 25 鍒嗛挓"`
- 绐楀彛鍐呮湁浠诲姟鍒欐甯告墦鍗★紝鏃犱换鍔℃彁绀?`"鍙兘浠婃棩鏈彂甯?`

**鍑芥暟娉ㄩ噴琛ラ綈**锛?
- 鍏ㄩ儴 9 涓嚱鏁版柊澧?瀹屽杽 docstring锛坄_is_window_open`銆乣_nearest_window_hint`銆乣run_checkin`銆乣_notify_and_return`銆乣_build_notification`銆乣get_env_str` 绛夛級

### 馃摉 鏂囨。
- `README.md` 鈥?寰界珷 31鈫?7锛屽姛鑳藉垪琛ㄣ€佹祴璇曡〃銆佺洰褰曠粨鏋勫悓姝ユ洿鏂?
- `CLAUDE.md` 鈥?SCF Cron 鏍煎紡淇锛岀姸鎬佹弿杩版洿鏂?
- `docs/guides/user/鑵捐浜慡CF閮ㄧ讲鎸囧崡.md` 鈥?缁嗗寲 7 姝ユ祦绋嬶紝鍑嵁鑴辨晱锛孋ron 璇存槑

## [0.12.0] 鈥?2026-06-14

### 馃悰 SCF 澶氱敤鎴烽摼璺慨澶?

**1. 澶氱敤鎴烽€氱煡缁熶竴璧?`_build_notification`**
- `_build_notification` 閲嶆瀯锛歚detail` 瀛楁瀵瑰叏閮ㄧ姸鎬佺敓鏁堬紙涓嶄粎 `ok`锛夛紝姣忔潯閫氱煡鏈熬缁熶竴杩藉姞 `馃晲 鍖椾含鏃堕棿` 鏃堕棿鎴?
- `_do_multi_or_single` 澶?profile 鍒嗘敮锛氭眹鎬荤粨鏋滈€氳繃 `_build_notification` 鏋勯€犻€氱煡鏍囬+姝ｆ枃锛屼笌鍗曠敤鎴疯矾寰勬牸寮忎竴鑷?
- 鏂板 `partial` 鐘舵€佹祴璇?2 涓紙`test_partial_status`銆乣test_partial_with_detail`锛?

**2. 閿欒娑堟伅绮剧‘鍖?*
- `_checkin_one` 涓?`not openid or not username` 鍒ゆ柇鎷嗗垎涓虹嫭绔嬫娴?
- 鍒嗗埆鍒楀嚭 `CHECKIN_OPENID_USER_X` 鎴?`CHECKIN_USERNAME_USER_X`锛屼笉鍐嶇缁熷啓涓€涓?

**3. 鍗曡处鍙峰紓甯搁殧绂?*
- 澶氱敤鎴峰惊鐜腑姣忎釜 `_checkin_one()` 璋冪敤鍖?try/except
- 浠讳竴璐﹀彿鎶涘嚭鏈鏈熷紓甯镐笉浼氶樆鏂悗缁处鍙锋墽琛?

**4. 鐘舵€佺爜淇**
- 閮ㄥ垎鎴愬姛鏃?status 浠?`"ok"` 鈫?`"partial"`锛圫erver閰?鏍囬涓嶅啀璇爣 鉁咃級
- 鍏ㄥけ璐ユ椂 status 浠?`all_results[0]["status"]` 鈫?鍥哄畾 `"error"`
- 鍗?profile 璧?`_notify_and_return`锛屽 profile 璧?`_build_notification` 姹囨€?

### 馃殌 SCF 榛樿澶氱敤鎴?+ 閮ㄧ讲宸ュ叿澧炲己

- `handler.py`锛氱Щ闄?`CHECKIN_PROFILES` 妫€娴嬪垎鏀紝榛樿濮嬬粓璋冪敤 `run_multi_checkin()`
- `deploy.py`锛氭柊澧?`gen-env` 瀛愬懡浠わ紝浠?`password.txt` 鐢熸垚 SCF 鎺у埗鍙板彲瀵煎叆鐨?`scf_env.json`
- `deploy.py`锛氭柊澧?`--env-json` 鍙傛暟锛岄儴缃叉椂閫氳繃 SCF CLI 闄勫甫鐜鍙橀噺
- `tests/deploy/test_handler.py`锛歚patch` 鐩爣浠?`run_checkin` 鏀逛负 `run_multi_checkin`

### 馃摝 GitHub Actions 澶氱敤鎴锋敮鎸?

- `.github/workflows/auto-checkin.yml`锛歚timeout-minutes: 5` 鈫?`10`
- `scripts/auto_checkin.sh`锛氭柊澧?`_get_env` 鍑芥暟 + `CHECKIN_PROFILES` 瑙ｆ瀽 + 澶氱敤鎴?config.json 鍐欏叆 + `--profiles` 鎵归噺鎵撳崱 + 姹囨€婚€氱煡

### 馃摉 鏂囨。

- `README.md`锛欸itHub Secrets 鍛藉悕 `OPENID`/`USERNAME`/`PASSWORD` 鈫?`CHECKIN_OPENID`/`CHECKIN_USERNAME`/`CHECKIN_PASSWORD`
- `deploy/tencent-scf/README.md`锛氶噸鍐欎负 11 绔犲畬鏁存暀绋嬶紝澶氱敤鎴蜂紭鍏堬紝鍚姣?娉ㄥ唽/鎶撳寘/鎵撳寘/閰嶇疆/瑙﹀彂鍣?鎺掗殰
- `password.txt`锛氱幆澧冨彉閲忓悕鍔?`_USER_X` 鍚庣紑锛屽榻?SCF 澶氱敤鎴锋牸寮?
- `AGENTS.md`锛氭祴璇曟暟 85 鈫?87锛孲CF 妯″潡琛ㄥ鍔?`gen-env` 璇存槑

### 馃И 娴嬭瘯

- 87 娴嬭瘯鍏ㄩ儴閫氳繃锛?5 鍘?+ 2 鏂板 `partial` 鐘舵€佹祴璇曪級

## [0.11.0] 鈥?2026-06-14

### 馃懃 澶氱敤鎴锋墦鍗＄郴缁?

**澶?profile 閰嶇疆鏀寔**锛?
- `cli_config.py` 閰嶇疆鏍煎紡鍗囩骇锛歚profiles` 瀛楀吀 + `current_profile` 鍒囨崲锛岃嚜鍔ㄨ縼绉绘棫鐗堟墎骞抽厤缃?
- 鏂板 `list_profiles()` / `switch_profile()` / `save_config(cfg, profile=...)` 鎺ュ彛
- `load_config(profile=...)` 鏄惧紡 profile 鍙傛暟锛岄粯璁よ繑鍥?current_profile

**鍏嶅瘑鐮佺櫥褰?*锛?
- `auth.py` 鏀寔 `--bind 0` 鏃犲瘑鐮佺櫥褰曪紙宸茬粦瀹?OpenID 鐨勮处鍙峰彲璺宠繃瀵嗙爜杈撳叆锛?
- 瀵嗙爜涓嶅啀蹇呭～锛宐ase64 娣锋穯瀛樺偍淇濈暀

**鍏ㄥ眬 --profile 鍙傛暟**锛?
- 娉ㄥ叆 `setup`銆乣status`銆乣config`銆乣login-openid`銆乣login-webvpn`銆乣login`銆乣tasks`銆乣detail`銆乣checkin`銆乣record`銆乣month` 鍏ㄩ儴瀛愬懡浠?
- `config profile list` / `config profile <鍚嶇О>` 鏌ョ湅鍜屽垏鎹㈣处鍙?

**鎵归噺鎵撳崱**锛?
- `checkin` 鏂板 `--profiles` 鍙傛暟锛岄€楀彿鍒嗛殧澶氫釜璐﹀彿
- 鏃犲弬鏁版椂榛樿鎵撳崱鍏ㄩ儴宸查厤缃处鍙?
- 姣忎釜 profile 鐙珛鎵ц锛氱櫥褰?鈫?浠诲姟 鈫?GPS 鍋忕Щ 鈫?鎻愪氦 鈫?纭 鈫?姹囨€?

### 馃啎 鏂拌处鍙?
- `USER_2`锛?0234150锛夛細鏂板绗簩 WeChat 璐﹀彿锛屽厤瀵嗙爜缁戝畾
- `USER_3`锛?0234146锛夛細鏂板绗笁 WeChat 璐﹀彿锛屽厤瀵嗙爜缁戝畾

### 馃敡 宸ュ叿淇
- `capture_openid_emulator.py`锛氫笁澶т慨澶?鈥?`mitmdump` 鑷姩鎼滅储 PATH銆乣cert_hash` 闄嶇骇 Python cryptography銆丄ndroid 12 bind mount 鏇夸唬 remount

### 馃摉 鏂囨。鍚屾
- **鏂板缓** `docs/guides/user/妯℃嫙鍣ㄨ嚜鍔ㄦ姄鍙朞penID.md` 鈥?妯℃嫙鍣ㄤ竴閿崟鑾蜂笓绡囷紝鍚畨鍏ㄥ垎鏋?
- **鏇存柊** `docs/guides/user/CLI鏁欑▼.md` 鈥?澶氳处鍙风鐞嗙珷鑺傘€佹ā鎷熷櫒鎹曡幏鏂瑰紡
- **鏇存柊** `docs/guides/user/瀹屾暣鎿嶄綔鎸囧崡.md` 鈥?妯℃嫙鍣ㄦ柟妗堝彇浠?Fiddler 鍋氶閫夛紝鏂板 4.3 澶氳处鍙风鐞?
- **鏇存柊** `docs/reference/璁よ瘉娴佺▼涓庢姄鍖呭垎鏋?md` 鈥?鍥涚鏂规瀵规瘮銆佸畨鍏ㄥ垎鏋?鍏?root 鍐嶇櫥褰?
- **鏇存柊** `docs/getting-started/蹇€熷紑濮?md` 鈥?鎺ㄨ崘鏂规鏀逛负妯℃嫙鍣ㄨ剼鏈?
- **鏇存柊** `docs/getting-started/閰嶇疆鍚戝.md` 鈥?鎹曡幏鏂瑰紡琛ㄦ柊澧炴ā鎷熷櫒
- **鏇存柊** `docs/getting-started/甯歌闂.md` 鈥?澶氳处鍙风鐞?FAQ
- **鏇存柊** `docs/README.md` 鈥?鐩綍绱㈠紩鏂板妯℃嫙鍣ㄦ枃妗ｏ紝淇閾炬帴
- **鏇存柊** `AGENTS.md` 鈥?鏂囨。瀵艰埅鏂板锛屾ā鎷熷櫒鎺ㄨ崘璇存槑

### 馃彈锔?SCF 澶氱敤鎴锋敮鎸?
- `deploy/tencent-scf/checkin.py`锛氭柊澧?`_checkin_one()` / `run_multi_checkin()`锛宍CHECKIN_PROFILES` 鐜鍙橀噺椹卞姩澶氱敤鎴峰惊鐜?
- `deploy/tencent-scf/handler.py`锛氭娴?`CHECKIN_PROFILES` 鑷姩鍒囨崲澶氱敤鎴锋ā寮?
- 姣忎釜 profile 鐙珛鎵ц鐧诲綍鈫掍换鍔♀啋鎵撳崱鈫掔‘璁わ紝姹囨€讳竴娆℃€?Server閰?閫氱煡
- 鍚庣紑鐜鍙橀噺鍛藉悕锛歚CHECKIN_OPENID_USER_1` / `CHECKIN_USERNAME_USER_2` 绛?
- 鍚戝悗鍏煎锛氭棤鍚庣紑 `CHECKIN_OPENID` 浣滀负鍏滃簳锛堝崟鐢ㄦ埛鏃х増鏃犵紳鍗囩骇锛?

### 馃攢 Profile 閲嶅懡鍚?
- `default` 鈫?`USER_1`锛氶厤缃嚜鍔ㄨ縼绉伙紝CLI 鍛戒护銆佹枃妗ｃ€佸府鍔╂枃鏈悓姝ユ洿鏂?
- `deploy/tencent-scf/README.md` 鈥?閲嶅啓锛屽簾寮冩棫 CLI 鏂瑰紡锛岀粺涓€鎵嬪姩涓婁紶娴佺▼

## [0.9.0] 鈥?2026-06-12

### 馃彈锔?SCF 閮ㄧ讲妯″潡閲嶆瀯

鍏ㄦā鍧楅《灞傛敞閲婅鑼冨寲锛堟墽琛屾祦绋嬪浘銆佽璁″師鐞嗐€佺幆澧冨彉閲忚〃銆佺姸鎬佺爜璇存槑锛夛細
- `checkin.py` 鈥?缂栨帓娴佺▼鍥俱€佸欢杩熸椂闂村嚱鏁板師鐞嗐€丟PS 閫€閬跨瓥鐣ャ€? 绉嶇姸鎬佺爜
- `handler.py` 鈥?寮傚父瀹夊叏缃戣璁°€佸仴搴锋鏌ユ敮鎸?
- `notify.py` 鈥?Server閰?鎺ㄩ€佹祦绋嬨€? 娆￠噸璇?3s 闂撮殧
- `deploy.py` 鈥?鎵撳寘閮ㄧ讲鏋舵瀯銆侀敊璇鐞嗕笁鏄庢不

鍙橀噺鍚嶉噸鏋勬彁鍗囧彲璇绘€э細
- `client` 鈫?`api_client`銆乣dorm_lat` 鈫?`dormitory_lat`銆乣cur_offset` 鈫?`current_offset_degrees`
- `stu_task_id` 鈫?`student_task_id`銆乣src_dst` 鈫?`target_src_dir`

妯″潡绾ф椂闂村喕缁撲慨澶嶏細`NOW` 鈫?`_now()` 寤惰繜鍑芥暟锛岄伩鍏?warm start 鍐荤粨銆?

杩愯鏃剁増鏈彉閲忓寲锛歚SCF_RUNTIME` 鐜鍙橀噺锛堥粯璁?Python 3.12锛夈€?

`scf_bootstrap` 鍒犻櫎锛堟爣鍑?Python 杩愯鏃舵棤闇€锛夈€?

### 馃И 瀹屾暣娴嬭瘯瑕嗙洊锛?6 鏂版祴璇曪級

`tests/deploy/` 鐩綍鏂板缓锛? 娴嬭瘯鏂囦欢瑕嗙洊鍏ㄩ儴 SCF 妯″潡锛?

| 鏂囦欢 | 娴嬭瘯鏁?| 瑕嗙洊鍐呭 |
|------|--------|----------|
| `test_notify.py` | 4 | 璺宠繃/鎴愬姛/500/閲嶈瘯 |
| `test_checkin_core.py` | 14 | 鏃堕棿/鐜鍙橀噺/閫氱煡 5 鐘舵€?|
| `test_checkin_api.py` | 7 | GPS 閫€閬?sign_data/MD5 |
| `test_handler.py` | 4 | 鍋ュ悍妫€鏌?姝ｅ父/寮傚父鎹曡幏 |
| `test_deploy_utils.py` | 4 | _fmt_size KB/MB/0 |

conftest.py 閲嶆瀯锛氱Щ闄ゆā鍧楃骇 mock锛岄噰鐢?`@patch('checkin.xxx')` 瀹氱偣鎷︽埅銆?

鎬昏 67 娴嬭瘯锛?1 鍘?+ 36 鏂帮級鍏ㄩ儴閫氳繃銆?

### 馃摉 鏂囨。
- `docs/memory/017-SCF閮ㄧ讲閲嶆瀯涓庢祴璇曞畬鍠?md` 鈥?鏂板
- `AGENTS.md` 鈥?娴嬭瘯鏁版洿鏂?31鈫?7锛?Reaple"鈫?Reqable"锛孲CF 璁捐瑕佺偣琛?
- `CLAUDE.md` 鈥?Four-tier design 鍚?SCF 灞傘€乨eploy 鍛戒护銆佺姸鎬佹洿鏂?

## [0.8.3] 鈥?2026-06-09

### 馃敶 鏃跺尯淇锛堢涓夋锛屾渶缁堟柟妗堬級

**鏍瑰洜**锛歷0.8.2 鐨勩€孶TC 瑙勮寖鍖栥€嶅紩鍏ヤ笁涓繛閿?bug锛?
1. bash `date` + `TZ=Asia/Shanghai` 鍦?GitHub Actions Ubuntu runner 涓婁笉鍙潬 鈫?閫氱煡鏃堕棿鏄剧ず娣蜂贡
2. `TZ` 鐜鍙橀噺鍙兘璇 GitHub Actions cron 璋冨害鍣ㄥ皢 `5 13 * * *` 瑙ｉ噴涓哄寳浜椂闂?13:05
3. 閫氱煡鏍囩鍏ㄦ爣 UTC锛屼笌 date 瀹為檯杈撳嚭鏃跺尯涓嶄竴鑷?

**淇**锛?
- `auto_checkin.sh`锛氬交搴曟斁寮?bash `date`锛屽叏閮ㄦ敼鐢?Python `datetime.now(timezone(timedelta(hours=8)))`
- 鏂板 `_beijing_now()` 鍑芥暟锛宍now_ts()` 鍚屾鏀圭敤 Python
- workflow锛?*绉婚櫎 `TZ: Asia/Shanghai`** 鐜鍙橀噺锛堝彲鑳藉奖鍝?cron 璋冨害鍣級
- workflow keepalive 姝ラ鏀圭敤鏄惧紡 Beijing 鏃跺尯
- 閫氱煡鏍囩鍏ㄩ儴鏀瑰洖銆屽寳浜椂闂淬€?

### 馃煛 鐘舵€佸尮閰嶄慨澶?

**鏍瑰洜**锛氭湇鍔″櫒 `signStatusName` 杩斿洖銆屾甯搞€嶈€岄潪 STATUS_MAP 鐨勩€屽凡鎵撳崱銆嶏紝瀵艰嚧 `auto_checkin.sh` case 鍖归厤澶辫触锛屾墦鍗℃垚鍔熷嵈 exit 1 + 鍙戝け璐ラ€氱煡銆?

**淇**锛?
- `auto_checkin.sh`锛歝ase 鏂板 `"姝ｅ父"` 鍖归厤
- `cli_ui.py`锛歋TATUS_MAP 0 鏀?`"宸叉墦鍗?` 鈫?`"姝ｅ父"`锛屼笌鏈嶅姟鍣ㄤ竴鑷?

### 馃摉 鏂囨。
- **鏂板** `docs/memory/016-鏃跺尯淇涓巆ron璋冨害鎺掗敊.md` 鈥?鍥涗釜 bug 鎺掓煡鍏ㄨ褰?
- **鏇存柊** `docs/memory/014-UTC鏃堕棿鍧?md` 鈥?淇閿欒缁撹
- **鏇存柊** `docs/guides/dev/GitHub-Actions閮ㄧ讲璁板綍.md` 鈥?琛ュ厖 cron 璋冨害鎺掗敊绔犺妭

## [0.8.2] 鈥?2026-06-09

### UTC 鏃堕棿瑙勮寖鍖?
- 鎵€鏈夐€氱煡鏂囨涓墦鍗＄獥鍙ｆ敼涓?UTC 鏃堕棿鏍囨敞锛?3:00鈥?4:30 UTC锛夛紝鍖椾含鏃堕棿鏀炬嫭鍙?
- `auto_checkin.sh` 鍜?workflow 娉ㄩ噴鍚屾鏀逛负 `UTC 13:05锛堝寳浜椂闂?21:05锛塦
- 鏂板 `docs/memory/014-UTC鏃堕棿鍧?md` 鈥?璁板綍鏈嶅姟鍣ㄥ熀浜?UTC 鍒ゅ畾鏃堕棿绐楀彛鐨勬牴鍥犲拰鏁欒
- `AGENTS.md` 鈥?鏂板 "UTC 鏃堕棿闄烽槺" 绔犺妭

### GPS 鑷姩閲嶈瘯
- `checkin.py`: 瓒呭嚭鎵撳崱鑼冨洿鏃惰嚜鍔ㄧ缉灏忓亸绉婚噺閲嶈瘯锛堟渶澶?5 娆★級锛屼笉鍐嶇洿鎺ヤ腑鏂?
- `auto_checkin.sh`: 绉婚櫎 GPS 瓒呭嚭鑼冨洿鎺ㄩ€佸垎鏀紙鍙嚜鍔ㄧ籂姝ｇ殑閿欒涓嶆帹閫侊級

### 閫氱煡缇庡寲
- 鎵€鏈夋帹閫侀€氱煡鏂囨绮剧畝锛岀粺涓€鏍囬鏍煎紡銆佸紩鐢ㄥ潡绐佸嚭鍏抽敭淇℃伅銆佸幓闄ゅ啑浣欒〃鏍?
- 鏈煡閿欒鏀圭敤浠ｇ爜鍧楁樉绀烘湇鍔″櫒杩斿洖

## [0.8.1] 鈥?2026-06-08

### Server閰?閫氱煡闈欓粯澶辫触淇

**鏍瑰洜**锛歚send_serverchan()` 涓や釜闅愯斀 bug 瀵艰嚧閫氱煡闈欓粯澶辫触锛?
1. `printf + --data-binary @-` 鍙戦€?Markdown 鍐呭鏃舵湭鍋?URL 缂栫爜锛屾崲琛?绠￠亾绗︾瓑鐗规畩瀛楃瀵艰嚧 Server閰?API 瑙ｆ瀽澶辫触
2. `> /dev/null 2>&1 || true` 涓㈠純浜?curl 鐨勬墍鏈夎緭鍑猴紙鍖呮嫭閿欒鍝嶅簲锛夛紝鏃ュ織姣棤鐥曡抗

**淇**锛?
- `send_serverchan()` 鈥?鏀圭敤 `--data-urlencode` 鑷姩 URL 缂栫爜 `title` 鍜?`desp`
- `send_serverchan()` 鈥?鎹曡幏 HTTP 鐘舵€佺爜 + 鍝嶅簲浣撳苟鍐欏叆鏃ュ織锛屼笉鍐嶉潤榛樹涪寮?
- `send_telegram()` 鈥?鍚屾牱鏀圭敤 `--data-urlencode` + 鍝嶅簲鏃ュ織
- 鑴氭湰鍚姩鏃舵柊澧為€氱煡娓犻亾鐘舵€佹鏌ワ紙鉁?宸查厤缃?/ 鈿狅笍 鏈厤缃?+ 閰嶇疆鎸囧紩锛?

### 鏃跺尯淇
- Bash: `export TZ='CST-8'`锛圥OSIX 鏍囧噯鏍煎紡锛屼笉渚濊禆 zoneinfo 鏂囦欢锛夆啋 涔嬪墠 `TZ='Asia/Shanghai'` 鍦ㄩ儴鍒嗙幆澧冩棤鏁?
- Python: `datetime.now()` 鈫?`datetime.now(timezone(timedelta(hours=8)))` 鈫?纭紪鐮?UTC+8锛屼笉鍙楃郴缁熸椂鍖哄奖鍝?
- Workflow 淇濇椿姝ラ鍚屾浣跨敤 `TZ='CST-8'`

### 淇濇椿鏈哄埗
- 鏂板 `.keepalive` 姣忔棩 commit锛岄槻姝?60 澶╂棤娲诲姩琚?GitHub 鍋滅敤瀹氭椂浠诲姟
- commit 甯?`[skip ci]` 闃叉閫掑綊瑙﹀彂
- Workflow 鏂板 `permissions: contents: write`

### 鏂囨。瀹屽杽
- **鏂板** `docs/guides/user/Server閰遍厤缃暀绋?md` 鈥?Server閰?浠庨浂閰嶇疆鏁欑▼
- **鏂板** `docs/guides/user/GitHub-Actions鑷姩鎵撳崱鏁欑▼.md` 鈥?GitHub Actions 鐢ㄦ埛鏁欑▼
- **鏂板** `docs/guides/dev/绛惧悕绠楁硶璇﹁В.md` 鈥?FlySource-sign 娣卞叆璁茶В锛堝弻璇疄鐜般€佷氦鍙夐獙璇併€佸父瑙侀櫡闃憋級
- **鏂板** `docs/guides/dev/椤圭洰鏋舵瀯涓庡紑鍙戞寚鍗?md` 鈥?鏋舵瀯鍏ㄦ櫙銆佹ā鍧楄璁°€佹暟鎹祦銆佹墿灞曟寚鍗?
- `docs/guides/user/鍏抽敭璇嶄笌姒傚康瑙ｉ噴.md` 鈥?鏂板"閫氱煡涓庤嚜鍔ㄥ寲"绔犺妭锛圫erver閰便€丟itHub Actions銆佷繚娲汇€佹椂鍖恒€乀elegram锛?
- `docs/guides/user/瀹屾暣鎿嶄綔鎸囧崡.md` 鈥?鏂板绗?5 绔?GitHub Actions + 鍙傝€冭祫鏂欐洿鏂?
- `docs/guides/user/CLI鏁欑▼.md` 鈥?鐗堟湰鏇存柊 + 鏂版寚鍗椾氦鍙夊紩鐢?
- `docs/guides/dev/GitHub-Actions閮ㄧ讲璁板綍.md` 鈥?鏂板閫氱煡璋冭瘯绔犺妭锛堥敊璇爜琛ㄣ€佹帓鏌ユ楠わ級
- `AGENTS.md` 鈥?鏂囨。绱㈠紩鏇存柊锛?1 浠芥寚鍗楋級
- `docs/memory/` 鈥?鏂板 012锛堥€氱煡淇锛? 013锛堟椂鍖轰慨澶嶏級

## [0.8.0] 鈥?2026-06-08

### GitHub Actions 鑷姩閮ㄧ讲涓婄嚎
- **鏂板** `.github/workflows/auto-checkin.yml` 鈥?姣忓ぉ 21:05 鍖椾含鏃堕棿鑷姩瑙﹀彂锛屾敮鎸?workflow_dispatch 鎵嬪姩瑙﹀彂
- **鏂板** `scripts/auto_checkin.sh` 鈥?bash 鎵ц鑴氭湰锛堝啓閰嶇疆 鈫?鐧诲綍 鈫?鑾峰彇浠诲姟 鈫?鎵撳崱 鈫?閫氱煡锛?
- **鏂板** `docs/guides/dev/GitHub-Actions閮ㄧ讲璁板綍.md` 鈥?閮ㄧ讲鏂囨。锛堥殣绉佸凡鑴辨晱锛?
- **鏂板** `docs/memory/010-GitHub-Actions閮ㄧ讲涓婄嚎.md` 鈥?閮ㄧ讲璁板繂妗ｆ

### 閫氱煡绯荤粺
- **Server閰?* 寰俊鎺ㄩ€侊紙涓婚€氶亾锛屽厤璐广€佹棤闇€瀹炲悕銆佹壂鐮佸嵆鐢級
- **Telegram Bot** 閫氱煡锛堝鐢ㄩ€氶亾锛?
- **GitHub 鍐呯疆閭欢** 鍏滃簳锛圫ettings 鈫?Notifications锛?
- 閫氱煡鍑芥暟缁熶竴涓?`notify()`锛岃嚜鍔ㄤ娇鐢ㄦ墍鏈夊凡閰嶇疆娓犻亾
- PushPlus 鍥犲疄鍚嶈璇佽姹傚純鐢?

### 鑴氭湰鍋ュ．鎬т慨澶?
- `grep -oP` 鏀逛负 `sed` 鎻愬彇瀛楁锛堟秷闄?Ubuntu runner PCRE 鍏煎鎬ч棶棰橈級
- `echo -e` 鏀逛负 `printf '%b'`锛堟秷闄よ法 shell 鍏煎鎬ч棶棰橈級
- 鎵€鏈?`GITHUB_*` 鐜鍙橀噺娣诲姞榛樿鍊硷紙鏈湴杩愯涓嶅啀宕╂簝锛?
- curl 娣诲姞 10s 杩炴帴瓒呮椂 + 15s 鎬昏秴鏃?

### 宸ヤ綔娴佷紭鍖?
- 姝ラ鍚嶆敼涓轰腑鏂囷紝鎻愬崌鍙鎬?
- 娣诲姞 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`锛屾秷闄?Node.js 20 寮冪敤璀﹀憡
- 鍒嗘敮缁熶竴涓?`main`

### 闅愮瀹夊叏
- `password.txt` 鏍煎紡鏍囧噯鍖栵紙鍙橀噺鍚嶅搴?GitHub Secrets锛?
- 鏂囨。涓墍鏈夊嚟鎹凡鑴辨晱澶勭悊
- `.gitignore` 纭繚 `password.txt` 涓嶄細琚彁浜?

## [0.7.2] 鈥?2026-06-08

### Bug 淇锛堝叧閿?鈥?cmd_status 宸叉墦鍗″嵈鏄剧ず"鏈墦鍗?锛?
涓夐噸鏍瑰洜鍚屾椂淇锛?
1. `get_one_record` 鏈紶 `sign_date` 鈫?鏄惧紡浼犲叆褰撳ぉ鏃ユ湡
2. 缂哄皯 `_token_expired` 妫€鏌?鈫?token 杩囨湡琚鎶ヤ负"鏈墦鍗? 鈫?娣诲姞妫€娴?
3. 鍒ゆ柇 `rec.get("data")` 鍦?`data: {}` 鏃跺洜绌哄瓧鍏?falsy 鈫?鏀逛负 `d and d.get("signStatus") is not None`

### 浠ｇ爜璐ㄩ噺锛堢畝娲佹€ф彁鍗囷級
- `scripts/cli.py`: 鎻愬彇妯″潡绾?`STATUS_MAP` 甯搁噺 + `_status_display(sc, sn)` 棰滆壊缂栫爜鍑芥暟锛屾秷闄?3 澶勯噸澶嶅瓧鍏搞€佺粺涓€ 7 绉嶇姸鎬侀鑹?
- `scripts/cli.py`: `_mask()` 鏀逛负 None-safe锛堣繑鍥?`""`锛夛紝4 澶勮皟鐢ㄧ畝鍖栦负 `_mask(v, N) or "fallback"`锛屾秷闄ゅ啑浣?`if/else` 瀹堝崼
- `scripts/cli.py`: 绉婚櫎 argparse 姝诲弬鏁?`config clear --token`锛堥粯璁よ涓哄凡娓呴櫎 token锛宍--token` 鏈湪 handler 浣跨敤锛?
- `scripts/cli.py` (`cmd_checkin`): 纭鏌ヨ澧炲姞 `_token_expired` 妫€娴?
- `scripts/cli.py` (`cmd_login`): 鐧诲綍鎴愬姛琛ュ厖 masked 瀛﹀彿鍜?token 鏄剧ず锛屼笌 `cmd_login_openid` 涓€鑷?

### 瀹夊叏闅愮鎻愬崌
- `scripts/cli.py`: 瀛﹀彿鍦?`status`/`config show`/鐧诲綍鎴愬姛涓簲鐢?`_mask(username, 3)` 鑴辨晱

### 鎵撳崱閫昏緫鏀硅繘
- `scripts/cli.py` (`cmd_checkin`): 鎻愪氦鎵撳崱鍚庤嚜鍔ㄨ皟鐢?`get_one_record` 鍥炴煡鏈嶅姟鍣ㄧ‘璁ゅ疄闄呮墦鍗＄姸鎬?

### 浠ｇ爜瀹℃煡
- `docs/review/2026-06-08-浠ｇ爜瀹℃煡.md` 鈥?鍒濇瀹℃煡锛? 涓棶棰橈級
- `docs/review/2026-06-08-娣卞害瀹℃煡.md` 鈥?娣卞害瀹℃煡锛堝叏閮ㄩ棶棰樺凡淇 7/7锛?

### 鏂囨。涓庤鑼?
- `CLAUDE.md` 鈥?鏂板"鍥炲蹇呴』鐢ㄤ腑鏂?绾﹀畾
- `AGENTS.md` 鈥?鏂板"鍥炲蹇呴』鐢ㄤ腑鏂?鍏抽敭绾﹀畾锛堢 6 鏉★級锛岄仐鐣欓棶棰樿〃宸叉竻绌?

## [0.7.1] 鈥?2026-06-07

### CLI 鐢ㄦ埛浣撻獙鍏ㄩ潰鍗囩骇

**鏂板 3 涓懡浠わ細**

- `setup` 鈥?浜や簰寮忛娆￠厤缃悜瀵硷紝寮曞鐢ㄦ埛杈撳叆 OpenID/瀛﹀彿/瀵嗙爜骞堕獙璇佺櫥褰?
- `status` 鈥?蹇€熺姸鎬佹瑙堬細鐧诲綍鐘舵€併€佸綋鍓嶄换鍔°€佷粖鏃ユ墦鍗¤褰曪紙涓€娆″懡浠ゆ浛浠ｄ互寰€ 3 涓懡浠わ級
- `config` 鈥?绠＄悊鏈湴閰嶇疆锛歚config show` 鏌ョ湅锛堝嚟鎹嚜鍔ㄦ帺鐮侊級銆乣config clear` 娓呴櫎 token

**杈撳嚭缇庡寲锛?*

- ANSI 缁堢棰滆壊绯荤粺锛坄Style` 绫伙級锛氱豢鑹?鎴愬姛 / 绾㈣壊=閿欒 / 榛勮壊=璀﹀憡 / 闈掕壊=淇℃伅 / 鐏拌壊=娆¤
- `divider()` 鍒嗘绾裤€乣kv()` 瀵归綈閿€艰銆乣bullet()` 鍥炬爣鍒楄〃
- `Spinner` 绾跨▼鍔ㄧ敾鎸囩ず鍣紙`鉅嬧牂鉅光牳鉅尖牬鉅︹牕鉅団爮`锛夛紝API 璋冪敤鏃惰嚜鍔ㄦ樉绀?
- `month` 鍛戒护鏂板 鉁?!/鈭?鍥炬爣鍜屽簳閮ㄦ眹鎬荤粺璁?
- `tasks` 鏀逛负缂栧彿鍒楄〃锛屼换鍔″悕绉伴珮浜?
- 鏃犲懡浠ゆ椂鏄剧ず鍝佺墝娆㈣繋椤?

**閿欒鎻愮ず鏀硅繘锛?*

- Token 杩囨湡 鈫?鏄庣‘鎻愮ず `python scripts/cli.py login-openid`
- 鐧诲綍缁戝畾鍐茬獊 鈫?鎻愮ず `--bind 0`
- 瀵嗙爜閿欒 鈫?鎻愮ず `--force-input`
- 缂哄皯 task_id 鈫?鎻愮ず鍏堣繍琛?`tasks`
- 瓒呭嚭鎵撳崱鑼冨洿 鈫?鎻愮ず `--force` 鎴栬皟鏁?`--offset`

**鎶€鏈粏鑺傦細**

- 闆舵柊澧炰緷璧栵紝绾?ANSI 杞箟鐮侊紙Windows 10+/Unix 閫氱敤锛?
- 灏婇噸 `NO_COLOR` 鐜鍙橀噺 + `isatty()` 绠￠亾妫€娴嬶紝鑴氭湰閲嶅畾鍚戣嚜鍔ㄩ檷绾т负绾枃鏈?
- Windows GBK 缁堢鑷姩 `sys.stdout.reconfigure(encoding='utf-8')`

### 楠岃瘉

- 鉁?鎵€鏈?10 涓?CLI 鍛戒护閫氳繃鐪熸満 API 娴嬭瘯
- 鉁?20/20 pytest 娴嬭瘯閫氳繃
- 鉁?`checkin` 姝ｇ‘妫€娴?浠婃棩宸茬鍒?
- 鉁?`month` 鏈堝害缁熻鍑嗙‘锛? 澶╂甯革級
- 鉁?ANSI 棰滆壊鍦ㄧ閬撹緭鍑烘椂鑷姩鍏抽棴

## [0.7.0] 鈥?2026-06-07

### 馃幆 绛惧悕闂缁堟瀬瑙ｅ喅

缁忚繃閫愬瓧鑺傚姣?Fiddler 鐪熷疄鎶撳寘绛惧悕锛?*纭绛惧悕绠楁硶锛圡D5 + Base64锛夎嚜濮嬭嚦缁堟纭?*銆?

鐪熸鍘熷洜锛?*鏈嶅姟鍣ㄥ弽鐖牎楠?*锛岃姹傝姹傚ご鍖呭惈寰俊灏忕▼搴忕幆澧冪壒寰侊紙`Referer`銆乣User-Agent`銆乣charset`锛夈€傜己灏戣繖浜涘ご鏃舵湇鍔″櫒鐩存帴杩斿洖"绛惧悕閿欒"銆?

### 淇

- `src/core/client.py`: 鏂板寰俊灏忕▼搴忎吉瑁呭ご锛坄charset`銆乣Referer`銆乣User-Agent`锛夛紝AppID/Version/UA 鍧囨敮鎸佺幆澧冨彉閲忚鐩?
- `src/core/client.py`: `_headers` 鏂板 `no_auth` 鍙傛暟锛坈aptcha 绔偣涓嶉渶瑕?Basic Auth锛?
- `src/core/client.py`: `sign_in()` 琛ラ綈 `Tenant-Id`/`Captcha-Key`/`Captcha-Code` 璇锋眰澶?
- `scripts/cli.py`: 淇 `tasks` 鍛戒护瀛楁鍚嶏紙`t['id']` 鈫?`t['taskId']`锛?
- `scripts/cli.py`: 淇 `record`/`month` 鍛戒护鐘舵€佹槧灏勶紙`signStatus=0` 涓?姝ｅ父/宸叉墦鍗?锛岄潪"鏈墦鍗?锛夛紝浼樺厛浣跨敤 API 杩斿洖鐨?`signStatusName`

### CLI 鑱斿姩浼樺寲

- `scripts/cli.py`: `getpass` 鏇挎崲涓?`secure_input()`锛屽瘑鐮佽緭鍏ュ洖鏄?`*` 鍗犱綅绗?
- `scripts/cli.py`: `login-openid --save-password` 淇濆瓨瀵嗙爜鍒伴厤缃枃浠?
- `scripts/cli.py`: `login-openid`/`login` 鐨?openid/username 鏀寔鐣欑┖浠庨厤缃枃浠惰鍙?
- `scripts/cli.py`: `tasks` 鑷姩淇濆瓨浠诲姟 ID 鈫?`detail`/`checkin`/`record`/`month` 鑷姩璇诲彇
- `scripts/cli.py`: 鏂板 `--force-input`锛堣烦杩囬厤缃瘑鐮侊級銆乣tasks --no-save`锛堜笉淇濆瓨浠诲姟 ID锛?
- 鏃ュ父浣跨敤绠€鍖栵細棣栨 `login-openid --save-password` 鍚庯紝鏃ュ父鍙渶 `tasks` 鈫?`checkin` 涓ゆ

### 楠岃瘉

- 鉁?鍏ㄩ摼璺?7 涓?CLI 鍛戒护鍏ㄩ儴閫氳繃鐪熷疄 API 楠岃瘉
- 鉁?20/20 pytest 娴嬭瘯閫氳繃
- 鉁?绛惧悕绠楁硶閫愬瓧鑺備笌寰俊灏忕▼搴忚緭鍑轰竴鑷?
- 鉁?`checkin` 鍛戒护鏈嶅姟鍣ㄦ帴鍙楄姹傦紙浠婃棩宸叉墦鍗℃晠杩斿洖"閲嶅鎵撳崱"鑰岄潪绛惧悕閿欒锛?
- 鉁?鍛戒护鑱斿姩锛歚tasks` 鈫?`detail` / `checkin` / `record` / `month` 鑷姩浼犻€?task_id

### 鏂囨。

- `docs/memory/006-绛惧悕闂缁堟瀬瑙ｅ喅.md` 鈥?瀹屾暣鎺掓煡璁板綍
- `docs/memory/007-CLI鑱斿姩涓庣敤鎴蜂綋楠屼紭鍖?md` 鈥?鑱斿姩浼樺寲璁板綍
- `docs/guides/user/CLI鏁欑▼.md` 鈥?CLI 璇︾粏鏁欑▼锛堣仈鍔ㄧ敤娉曪級
- `docs/plan/鏈嶅姟鍣ㄩ儴缃茶鍒?md` 鈥?闃舵涓夋湇鍔″櫒閮ㄧ讲瑙勫垝
- `docs/guides/user/瀹屾暣鎿嶄綔鎸囧崡.md` 鈥?鏇存柊鑷?v0.7.0

## [0.6.1] 鈥?2026-06-07

### Bug 淇
- `src/core/client.py`: `_post()` 淇 `extra_headers` 鍙傛暟鏈浆鍙戝埌 `_request()` 鐨?bug锛屽鑷?OpenID 鐧诲綍鏃犳硶浼犻€?`Web-Type`/`Tenant-Id` 澶?
- `src/core/client.py`: httpx 瀹㈡埛绔柊澧?`verify=certifi.where()` 瑙ｅ喅 Windows Python SSL 璇佷功缂哄け闂
- `src/core/client.py`: httpx 瀹㈡埛绔柊澧?`trust_env=False` 瑙ｅ喅 Windows 鐜浠ｇ悊骞叉壈 HTTPS 鐩磋繛
- `src/utils/sign.py`: 绛惧悕绠楁硶鏇存锛岀Щ闄や腑闂村浣欑殑瀛楃涓诧紙`path + "?sign=" + inner_hash` 鏍煎紡缁?JS 婧愮爜浜ゅ弶楠岃瘉纭姝ｇ‘锛?

### 鏂板
- `docs/guides/user/瀹屾暣鎿嶄綔鎸囧崡.md`: 鏂板瀹屾暣鎿嶄綔鎸囧崡锛?30 琛岋級锛岃鐩栫幆澧冨噯澶囥€丱penID 鎶撳寘銆丆LI 浣跨敤銆佺鍚嶇畻娉曘€佸畨鍏ㄨ璁°€丗AQ
- `requirements.txt`: 鏂板 `certifi==2025.11.12` 鐩存帴渚濊禆

### 楠岃瘉
- 閫氳繃 Fiddler + MuMu 妯℃嫙鍣ㄦ垚鍔熸姄鍖呰幏鍙栫湡瀹?OpenID
- 閫氳繃 ADB bind mount 鏂规鎴愬姛瀹夎绯荤粺绾?CA 璇佷功鍒版ā鎷熷櫒
- OpenID 鐧诲綍鎴愬姛锛坄login-openid --bind 0`锛?
- 鍏ㄩ儴 20 涓?pytest 娴嬭瘯閫氳繃

## [0.6.0] 鈥?2026-06-07

### 淇锛堟寜瀹℃煡浼樺厛绾э級

**馃敶 P0**
- `src/core/client.py`: 鏂板 `__enter__`/`__exit__` 涓婁笅鏂囩鐞嗗櫒锛屾敮鎸?`with ApiClient() as c`
- `src/main.py`: 鏂板 `CORSMiddleware` 璺ㄥ煙鏀寔鍜?`lifespan` 鐢熷懡鍛ㄦ湡浜嬩欢绠＄悊 ApiClient 杩炴帴姹?

**馃煛 P1**
- `src/core/client.py`: `BASE_URL` 浠庢ā鍧楃骇甯搁噺鏀逛负瀹炰緥灞炴€э紝鏋勯€犲嚱鏁版敮鎸?`base_url` 鍙傛暟锛屽吋瀹瑰鐜鍒囨崲
- `tests/`: 鏂板 20 涓?pytest 娴嬭瘯鐢ㄤ緥锛坈rypto 6 + sign 6 + geo 8锛夛紝瑕嗙洊 MD5/Base64 鏍囧噯鍚戦噺銆佺鍚嶇畻娉曟牸寮忔牎楠屻€丠aversine 宸茬煡璺濈銆侀殢鏈哄亸绉荤瀛愬彲閲嶇幇鎬?

**馃煝 P2**
- `scripts/cli.py:49`: 瀵嗙爜涓夌洰琛ㄨ揪寮忔敼涓烘竻鏅?`if/else` 鍒嗘敮
- `src/core/client.py`: `_request()` 鏂板鎸囨暟閫€閬块噸璇曟満鍒讹紙鏈€澶?3 娆★紝1s/2s/4s锛夛紝浠呴噸璇曠綉缁?瑙ｆ瀽閿欒锛屼笉褰卞搷 401

**鈿?P3**
- `.env.example`: `FLYSOURCE_CLIENT_ID`銆乣FLYSOURCE_CLIENT_SECRET`銆乣CHECKIN_BASE_URL` 鍙栨秷娉ㄩ噴锛屽紑绠卞嵆鐢?
- `requirements.txt`: 鎵€鏈変緷璧栦粠 `>=` 鏀逛负鍥哄畾鐗堟湰鍙烽攣瀹?

### 鍏朵粬
- `src/utils/geo.py`: `random_offset` 鏂板鍙€?`seed` 鍙傛暟锛屾敮鎸佹祴璇曞満鏅鐜?
- 鎵€鏈?8 涓簮鐮佹枃浠舵柊澧炰腑鏂囨敞閲婏紙妯″潡銆佺被銆佸嚱鏁扮骇鍒級锛屾彁鍗囧彲璇绘€?
- `docs/guides/user/fiddler-鎶撳寘鑾峰彇OpenID.md`: 鏂板 Fiddler 鎶撳寘鍏ㄦ祦绋嬫寚鍗楋紙341 琛岋級锛屽惈 2.1 鑺傛眽鍖栬鏄?
- `docs/memory/004-瀹℃煡淇涓嶰penID鍙戠幇.md`: 鏈浼氳瘽璁板繂瀛樻。
- 娓呯悊涓存椂鏂囦欢锛坈aptcha.png銆?pytest_cache銆? 涓?__pycache__锛?
- `docs/CHANGELOG.md`: 鏂板 v0.6.0 鏉＄洰
- `AGENTS.md`: 閬楃暀闂琛ㄥ凡娓呯┖

## [v0.1 鈥?v0.5] 鈥?2026-06-07 路 鏃╂湡蹇€熻凯浠?

**v0.1** 椤圭洰楠ㄦ灦锛團astAPI + APScheduler + SQLAlchemy锛夈€丟it 鍒濆鍖栥€乣.env.example`
**v0.2** MuMu 12 妯℃嫙鍣?Root + ADB 鎷夊彇 6 涓?`.wxapkg`
**v0.3** 鍙嶇紪璇戠‘璁ょ洰鏍囧皬绋嬪簭銆佽繕鍘熺鍚嶇畻娉曪紙FlySource-sign + stuTaskId锛夈€佹彁鍙?ClientId/ClientSecret
**v0.4** CLI 宸ュ叿鍒濈増锛? 瀛愬懡浠わ級銆佹牳蹇冩ā鍧楋紙sign/crypto/geo/client锛夈€佸嚟鎹畨鍏ㄥ姞鍥?
**v0.5** 鍏ㄩ噺浠ｇ爜瀹℃煡锛? Critical / 5 Important / 6 Minor锛?
