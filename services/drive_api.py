"""Google Drive API連携モジュール - 選手写真のアップロード・管理"""

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# 写真保存先フォルダID
PHOTO_FOLDER_ID = '1rFwkADAV9l6GBEYmSgJrqCsSOg3pLbSK'

# 許可するMIMEタイプ
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}

# 最大ファイルサイズ (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


def get_drive_service():
    """Google Drive APIサービスを取得"""
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    return build('drive', 'v3', credentials=credentials)


def upload_photo(file_data, filename, mime_type, player_id):
    """
    写真をGoogle Driveにアップロード

    Args:
        file_data: ファイルのバイナリデータ
        filename: 元のファイル名
        mime_type: MIMEタイプ
        player_id: 選手ID（ファイル名に使用）

    Returns:
        dict: {'success': True, 'url': '...', 'file_id': '...'} または
              {'success': False, 'error': '...'}
    """
    # MIMEタイプチェック
    if mime_type not in ALLOWED_MIME_TYPES:
        return {
            'success': False,
            'error': f'許可されていないファイル形式です。JPEG, PNG, GIF, WebPのみ対応しています。'
        }

    # ファイルサイズチェック
    if len(file_data) > MAX_FILE_SIZE:
        return {
            'success': False,
            'error': f'ファイルサイズが大きすぎます。5MB以下にしてください。'
        }

    try:
        service = get_drive_service()

        # 拡張子を決定
        ext_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp'
        }
        ext = ext_map.get(mime_type, '.jpg')

        # ファイル名を player_id ベースに
        drive_filename = f'player_{player_id}{ext}'

        # 既存の同名ファイルを検索して削除（上書き用）
        existing = service.files().list(
            q=f"name contains 'player_{player_id}' and '{PHOTO_FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()

        for file in existing.get('files', []):
            service.files().delete(fileId=file['id']).execute()

        # ファイルメタデータ
        file_metadata = {
            'name': drive_filename,
            'parents': [PHOTO_FOLDER_ID]
        }

        # アップロード
        media = MediaIoBaseUpload(
            io.BytesIO(file_data),
            mimetype=mime_type,
            resumable=True
        )

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webContentLink, webViewLink'
        ).execute()

        file_id = file.get('id')

        # 公開URLを生成（リンクを知っている全員が閲覧可能な設定済み）
        # 直接表示用のURL形式
        photo_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w200"

        return {
            'success': True,
            'url': photo_url,
            'file_id': file_id
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'アップロードに失敗しました: {str(e)}'
        }


def delete_photo(file_id):
    """
    写真をGoogle Driveから削除

    Args:
        file_id: DriveのファイルID

    Returns:
        dict: {'success': True} または {'success': False, 'error': '...'}
    """
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        return {'success': True}
    except Exception as e:
        return {
            'success': False,
            'error': f'削除に失敗しました: {str(e)}'
        }


def get_photo_url_by_player_id(player_id):
    """
    選手IDから写真URLを取得

    Args:
        player_id: 選手ID

    Returns:
        str or None: 写真URL、見つからない場合はNone
    """
    try:
        service = get_drive_service()

        results = service.files().list(
            q=f"name contains 'player_{player_id}' and '{PHOTO_FOLDER_ID}' in parents and trashed=false",
            fields="files(id)"
        ).execute()

        files = results.get('files', [])
        if files:
            file_id = files[0]['id']
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w200"

        return None

    except Exception:
        return None
