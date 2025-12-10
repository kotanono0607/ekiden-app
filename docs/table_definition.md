# テーブル定義書

南陽東置賜 駅伝チーム管理アプリ

## 概要

本アプリケーションはGoogle Spreadsheetsをデータベースとして使用します。
各シートは1行目に物理名（カラム名）、2行目に論理名（表示名）、3行目以降にデータを格納します。

---

## 1. Players（選手マスタ）

**物理名**: Players
**概要**: チームに所属する選手の基本情報を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | id | システムID | String | ○ | PK。自動採番（例: P001） |
| 2 | registration_number | 登録番号 | String | | 陸連登録番号など |
| 3 | name_sei | 姓 | String | ○ | |
| 4 | name_mei | 名 | String | ○ | |
| 5 | birth_date | 生年月日 | Date | | YYYY-MM-DD形式 |
| 6 | grade | 学年 | String | | Masters参照(grade_list) |
| 7 | affiliation | 所属 | String | | Masters参照(affiliation_list) |
| 8 | category | 区分 | String | | Masters参照(category_list) |
| 9 | status | 状態 | String | | 現役/引退など。Masters参照(status_list) |
| 10 | race_count | 出場回数 | Number | | 自動カウント |
| 11 | pb_1500m | PB 1500m | String | | MM:SS形式 |
| 12 | pb_3000m | PB 3000m | String | | MM:SS形式 |
| 13 | pb_5000m | PB 5000m | String | | MM:SS形式 |
| 14 | pb_10000m | PB 10000m | String | | MM:SS形式 |
| 15 | pb_half | PB ハーフ | String | | H:MM:SS形式 |
| 16 | pb_full | PB フル | String | | H:MM:SS形式 |
| 17 | comment | 備考 | String | | 自由記述 |
| 18 | is_deleted | 削除フラグ | Boolean | | TRUE/FALSE。論理削除用 |
| 19 | created_at | 作成日時 | Datetime | ○ | |
| 20 | updated_at | 更新日時 | Datetime | ○ | |

---

## 2. Records（記録データ）

**物理名**: Records
**概要**: 選手の競技記録を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | record_id | 記録ID | String | ○ | PK。自動採番（例: R001） |
| 2 | player_id | 選手ID | String | ○ | FK。Players.id を参照 |
| 3 | race_id | 大会ID | String | | FK。Races.race_id を参照 |
| 4 | date | 日付 | Date | ○ | YYYY-MM-DD形式 |
| 5 | section | 区間/種目 | String | ○ | 例: 5000m, 1区 |
| 6 | distance_km | 距離(km) | Number | | |
| 7 | time | タイム | String | ○ | MM:SS または H:MM:SS形式 |
| 8 | time_sec | タイム(秒) | Number | | 秒換算値 |
| 9 | is_pb | 自己ベスト | Boolean | | TRUE/FALSE |
| 10 | is_section_record | 区間記録 | Boolean | | TRUE/FALSE |
| 11 | split_times_json | スプリットタイム | String | | JSON形式 |
| 12 | rank_in_section | 区間順位 | Number | | |
| 13 | memo | メモ | String | | |
| 14 | created_at | 作成日時 | Datetime | ○ | |
| 15 | updated_at | 更新日時 | Datetime | ○ | |
| 16 | player_name | 選手氏名 | String | | CSV参照。Players.name_sei + name_mei |
| 17 | race_name | 大会名 | String | | CSV参照。Races.race_name |
| 18 | race_type | 大会タイプ | String | | CSV参照。Races.type |

---

## 3. Races（大会マスタ）

**物理名**: Races
**概要**: 大会情報を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | race_id | 大会ID | String | ○ | PK。自動採番（例: RAC001） |
| 2 | race_name | 大会名 | String | ○ | |
| 3 | short_name | 略称 | String | | |
| 4 | date | 開催日 | Date | ○ | YYYY-MM-DD形式 |
| 5 | location | 開催地 | String | | |
| 6 | type | 大会タイプ | String | | Masters参照(race_type_list) |
| 7 | section_count | 区間数 | Number | | 駅伝の場合 |
| 8 | importance | 重要度 | String | | Masters参照(importance_list) |
| 9 | memo | 備考 | String | | |
| 10 | created_at | 作成日時 | Datetime | ○ | |
| 11 | updated_at | 更新日時 | Datetime | ○ | |

---

## 4. TeamRecords（チーム記録）

**物理名**: TeamRecords
**概要**: 駅伝大会でのチーム総合記録を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | team_record_id | チーム記録ID | String | ○ | PK。自動採番（例: TR001） |
| 2 | race_id | 大会ID | String | ○ | FK。Races.race_id を参照 |
| 3 | total_time | 総合タイム | String | ○ | H:MM:SS形式 |
| 4 | total_time_sec | 総合タイム(秒) | Number | | 秒換算値 |
| 5 | rank | 総合順位 | Number | | |
| 6 | total_teams | 出場チーム数 | Number | | |
| 7 | category | 出場カテゴリ | String | | |
| 8 | memo | メモ | String | | |
| 9 | created_at | 作成日時 | Datetime | ○ | |
| 10 | updated_at | 更新日時 | Datetime | ○ | |

---

## 5. RaceOrders（大会オーダー）

**物理名**: RaceOrders
**概要**: 駅伝大会での区間オーダー（走順）を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | order_id | オーダーID | String | ○ | PK。自動採番（例: ORD001） |
| 2 | team_record_id | チーム記録ID | String | ○ | FK。TeamRecords.team_record_id を参照 |
| 3 | section_no | 区間番号 | Number | ○ | 1, 2, 3... |
| 4 | section_name | 区間名 | String | | 例: 1区, アンカー |
| 5 | player_id | 選手ID | String | ○ | FK。Players.id を参照 |
| 6 | record_id | 記録ID | String | | FK。Records.record_id を参照 |
| 7 | memo | メモ | String | | |

