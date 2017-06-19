# gm-share-tool
gm-share, wechat tool

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


# need config in django
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
WEIBO_CHECK_URL = ''
```
