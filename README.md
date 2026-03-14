# CD取り込み自動化ワークフロー GUI

音楽CDの取り込みから各種フォーマット変換、タグ付け、アートワーク処理、NAS転送までを一元管理するGUIアプリケーションです。

> 現在の状態: Step 0-7 の日常運用フローは一通り安定しています。Step 3 の自動紐づけとインスト同期も見直しを完了し、通常運用で完了扱いにできる状態です。

**現行の主要アップデート:**
- ✅ フォルダ構成の階層化（アーティスト名/アルバム名の2階層構造）
- ✅ FreeFileSync 設定ファイル指定機能
- ✅ 出力フォルダパス自動化（aac_output、opus_output）
- ✅ 外部ツール起動時の詳細ガイド表示
- ✅ ツールパス自動検出機能
- ✅ 環境変数対応による複数ユーザー環境サポート
- ✅ Demucs生成インストファイルの完全サポート
- ✅ Step 3 の自動紐づけ安定化（誤マッピング抑止・詳細デバッグログ追加）

## ⚠️ 重要な注意事項

**このアプリケーションは個人的な使用を目的として開発されたものです。**

- 作者自身のワークフローに最適化されており、他の環境での動作は保証されません
- 使用は自己責任でお願いします
- データの損失や破損が発生する可能性があります
- **必ず重要なデータはバックアップしてからご使用ください**
- 外部ツールの動作や互換性については各ツールの公式ドキュメントを参照してください

## 主な機能

### 8ステップのワークフロー管理

- **Step 0**: Music Center取り込みガイド（CD取り込み手順の案内）
- **Step 1**: 新規アルバム取り込み（フォルダ選択・state.json生成）
- **Step 2**: Demucs処理（ボーカル分離・インスト版作成、またはインスト版ファイルの取り込み）
- **Step 3**: FLAC完成（Mp3tag連携・タグ付け・リネーム・ReplayGain自動適用）
- **Step 4**: AAC変換（MediaHuman Audio Converter連携）
- **Step 5**: Opus変換（foobar2000連携）
- **Step 6**: アートワーク最適化（ImageMagick連携・JPEG/WebP生成）
- **Step 7**: NAS転送（WinSCP連携・クリーンアップ）

### 便利な機能

- **自動進捗管理**: 各アルバムの進行状況を`state.json`で自動保存
- **ステップロールバック**: 「⏪ 前ステップへ」ボタンで前のステップに戻してやり直し可能
- **作業破棄**: 「作業破棄」ボタンでアルバムフォルダをゴミ箱へ安全に移動
- **設定GUI**: ⚙️ 設定ボタンで config.ini の各種設定をGUIで編集可能
- **ログビューア**: 📋 ログボタンで処理履歴を確認可能
- **アルバム自動スキャン**: 5秒ごとに「work」フォルダをスキャンして最新状態を表示
- **自動スキップ**: Demucs自動除外キーワードに合致した楽曲を自動除外
- **外部ツール起動ガイド**: ツール起動時に詳細な操作手順を表示
- **フォルダ階層化**: アーティスト名/アルバム名の2階層構造で複数アルバムを整理

### Step 3 の現行仕様

- `originalFile` と実ファイルの紐づけは、トラック番号・タイトル正規化・一意候補を優先して決定します。
- インストファイルは通常トラックと分離して扱い、同一FLACが複数トラックへ誤割当されないようにしています。
- 再スキャン時は詳細デバッグログを出力するため、問題発生時もログだけで判断経路を追えます。
- 自動判定で確定できない曲は無理に紐づけず「未検出」として残し、手動紐づけで補正します。

## システム要件

