# CD Workflow GUI v1.0 リリース手順

## リリース準備チェックリスト

### ✅ 完了項目

- [x] 一括処理機能を無効化（v1.0では実装予定として記載）
- [x] README_v1.0.md 作成
- [x] CHANGELOG_v1.0.md 作成
- [x] LICENSE ファイル作成
- [x] .gitignore 強化
- [x] config.ini.sample 作成
- [x] LAUNCH_GUI.bat 統合版作成

### 📋 リリース前の最終確認

1. **動作確認**
   ```cmd
   LAUNCH_GUI.bat
   ```
   - [ ] 初回セットアップが正常に動作する
   - [ ] GUIが起動する
   - [ ] 各ステップが正常に動作する
   - [ ] 設定画面が開く
   - [ ] ロールバック機能が動作する

2. **ファイル確認**
   - [ ] 不要なファイルが含まれていない
   - [ ] config.ini に個人情報が含まれていない
   - [ ] work/ ディレクトリが空（または.gitignoreで除外）

3. **ドキュメント確認**
   - [ ] README_v1.0.md の内容が正確
   - [ ] CHANGELOG_v1.0.md が最新
   - [ ] config.ini.sample が正しい

## GitHubリリース手順

### 1. リポジトリ準備

```bash
# 現在のディレクトリで実行
cd "C:\Users\kouki\Desktop\CD取り込み自動化v2"

# Gitリポジトリ初期化（まだの場合）
git init

# README.mdをv1.0版に差し替え
copy README_v1.0.md README.md

# CHANGELOG.mdをv1.0版に差し替え
copy CHANGELOG_v1.0.md CHANGELOG.md

# ファイルを追加
git add .

# コミット
git commit -m "Release v1.0.0 - Initial public release"

# タグを作成
git tag -a v1.0.0 -m "Version 1.0.0 - Initial Release"
```

### 2. GitHubリポジトリ作成

1. GitHubにログイン
2. 「New repository」をクリック
3. リポジトリ名: `RipTagOptimize`
4. Description: 音楽CDの取り込みから各種変換・転送までを一元管理するGUIアプリ
5. Public を選択
6. 「Create repository」をクリック

### 3. リモートリポジトリと連携

```bash
# リモートリポジトリを追加（YOUR_USERNAMEを実際のユーザー名に変更）
git remote add origin https://github.com/YOUR_USERNAME/RipTagOptimize.git

# プッシュ
git branch -M main
git push -u origin main

# タグをプッシュ
git push origin v1.0.0
```

### 4. GitHubでリリースを作成

1. GitHubリポジトリページの「Releases」をクリック
2. 「Create a new release」をクリック
3. 「Choose a tag」で `v1.0.0` を選択
4. Release title: `v1.0.0 - Initial Release`
5. Description に以下を記載：

```markdown
## 🎉 CD Workflow GUI v1.0.0 - Initial Release

音楽CDの取り込みから各種フォーマット変換、タグ付け、アートワーク処理、NAS転送までを一元管理するGUIアプリケーションの初回リリースです。

### ✨ 主な機能

- 8ステップのワークフロー管理
- 自動進捗保存（state.json）
- ステップロールバック機能
- 設定GUI（ツールパス・品質設定・Demucs設定）
- ログビューア
- 外部ツール連携（Mp3tag、MediaHuman、foobar2000等）

### 📥 インストール

1. リポジトリをクローン
2. `LAUNCH_GUI.bat` を実行（初回は自動セットアップ）

詳細は [README.md](README.md) を参照してください。

### 📝 変更履歴

[CHANGELOG.md](CHANGELOG.md) を参照してください。

### 🐛 既知の問題

- 一括処理機能は次期バージョンで実装予定
- Windows専用（Linux/macOS未対応）
```

6. 「Publish release」をクリック

## リリース後の作業

### README.md の更新（次の開発用）

```bash
# v1.0のREADME.mdを元に戻す
git checkout README.md
```

### 開発ブランチの作成

```bash
# develop ブランチを作成
git checkout -b develop

# 一括処理機能を有効化（次期バージョン用）
# gui/main_window.py の該当部分のコメントを外す

git add .
git commit -m "Start development for v1.1.0 - Re-enable batch process feature"
git push -u origin develop
```

## 注意事項

### 含めないもの

- 個人情報（NASパス、ユーザー名等）
- 作業中のアルバムデータ（work/ディレクトリ）
- 仮想環境（.venv/）
- IDE設定（.vscode/、.idea/）

### セキュリティ

- config.ini.sample は一般的な例のみ
- 実際の config.ini は .gitignore で除外
- パスワードやトークンは含めない

## トラブルシューティング

### プッシュに失敗する場合

```bash
# 認証情報を確認
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# HTTPSの場合はPersonal Access Tokenを使用
# Settings > Developer settings > Personal access tokens
```

### 大きなファイルがある場合

```bash
# Git LFSを使用
git lfs install
git lfs track "*.mp3"
git lfs track "*.flac"
git add .gitattributes
git commit -m "Add Git LFS tracking"
```

## 完了確認

- [ ] GitHubリポジトリが公開されている
- [ ] v1.0.0 タグが存在する
- [ ] Releaseページにv1.0.0が表示されている
- [ ] README.md が正しく表示されている
- [ ] ライセンスが設定されている

## 次のステップ

1. SNSやブログで告知
2. issueで機能要望・バグ報告を受け付け
3. v1.1.0の開発開始（一括処理機能の実装）
