import aiohttp
from aliyunsdkcore.auth.composer.rpc_signature_composer import get_signed_url

DEFAULT_REGION = 'cn-hangzhou'
FIXTURE = {
    DEFAULT_REGION: dict(host='dm.aliyuncs.com', version='2015-11-23'),
    'ap-southeast-1': dict(host='dm.ap-southeast-1.aliyuncs.com',
                           version='2017-06-22'),
    'ap-southeast-2': dict(host='dm.ap-southeast-2.aliyuncs.com',
                           version='2017-06-22'),
}


async def send_single(to_address, subject, text, html):
    region = DEFAULT_REGION
    fixture = FIXTURE[region]
    alias = 'PIE'
    account = ''
    ak_id = ''
    ak_secret = ''

    params = {
        'Version': fixture['version'],
        'RegionId': region,

        'Action': 'SingleSendMail',
        'AccountName': account,
        'ReplyToAddress': True,
        'AddressType': 0,
        'ToAddress': to_address,
        'FromAlias': alias,
        'Subject': subject,
        'HtmlBody': html,
        'TextBody': text,
    }
    url = 'https://' + fixture['host'] + get_signed_url(
        params, ak_id, ak_secret, 'JSON',
        'GET', {})
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.get(url) as resp:
            return await resp.json()
