# CD取り込み自動化ワークフロー・マスターGUI

CD取り込みワークフローを管理・自動化するGUIアプリケーション

## 機能概要

- **10ステップのワークフロー管理**: 取り込みからアーカイブまで
- **状態管理**: 各アルバムの進捗を `state.json` で永続化
- **外部ツール連携**: FastCopy, Mp3tag, MediaHuman, foobar2000, WinSCP 等
- **Demucs自動検出**: インスト曲とそのペア原曲を自動判定
- **アートワーク自動処理**: ImageMagick でリサイズ・変換

## セットアップ手順

### 1. Python環境の準備

Python 3.12 がインストールされていることを確認してください。

```cmd
python --version
```

### 2. 仮想環境の作成

プロジェクトルートで以下のコマンドを実行:

```cmd
python -m venv .venv
```

### 3. 仮想環境のアクティベート

```cmd
.venv\Scripts\activate
```

### 4. 依存ライブラリのインストール

```cmd
pip install -r requirements.txt
```

### 5. 設定ファイルの編集

`config.ini` を開き、各ツールのパスと作業ディレクトリを確認・編集してください。

```ini
[Paths]
FastCopy = C:\Users\kouki\FastCopy\FastCopy.exe
Mp3Tag = C:\Program Files\Mp3tag\Mp3tag.exe
...
```

### 6. 作業フォルダの作成

`config.ini` で指定した `WorkDir` が存在しない場合、自動的に作成されます。

## 起動方法

### 方法1: バッチファイルから起動（推奨）

```cmd
LAUNCH_GUI.bat
```

バッチファイルは自動的に仮想環境をアクティベートし、GUIを起動します。

### 方法2: 直接起動

仮想環境をアクティベートした後:

```cmd
python main.py
```

## 使用方法

### 新規取り込み (Step 1)

1. ツールバーの「新規取り込み」ボタンをクリック
2. Music Center のアルバムフォルダを選択
3. 「取り込み開始」をクリック

### ワークフロー進行

- 左ペインでアルバムを選択
- 右ペインに現在のステップが表示される
- 各ステップの指示に従って作業
- 完了後「完了」ボタンで次のステップへ

### 各ステップの概要

1. **新規取り込み**: Music Center → work フォルダへ移動
2. **Demucs処理**: 音源分離（インスト版作成）
3. **FLAC完成**: Mp3tag でタグ付け・リネーム
4. **AAC変換**: MediaHuman で AAC/M4A 作成
5. **Opus変換**: foobar2000 で Opus 作成
6. **アートワーク縮小**: 自動で JPG/WebP リサイズ
7. **アートワーク交換**: 圧縮音源にアートワーク埋め込み
8. **ReplayGain**: foobar2000 で音量正規化
9. **最終配置**: WinSCP で NAS/クラウドへ転送
10. **クリーンアップ**: 作業フォルダをゴミ箱へ

## トラブルシューティング

### ツールが見つからない

`config.ini` でツールのパスが正しく設定されているか確認してください。

### state.json が作成されない

- work フォルダに書き込み権限があるか確認
- FLAC ファイルが正しく取り込まれているか確認

### アートワークが検出されない

- Mp3tag でアートワークが正しく埋め込まれているか確認
- FLAC ファイルに pictures タグが存在するか確認

## ディレクトリ構造

```
CD取り込み自動化v2/
├─ LAUNCH_GUI.bat          # 起動用バッチファイル
├─ main.py                 # エントリーポイント
├─ config.ini              # 設定ファイル
├─ requirements.txt        # 依存ライブラリ
├─ README.md               # このファイル
├─ .venv/                  # Python仮想環境
├─ work/                   # 作業フォルダ（自動作成）
├─ gui/                    # GUIコンポーネント
│   ├─ main_window.py
│   └─ step_panels/
│       ├─ step1_import.py
│       ├─ step2_demucs.py
│       ├─ step3_tagging.py
│       └─ step_generic.py
└─ logic/                  # ビジネスロジック
    ├─ config_manager.py
    ├─ state_manager.py
    ├─ workflow_manager.py
    ├─ external_tools.py
    ├─ demucs_detector.py
    └─ artwork_handler.py
```

## ライセンス

個人利用のみ

## 作成者

kouki
