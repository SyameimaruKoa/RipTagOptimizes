# CDワークフローGUI 要件定義書 v3→v4 更新内容

## 更新日: 2025年11月9日

## 主な変更点

### 1. 実装状況の明確化
各ステップに実装状況を追加:
- ✅ = 完全実装済み
- 🔶 = 部分実装済み（機能追加が必要）
- ❌ = 未実装

### 2. 新規追加: Step 0 (Music Center ガイド)
- Music Center 起動ボタン
- CD リッピング手順ガイド
- Step 1 へのスキップ機能

### 3. Step 1 (新規取り込み) の強化
- **複数アルバム一括取り込み対応**
- 非ネイティブダイアログ + サイドバーショートカット
- 自動アルバム検出機能
- **二段階コピー方式による安全性向上**
  - copytree → send2trash (失敗時は shutil.rmtree)
  - ProcessLookupError 対策実装済み
- 自動 Step 2 進行機能

### 4. Step 3 (FLAC完成) の機能拡張
- **自動ファイル紐づけロジック**
  - トラック番号優先マッチング
  - タイトル正規化フォールバック
  - Instrumental ペア自動検出
- **アートワーク自動検査** (mutagen 使用)
  - hasArtwork フラグ自動設定
- **ReplayGain 自動測定** (foobar2000 連携)
  - config.ini で有効/無効切り替え可能
- ファイル再スキャンボタン追加
- 手順ガイドパネル常時表示

### 5. Step 4/5 (AAC/Opus 変換) の検証強化
- **ファイル数バリデーション確認ダイアログ**
  - 期待値 = finalFile + instrumentalFile
  - 不足時は警告ダイアログで確認
  - ユーザー判断で進行可否を選択可能

### 6. Step 7 の構造変更
- **3サブステップ方式に変更**
  - 7-1: FLAC転送 (FreeFileSync)
  - 7-2: AAC転送 (FreeFileSync)
  - 7-3: Opus転送 (WinSCP)
- タブ式UI実装
- 各サブステップで自動ツール起動

### 7. 未実装・今後の課題
**Step 6 (アートワーク縮小)**
- ❌ hasArtwork フラグによる自動スキップ
- ❌ magick.exe 自動実行
- ❌ config.ini の品質設定読み込み

**クリーンアップ**
- ❌ Step 7 完了時の自動削除提案
- ❌ 完了済みアルバム一括削除

**config.ini 連携**
- ❌ Flac/Metaflac/Magick パス設定の活用
- ❌ JpegQuality/WebpQuality 設定の活用

## state.json スキーマの追加フィールド

```json
{
  "hasArtwork": true,  // Step 3 で自動設定
  "tracks": [
    {
      "finalFile": "01 - Title.flac",
      "instrumentalFile": "02 - Title (Inst).flac",
      "hasInstrumental": true,
      "isInstrumental": false
    }
  ],
  "paths": {
    "rawFlacSrc": "_flac_src"  // Step 1 で FLAC 移動先
  }
}
```

## 技術的改善

1. **安全性向上**
   - 二段階コピーで元データ保護
   - ProcessLookupError フォールバック処理
   - 確認ダイアログの充実

2. **自動化推進**
   - ファイル紐づけ自動化
   - アートワーク検査自動化
   - ReplayGain 測定自動化

3. **UX改善**
   - 複数アルバム一括処理
   - サイドバーショートカット
   - 手順ガイド常時表示
   - リッチなフィードバック（金色バッジ等）