- **OS**: Windows 10/11
- **Python**: 3.12以降
- **外部ツール**（パスは設定GUIで指定可能、初回起動時に自動検出）:
  - Music Center（Sony製CDプレーヤー）
  - Mp3tag（タグ編集用）
  - MediaHuman Audio Converter（AAC変換用）
  - foobar2000（Opus変換・ReplayGain用）
  - WinSCP（NAS転送用）
  - FreeFileSync（ファイル同期、オプション）
  - flac/metaflac（FLAC処理用）
  - ImageMagick（アートワーク処理用）
  - iTunes（AAC登録用、オプション）
  - demucs（Pythonパッケージ、オプション・ボーカル分離用）

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/SyameimaruKoa/RipTagOptimizes.git
cd RipTagOptimizes
```

### 2. 起動（初回自動セットアップ）

```cmd
LAUNCH_GUI.bat
```

初回実行時は自動で以下を実行します：
- Python仮想環境（.venv）の作成
- 必要なライブラリのインストール

## 使い方

### 基本的なワークフロー

1. **LAUNCH_GUI.bat** を実行してGUIを起動
2. **Step 1**で新規アルバムフォルダを選択
3. 各ステップを順番に実行
4. 外部ツールを起動して処理を実行
5. 「完了」ボタンで次のステップへ進む

### 設定

ツールバーの「⚙️ 設定」から以下を設定できます：

#### 1. ツールパス設定
- **各外部ツールのパス**: 実行ファイルのパスを指定（初回起動時に自動検出）
- **FreeFileSync設定ファイル**: `.ffs_gui` ファイルのパスを指定（オプション）
- 環境変数（`%USERPROFILE%`、`%LOCALAPPDATA%`）をサポート

#### 2. 出力フォルダ設定
- **ExternalOutputDir**: AAC/Opus変換後のファイルを保存する親フォルダ
  - `aac_output`（フォルダ名）: `ExternalOutputDir/aac_output` に AAC を自動保存
  - `opus_output`（フォルダ名）: `ExternalOutputDir/opus_output` に Opus を自動保存
  
#### 3. 品質設定
- **JPEGの品質**: アートワーク JPEG 品質（1-100、デフォルト: 85）
- **WebPの品質**: アートワーク WebP 品質（1-100、デフォルト: 85）
- **リサイズ幅**: アートワーク縮小幅ピクセル（デフォルト: 600）

#### 4. Demucs設定
- **自動除外キーワード**: この文字列を含む楽曲はDemucs処理から自動除外
- キーワードの動的追加・削除が可能
- 例: "inst.", "(inst)", "オフボーカル", "カラオケ" など

#### 環境変数のサポート

`config.ini`では、パス設定に環境変数を使用できます。複数ユーザー環境やポータブルな設定を実現：

```ini
[Paths]
winscp = %LOCALAPPDATA%\Programs\WinSCP\WinSCP.exe
musiccenterdir = %USERPROFILE%\Music\Music Center

[DefaultDirectories]
demucs_output = %USERPROFILE%\Downloads
artwork_select = %USERPROFILE%\Downloads

[Settings]
externaloutputdir = %USERPROFILE%\Videos\エンコード済み
```

#### ファイルダイアログの初期位置設定

各ステップのファイル選択ダイアログの初期位置は、`config.ini`の`[DefaultDirectories]`セクションで設定：

- **demucs_output**: Demucs出力フォルダ選択の初期位置
- **aac_output**: AAC出力フォルダ選択の初期位置（ExternalOutputDir配下のフォルダ名）
- **opus_output**: Opus出力フォルダ選択の初期位置（ExternalOutputDir配下のフォルダ名）
- **artwork_select**: アートワーク画像選択の初期位置

### ロールバック機能

ステップを間違えた場合、前のステップに戻して処理をやり直すことができます：

1. 対象アルバムを左のリストから選択
2. ツールバーの「⏪ 前ステップへ」をクリック
3. 前のステップに戻ります（完了フラグもクリア）

**注意**: Step 1未満には戻せません。Step 2でのやり直しが最初からの巻き直しの最小単位です。

### 作業破棄機能

アルバムの処理を中止したい場合：

1. 対象アルバムを左のリストから選択
2. ツールバーの「作業破棄」をクリック
3. 確認ダイアログが表示されます
4. 「はい」で、アルバムフォルダはゴミ箱へ移動（完全削除ではなく復元可能）

## （オプション）Demucsによるボーカル除去

Step 2 では、以下の2つのワークフローに対応します：

### 1. インスト音源を既に保有している場合

アルバムフォルダに `no_vocals.wav` または `no_vocals.flac` が既に存在する場合、RipTagOptimize は自動的に検出し、タグ付けやエンコードの対象とします。

- Step 1 でフォルダを取り込むだけでOK

### 2. Demucsで新規にインスト音源を生成する場合

#### ローカル実行について
Step 2 ではローカルにインストールされた Demucs を用いて `no_vocals.wav` / `minus_vocals.flac` を生成できます。

- 対象トラックを選択してから実行
- 生成されたインスト音源は FLAC へ変換後 `(Inst)` 付きファイル名で統合

#### Google Colab での実行（推奨）

Google Colab を使用した Demucs 処理も推奨しています。GPU 環境により高速に処理できます。

- Step 2 パネルの「Colabを開く」ボタンで公開ノートブックにアクセス
- Colab上で処理実行後、完了したフォルダを Step 2 で指定

### 自動除外キーワード

⚙️ 設定 → Demucs タブで「自動除外キーワード」を管理できます。

以下に合致する楽曲は自動的に Demucs 処理から除外されます：
- "inst.", "(inst)", "インスト" など
- "オフボーカル", "カラオケ" など
- "ドラマ", "ボーナス・トラック" など
- その他ユーザーが追加したキーワード

## ディレクトリ構造

### アルバムフォルダの階層

v2.0 では、複数アルバムの管理を容易にするため、アーティスト名/アルバム名の2階層構造を採用しています：

```
work/
  └─ [ArtistName]/              ← アーティスト名フォルダ
       └─ [AlbumName]/          ← アルバムフォルダ
            ├─ state.json       ← 進捗管理ファイル（各アルバムの処理状態）
            ├─ *.flac           ← (Step3完成) 完成品FLAC（タグ付け済み、作業用）
            ├─ _flac_src/       ← (Step1) 生FLAC置き場
            ├─ htdemucs_ft/     ← (Step2) Demucs出力
            ├─ _aac_output/     ← (Step4) AAC出力先（MediaHuman）
            ├─ _opus_output/    ← (Step5) Opus出力先（foobar2000）
            ├─ _artwork_resized/ ← (Step6) リサイズ画像
            ├─ _final_flac/     ← (Step7) 完成品FLACのコピー（YouTube Music/NAS転送用）
            └─ _logs/           ← 自動処理ログ
