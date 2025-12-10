# Recordsテーブル定義変更報告書

**報告日**: 2024年12月10日
**報告者**: 開発チーム
**対象**: テーブル定義担当者

---

## 1. 変更概要

Recordsテーブルに対して、以下の変更を実施しました。

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| カラム数 | 15 | 19 |
| 種目/区間 | 1カラム（section） | 2カラム（event, section） |

---

## 2. 変更内容

### 2.1 カラム分離（重要）

**変更前**
```
| 5 | section | 区間/種目 | String | ○ | 例: 5000m, 1区 |
```

**変更後**
```
| 5 | event   | 種目 | String | | 例: 5000m, 3000m（トラック競技用） |
| 6 | section | 区間 | String | | 例: 1区, 2区, 7区（駅伝用） |
```

**理由**: 既存のExcelデータでは「種目」と「区間」が別カラムとして管理されており、データ移行の整合性を確保するため。

### 2.2 CSV参照カラム追加

以下の3カラムを追加しました（非正規化カラム）。

| No. | 物理名 | 論理名 | 参照元 |
|-----|--------|--------|--------|
| 17 | player_name | 選手氏名 | Players.name_sei + name_mei |
| 18 | race_name | 大会名 | Races.race_name |
| 19 | race_type | 大会タイプ | Races.type |

**理由**: スプレッドシート上での視認性向上、およびJOINなしでのデータ確認を可能にするため。

---

## 3. 変更後のカラム一覧

| No. | 物理名 | 論理名 | データ型 | 必須 |
|-----|--------|--------|----------|------|
| 1 | record_id | 記録ID | String | ○ |
| 2 | player_id | 選手ID | String | ○ |
| 3 | race_id | 大会ID | String | |
| 4 | date | 日付 | Date | ○ |
| 5 | **event** | **種目** | String | |
| 6 | section | 区間 | String | |
| 7 | distance_km | 距離(km) | Number | |
| 8 | time | タイム | String | ○ |
| 9 | time_sec | タイム(秒) | Number | |
| 10 | is_pb | 自己ベスト | Boolean | |
| 11 | is_section_record | 区間記録 | Boolean | |
| 12 | split_times_json | スプリットタイム | String | |
| 13 | rank_in_section | 区間順位 | Number | |
| 14 | memo | メモ | String | |
| 15 | created_at | 作成日時 | Datetime | ○ |
| 16 | updated_at | 更新日時 | Datetime | ○ |
| 17 | **player_name** | **選手氏名** | String | |
| 18 | **race_name** | **大会名** | String | |
| 19 | **race_type** | **大会タイプ** | String | |

※太字は今回追加されたカラム

---

## 4. 対応依頼事項

### スプレッドシート担当者への依頼

1. **Recordsシートのヘッダー行を更新**してください
   - 5列目に「event」を挿入
   - 既存の「section」は6列目に移動
   - 17〜19列目にCSV参照カラムを追加

2. **ヘッダー行の正しい順序**:
```
record_id | player_id | race_id | date | event | section | distance_km | time | time_sec | is_pb | is_section_record | split_times_json | rank_in_section | memo | created_at | updated_at | player_name | race_name | race_type
```

---

## 5. 影響範囲

| 対象 | 影響 | 対応状況 |
|------|------|----------|
| sheet_api.py | RECORD_EXPECTED_HEADERS更新 | 完了 |
| table_definition.md | テーブル定義更新 | 完了 |
| スプレッドシート | ヘッダー更新必要 | **対応依頼中** |
| 既存画面 | 影響なし | - |

---

## 6. 備考

- 既存のExcelデータ（約600件）は「種目」「区間」が分離されているため、今回の変更によりスムーズにインポート可能
- CSV参照カラムはスプレッドシートの数式（VLOOKUP等）で自動入力することを推奨

以上
