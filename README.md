# 陸上競技チーム管理システム データベース仕様書

**作成日:** 2025年12月9日
**バージョン:** 1.0

## 1. 概要
本ドキュメントは、陸上競技（長距離・駅伝）チームの個人情報、大会記録、チーム記録などを管理するためのデータベース（Googleスプレッドシート）のテーブル定義書である。

## 2. テーブル一覧（シート構成）
システムは以下の8つのテーブル（スプレッドシート）で構成される。

| No. | テーブル名 (物理名) | テーブル名 (論理名) | 概要 |
| :-- | :--- | :--- | :--- |
| 1 | **Players** | 選手マスタ | 所属選手の基本情報、属性、PB等を管理する。 |
| 2 | **Races** | 大会マスタ | 出場する大会の基本情報を管理する。 |
| 3 | **Records** | 個人記録データ | 個人のレース結果（トラック、ロード、駅伝区間記録）を蓄積するトランザクションテーブル。 |
| 4 | **TeamRecords** | チーム記録 | 駅伝等におけるチームとしての総合結果を管理する親テーブル。 |
| 5 | **RaceOrders** | 大会オーダー | チーム記録に紐付く、実際の区間エントリー情報（誰がどこを走ったか）を管理する子テーブル。 |
| 6 | **Simulations** | シミュレーション | 駅伝オーダーのシミュレーション情報を管理する親テーブル。 |
| 7 | **SimulationOrders** | シミュレーションオーダー | シミュレーションに紐付く、区間配置案を管理する子テーブル。 |
| 8 | **Masters** | 汎用マスタ | システム内で使用する各種区分値、選択肢リスト等を一元管理する。 |

---

## 3. テーブル詳細定義

### 3.1. Players（選手マスタ）
* **物理名:** `Players`
* **概要:** チームに所属する全選手（現役・OB/OG・スタッフ含む）の基本情報を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `id` | システムID | String | ○ | PK (Primary Key)。自動採番（例: P001）。 |
| 2 | `registration_number` | 登録番号/学籍番号 | String | | 陸連登録番号や学籍番号など。ユニーク制約推奨。 |
| 3 | `name_sei` | 姓 | String | ○ | |
| 4 | `name_mei` | 名 | String | ○ | |
| 5 | `birth_date` | 生年月日 | Date | ○ | YYYY-MM-DD形式。年齢計算等に使用。 |
| 6 | `grade` | 学年 | String | | 学生の場合のみ入力（例: 1年, 2年）。Masters参照(grade_list)。 |
| 7 | `affiliation` | 所属 | String | | 学校名、学部学科、所属企業名など。 |
| 8 | `category` | 区分 | String | ○ | Masters参照(category_list)。例: 大学生, 社会人。 |
| 9 | `status` | 状態 | String | ○ | Masters参照(status_list)。例: 現役, 引退。 |
| 10 | `race_count` | 出場回数 | Number | | Recordsテーブルの登録数からバッチ等で自動計算更新を想定。初期値0。 |
| 11 | `pb_1500m` | PB 1500m | String | | "MM:SS"形式。 |
| 12 | `pb_3000m` | PB 3000m | String | | "MM:SS"形式。 |
| 13 | `pb_5000m` | PB 5000m | String | | "MM:SS"形式。 |
| 14 | `pb_10000m` | PB 10000m | String | | "HH:MM:SS" または "MM:SS"形式。 |
| 15 | `pb_half` | PB ハーフ | String | | "HH:MM:SS"形式。 |
| 16 | `pb_full` | PB フル | String | | "HH:MM:SS"形式。 |
| 17 | `comment` | 自由記述 | String | | 特記事項など。 |
| 18 | `is_deleted` | 削除フラグ | Boolean | ○ | 初期値FALSE。論理削除に使用。 |
| 19 | `created_at` | 作成日時 | Datetime | ○ | システム日付自動設定。 |
| 20 | `updated_at` | 更新日時 | Datetime | ○ | システム日付自動設定。 |