---

## 6. Masters（汎用マスタ）

**物理名**: Masters
**概要**: 各種選択肢リストを管理する汎用マスタ。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | type | マスタ種別 | String | ○ | category_list, grade_list など |
| 2 | code | コード値 | String | ○ | 選択肢の値 |
| 3 | name | 表示名 | String | ○ | 画面表示用 |
| 4 | sort_order | 表示順 | Number | | 昇順でソート |
| 5 | memo | メモ | String | | |

### マスタ種別一覧

| type | 用途 |
|------|------|
| category_list | 選手区分（中学生、高校生、一般など） |
| grade_list | 学年 |
| status_list | 選手状態（現役、引退など） |
| affiliation_list | 所属 |
| race_type_list | 大会タイプ（駅伝、記録会、ロードレースなど） |
| importance_list | 大会重要度 |
| event_type_list | カレンダー予定種別 |
| weather_list | 天候 |
| attendance_status_list | 出欠ステータス |

---

## 7. Events（カレンダー予定）

**物理名**: Events
**概要**: チームのスケジュール（練習、大会、合宿等）を管理する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | event_id | 予定ID | String | ○ | PK。自動採番（例: EVT001） |
| 2 | date | 日付 | Date | ○ | YYYY-MM-DD形式 |
| 3 | event_type | 種別 | String | ○ | Masters参照(event_type_list)。例: 練習, 大会, 合宿, 休み |
| 4 | title | タイトル | String | ○ | 予定名 |
| 5 | start_time | 開始時刻 | String | | HH:MM形式 |
| 6 | end_time | 終了時刻 | String | | HH:MM形式 |
| 7 | location | 場所 | String | | 練習場所、集合場所など |
| 8 | memo | メモ | String | | 詳細情報、持ち物など |
| 9 | created_at | 作成日時 | Datetime | ○ | |
| 10 | updated_at | 更新日時 | Datetime | ○ | |

---

## 8. PracticeLogs（練習日誌）

**物理名**: PracticeLogs
**概要**: 日々の練習内容、コンディション、参加人数などを記録する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | log_id | 日誌ID | String | ○ | PK。自動採番（例: LOG001） |
| 2 | date | 日付 | Date | ○ | YYYY-MM-DD形式 |
| 3 | title | タイトル | String | ○ | 練習内容の要約（例: ポイント練習、各自ジョグ） |
| 4 | content | 内容 | String | | 詳細な練習メニューや設定タイムなど |
| 5 | weather | 天候 | String | | 例: 晴れ, 曇り, 雨。Masters参照(weather_list) |
| 6 | temperature | 気温 | Number | | 単位: ℃ |
| 7 | participants | 参加人数 | Number | | |
| 8 | memo | メモ | String | | チーム全体の雰囲気、特記事項など |
| 9 | created_at | 作成日時 | Datetime | ○ | |
| 10 | updated_at | 更新日時 | Datetime | ○ | |

---

## 9. Attendance（出欠）

**物理名**: Attendance
**概要**: 練習やイベント単位での各選手の出欠状況を記録する。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | attendance_id | 出欠ID | String | ○ | PK。自動採番（例: ATT001） |
| 2 | date | 日付 | Date | ○ | 対象日。Events.dateまたはPracticeLogs.dateと対応 |
| 3 | player_id | 選手ID | String | ○ | FK。Players.id を参照 |
| 4 | status | 出欠 | String | ○ | Masters参照(attendance_status_list)。例: 出席, 欠席, 遅刻, 早退 |
| 5 | memo | 備考 | String | | 欠席理由や遅刻理由など |
| 6 | created_at | 作成日時 | Datetime | ○ | |

---

## 10. Simulations（シミュレーション）※非推奨

**物理名**: Simulations
**概要**: 区間オーダーのシミュレーションデータ。※現在は使用していません。

| No. | 物理名 | 論理名 | データ型 | 必須 | 備考・制約 |
|-----|--------|--------|----------|------|------------|
| 1 | created_at | 作成日時 | Datetime | ○ | |
| 2 | title | タイトル | String | ○ | |
| 3 | order_data | オーダーデータ | String | ○ | JSON形式 |

---

## 推奨マスタデータ

以下のデータをMastersシートに登録することを推奨します。

### event_type_list（予定種別）
| type | code | name | sort_order |
|------|------|------|------------|
| event_type_list | 練習 | 練習 | 1 |
| event_type_list | 大会 | 大会 | 2 |
| event_type_list | 合宿 | 合宿 | 3 |
| event_type_list | 休み | 休み | 4 |

### weather_list（天候）
| type | code | name | sort_order |
|------|------|------|------------|
| weather_list | 晴れ | 晴れ | 1 |
| weather_list | 曇り | 曇り | 2 |
| weather_list | 雨 | 雨 | 3 |
| weather_list | 雪 | 雪 | 4 |

### attendance_status_list（出欠ステータス）
| type | code | name | sort_order |
|------|------|------|------------|
| attendance_status_list | 出席 | 出席 | 1 |
| attendance_status_list | 欠席 | 欠席 | 2 |
| attendance_status_list | 遅刻 | 遅刻 | 3 |
| attendance_status_list | 早退 | 早退 | 4 |

---

## 更新履歴

| 日付 | 更新内容 |
|------|----------|
| 2024-12-10 | RecordsテーブルにCSV参照カラム（player_name, race_name, race_type）を追加。 |
| 2024-12-09 | カレンダー、練習日誌、出欠機能を追加。Events, PracticeLogs, Attendanceシートを追加。 |
