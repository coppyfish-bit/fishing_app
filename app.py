from pyodide_http import patch_all
from js import Response

patch_all()

async def on_fetch(request, env):
    try:
        # 'DB' は先ほど設定したバインディング名です
        # 'catch_records' テーブルから最新の 10 件を取得します
        query = "SELECT * FROM catch_records ORDER BY id DESC LIMIT 10"
        result = await env.DB.prepare(query).all()
        
        # 取得したデータをテキスト形式で返して確認します
        return Response.new(f"接続成功！データ件数: {len(result.results)}\n内容: {result.results}")
    
    except Exception as e:
        return Response.new(f"エラーが発生しました: {str(e)}")
