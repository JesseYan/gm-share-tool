# gm-share-tool
share-tool: 
* weichat
* wechat_line
* weibo
* qq

wechat tool:

# rely on list:
```shell
six>=1.10.0
Django>=1.7.4
requests>=2.18.1
redis>=2.10.5
helios
gm-logging
gm-types
```

# update note:
add version after every change in `__init.py` 


# need config in django setting files
### redis:
```python
REDIS_CONFIG = {
    'host': '',
    'port': '',
    'db': '',
}
```

### weixin:
```python
WX_APP_ID = ''
WX_APP_SECRET = ''
```

### weibo:
```python
WEIBO_SHARE_HOST = ''
```
