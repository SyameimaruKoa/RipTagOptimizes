# CDワークフローGUI 更新履歴 (v5)

## Step6 アートワーク自動埋め込み修正 (2026年3月2日)

### 問題
- Step 6 の自動埋め込み処理が `_aac_output/アルバム名` / `_opus_output/アルバム名` を参照しており、
  v5 で導入した2階層構成 `_aac_output/アーティスト名/アルバム名` と不一致になっていた。
- そのため、実在する出力フォルダがあっても「出力フォルダが存在しません」と表示され、
  AAC/Opus へのジャケット埋め込みがスキップされるケースが発生していた。

### 対応
- `gui/step_panels/step6_artwork.py` に `_resolve_codec_output_dir()` を追加。
- 自動埋め込み時の探索順を以下に統一：
  1. `_<codec>_output/アーティスト名/アルバム名`（現行）
  2. `_<codec>_output/アルバム名`（旧構成フォールバック）
  3. `_<codec>_output`（最終フォールバック）
- `on_open_mp3tag_opus()` の警告文で発生し得る変数名タイポ（`sanitized_album_名`）を修正。

### 影響
- Step 4/5 で取り込んだ2階層フォルダに対して、Step 6 の自動埋め込みが正しく実行される。
- 既存の単階層データでも従来どおり動作する。

## README 更新 (2026年1月15日)

実装内容に合わせて README を全面的に見直し・拡張：

- **v2.0 アップデート情報**: 最新機能を反映
- **ステップ説明**: 各ステップの役割を詳細化
- **設定方法**: ツールパス、出力フォルダ、品質設定を4つに整理
- **config.ini / state.json**: 詳細な構成を記載
- **トラブルシューティング**: 7つの項目に拡張（GUIが起動しない、ステップが進まない、state.json が見つからない、など）
- **ディレクトリ構造**: 2階層フォルダ構造に対応、フォルダ名のサニタイズ処理を説明
- **Demucs セクション**: ローカル実行と Google Colab を分離

---

## v5.0 (2026年1月6日)

### 概要
v5.0 では、フォルダ構成の階層化、UI/UX の大幅改善、設定管理の自動化、外部ツール連携の強化など、多数の機能追加と改善を実施しました。

---

## 主要機能

### 1. フォルダ構成の階層化
**アーティスト名/アルバム名の2階層構造を導入**

- **対象フォルダ:**
  - `_aac_output/` : アーティスト名/アルバム名/ (Step 4)
  - `_opus_output/` : アーティスト名/アルバム名/ (Step 5)
  - `_final_flac/` : アーティスト名/アルバム名/ (Step 7)

- **実装詳細:**
  - アーティスト名を `StateManager.get_artist_name()` から取得
  - フォルダ名に使用できない文字は `_sanitize_foldername()` で全角文字に置換
  - 親フォルダの自動作成により、フォルダ構成の矛盾を防止
  - フォールバック処理により、既存の単階層フォルダにも対応

**修正ファイル:**
- `gui/step_panels/step4_aac.py`
- `gui/step_panels/step5_opus.py`
- `gui/step_panels/step6_artwork.py`
- `gui/step_panels/step7_transfer.py`
- `gui/step_panels/step_generic.py`

---

### 2. FreeFileSync 設定ファイル指定機能
**FreeFileSync 起動時に設定ファイル（.ffs_gui）を指定**

- config.ini に `freefilesync_config` パスを追加
- 設定ファイルが存在する場合は指定して起動
- ファイルが無い場合は通常起動（フォールバック）
- 設定ダイアログで FreeFileSync 設定ファイルパスを編集可能

**修正ファイル:**
- `config.ini` : `freefilesync_config` パスを追加
- `gui/step_panels/step7_transfer.py` : 設定ファイルを引数として渡す
- `gui/settings_dialog.py` : FreeFileSync 設定ファイルの入力・参照機能を追加

---

### 3. 出力フォルダパス自動化
**m4a/Opus 取り込みパスの自動組み立て**

