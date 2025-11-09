# Changelog

All notable changes to this project will be documented in this file.

## ⚠️ 重要な注意

このアプリケーションは個人的な使用を目的として開発されたものです。他の環境での動作は保証されません。使用は自己責任でお願いします。

## [1.0.0] - 2025-01-09

### Added

#### Core Features
- 8ステップのワークフロー管理システム
  - Step 0: Music Center取り込みガイド
  - Step 1: 新規アルバム取り込み
  - Step 2: Demucs処理（ボーカル分離）
  - Step 3: タグ付け・リネーム（Mp3tag連携）
  - Step 4: AAC変換（MediaHuman連携）
  - Step 5: Opus変換（foobar2000連携）
  - Step 6: アートワーク最適化（ImageMagick連携）
  - Step 7: NAS転送・クリーンアップ

#### Workflow Management
- state.jsonによる進捗管理
- アルバム別の作業状態自動保存
- ステップロールバック機能（Step 2以降）
- 作業破棄機能（ゴミ箱へ安全移動）

#### User Interface
- PySide6ベースのモダンなGUI
- 左側：アルバムリスト（自動更新）
- 右側：ステップ別パネル表示
- ツールバー：主要機能へのクイックアクセス
- ステータスバー：現在の状態表示

#### Settings
- 設定GUI（config.ini編集）
  - ツールパスタブ：外部ツールの実行ファイルパス設定
  - 品質設定タブ：JPEG/WebP品質、リサイズ幅
  - Demucs設定タブ：除外キーワード管理（動的追加・削除）

#### Demucs Features
- 自動除外キーワード検出
  - ファイル名にキーワードが含まれる場合、Demucs処理をスキップ
  - デフォルトキーワード：instrumental, inst, off vocal, カラオケ等
- Demucsスキップ警告
  - スキップ後の手動紐づけ機能使用時に警告表示
- 手動紐づけダイアログ
  - originalFile ↔ currentFile の手動マッピング
  - difflib自動マッチング機能

#### Artwork Handling
- hasArtwork検出によるStep 6自動スキップ
- ImageMagickによるリサイズ・品質最適化
  - JPEG品質設定（デフォルト85%）
  - WebP品質設定（デフォルト85%）
  - リサイズ幅設定（デフォルト600px）

#### Cleanup & Transfer
- send2trashによる安全な削除
- shutil.moveによるフォルダ移動
- WinSCPによるSFTP転送対応
- FreeFileSyncによるNAS同期対応
- 中間ファイルの自動クリーンアップ

#### Logging
- LogManagerによる処理ログ記録
- ログビューアダイアログ
- ステップ別ログファイル（_logs/ディレクトリ）

#### Setup & Launch
- 統合起動スクリプト（LAUNCH_GUI.bat）
  - 初回実行時：自動セットアップ（venv作成・依存関係インストール）
  - 2回目以降：即座にGUI起動
  - requirements.txt更新時：自動再インストール
- ヘルプ表示機能（-h, --help）

#### Developer Tools
- VSCode設定ファイル（.vscode/settings.json）
  - Pylance型チェック最適化
  - 仮想環境パス設定
- pyrightconfig.json（Pylance設定）
- .gitignore（Python標準 + プロジェクト固有）

### Technical Details

#### Dependencies
- PySide6 (Qt for Python)
- send2trash (安全なファイル削除)
- その他（requirements.txt参照）

#### Architecture
- GUIフレームワーク: PySide6
- 状態管理: JSON (state.json)
- 設定管理: INI (config.ini)
- ログ管理: テキストファイル

#### File Structure
```
.
├── gui/                    # GUIコンポーネント
│   ├── main_window.py     # メインウィンドウ
│   ├── settings_dialog.py # 設定ダイアログ
│   └── step_panels/       # ステップ別パネル
├── logic/                 # ビジネスロジック
│   ├── config_manager.py  # 設定管理
│   ├── state_manager.py   # 状態管理
│   └── workflow_manager.py # ワークフロー管理
├── config.ini            # 設定ファイル
├── main.py               # エントリポイント
├── LAUNCH_GUI.bat        # 起動スクリプト
└── requirements.txt      # Python依存関係
```

### Known Limitations

- 一括処理機能は v1.0 では無効化（次期バージョンで実装予定）
- Step 0, 1 へのロールバックは不可
- Windows専用（Linux/macOS未対応）

### Notes

- 初回リリースバージョン
- 基本的なワークフロー管理機能を実装
- 外部ツール連携による柔軟な処理

---

## Release Information

- **Version**: 1.0.0
- **Release Date**: 2025-01-09
- **Platform**: Windows 10/11
- **Python Version**: 3.12+
