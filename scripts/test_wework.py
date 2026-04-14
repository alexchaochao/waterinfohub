import os
from waterinfohub.services.wework_notify import send_wework_message

if __name__ == '__main__':
    webhook = os.getenv('WEWORK_WEBHOOK_URL')
    if not webhook:
        print('WEWORK_WEBHOOK_URL not set, using example value for test.')
        webhook = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=bbbdc60a-0fce-4704-a0cb-68840c6a6944'
    ok = send_wework_message('Test message: WaterInfoHub webhook test', webhook)
    print('send result:', ok)
