# CD取り込み自動化ワークフロー GUI - CHANGELOG v2.0

**リリース日:** 2025年11月10日

---

## 🎉 v2.0 主要機能

### 🎵 Demucs生成インストファイルの完全サポート

**問題点（v1.x）:**
- Demucs（AI音源分離）で生成したインストファイルが正しく認識されない
- ボーカル入りトラックとインストトラックの紐づけが不正確
- 手動紐づけダイアログにインストファイルが表示されない

**解決策（v2.0）:**
- ✅ **自動検出ロジックの強化**
  - `(StemRoller)` 付きファイルを優先的に検出
  - バージョン情報（M@STER VERSION, GAME VERSION）を考慮した正確なマッチング
  - 既存の `(Inst).flac` ファイルとの互換性維持

- ✅ **独立トラックとしての管理**
  - インストファイルを`state.json`に独立したトラックとして記録
  - 親トラック（ボーカル入り）との関連付けを維持
  - 後続ステップ（AAC/Opus変換、転送）で正しく処理

- ✅ **UIの改善**
  - 🎵 親トラック（ボーカル入り）
    - └ 🎹 インストトラック（子要素として表示）
  - 🎹 独立インストトラック（単体表示）
  - 手動紐づけダイアログに全てのFLACファイルを表示

**技術的詳細:**
- `step3_tagging.py`: `update_file_mapping()` メソッドの全面改修
- インストファイルの優先度ロジック: (StemRoller) > (Inst) > state.json記録
- `by_title_inst` 辞書による正規化タイトルマッチング

---

### 🌍 環境変数対応による複数ユーザー環境サポート

**問題点（v1.x）:**
- `config.ini`にハードコードされたユーザーパス（`C:\Users\kouki\...`）
- 他のユーザー環境では設定ファイルの手動修正が必要

**解決策（v2.0）:**
- ✅ **Windows環境変数のサポート**
  - `%USERPROFILE%`: ユーザーホームディレクトリ
  - `%LOCALAPPDATA%`: ローカルAppDataフォルダ
  - `~`: ユーザーホームディレクトリ（クロスプラットフォーム）

- ✅ **自動展開機能**
  - `ConfigManager.expand_path()` メソッドで自動的に環境変数を展開
  - パス系設定（`*dir`, `*path`）は自動的に展開処理

**設定例:**
```ini
[Paths]
winscp = %LOCALAPPDATA%\Programs\WinSCP\WinSCP.exe
flac = %USERPROFILE%\OneDrive\CUIApplication\flac\flac.exe
musiccenterdir = %USERPROFILE%\Music\Music Center

[Settings]
externaloutputdir = %USERPROFILE%\Videos\エンコード済み
```

**技術的詳細:**
- `logic/config_manager.py`: `expand_path()` 静的メソッド追加
- `os.path.expandvars()` と `os.path.expanduser()` の組み合わせ
- 既存コードへの影響最小限（後方互換性維持）

---

### 📂 ファイルダイアログの初期位置カスタマイズ機能

**問題点（v1.x）:**
- ファイル選択ダイアログの初期位置が固定
- 外部ツールの出力先が毎回異なる場合に不便

**解決策（v2.0）:**
- ✅ **`[DefaultDirectories]` セクションの追加**
  - 各ステップのファイルダイアログ初期位置を個別に設定可能
  - 空欄時は適切なフォールバック（ダウンロードフォルダなど）

**設定項目:**
```ini
[DefaultDirectories]
demucs_output = %USERPROFILE%\Downloads
aac_output = %USERPROFILE%\Videos\エンコード済み\変換MediaHuman
opus_output = %USERPROFILE%\Videos\エンコード済み\foobar2000
artwork_select = %USERPROFILE%\Downloads
```

**対応ステップ:**
- **Step 2**: Demucs出力フォルダ選択 → `demucs_output`
- **Step 4**: AAC出力フォルダ選択 → `aac_output`
- **Step 5**: Opus出力フォルダ選択 → `opus_output`
- **Step 6**: アートワーク画像選択 → `artwork_select`

