# CD Workflow GUI v2.0 リリース手順

## リリース準備チェックリスト

### ✅ v2.0 完了項目

- [x] Demucs生成インストファイルの完全サポート
- [x] 環境変数対応の実装
- [x] ファイルダイアログ初期位置カスタマイズ
- [x] config.ini の環境変数化
- [x] README.md のバージョン更新（v2.0）
- [x] CHANGELOG_v2.0.md 作成
- [x] main.py にバージョン情報追加
- [x] 設定キー名の統一（*_output）

### 📋 リリース前の最終確認

1. **動作確認**
   ```cmd
   LAUNCH_GUI.bat
   ```
   - [ ] 初回セットアップが正常に動作する
   - [ ] GUIが起動する（タイトルに "v2.0.0" 表示）
   - [ ] Step 3 でDemucs生成インストファイルが正しく表示される
   - [ ] 環境変数（%USERPROFILE%等）が正しく展開される
   - [ ] ファイルダイアログの初期位置が config.ini で設定可能
   - [ ] 既存の v1.x state.json が読み込める

2. **ファイル確認**
   - [ ] config.ini が環境変数形式になっている
   - [ ] 個人情報が含まれていない
   - [ ] work/ ディレクトリが空（または.gitignoreで除外）
   - [ ] CHANGELOG_v2.0.md が完成している

3. **ドキュメント確認**
   - [ ] README.md に v2.0 の情報が記載されている
   - [ ] 環境変数の使用方法が説明されている
   - [ ] 移行ガイドが明確

## GitHubリリース手順

### 1. 最終コミット

```bash
cd "C:\Users\kouki\Downloads\RipTagOptimizes"

# 変更を確認
git status

# ファイルを追加
git add .

# コミット
git commit -m "Release v2.0.0 - Demucs support & Environment variables"

# タグを作成
git tag -a v2.0.0 -m "Version 2.0.0 - Demucs インストファイル完全サポート & 環境変数対応"
```

### 2. リモートリポジトリにプッシュ

```bash
# プッシュ
git push origin main

# タグをプッシュ
git push origin v2.0.0
```

### 3. GitHubでリリースを作成

1. GitHubリポジトリページの「Releases」をクリック
2. 「Draft a new release」をクリック
3. 「Choose a tag」で `v2.0.0` を選択
4. Release title: `v2.0.0 - Demucs完全サポート & 環境変数対応`
5. Description に以下を記載：

```markdown
## 🎉 CD Workflow GUI v2.0.0 - Major Update

### 🎵 主要アップデート

#### 1. Demucs生成インストファイルの完全サポート
- ✅ AI音源分離（Demucs）で生成したインストファイルの自動検出
- ✅ ボーカル入りトラックとの正確な紐づけ
- ✅ 階層表示による視覚的な親子関係
- ✅ 後続ステップ（AAC/Opus変換）での正しい処理

#### 2. 環境変数対応による複数ユーザー環境サポート
- ✅ `%USERPROFILE%`、`%LOCALAPPDATA%` などの環境変数をサポート
- ✅ ユーザー名が異なる環境でも設定ファイルをそのまま使用可能
- ✅ 自動展開機能による透過的な処理

#### 3. ファイルダイアログ初期位置のカスタマイズ
- ✅ 各ステップのファイル選択ダイアログの初期位置を個別設定
- ✅ Demucs出力、AAC/Opus出力、アートワーク選択に対応
- ✅ フォールバック機能による柔軟な動作

### 🐛 バグ修正

- ボーカル入りトラックがインストファイルに誤紐づけされる問題を修正
- 手動紐づけダイアログでインストファイルが表示されない問題を修正
- バージョン情報（M@STER VERSION等）を考慮したマッチング精度の向上

### 📝 設定ファイルの変更

**v1.x からの移行:**
```ini
# v1.x（旧形式）
winscp = C:\Users\kouki\AppData\Local\Programs\WinSCP\WinSCP.exe

# v2.0（推奨形式）
winscp = %LOCALAPPDATA%\Programs\WinSCP\WinSCP.exe
```

**新規セクション:**
```ini
[DefaultDirectories]
demucs_output = %USERPROFILE%\Downloads
aac_output = %USERPROFILE%\Downloads
opus_output = %USERPROFILE%\Downloads
artwork_select = %USERPROFILE%\Downloads
```

### 🚀 移行方法

1. アプリケーションを起動
2. 既存アルバムを選択
3. **Step 3 で「ファイル再スキャン」をクリック**
4. インストファイルが正しく表示されることを確認

### 📊 変更統計

- 変更ファイル数: 10+
- 追加コード行数: 約300行
- 修正バグ数: 5件
- 新機能数: 3件

### 📖 詳細情報

- [完全なCHANGELOG](CHANGELOG_v2.0.md)
- [README](README.md)

---

**⚠️ 注意事項**
- v1.x の state.json は互換性がありますが、Step 3 で再スキャン推奨
- config.ini は環境変数形式への更新を推奨（旧形式も動作します）
```

6. 「Publish release」をクリック

## リリース後の作業

### 1. リリースノートをSNS等で共有

Twitterやブログで告知する場合のテンプレート：

```
🎉 CD Workflow GUI v2.0.0 をリリースしました！

✨ 主要アップデート：
・Demucs生成インストファイルの完全サポート
・環境変数対応（複数ユーザー環境対応）
・ファイルダイアログ初期位置カスタマイズ

GitHub: https://github.com/YOUR_USERNAME/RipTagOptimize/releases/tag/v2.0.0
#CDリッピング #自動化 #Python #PySide6
```

### 2. Issue/Discussionの整理

- [ ] v2.0 で解決した Issue をクローズ
- [ ] 次期バージョン（v3.0）の計画を Discussions に投稿
- [ ] ユーザーフィードバックを受け付ける Issue テンプレートを作成

### 3. 次期バージョンの準備

```bash
# develop ブランチを作成（まだの場合）
git checkout -b develop

# v2.1 または v3.0 の開発開始
# マイルストーンを作成
```

## v3.0 に向けた予定機能

- バッチ処理機能の強化
- より詳細なエラーレポート
- UIテーマのカスタマイズ
- 自動アップデート機能
- クロスプラットフォーム対応の検討

## トラブルシューティング

### タグが既に存在する場合

```bash
# ローカルタグを削除
git tag -d v2.0.0

# リモートタグを削除
git push origin :refs/tags/v2.0.0

# 再作成
git tag -a v2.0.0 -m "Version 2.0.0"
git push origin v2.0.0
```

### リリースを編集したい場合

1. GitHubのReleasesページへ
2. 該当リリースの「Edit release」をクリック
3. 内容を修正して「Update release」

## 完了確認チェックリスト

- [ ] GitHubリポジトリに v2.0.0 タグが存在する
- [ ] Releaseページに v2.0.0 が表示されている
- [ ] CHANGELOG_v2.0.md がリポジトリに含まれている
- [ ] README.md が v2.0 の情報を含んでいる
- [ ] main.py に `__version__ = "2.0.0"` が記載されている
- [ ] リリースノートが公開されている

## セキュリティチェック

- [ ] config.ini に個人情報（NASパス、ユーザー名等）が含まれていない
- [ ] work/ ディレクトリが除外されている
- [ ] .venv/ が除外されている
- [ ] 秘密鍵やトークンが含まれていない

---

**リリース完了日:** 2025年11月10日