### 3.2. Races（大会マスタ）
* **物理名:** `Races`
* **概要:** 大会のマスタ情報を管理し、Records入力時の表記ゆれを防ぐ。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `race_id` | 大会ID | String | ○ | PK。自動採番（例: RAC001）。 |
| 2 | `race_name` | 大会名 | String | ○ | 正式名称。 |
| 3 | `short_name` | 略称 | String | ○ | 表示用略称。 |
| 4 | `date` | 開催日 | Date | ○ | YYYY-MM-DD形式。 |
| 5 | `location` | 開催地 | String | | 競技場名、コース名など。 |
| 6 | `type` | 大会タイプ | String | ○ | Masters参照(race_type_list)。例: トラック, ロード, 駅伝。 |
| 7 | `section_count` | 区間数 | Number | | `type`が'駅伝'の場合の総区間数。その他はnullまたは0。 |
| 8 | `importance` | 重要度 | String | | Masters参照(importance_list)。例: A, B, C。 |
| 9 | `memo` | 備考 | String | | |
| 10 | `created_at` | 作成日時 | Datetime | ○ | |
| 11 | `updated_at` | 更新日時 | Datetime | ○ | |

### 3.3. Records（個人記録データ）
* **物理名:** `Records`
* **概要:** 個人のレース結果を記録する。トラック・ロードの記録と、駅伝の区間記録を混在して管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `record_id` | 記録ID | String | ○ | PK。自動採番（例: R001）。 |
| 2 | `player_id` | 選手ID | String | ○ | FK (Foreign Key)。Players.id を参照。 |
| 3 | `race_id` | 大会ID | String | ○ | FK。Races.race_id を参照。 |
| 4 | `date` | 日付 | Date | ○ | レース実施日。通常はRaces.dateと同じだが、複数日開催の場合に備えて保持。 |
| 5 | `section` | 種目名/区間名 | String | ○ | トラックは「5000m」、駅伝は「1区」のように入力。 |
| 6 | `distance_km` | 距離(km) | Number | ○ | 分析用実数値（例: 5.0, 21.0975, 8.6）。 |
| 7 | `time` | 記録タイム | String | ○ | 表示用文字列。"HH:MM:SS" または "MM:SS"。 |
| 8 | `time_sec` | タイム(秒) | Number | ○ | 計算・グラフ用数値。`time`から自動計算。 |
| 9 | `is_pb` | PBフラグ | Boolean | ○ | 今回の記録が自己ベスト更新時にTRUE。初期値FALSE。 |
| 10 | `is_section_record`| 区間新フラグ | Boolean | ○ | 駅伝等で区間新記録樹立時にTRUE。初期値FALSE。 |
| 11 | `split_times_json`| ラップタイム | String | | JSON形式文字列（例: `{"1km":"2:55", "2km":"5:55"}`）。 |
| 12 | `rank_in_section` | 種目別/区間順位| Number | | その種目または区間における順位。 |
| 13 | `memo` | メモ | String | | 個人の振り返りなど。 |
| 14 | `created_at` | 作成日時 | Datetime | ○ | |
| 15 | `updated_at` | 更新日時 | Datetime | ○ | |

### 3.4. TeamRecords（チーム記録）
* **物理名:** `TeamRecords`
* **概要:** 駅伝等におけるチームとしての総合結果を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `team_record_id` | チーム記録ID | String | ○ | PK。自動採番（例: TR001）。 |
| 2 | `race_id` | 大会ID | String | ○ | FK。Races.race_id を参照。対象大会は `type`='駅伝'を想定。 |
| 3 | `total_time` | 総合タイム | String | ○ | 表示用文字列。"HH:MM:SS"。 |
| 4 | `total_time_sec` | 総合タイム(秒) | Number | ○ | 計算用数値。 |
| 5 | `rank` | 総合順位 | Number | | |
| 6 | `total_teams` | 出場チーム数 | Number | | 母数把握用。 |
| 7 | `category` | 出場カテゴリ | String | | 例: 一般の部、高校の部。Masters参照(category_list)も可。 |
| 8 | `memo` | メモ | String | | チームとしての総括など。 |
| 9 | `created_at` | 作成日時 | Datetime | ○ | |
| 10 | `updated_at` | 更新日時 | Datetime | ○ | |