**技術的詳細:**
- `ConfigManager.get_default_directory()` メソッド追加
- 各ステップパネルでフォールバックロジック実装
- ユーザビリティ向上（毎回同じフォルダから選択可能）

---

## 🐛 バグ修正

### Step 3: ファイル紐づけの問題
- **修正**: ボーカル入りトラックがインストファイルに誤紐づけされる問題
  - `norm_title()` に `remove_version_info` パラメータを追加
  - バージョン情報の有無で適切にマッチング

- **修正**: `state.json` の `finalFile` がインストファイル名になる問題
  - トラックタイプ（ボーカル/インスト）を正確に判定
  - `isInstrumental` フラグの正確な設定

- **修正**: 手動紐づけダイアログにインストファイルが表示されない
  - 物理ファイルシステムから全FLACファイルを取得するロジックは正常
  - `state.json` への独立トラック追加で解決

### Step 2: Demucs処理
- **改善**: FLAC変換時のプログレスダイアログ追加
  - `QProgressDialog` によるユーザーフィードバック
  - キャンセル可能な処理

- **改善**: Google Colab リンクをフルURLに変更
  - `.ipynb` 拡張子付きで正しく開くように修正

### 設定関連
- **削除**: 重複設定 `transfer_external` の削除
  - `ExternalOutputDir` (`[Settings]`) で統一
  - `[DefaultDirectories]` から削除して整理

---

## 📝 ドキュメント更新

### README.md
- v2.0 の主要アップデート情報を追加
- 環境変数の使用方法を記載
- ファイルダイアログ初期位置設定の説明を追加

### config.ini
- デフォルト設定を環境変数形式に更新
- `[DefaultDirectories]` セクションを追加
- コメントと説明を充実

---

## 🔧 技術的改善

### コード品質
- デバッグログの充実（インストファイル検出プロセス）
- 関数の責任分離（`_append_mapping_row_*` メソッド群）
- 型ヒントの追加（複数箇所）

### パフォーマンス
- ファイルマッチングアルゴリズムの最適化
- 重複処理の削減（`processed_files` セットの活用）

### メンテナンス性
- 設定キー名の統一（`*_import` → `*_output`）
- マジックナンバーの削除
- コメントの充実

---

## 🚀 移行ガイド（v1.x → v2.0）

### 1. config.ini の更新

**手動更新が必要な項目:**
```ini
# v1.x（手動修正推奨）
winscp = C:\Users\kouki\AppData\Local\Programs\WinSCP\WinSCP.exe

# v2.0（推奨形式）
winscp = %LOCALAPPDATA%\Programs\WinSCP\WinSCP.exe
```

**新規追加項目（オプション）:**
```ini
[DefaultDirectories]
demucs_output = %USERPROFILE%\Downloads
aac_output = %USERPROFILE%\Downloads
opus_output = %USERPROFILE%\Downloads
artwork_select = %USERPROFILE%\Downloads
```

### 2. state.json の互換性

- ✅ **v1.x の state.json は v2.0 で読み込み可能**
- ⚠️ **再スキャン推奨**: Step 3 で「ファイル再スキャン」を実行することで、インストファイルが正しく認識されます

### 3. 既存プロジェクトの動作確認

1. アプリケーション起動
2. 既存アルバムを選択
3. Step 3 で「ファイル再スキャン」をクリック
4. インストファイルが正しく表示されることを確認

---

## 📊 統計情報

- **変更ファイル数**: 10+
- **追加コード行数**: 約300行
- **削除コード行数**: 約50行
- **修正バグ数**: 5件
- **新機能数**: 3件

---

## 🙏 謝辞

v2.0 の開発にあたり、実際の使用を通じて発見された問題点のフィードバックに感謝します。

---

## 📅 次期バージョン予定（v3.0）

- バッチ処理機能の強化
- より詳細なエラーレポート
- UIテーマのカスタマイズ
- 自動アップデート機能

---

**完全な変更履歴**: [GitHub Releases](https://github.com/SyameimaruKoa/RipTagOptimize/releases)
