from sanic import response

from ..services.aliyun.dm import send_single
from .api import bp
from .models import Token


@bp.route('/email')#, methods=['POST'])
async def email_login(request):
    email = request.args.get('email')
    async with request.app.engine.begin():
        token = await Token.new(email=email, action=Token.Actions.login)
    await send_single(email, '登录 PIE', '', f'''\
<html>
<body>
    <a href="{request.app.url_for('auth.token_login', token=token, _external=True)}">
        请点击登录
    </a>
</body>
</html>
''')
    return response.json(dict(success=True))
