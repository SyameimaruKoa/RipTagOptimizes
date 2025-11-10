# CDワークフローGUI 更新履歴 (v4)

**更新日:** 2025年11月9日

## ドキュメント更新

### 要件定義書 (v3 → v4)
- ファイル名: `CDワークフローGUI_要件定義書_v3.html`
- 実装状況の凡例を追加 (✅完全実装 / 🔶部分実装 / ❌未実装)
- Step 0 (Music Center ガイド) を新規追加
- Step 1-7 の実装状況を詳細化

### 実装指示書 (v10 → v11)
- ファイル名: `CDワークフローGUI_実装指示書_v10.html`
- 各ステップに実装ファイル名を明記
- 実装済み機能の詳細説明を追加
- 未実装機能のリストアップ

## 主要な実装済み機能

### Step 0: Music Center 取り込みガイド ✅
- Music Center 自動起動機能
- CD リッピング手順案内
- Step 1 へのスキップボタン

### Step 1: 新規取り込み ✅
- **複数アルバム一括取り込み**
- 非ネイティブダイアログ + サイドバーショートカット
- 自動アルバム検出 (.flac ファイル検索)
- **二段階コピー方式** (copytree → send2trash)
- ProcessLookupError フォールバック処理
- 自動 Step 2 進行

### Step 2: Demucs処理 ✅
- チェックボックス式UI
- 自動除外ロジック (SkipKeywords)
- インストペア曲検出
- フォルダ選択とバリデーション

### Step 3: FLAC完成 ✅
- Mp3tag 起動と監視
- **自動ファイル紐づけ**
  - トラック番号優先マッチング
  - タイトル正規化フォールバック
  - Inst ペア検出 (金色バッジ表示)
- **アートワーク自動検査** (mutagen)
- **ReplayGain 自動測定** (foobar2000)
- ファイル再スキャン機能
- 手順ガイドパネル常時表示

### Step 4/5: AAC/Opus 変換 ✅
- MediaHuman / foobar2000 起動
- **ファイル数バリデーション強化**
  - 期待値 vs 実際の比較
  - 確認ダイアログで警告
  - ユーザー判断で進行可否選択
- UI統一 (同じレイアウト)

### Step 6: アートワーク縮小 🔶
**現在の実装:**
- UI パネル存在
- magick.exe コマンドのクリップボードコピー

**未実装:**
- ❌ hasArtwork フラグによる自動スキップ
- ❌ magick.exe 自動実行
- ❌ config.ini 品質設定読み込み

### Step 7: 最終転送 ✅
- **3サブステップ方式**
  - 7-1: FLAC転送 (FreeFileSync)
  - 7-2: AAC転送 (FreeFileSync)
  - 7-3: Opus転送 (WinSCP)
- タブ式UI
- 各サブステップで自動ツール起動
- 完了後の自動遷移

## 未実装機能

### 優先度: 高
1. **Step 6 自動化**
   - hasArtwork フラグチェック
   - magick.exe 自動実行
   - 画像抽出と変換処理

2. **config.ini 連携強化**
   - Flac/Metaflac/Magick パス設定
   - JpegQuality/WebpQuality 設定

3. **クリーンアップ機能**
   - Step 7 完了時の自動削除提案
   - 完了済みアルバム一括削除

### 優先度: 中
1. **Step 6/7 スキップロジック**
   - hasArtwork == false 時の自動スキップ
   - スキップ理由の明示

2. **エラーハンドリング強化**
   - 各ステップのエラー情報詳細化
   - リトライ機能

### 優先度: 低
1. **ログ機能**
   - _logs フォルダへの実行ログ保存
   - エラーログのダイアログ表示

2. **設定画面**
   - config.ini をGUIで編集
   - ツールパスの自動検出

## state.json スキーマ拡張

```json
{
  "version": "1.0",
  "hasArtwork": true,  // Step 3 で自動設定 (null/true/false)
  "tracks": [
    {
      "id": "track_001",
      "originalFile": "01.flac",
      "finalFile": "01 - Title.flac",
      "instrumentalFile": "02 - Title (Inst).flac",  // 新規追加
      "hasInstrumental": true,  // 新規追加
      "isInstrumental": false,  // 新規追加
      "demucsTarget": true
    }
  ],
  "paths": {
    "rawFlacSrc": "_flac_src",  // Step 1 で FLAC 移動先
    "demucsOutput": "",
    "aacOutput": "_aac_output",
    "opusOutput": "_opus_output",
    "artworkResized": "_artwork_resized",
    "finalFlac": "_final_flac"
  },
  "flags": {
    "step2_skipped": false
  }
}
```

## 技術的改善点

### 安全性
- 二段階コピー方式による元データ保護
- ProcessLookupError フォールバック処理
- 確認ダイアログの充実

### 自動化
- ファイル紐づけ自動化
- アートワーク検査自動化
- ReplayGain 測定自動化
- Step 進行自動化

### UX
- 複数アルバム一括処理
- サイドバーショートカット
- 手順ガイド常時表示
- リッチなフィードバック (金色バッジ等)
- タブ式UI (Step 7)

## 次のアクション

1. **Step 6 自動化実装**
   - hasArtwork チェック追加
   - magick.exe 自動実行ロジック
   - config.ini 品質設定読み込み

2. **クリーンアップ機能実装**
   - Step 7 完了時の削除提案ダイアログ
   - send2trash による安全な削除

3. **config.ini パス設定活用**
   - Flac/Metaflac/Magick パスの読み込み
   - 未設定時の自動検出またはエラー表示

4. **テストとバグ修正**
   - 各ステップの動作確認
   - エッジケースのテスト
   - エラーハンドリング強化