```

### フォルダ名の自動サニタイズ

Windows では使用できない文字（`<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*`）をフォルダ名から検出した場合、自動的に全角文字に置換されます。
- 例: `Album: Remastered` → `Album：Remastered`

### 重要なファイル

#### state.json

各アルバムの処理進捗を管理する JSON ファイル。以下の情報を保存します：

- **currentStep**: 現在のステップ（1-7）
- **status**: アルバムの状態（"IN_PROGRESS", "COMPLETED"）
- **flags**: 各ステップのスキップフラグ（例：`step2_skipped`）
- **tracks**: トラック情報（ファイルの紐づけ、ReplayGain値など）
- **album**: アルバム名、アーティスト名、メタデータ
- **paths**: 各出力フォルダのパス設定

**注意**: 
- このファイルは Git 管理されません。各ユーザー環境で自動生成されます
- 手動編集は推奨されません。ロールバックや設定GUI経由での変更を使用してください

#### config.ini

アプリケーション全体の設定ファイル。以下の情報を管理します：

##### [Paths] セクション
```ini
mp3tag = C:\Program Files\Mp3tag\Mp3tag.exe
mediahuman = C:\Program Files\MediaHuman\Audio Converter\MHAudioConverter.exe
foobar2000 = C:\Program Files\foobar2000\foobar2000.exe
winscp = %LOCALAPPDATA%\Programs\WinSCP\WinSCP.exe
flac = %USERPROFILE%\OneDrive\CUIApplication\flac\flac.exe
metaflac = %USERPROFILE%\OneDrive\CUIApplication\flac\metaflac.exe
magick = C:\Program Files\ImageMagick-7.1.2-Q16\magick.exe
itunes = C:\Program Files\iTunes\iTunes.exe
freefilesync = C:\Program Files\FreeFileSync\FreeFileSync.exe
freefilesync_config = （オプション）.ffs_gui ファイルパス
musiccenterdir = %USERPROFILE%\Music\Music Center
workdir = .\work
```

##### [DefaultDirectories] セクション
```ini
demucs_output = %USERPROFILE%\Downloads
aac_output = 変換MediaHuman       ← ExternalOutputDir配下のフォルダ名
opus_output = foobar2000           ← ExternalOutputDir配下のフォルダ名
artwork_select = %USERPROFILE%\Downloads
```

##### [Settings] セクション
```ini
jpegquality = 85
webpquality = 85
resizewidth = 600
autoreplaygain = 1
externaloutputdir = %USERPROFILE%\Videos\エンコード済み
foobaruseaddswitch = 1
accepteddisclaimer = false
```

##### [Demucs] セクション
自動除外キーワード（カンマ区切り）

##### [Artwork] セクション
アートワーク品質設定（JPEGクオリティ、WebPクオリティ、リサイズ幅）

**注意**: 
- このファイルは Git 管理されません（個人設定のため）
- 初回起動時、一般的なツールパスを自動検出して作成されます
- 環境変数（`%USERPROFILE%`、`%LOCALAPPDATA%`）をサポート
- 異なるユーザー名でも同じ config.ini を使用可能

## トラブルシューティング

### GUIが起動しない

**症状**: `LAUNCH_GUI.bat` を実行しても何も起動しない、またはエラーが表示される

**解決策**:
1. Python 3.12以降がインストールされているか確認
   ```cmd
   python --version
   ```
2. `.venv`フォルダを削除して`LAUNCH_GUI.bat`を再実行（仮想環境を再作成）
3. 手動で仮想環境を作成・起動してから起動
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

### 外部ツールが起動しない

**症状**: ステップパネルで「実行」ボタンを押しても何も起動しない

**解決策**:
1. ⚙️ 設定 → 「ツールパス」タブでツールのパスが正しく設定されているか確認
   - 「参照」ボタンで手動選択が可能
2. 指定されたパスでツールが実際にインストールされているか確認
3. 初回起動後、自動検出機能でパスが正しく設定されているか確認

### ステップが進まない

**症状**: 「完了」ボタンを押してもステップが次に進まない

**解決策**:
1. 各ステップの「完了」ボタンを正確に押しているか確認
2. ツールバーの「再スキャン」ボタンを押して状態を再読み込みしてください
3. ログビューア（📋 ログボタン）でエラーメッセージを確認
4. 以下のことが完了しているか確認：
   - **Step 2 (Demucs処理)**: インスト版ファイルが `_flac_src` または `htdemucs_ft` に存在
   - **Step 3 (タグ付け)**: 全トラックのファイル紐づけが完了（手動マッチングまたは自動検出）
   - **Step 4 (AAC変換)**: AAC ファイルが `_aac_output` フォルダに十分な数存在
   - **Step 5 (Opus変換)**: Opus ファイルが `_opus_output` フォルダに十分な数存在
   - **Step 6 (アートワーク)**: `cover.jpg` と `cover.webp` が存在

### state.json が見つからない

**症状**: アルバムが左のリストに表示されない

**解決策**:
1. アルバムフォルダが `work/[ArtistName]/[AlbumName]/` の2階層構造になっているか確認
2. フォルダ内に `state.json` が存在するか確認
3. 新しいアルバムの場合は、「新規取り込み」から Step 1 でアルバムを追加してください

### 画像ファイルがアートワーク最適化できない

**症状**: Step 6 でアートワーク最適化を実行してもファイルが生成されない

**解決策**:
1. ImageMagick がインストールされており、パスが正しく設定されているか確認
2. 元となる画像ファイル（JPG/PNG等）がアルバムフォルダに存在するか確認
3. 画像ファイルの形式がサポートされているか確認（JPG、PNG、WEBP等）
4. 設定 → アートワーク タブで品質設定が適切か確認

### ファイル紐づけがうまくいかない

**症状**: Step 3 でファイルが自動的に紐づけられない、または間違った紐づけになる

**解決策**:
1. ログ内の `[DEBUG][Step3]` / `[WARN][Step3]` を確認し、`strategy=selected` の最終決定内容を確認
2. `strategy=not-found` または `strategy=title-no-ver-ambiguous` が出ている場合は自動確定を保留しています
3. Mp3tag 側でトラック番号とタイトルタグが正しいか確認
4. 「ファイル再スキャン」を実行して再判定
5. それでも解決しない場合は「手動紐づけ」ボタンで対象曲のみ補正

### 複数ユーザー環境で設定が共有されない

**症状**: 別のユーザーで起動したら設定がリセットされている

**解決策**:
1. config.ini のパス設定で環境変数を使用するか確認
   - `%USERPROFILE%`, `%LOCALAPPDATA%` 等の環境変数を使用
   - 絶対パス（例: `C:\Users\UserA\...`）は避ける
2. 各ユーザーで初回起動時に自動検出が行われます

## 開発情報

- **Language**: Python 3.12
- **GUI Framework**: PySide6 (Qt for Python)
- **State Management**: JSON
- **Version Control**: Git

## ライセンス

MIT License

## 免責事項

このソフトウェアは「現状のまま」提供され、明示または黙示を問わず、いかなる保証もありません。作者は、このソフトウェアの使用によって生じたいかなる損害についても責任を負いません。

**本アプリケーションは作者個人の使用を目的として開発されたものであり、汎用性や互換性は保証されません。ご使用の際は必ず事前にバックアップを取り、自己責任でご利用ください。**

## 作者

YOUR_NAME

## 更新履歴

詳細は [CHANGELOG_v5.md](CHANGELOG_v5.md) を参照してください。