- **aac_output と opus_output の設定方式を変更:**
  - 変更前：フルパス（`%USERPROFILE%\Videos\エンコード済み\変換MediaHuman` など）
  - 変更後：フォルダ名単体（`変換MediaHuman`, `foobar2000`）
  - これらは `ExternalOutputDir` 配下に自動的に配置される

- **Step 4・5 での取り込み時に自動的にパスを組み立て:**
  - `ExternalOutputDir + aac_output/opus_output` フォルダ名で初期ダイアログ位置を設定
  - フォルダが存在しない場合は `ExternalOutputDir` を開く（フォールバック）
  - ユーザーが手動選択した場合も対応

- **UI に設定指示を追加:**
  - Step 4 と Step 5 パネルに設定方法を黄色パネルで表示
  - MediaHuman: `ExternalOutputDir/変換MediaHuman` に出力するよう案内
  - foobar2000: `ExternalOutputDir/foobar2000` に出力するよう案内

**修正ファイル:**
- `config.ini` : `aac_output` と `opus_output` をフォルダ名単体に変更
- `logic/config_manager.py` : `get_directory_name()` メソッドを追加
- `gui/step_panels/step4_aac.py` : パス自動組み立てロジックと UI 設定指示を追加
- `gui/step_panels/step5_opus.py` : パス自動組み立てロジックと UI 設定指示を追加

**ユーザー対応:**
- MediaHuman 設定: オプション → フォルダ → 出力フォルダ を `ExternalOutputDir/変換MediaHuman` に設定
- foobar2000 設定: Converter設定 → 出力フォルダ を `ExternalOutputDir/foobar2000` に設定

---

### 4. GUI メッセージ改善：外部ツール起動時の操作方法明確化
**すべての外部ツール起動時に詳細な案内ダイアログを表示**

- **問題点:**
  - ユーザーが「〇〇を起動しました」と表示されても、次に何をすれば良いかが不明確

- **解決策:**
  - ツールが起動したことの確認
  - このツールで実行すべき作業（メタデータ編集、変換など）を明記
  - 作業完了後の手順（ツールを閉じる）を説明
  - 自動検出状況（アプリケーションが終了を監視中）を表示

**対象ツール:**
1. **Mp3tag** (Step 3): メタデータ編集とリネーム方法を説明
2. **MediaHuman** (Step 4): フォルダ追加と AAC 変換方法を説明、クリップボード自動コピー機能の説明
3. **foobar2000** (Step 5): ファイル追加と Opus 変換方法を説明、クリップボード自動コピー機能の説明
4. **Music Center** (Step 0): CD 挿入と FLAC 形式での取り込み指示
5. **WinSCP** (Step 7): NAS/サーバー接続と FLAC アップロード指示
6. **iTunes** (Step 7): AAC ファイルの追加方法（ドラッグ&ドロップまたは手動）を説明

**修正ファイル:**
- `gui/step_panels/step0_music_center.py`
- `gui/step_panels/step3_tagging.py`
- `gui/step_panels/step4_aac.py`
- `gui/step_panels/step5_opus.py`
- `gui/step_panels/step7_transfer.py`

**UX 改善効果:**
- ユーザーが起動直後に実施すべき操作が明確になる
- 既に起動中の場合の動作も説明される
- QMessageBox で確認後、ユーザーが各ツールに集中できる
- ツール終了後、自動的に RipTagOptimizes が次のステップへ進む

---

### 5. 設定管理の自動化
**ツールパス自動検出機能とGit管理の最適化**

- **ツールパス自動検出機能:**
  - 初回起動時、一般的なツール（Mp3tag、MediaHuman、foobar2000、WinSCP、iTunes、FreeFileSync、ImageMagick、FLAC）のパスを自動検出
  - `Program Files`、`Program Files (x86)`、`%LOCALAPPDATA%\Programs` 内のツールを自動的に config.ini に書き込み
  - ユーザーによる手動設定の手間を削減

