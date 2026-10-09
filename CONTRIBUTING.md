# macOS対応への協力

現在の配布対象はWindows版のみです。macOS版は未提供で、現状のソースをそのままパッケージ化しても、Windowsと同じ保存先保護は得られません。DMG作成だけでなく、次の移植・検証への協力を歓迎します。

## 必要な作業

- ファイルを読み書きする前に、macOSのマウント表から保存先が起動ボリューム内のローカルファイルシステムであることを確認する。ネットワーク・外付け・判定不能な保存先は拒否する。確認のために対象パスを先に開いてはならない。
- iCloud、File Provider、既知の同期フォルダを拒否する。`Library/Mobile Documents`、`Library/CloudStorage`、CloudDocsコンテナ、iCloud同期のDesktop/Documentsを検討する。すべての同期・バックアップソフトの検出を保証する表現は避ける。
- 保存結果の表示を、WindowsのExplorerからmacOSのFinderに対応させる。
- macOS上でPyInstallerの `--onedir --windowed` を用いて、PythonとTkinterを含む `.app` を作成する。Tkinterでは `--argv-emulation` を使わない。
- Apple Silicon（arm64）とIntel（x86_64）は個別にビルド・起動確認する。Windowsからのクロスビルドや、完成バイナリの単純な合成で代用しない。
- `hdiutil` でDMGを作成・検証する。Developer ID署名・Apple公証を行わない場合は、Releaseにその制限を明示する。

## 受入確認

- 合成PDFだけを使用し、既存の回帰テストと、マウント・同期・リンク拒否のmacOSテストを通す。
- 実際の `.app` で起動、ファイル選択、処理、保存、終了を確認する。
- 画像PDFだけを保存し、元PDF・作業画像・OCR本文・個人情報をログや一時ファイルに残さない設計を維持する。
- アップロード、テレメトリー、自動更新、不要な通信を追加しない。
- パッケージとGit履歴に作者の端末パス、個人情報、実際のCIC資料を含めない。
- macOS版が未検証の間は、Windows版と同等の安全性をうたわない。

実際のCIC PDFや個人情報をIssue・Pull Request・CIに送信しないでください。再現例は架空の値で作成してください。公開やライセンスの変更は、この移植作業とは別に確認が必要です。

参考: [PyInstallerのmacOS注意事項](https://pyinstaller.org/en/stable/feature-notes.html)、[Appleのマウント定義](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/mount.h)。