### 3.5. RaceOrders（大会オーダー）
* **物理名:** `RaceOrders`
* **概要:** TeamRecordsに対する実際の区間エントリー情報を管理する関連テーブル。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `order_id` | オーダーID | String | ○ | PK。自動採番（例: ORD001）。 |
| 2 | `team_record_id` | チーム記録ID | String | ○ | FK。TeamRecords.team_record_id を参照。 |
| 3 | `section_no` | 区間番号 | Number | ○ | 1から始まる連番。ソートキー。 |
| 4 | `section_name` | 区間名 | String | ○ | 表示用（例: 1区, アンカー）。 |
| 5 | `player_id` | 選手ID | String | ○ | FK。Players.id を参照。実際に走った選手。 |
| 6 | `record_id` | 記録ID | String | | FK。Records.record_id を参照。その区間の個人記録と紐付け。 |
| 7 | `memo` | メモ | String | | 区間配置の意図、当日の変更理由など。 |

### 3.6. Simulations（シミュレーション）
* **物理名:** `Simulations`
* **概要:** 駅伝オーダーのシミュレーション案を管理するヘッダー情報。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `sim_id` | シミュレーションID| String | ○ | PK。自動採番（例: SIM001）。 |
| 2 | `title` | タイトル | String | ○ | 例: 〇〇駅伝Aチーム案（ベストメンバー）。 |
| 3 | `target_race_id` | 対象大会ID | String | | FK。Races.race_id を参照。想定する大会があれば指定。 |
| 4 | `total_time_predicted`| 予想総合タイム | String | | オーダーに基づく積算タイム予測。"HH:MM:SS"。 |
| 5 | `memo` | メモ | String | | 前提条件、戦略コンセプトなど。 |
| 6 | `created_at` | 作成日時 | Datetime | ○ | |
| 7 | `updated_at` | 更新日時 | Datetime | ○ | |

### 3.7. SimulationOrders（シミュレーションオーダー）
* **物理名:** `SimulationOrders`
* **概要:** シミュレーション案に基づく区間配置の詳細を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `sim_order_id` | オーダーID | String | ○ | PK。自動採番（例: SO001）。 |
| 2 | `sim_id` | シミュレーションID| String | ○ | FK。Simulations.sim_id を参照。 |
| 3 | `section_no` | 区間番号 | Number | ○ | 1から始まる連番。 |
| 4 | `section_name` | 区間名 | String | ○ | 表示用（例: 1区）。 |
| 5 | `player_id` | 選手ID | String | ○ | FK。Players.id を参照。候補選手。 |
| 6 | `predicted_time` | 予想区間タイム | String | | その選手が走った場合の想定タイム。"MM:SS"等。 |
| 7 | `memo` | メモ | String | | 起用理由など。 |

### 3.8. Masters（汎用マスタ）
* **物理名:** `Masters`
* **概要:** アプリケーション内で使用する選択肢リスト等を一元管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
| :-- | :--- | :--- | :--- | :--: | :--- |
| 1 | `type` | マスタ種別 | String | ○ | データのグループ識別子（例: category_list）。 |
| 2 | `code` | コード値 | String | ○ | システム内部で扱う値（例: univ）。`type`内でユニーク。 |
| 3 | `name` | 表示名 | String | ○ | UI表示用の値（例: 大学生）。 |
| 4 | `sort_order` | 表示順 | Number | ○ | UI表示順序制御用。 |
| 5 | `memo` | メモ | String | | |

---
**特記事項:**
* スプレッドシートをデータベースとして使用するため、各シートの1行目は物理名、2行目は論理名とし、データは3行目以降に格納する運用を前提とする。
* FK（外部キー）制約はスプレッドシート上では物理的に強制できないため、アプリケーション（GAS等）側で整合性を担保する実装が必要である。
* 日時項目（`created_at`, `updated_at`）は、レコード挿入・更新時にシステム側で現在日時をセットすること。