- **Git 管理から除外:**
  - `config.ini` を .gitignore に追加（個人設定ファイルのため）
  - `state.json` を .gitignore に追加（各環境で自動生成されるため）
  - `config.ini.sample` をサンプルファイルとして追加

- **README 更新:**
  - `state.json` の役割と構造を詳細に説明
  - `config.ini` の管理方法と自動検出機能を説明
  - ファイル構造セクションを拡張

**修正ファイル:**
- `logic/config_manager.py` : `_detect_tool_paths()` メソッドを追加し、ツールパス自動検出機能を実装
- `.gitignore` : config.ini と state.json を追加
- `config.ini.sample` : 新規作成（サンプル設定ファイル）
- `README.md` : 重要なファイルセクションを追加

**ユーザーメリット:**
- 初回セットアップが大幅に簡素化
- ツールが標準的な場所にインストールされていれば、自動的に config.ini に設定される
- Git 管理が整理され、個人設定ファイルが共有されない

---

## 技術的改善

### UI/UX
- 設定指示パネルの背景色とテキスト色を最適化（黄色背景 + 濃い灰色テキスト）
- 外部ツール起動時の情報ダイアログを統一
- フォルダ選択ダイアログの初期位置を最適化

### ファイル管理
- アーティスト名/アルバム名の2階層構造により、複数アルバムの管理が容易に
- フォルダ名サニタイズ処理により、Windows でのファイル名エラーを防止
- フォールバック処理により、既存の単階層フォルダとの互換性を維持

### 設定管理
- ツールパス自動検出により、初回セットアップの手間を削減
- 環境変数形式（`%USERPROFILE%`、`%LOCALAPPDATA%`）で設定を保存し、ポータビリティを向上
- Git 管理から個人設定を除外し、チーム開発やバージョン管理を改善

---

## 既知の問題と今後の改善予定

### 既知の問題
なし

### 今後の改善予定
- Step 6 自動化（hasArtwork フラグによる自動スキップ）
- クリーンアップ機能（完了済みアルバムの一括削除）
- エラーハンドリング強化

---

## 互換性

- **Python**: 3.12 以降
- **OS**: Windows 10/11
- **既存データ**: v4.x からの移行時、既存のフォルダ構造もサポート（フォールバック処理）

---

## 移行ガイド

### v4.x からの移行

1. **config.ini の更新:**
   - `aac_output` と `opus_output` をフォルダ名単体に変更
   - 例: `aac_output = 変換MediaHuman`、`opus_output = foobar2000`

2. **外部ツール設定の確認:**
   - MediaHuman: 出力フォルダを `ExternalOutputDir/変換MediaHuman` に設定
   - foobar2000: 出力フォルダを `ExternalOutputDir/foobar2000` に設定

3. **既存アルバムの処理:**
   - 既存の単階層フォルダも引き続き動作します
   - 新規アルバムは自動的に2階層構造で作成されます

---


## まとめ

v5.0 では、ユーザビリティの大幅な改善、設定管理の自動化、フォルダ構成の階層化など、多数の機能追加と改善を実施しました。これにより、初回セットアップが簡素化され、外部ツール連携がより直感的になり、複数アルバムの管理が容易になりました。

## v5.x 更新 (2026/03/14)
- Step2 (Demucs): 
  - 処理対象外の曲ファイルを一時的に \demucs_ignore\ フォルダへ退避し、外部での一括選択操作を効率化。
  - Colabで開くボタンを押下した際、自動で完了ボタンを有効化するように直感性を向上

- Step3 (Tagging): 
  - インストゥルメンタルへのタグ・ファイル名同期を一括で行う「インストを一括同期」ボタンを追加。Mp3tagでの煩雑な手作業（ジャンル変更、タイトルの(Instrumental)(StemRoller)付与、ジャケット画像・メタデータの手動コピー等）を自動化。
  - インスト同期時、ファイル名が \%Track%-%title%\ の形式になるように修正。トラック番号が 10/14 のようになっている場合も単品の数字を抽出してゼロ埋めする処理を追加。
